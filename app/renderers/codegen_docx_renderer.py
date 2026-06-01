import json
import shutil
from pathlib import Path
from typing import Protocol

from app.core.config import Settings, get_settings
from app.llm.docx_codegen import DocxCodeGenerator, DocxCodegenResult
from app.renderers.base import RenderedArtifact
from app.renderers.docx_renderer import DocxRenderer
from app.schemas.artifact_plan import ArtifactPlan
from app.schemas.document_spec import DocumentSpec, document_spec_from_plan
from app.schemas.formats import ArtifactFormat
from app.schemas.generation_spec import GenerationSpec
from app.services.docx_sandbox import DocxSandboxRunner, SandboxResult
from app.services.docx_validator import DocxValidationResult, DocxValidator


class DocxCodeGeneratorProtocol(Protocol):
    def generate(self, document_spec: DocumentSpec) -> DocxCodegenResult:
        pass

    def repair(
        self,
        *,
        document_spec: DocumentSpec,
        previous_python_code: str,
        sandbox_result: dict | None = None,
        validation_errors: list[str] | None = None,
    ) -> DocxCodegenResult:
        pass


class DocxSandboxRunnerProtocol(Protocol):
    def run(self, *, input_dir: Path, output_dir: Path, code_filename: str) -> SandboxResult:
        pass


class DocxValidatorProtocol(Protocol):
    def validate(self, file_path: Path, document_spec: DocumentSpec) -> DocxValidationResult:
        pass


class CodegenDocxRenderer:
    output_format = ArtifactFormat.docx

    def __init__(
        self,
        settings: Settings | None = None,
        generator: DocxCodeGeneratorProtocol | None = None,
        sandbox: DocxSandboxRunnerProtocol | None = None,
        validator: DocxValidatorProtocol | None = None,
        fallback_renderer: DocxRenderer | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.generator = generator or DocxCodeGenerator(self.settings)
        self.sandbox = sandbox or DocxSandboxRunner(self.settings)
        self.validator = validator or DocxValidator()
        self.fallback_renderer = fallback_renderer or DocxRenderer(self.settings)

    def render(self, artifact_id: str, plan: ArtifactPlan | DocumentSpec) -> RenderedArtifact:
        document_spec = _ensure_document_spec(plan)

        if not self.settings.docx_codegen_enabled:
            return self._fallback(
                artifact_id,
                document_spec,
                "DOCX codegen is disabled; fallback renderer was used.",
            )

        work_dir = (self.settings.artifact_storage_path / "codegen" / artifact_id).resolve()
        input_dir = work_dir / "input"
        output_dir = work_dir / "output"
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        document_spec_path = input_dir / "document_spec.json"
        document_spec_path.write_text(
            json.dumps(
                {"document_spec": document_spec.model_dump(mode="json")},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        try:
            return self._render_with_codegen_attempts(
                artifact_id=artifact_id,
                document_spec=document_spec,
                work_dir=work_dir,
                input_dir=input_dir,
                output_dir=output_dir,
            )
        except Exception as exc:
            return self._fallback(
                artifact_id,
                document_spec,
                f"DOCX codegen failed; fallback renderer was used. Reason: {exc}",
                work_dir,
            )

    def _render_with_codegen_attempts(
        self,
        *,
        artifact_id: str,
        document_spec: DocumentSpec,
        work_dir: Path,
        input_dir: Path,
        output_dir: Path,
    ) -> RenderedArtifact:
        repair_attempts = self.settings.docx_codegen_repair_attempts
        total_attempts = repair_attempts + 1
        attempt_diagnostics: list[dict] = []
        warnings: list[str] = []
        codegen_result = self.generator.generate(document_spec)

        for attempt_number in range(1, total_attempts + 1):
            paths = _attempt_paths(work_dir, input_dir, attempt_number)
            _write_codegen_attempt(paths, codegen_result)
            warnings.extend(codegen_result.warnings)

            sandbox_result = self.sandbox.run(
                input_dir=input_dir,
                output_dir=output_dir,
                code_filename=paths["code"].name,
            )
            _write_sandbox_result(paths, sandbox_result)

            attempt_info = {
                "attempt": attempt_number,
                "code_path": str(paths["code"]),
                "sandbox_result_path": str(paths["sandbox_result"]),
                "validation_result_path": None,
                "sandbox_succeeded": sandbox_result.succeeded,
                "validation_succeeded": None,
            }
            attempt_diagnostics.append(attempt_info)

            if not sandbox_result.succeeded:
                if attempt_number <= repair_attempts:
                    warnings.append(f"DOCX codegen repair attempt {attempt_number} was used after sandbox failure.")
                    codegen_result = self.generator.repair(
                        document_spec=document_spec,
                        previous_python_code=codegen_result.python_code,
                        sandbox_result=sandbox_result.model_dump(),
                        validation_errors=[],
                    )
                    continue

                message = _sandbox_failure_message(sandbox_result, attempt_number)
                return self._fallback(artifact_id, document_spec, message, work_dir)

            validation_result = self._validate_docx(paths, sandbox_result, document_spec)
            if validation_result is not None:
                attempt_info["validation_result_path"] = str(paths["validation_result"])
                attempt_info["validation_succeeded"] = validation_result.valid
                warnings.extend(validation_result.warnings)

                if not validation_result.valid:
                    if attempt_number <= repair_attempts:
                        warnings.append(
                            f"DOCX codegen repair attempt {attempt_number} was used after validation failure."
                        )
                        codegen_result = self.generator.repair(
                            document_spec=document_spec,
                            previous_python_code=codegen_result.python_code,
                            sandbox_result=sandbox_result.model_dump(),
                            validation_errors=validation_result.errors,
                        )
                        continue

                    message = _validation_failure_message(validation_result, attempt_number)
                    return self._fallback(artifact_id, document_spec, message, work_dir)

            file_name = f"{artifact_id}.docx"
            file_path = (self.settings.artifact_storage_path / file_name).resolve()
            shutil.copy2(sandbox_result.output_path, file_path)
            return RenderedArtifact(
                file_name=file_name,
                file_path=file_path,
                file_size=file_path.stat().st_size,
                warnings=warnings,
                diagnostics={
                    "renderer": "codegen_docx",
                    "codegen_work_dir": str(work_dir),
                    "generated_code_path": str(paths["code"]),
                    "sandbox_result_path": str(paths["sandbox_result"]),
                    "attempts": attempt_diagnostics,
                },
            )

        return self._fallback(
            artifact_id,
            document_spec,
            "DOCX codegen exhausted all attempts; fallback renderer was used.",
            work_dir,
        )

    def _validate_docx(
        self,
        paths: dict[str, Path],
        sandbox_result: SandboxResult,
        document_spec: DocumentSpec,
    ) -> DocxValidationResult | None:
        if not self.settings.docx_validation_enabled:
            return None

        validation_result = self.validator.validate(sandbox_result.output_path, document_spec)
        paths["validation_result"].write_text(
            json.dumps(validation_result.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return validation_result

    def _fallback(
        self,
        artifact_id: str,
        document_spec: DocumentSpec,
        warning: str,
        work_dir: Path | None = None,
    ) -> RenderedArtifact:
        if not self.settings.docx_codegen_fallback_enabled:
            raise RuntimeError(warning)

        rendered = self.fallback_renderer.render(artifact_id, document_spec)
        return RenderedArtifact(
            file_name=rendered.file_name,
            file_path=rendered.file_path,
            file_size=rendered.file_size,
            warnings=[warning, *rendered.warnings],
            diagnostics={
                **rendered.diagnostics,
                "renderer": "fallback_docx",
                "codegen_work_dir": str(work_dir) if work_dir is not None else None,
            },
        )


def _attempt_paths(work_dir: Path, input_dir: Path, attempt_number: int) -> dict[str, Path]:
    if attempt_number == 1:
        prefix = ""
        code_name = "generated_code.py"
    else:
        repair_number = attempt_number - 1
        prefix = f"repair_{repair_number}_"
        code_name = f"{prefix}generated_code.py"

    return {
        "code": input_dir / code_name,
        "response": work_dir / f"{prefix}codegen_response.json",
        "sandbox_result": work_dir / f"{prefix}sandbox_result.json",
        "stdout": work_dir / f"{prefix}stdout.txt",
        "stderr": work_dir / f"{prefix}stderr.txt",
        "validation_result": work_dir / f"{prefix}validation_result.json",
    }


def _write_codegen_attempt(paths: dict[str, Path], codegen_result: DocxCodegenResult) -> None:
    paths["code"].write_text(codegen_result.python_code, encoding="utf-8")
    paths["response"].write_text(
        json.dumps(
            {
                "warnings": codegen_result.warnings,
                "raw_output": codegen_result.raw_output,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_sandbox_result(paths: dict[str, Path], sandbox_result: SandboxResult) -> None:
    paths["stdout"].write_text(sandbox_result.stdout, encoding="utf-8")
    paths["stderr"].write_text(sandbox_result.stderr, encoding="utf-8")
    paths["sandbox_result"].write_text(
        json.dumps(sandbox_result.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _ensure_document_spec(plan: ArtifactPlan | DocumentSpec) -> DocumentSpec:
    if isinstance(plan, DocumentSpec):
        return plan
    generation_spec = GenerationSpec(
        output_format=plan.output_format,
        title=plan.title,
        formatting=plan.formatting,
    )
    return document_spec_from_plan(generation_spec, plan)


def _sandbox_failure_message(result: SandboxResult, attempts: int) -> str:
    if result.timed_out:
        return (
            "DOCX codegen sandbox timed out after "
            f"{attempts} attempt(s); fallback renderer was used."
        )
    return (
        "DOCX codegen sandbox failed after "
        f"{attempts} attempt(s); fallback renderer was used. Last exit code: {result.exit_code}."
    )


def _validation_failure_message(result: DocxValidationResult, attempts: int) -> str:
    details = "; ".join(result.errors) or "unknown validation error"
    return (
        "DOCX validation failed after "
        f"{attempts} attempt(s); fallback renderer was used. Reason: {details}"
    )

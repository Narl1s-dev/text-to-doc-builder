import json
import shutil
from pathlib import Path
from typing import Protocol

from app.core.config import Settings, get_settings
from app.llm.docx_codegen import DocxCodeGenerator
from app.renderers.base import RenderedArtifact
from app.renderers.docx_renderer import DocxRenderer
from app.schemas.artifact_plan import ArtifactPlan
from app.schemas.document_spec import DocumentSpec, document_spec_from_plan
from app.schemas.formats import ArtifactFormat
from app.schemas.generation_spec import GenerationSpec
from app.services.docx_sandbox import DocxSandboxRunner, SandboxResult


class DocxCodeGeneratorProtocol(Protocol):
    def generate(self, document_spec: DocumentSpec):
        pass


class DocxSandboxRunnerProtocol(Protocol):
    def run(self, *, input_dir: Path, output_dir: Path, code_filename: str) -> SandboxResult:
        pass


class CodegenDocxRenderer:
    output_format = ArtifactFormat.docx

    def __init__(
        self,
        settings: Settings | None = None,
        generator: DocxCodeGeneratorProtocol | None = None,
        sandbox: DocxSandboxRunnerProtocol | None = None,
        fallback_renderer: DocxRenderer | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.generator = generator or DocxCodeGenerator(self.settings)
        self.sandbox = sandbox or DocxSandboxRunner(self.settings)
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
        generated_code_path = input_dir / "generated_code.py"
        response_path = work_dir / "codegen_response.json"
        sandbox_result_path = work_dir / "sandbox_result.json"
        stdout_path = work_dir / "stdout.txt"
        stderr_path = work_dir / "stderr.txt"

        document_spec_path.write_text(
            json.dumps(
                {"document_spec": document_spec.model_dump(mode="json")},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        try:
            codegen_result = self.generator.generate(document_spec)
            generated_code_path.write_text(codegen_result.python_code, encoding="utf-8")
            response_path.write_text(
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

            sandbox_result = self.sandbox.run(
                input_dir=input_dir,
                output_dir=output_dir,
                code_filename=generated_code_path.name,
            )
            stdout_path.write_text(sandbox_result.stdout, encoding="utf-8")
            stderr_path.write_text(sandbox_result.stderr, encoding="utf-8")
            sandbox_result_path.write_text(
                json.dumps(sandbox_result.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            if not sandbox_result.succeeded:
                message = _sandbox_failure_message(sandbox_result)
                return self._fallback(artifact_id, document_spec, message, work_dir)

            file_name = f"{artifact_id}.docx"
            file_path = (self.settings.artifact_storage_path / file_name).resolve()
            shutil.copy2(sandbox_result.output_path, file_path)
            return RenderedArtifact(
                file_name=file_name,
                file_path=file_path,
                file_size=file_path.stat().st_size,
                warnings=codegen_result.warnings,
                diagnostics={
                    "renderer": "codegen_docx",
                    "codegen_work_dir": str(work_dir),
                    "generated_code_path": str(generated_code_path),
                    "sandbox_result_path": str(sandbox_result_path),
                },
            )
        except Exception as exc:
            return self._fallback(
                artifact_id,
                document_spec,
                f"DOCX codegen failed; fallback renderer was used. Reason: {exc}",
                work_dir,
            )

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


def _ensure_document_spec(plan: ArtifactPlan | DocumentSpec) -> DocumentSpec:
    if isinstance(plan, DocumentSpec):
        return plan
    generation_spec = GenerationSpec(
        output_format=plan.output_format,
        title=plan.title,
        formatting=plan.formatting,
    )
    return document_spec_from_plan(generation_spec, plan)


def _sandbox_failure_message(result: SandboxResult) -> str:
    if result.timed_out:
        return "DOCX codegen sandbox timed out; fallback renderer was used."
    return (
        "DOCX codegen sandbox failed; fallback renderer was used. "
        f"Exit code: {result.exit_code}."
    )

from dataclasses import dataclass
import io
from pathlib import Path
import tarfile
from typing import Any

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class SandboxResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    output_path: Path

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and self.output_path.exists()

    def model_dump(self) -> dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timed_out": self.timed_out,
            "output_path": str(self.output_path),
            "succeeded": self.succeeded,
        }


class SandboxUnavailableError(Exception):
    """Raised when Docker sandbox execution is unavailable."""


class DocxSandboxRunner:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def run(self, *, input_dir: Path, output_dir: Path, code_filename: str) -> SandboxResult:
        try:
            import docker
            from docker.errors import DockerException
            from requests.exceptions import ReadTimeout
        except ImportError as exc:
            raise SandboxUnavailableError("Docker SDK is not installed.") from exc

        input_dir = input_dir.resolve()
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        result_path = output_dir / "result.docx"

        try:
            client = docker.from_env()
            container = client.containers.create(
                image=self.settings.docx_codegen_image,
                command=["python", f"/input/{code_filename}"],
                network_disabled=True,
                environment={},
                mem_limit=self.settings.docx_codegen_memory_limit,
                nano_cpus=int(self.settings.docx_codegen_cpu_limit * 1_000_000_000),
                working_dir="/workspace",
            )
            container.put_archive("/input", _make_input_archive(input_dir))
            container.start()
        except DockerException as exc:
            raise SandboxUnavailableError(f"Docker sandbox could not start: {exc}") from exc

        timed_out = False
        exit_code: int | None = None
        try:
            try:
                wait_result = container.wait(timeout=self.settings.docx_codegen_timeout_seconds)
                exit_code = wait_result.get("StatusCode")
            except ReadTimeout:
                timed_out = True
                container.kill()

            stdout = _decode_logs(container.logs(stdout=True, stderr=False))
            stderr = _decode_logs(container.logs(stdout=False, stderr=True))
            if exit_code == 0 and not timed_out:
                _copy_container_file(container, "/output/result.docx", result_path)
        finally:
            container.remove(force=True)

        return SandboxResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            timed_out=timed_out,
            output_path=result_path,
        )


def _decode_logs(value: bytes | str) -> str:
    if isinstance(value, str):
        return value
    return value.decode("utf-8", errors="replace")


def _make_input_archive(input_dir: Path) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for path in input_dir.iterdir():
            if path.is_file():
                archive.add(path, arcname=path.name)
    buffer.seek(0)
    return buffer.read()


def _copy_container_file(container, container_path: str, target_path: Path) -> None:
    chunks, _ = container.get_archive(container_path)
    buffer = io.BytesIO()
    for chunk in chunks:
        buffer.write(chunk)
    buffer.seek(0)

    with tarfile.open(fileobj=buffer, mode="r") as archive:
        member = archive.next()
        if member is None:
            return
        extracted = archive.extractfile(member)
        if extracted is None:
            return
        target_path.write_bytes(extracted.read())

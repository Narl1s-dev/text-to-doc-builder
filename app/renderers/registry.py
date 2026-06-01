from app.core.errors import AppError
from app.renderers.base import BaseRenderer
from app.renderers.codegen_docx_renderer import CodegenDocxRenderer
from app.schemas.formats import ArtifactFormat, normalize_artifact_format


class UnsupportedRendererError(AppError):
    pass


class RendererRegistry:
    def __init__(self, renderers: list[BaseRenderer] | None = None) -> None:
        configured_renderers = renderers or [CodegenDocxRenderer()]
        self._renderers = {renderer.output_format: renderer for renderer in configured_renderers}

    def get(self, output_format: ArtifactFormat | str) -> BaseRenderer:
        try:
            normalized_format = normalize_artifact_format(output_format)
        except ValueError as exc:
            raise UnsupportedRendererError(str(exc)) from exc

        renderer = self._renderers.get(normalized_format)
        if renderer is None:
            raise UnsupportedRendererError(f"Renderer for '{normalized_format.value}' is not configured.")
        return renderer

    def supported_formats(self) -> tuple[ArtifactFormat, ...]:
        return tuple(sorted(self._renderers.keys(), key=lambda item: item.value))

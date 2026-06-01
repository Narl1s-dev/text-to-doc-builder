from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings
from app.schemas.artifact_plan import ArtifactBlock, ArtifactPlan
from app.schemas.document import DocumentCreateRequest
from app.schemas.document_spec import DocumentSpec, document_spec_from_plan
from app.schemas.formats import (
    DEFAULT_OUTPUT_FORMAT,
    infer_artifact_format_from_prompt,
    is_render_supported,
)
from app.schemas.generation_spec import FormattingSpec, GenerationSpec


class DefaultsResolver:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def default_formatting(self) -> FormattingSpec:
        return FormattingSpec(
            font_family=self.settings.default_font_family,
            font_size=self.settings.default_font_size,
        )

    def resolve_generation_spec(
        self,
        payload: DocumentCreateRequest,
        parsed_spec: GenerationSpec | dict[str, Any] | None = None,
    ) -> tuple[GenerationSpec, list[str]]:
        data = self._base_generation_spec_data(payload)
        if parsed_spec:
            data.update(_to_dict(parsed_spec))
        data.update(payload.overrides)

        warnings: list[str] = []
        if not data.get("title"):
            data["title"] = "Документ"
            warnings.append("Title was not provided; default title was used.")

        data["output_format"] = self._resolve_requested_format(payload, data.get("output_format"))

        data["formatting"] = self._merge_formatting(data.get("formatting"))
        return GenerationSpec.model_validate(data), warnings

    def resolve_artifact_plan(
        self,
        spec: GenerationSpec,
        payload: DocumentCreateRequest,
        parsed_plan: ArtifactPlan | dict[str, Any] | None = None,
    ) -> tuple[ArtifactPlan, list[str]]:
        data = {
            "artifact_type": "document",
            "output_format": spec.output_format,
            "title": spec.title,
            "formatting": spec.formatting.model_dump(mode="json"),
            "blocks": [],
        }
        if parsed_plan:
            data.update(_to_dict(parsed_plan))

        warnings: list[str] = []
        data["output_format"] = spec.output_format
        data["title"] = data.get("title") or spec.title or "Документ"
        data["formatting"] = self._merge_formatting(data.get("formatting"))

        if not data.get("blocks"):
            data["blocks"] = self._fallback_blocks(data["title"], payload.prompt)
            warnings.append("Artifact plan had no blocks; fallback blocks were created.")

        return ArtifactPlan.model_validate(data), warnings

    def fallback_plan(self, payload: DocumentCreateRequest) -> LLMPlanningFallback:
        spec, spec_warnings = self.resolve_generation_spec(payload)
        plan, plan_warnings = self.resolve_artifact_plan(spec, payload)
        document_spec, document_spec_warnings = self.resolve_document_spec(spec, plan)
        return LLMPlanningFallback(
            spec,
            document_spec,
            plan,
            spec_warnings + plan_warnings + document_spec_warnings,
        )

    def resolve_document_spec(
        self,
        spec: GenerationSpec,
        artifact_plan: ArtifactPlan,
        parsed_document_spec: DocumentSpec | dict[str, Any] | None = None,
    ) -> tuple[DocumentSpec, list[str]]:
        if parsed_document_spec:
            data = _to_dict(parsed_document_spec)
            data["output_format"] = artifact_plan.output_format
            data["title"] = data.get("title") or artifact_plan.title or spec.title
            data["document_type"] = data.get("document_type") or spec.document_type
            data["language"] = data.get("language") or spec.language
            data["audience"] = data.get("audience") or spec.audience
            data["tone"] = data.get("tone") or spec.tone
            data["style"] = data.get("style") or spec.style
            data["formatting"] = self._merge_formatting(data.get("formatting"))
            data["source_facts"] = data.get("source_facts") or spec.source_facts

            content = data.get("content_markdown")
            if isinstance(content, str) and content.strip():
                return DocumentSpec.model_validate(data), []

        return document_spec_from_plan(spec, artifact_plan), [
            "Document spec content_markdown was derived from artifact_plan blocks."
        ]

    def _base_generation_spec_data(self, payload: DocumentCreateRequest) -> dict[str, Any]:
        return {
            "output_format": payload.output_format,
            "document_type": "general_document",
            "title": payload.overrides.get("title", "Документ"),
            "language": self.settings.default_language,
            "audience": "general",
            "tone": self.settings.default_tone,
            "style": self.settings.default_style,
            "formatting": self.default_formatting().model_dump(mode="json"),
        }

    def _resolve_requested_format(self, payload: DocumentCreateRequest, parsed_format) -> object:
        if payload.output_format is not None:
            return payload.output_format
        inferred_format = infer_artifact_format_from_prompt(payload.prompt)
        if inferred_format is not None:
            return inferred_format
        return parsed_format or DEFAULT_OUTPUT_FORMAT

    def _merge_formatting(self, value: Any) -> dict[str, Any]:
        base = self.default_formatting().model_dump(mode="json")
        if isinstance(value, FormattingSpec):
            base.update(value.model_dump(mode="json", exclude_none=True))
        elif isinstance(value, dict):
            base.update(value)
        return base

    def _fallback_blocks(self, title: str, prompt: str) -> list[dict[str, Any]]:
        return [
            ArtifactBlock(type="heading", level=1, text=title).model_dump(mode="json"),
            ArtifactBlock(type="paragraph", text=prompt).model_dump(mode="json"),
        ]


@dataclass(frozen=True)
class LLMPlanningFallback:
    generation_spec: GenerationSpec
    document_spec: DocumentSpec
    artifact_plan: ArtifactPlan
    warnings: list[str]


def _to_dict(value: GenerationSpec | DocumentSpec | ArtifactPlan | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return value.model_dump(mode="json", exclude_none=True)

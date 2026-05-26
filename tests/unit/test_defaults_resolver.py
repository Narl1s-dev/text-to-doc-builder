from app.core.config import Settings
from app.schemas.formats import ArtifactFormat
from app.schemas.document import DocumentCreateRequest
from app.services.defaults_resolver import DefaultsResolver


def test_defaults_resolver_applies_base_values() -> None:
    resolver = DefaultsResolver(Settings())
    payload = DocumentCreateRequest(prompt="Сделай документ")

    fallback = resolver.fallback_plan(payload)

    assert fallback.generation_spec.output_format == "docx"
    assert fallback.generation_spec.language == "ru"
    assert fallback.generation_spec.style == "business"
    assert fallback.generation_spec.formatting.font_family == "Times New Roman"
    assert fallback.artifact_plan.title == "Документ"
    assert fallback.artifact_plan.blocks[0].type == "heading"


def test_defaults_resolver_normalizes_unsupported_output_format_from_llm() -> None:
    resolver = DefaultsResolver(Settings())
    payload = DocumentCreateRequest(prompt="Сделай презентацию")

    spec, warnings = resolver.resolve_generation_spec(
        payload,
        {"output_format": "pptx", "title": "Презентация"},
    )

    assert spec.output_format == ArtifactFormat.pptx
    assert warnings == []


def test_defaults_resolver_infers_future_format_from_prompt() -> None:
    resolver = DefaultsResolver(Settings())
    payload = DocumentCreateRequest(prompt="Сделай презентацию о выцветании кораллов")

    fallback = resolver.fallback_plan(payload)

    assert fallback.generation_spec.output_format == ArtifactFormat.pptx
    assert fallback.artifact_plan.output_format == ArtifactFormat.pptx


def test_defaults_resolver_prompt_format_beats_llm_default_docx() -> None:
    resolver = DefaultsResolver(Settings())
    payload = DocumentCreateRequest(prompt="Сделай презентацию")

    spec, warnings = resolver.resolve_generation_spec(
        payload,
        {"output_format": "docx", "title": "Презентация"},
    )
    plan, _ = resolver.resolve_artifact_plan(
        spec,
        payload,
        {"output_format": "docx", "title": "Презентация"},
    )

    assert spec.output_format == ArtifactFormat.pptx
    assert plan.output_format == ArtifactFormat.pptx
    assert warnings == []

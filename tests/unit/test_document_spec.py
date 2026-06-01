import pytest
from pydantic import ValidationError

from app.schemas.artifact_plan import ArtifactBlock, ArtifactPlan
from app.schemas.document_spec import DocumentSpec, document_spec_from_plan
from app.schemas.generation_spec import GenerationSpec


def test_document_spec_requires_content_markdown() -> None:
    with pytest.raises(ValidationError):
        DocumentSpec(title="Документ", content_markdown="   ")


def test_document_spec_can_be_derived_from_artifact_plan_blocks() -> None:
    generation_spec = GenerationSpec(title="Итоги встречи", source_facts=["Факт 1"])
    artifact_plan = ArtifactPlan(
        title="Итоги встречи",
        blocks=[
            ArtifactBlock(type="heading", level=1, text="Итоги встречи"),
            ArtifactBlock(type="paragraph", text="Обсудили план запуска."),
            ArtifactBlock(type="bullet_list", items=["Подготовить документ", "Согласовать сроки"]),
            ArtifactBlock(type="table", rows=[["Роль", "Ответственный"], ["Документ", "Анна"]]),
        ],
    )

    document_spec = document_spec_from_plan(generation_spec, artifact_plan)

    assert document_spec.schema_version == "document_spec.v1"
    assert document_spec.title == "Итоги встречи"
    assert document_spec.source_facts == ["Факт 1"]
    assert "# Итоги встречи" in document_spec.content_markdown
    assert "- Подготовить документ" in document_spec.content_markdown
    assert "| Роль | Ответственный |" in document_spec.content_markdown

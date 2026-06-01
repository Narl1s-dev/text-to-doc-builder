import pytest

from app.llm.response_validator import LLMResponseValidationError, LLMResponseValidator


def test_llm_response_validator_parses_planning_json() -> None:
    validator = LLMResponseValidator()

    result = validator.parse_planning_response(
        """
        {
          "generation_spec": {
            "output_format": "docx",
            "title": "Итоги встречи"
          },
          "document_spec": {
            "schema_version": "document_spec.v1",
            "output_format": "docx",
            "title": "Итоги встречи",
            "content_markdown": "# Итоги встречи\\n\\nКраткое резюме."
          },
          "artifact_plan": {
            "artifact_type": "document",
            "output_format": "docx",
            "title": "Итоги встречи",
            "blocks": [
              {"type": "heading", "level": 1, "text": "Итоги встречи"}
            ]
          },
          "warnings": []
        }
        """
    )

    assert result.generation_spec.title == "Итоги встречи"
    assert result.document_spec is not None
    assert result.document_spec.content_markdown.startswith("# Итоги встречи")
    assert result.artifact_plan.blocks[0].type == "heading"


def test_llm_response_validator_rejects_invalid_json() -> None:
    validator = LLMResponseValidator()

    with pytest.raises(LLMResponseValidationError) as exc_info:
        validator.parse_planning_response("not json")

    assert exc_info.value.raw_output == "not json"


def test_llm_response_validator_normalizes_loose_llm_shapes() -> None:
    validator = LLMResponseValidator()

    result = validator.parse_planning_response(
        """
        {
          "generation_spec": {
            "output_format": "docx",
            "title": "Краткий отчет",
            "length": "short",
            "constraints": ["выводы", "следующие шаги"],
            "structure": ["heading", "paragraph", "bullet_list"]
          },
          "artifact_plan": {
            "artifact_type": "document",
            "output_format": "docx",
            "title": "Краткий отчет",
            "blocks": [
              {"type": "heading", "text": "Краткий отчет"},
              {"type": "bullet_list", "items": "Следующий шаг"}
            ]
          },
          "warnings": []
        }
        """
    )

    assert result.generation_spec.length.mode == "short"
    assert result.generation_spec.constraints == {"must_include": ["выводы", "следующие шаги"]}
    assert result.generation_spec.structure.sections == ["heading", "paragraph", "bullet_list"]
    assert result.artifact_plan.blocks[0].level == 1
    assert result.artifact_plan.blocks[1].items == ["Следующий шаг"]


def test_llm_response_validator_normalizes_string_fields_from_llm() -> None:
    validator = LLMResponseValidator()

    result = validator.parse_planning_response(
        """
        {
          "generation_spec": {
            "output_format": "docx",
            "title": "Выцветание кораллов",
            "source_facts": "Выцветание кораллов связано с повышением температуры воды.",
            "constraints": "Использовать понятный научно-популярный стиль.",
            "formatting": "A4 portrait, Times New Roman 12",
            "structure": "Введение, причины, последствия, заключение"
          },
          "artifact_plan": {
            "artifact_type": "document",
            "output_format": "docx",
            "title": "Выцветание кораллов",
            "blocks": [
              {"type": "heading", "text": "Выцветание кораллов"},
              {"type": "paragraph", "text": "Кораллы выцветают из-за стресса."}
            ]
          },
          "warnings": []
        }
        """
    )

    assert result.generation_spec.source_facts == [
        "Выцветание кораллов связано с повышением температуры воды."
    ]
    assert result.generation_spec.constraints == {
        "description": "Использовать понятный научно-популярный стиль."
    }
    assert result.generation_spec.formatting.page_size == "A4"
    assert result.generation_spec.structure.sections == [
        "Введение",
        "причины",
        "последствия",
        "заключение",
    ]


def test_llm_response_validator_uses_default_margins_for_human_default_value() -> None:
    validator = LLMResponseValidator()

    result = validator.parse_planning_response(
        """
        {
          "generation_spec": {
            "output_format": "docx",
            "title": "Coral Bleaching",
            "formatting": {
              "page_size": "A4",
              "font": "Times New Roman",
              "font_size": 12,
              "margins": "default"
            }
          },
          "artifact_plan": {
            "artifact_type": "document",
            "output_format": "docx",
            "title": "Coral Bleaching",
            "formatting": {
              "margins": "default"
            },
            "blocks": [
              {"type": "heading", "text": "Coral Bleaching"}
            ]
          },
          "warnings": []
        }
        """
    )

    assert result.generation_spec.formatting.font_family == "Times New Roman"
    assert result.generation_spec.formatting.margins.top_cm == 2
    assert result.artifact_plan.formatting.margins.left_cm == 3


def test_llm_response_validator_repairs_missing_formats_and_schema_version() -> None:
    validator = LLMResponseValidator()

    result = validator.parse_planning_response(
        """
        {
          "generation_spec": {
            "output_format": null,
            "title": "Coral Bleaching Essay"
          },
          "document_spec": {
            "schema_version": "1.0",
            "output_format": null,
            "title": "Coral Bleaching Essay",
            "content_markdown": "# Coral Bleaching Essay\\n\\nCoral bleaching is a major ocean health issue."
          },
          "artifact_plan": {
            "artifact_type": "document",
            "output_format": null,
            "title": "Coral Bleaching Essay",
            "blocks": [
              {"type": "heading", "text": "Coral Bleaching Essay"}
            ]
          },
          "warnings": []
        }
        """
    )

    assert result.generation_spec.output_format == "docx"
    assert result.document_spec is not None
    assert result.document_spec.schema_version == "document_spec.v1"
    assert result.document_spec.output_format == "docx"
    assert result.artifact_plan.output_format == "docx"

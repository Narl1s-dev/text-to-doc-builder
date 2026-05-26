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
    assert result.artifact_plan.blocks[0].type == "heading"


def test_llm_response_validator_rejects_invalid_json() -> None:
    validator = LLMResponseValidator()

    with pytest.raises(LLMResponseValidationError):
        validator.parse_planning_response("not json")


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

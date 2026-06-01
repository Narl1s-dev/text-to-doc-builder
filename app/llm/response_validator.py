import json
import re
from typing import Any

from pydantic import ValidationError

from app.llm.schemas import LLMPlanningResponse


class LLMResponseValidationError(Exception):
    """Raised when an LLM response cannot be parsed into the expected schema."""

    def __init__(self, message: str, raw_output: str | None = None) -> None:
        super().__init__(message)
        self.raw_output = raw_output


class LLMResponseValidator:
    def parse_planning_response(self, raw_output: str) -> LLMPlanningResponse:
        cleaned = _strip_markdown_fence(raw_output)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMResponseValidationError(
                f"LLM response is not valid JSON: {exc}",
                raw_output=raw_output,
            ) from exc

        payload = _normalize_planning_payload(payload)
        try:
            return LLMPlanningResponse.model_validate(payload)
        except ValidationError as exc:
            raise LLMResponseValidationError(
                f"LLM response did not match planning schema: {exc}",
                raw_output=raw_output,
            ) from exc


def _strip_markdown_fence(value: str) -> str:
    text = value.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return text


def _normalize_planning_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload

    generation_spec = payload.get("generation_spec")
    if isinstance(generation_spec, dict):
        if generation_spec.get("output_format") is None:
            generation_spec["output_format"] = "docx"

        source_facts = generation_spec.get("source_facts")
        if isinstance(source_facts, str):
            generation_spec["source_facts"] = [source_facts]

        length = generation_spec.get("length")
        if isinstance(length, str):
            generation_spec["length"] = {"mode": length}

        constraints = generation_spec.get("constraints")
        if isinstance(constraints, list):
            generation_spec["constraints"] = {"must_include": constraints}
        elif isinstance(constraints, str):
            generation_spec["constraints"] = {"description": constraints}

        formatting = generation_spec.get("formatting")
        generation_spec["formatting"] = _normalize_formatting(formatting)

        structure = generation_spec.get("structure")
        if isinstance(structure, list):
            generation_spec["structure"] = {"sections": structure}
        elif isinstance(structure, str):
            generation_spec["structure"] = {"sections": _split_human_list(structure)}

    artifact_plan = payload.get("artifact_plan")
    if isinstance(artifact_plan, dict):
        if artifact_plan.get("output_format") is None:
            artifact_plan["output_format"] = "docx"

        artifact_plan["formatting"] = _normalize_formatting(artifact_plan.get("formatting"))

        blocks = artifact_plan.get("blocks")
        if isinstance(blocks, list):
            artifact_plan["blocks"] = [_normalize_block(block) for block in blocks]

    document_spec = payload.get("document_spec")
    if isinstance(document_spec, dict):
        if document_spec.get("schema_version") != "document_spec.v1":
            document_spec["schema_version"] = "document_spec.v1"

        if document_spec.get("output_format") is None:
            document_spec["output_format"] = "docx"

        document_spec["formatting"] = _normalize_formatting(document_spec.get("formatting"))

        source_facts = document_spec.get("source_facts")
        if isinstance(source_facts, str):
            document_spec["source_facts"] = [source_facts]

        content_markdown = document_spec.get("content_markdown")
        if isinstance(content_markdown, list):
            document_spec["content_markdown"] = "\n\n".join(
                str(item).strip() for item in content_markdown if str(item).strip()
            )

    return payload


def _normalize_formatting(formatting: Any) -> dict[str, Any]:
    if isinstance(formatting, str):
        return {"description": formatting}
    if not isinstance(formatting, dict):
        return {}

    normalized = dict(formatting)
    if "font" in normalized and "font_family" not in normalized:
        normalized["font_family"] = normalized.pop("font")

    margins = normalized.get("margins")
    if isinstance(margins, str):
        normalized.pop("margins")

    return normalized


def _normalize_block(block: Any) -> Any:
    if not isinstance(block, dict):
        return block

    block_type = block.get("type")
    if block_type in {"bullet_list", "numbered_list"} and isinstance(block.get("items"), str):
        block["items"] = [block["items"]]

    if block_type == "heading" and block.get("level") is None:
        block["level"] = 1

    return block


def _split_human_list(value: str) -> list[str]:
    items = [item.strip(" .;") for item in re.split(r"[,;\n]", value)]
    return [item for item in items if item]

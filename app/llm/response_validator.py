import json
import re
from typing import Any

from pydantic import ValidationError

from app.llm.schemas import LLMPlanningResponse


class LLMResponseValidationError(Exception):
    """Raised when an LLM response cannot be parsed into the expected schema."""


class LLMResponseValidator:
    def parse_planning_response(self, raw_output: str) -> LLMPlanningResponse:
        cleaned = _strip_markdown_fence(raw_output)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMResponseValidationError(f"LLM response is not valid JSON: {exc}") from exc

        payload = _normalize_planning_payload(payload)
        try:
            return LLMPlanningResponse.model_validate(payload)
        except ValidationError as exc:
            raise LLMResponseValidationError(f"LLM response did not match planning schema: {exc}") from exc


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
        if isinstance(formatting, str):
            generation_spec["formatting"] = {"description": formatting}

        structure = generation_spec.get("structure")
        if isinstance(structure, list):
            generation_spec["structure"] = {"sections": structure}
        elif isinstance(structure, str):
            generation_spec["structure"] = {"sections": _split_human_list(structure)}

    artifact_plan = payload.get("artifact_plan")
    if isinstance(artifact_plan, dict):
        blocks = artifact_plan.get("blocks")
        if isinstance(blocks, list):
            artifact_plan["blocks"] = [_normalize_block(block) for block in blocks]

    return payload


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

import json

from app.schemas.document import DocumentCreateRequest


class PromptBuilder:
    prompt_version = "generation-planning-v1"

    def build_planning_messages(self, payload: DocumentCreateRequest) -> list[dict[str, str]]:
        system_prompt = """
You are a document generation planner.
Return only valid JSON, without markdown fences or explanations.
The JSON must contain exactly these top-level keys:
- generation_spec
- artifact_plan
- warnings

The service prototype can render only docx now. If the user asks for another format,
record that in warnings and normalize output_format to "docx".

generation_spec fields:
output_format, document_type, title, language, audience, tone, style, length,
source_facts, constraints, formatting, structure.

artifact_plan fields:
artifact_type, output_format, title, blocks, formatting, metadata.

Supported artifact_plan block types:
- heading: { "type": "heading", "level": 1, "text": "..." }
- paragraph: { "type": "paragraph", "text": "..." }
- bullet_list: { "type": "bullet_list", "items": ["..."] }
- numbered_list: { "type": "numbered_list", "items": ["..."] }
- table: { "type": "table", "rows": [["Header 1", "Header 2"], ["Cell", "Cell"]] }

Use defaults when the user does not specify details:
language "ru", style "business", tone "neutral", title "Документ",
A4 portrait, Times New Roman 12, line spacing 1.15.
Preserve user facts. Do not invent critical facts.
""".strip()

        user_payload = {
            "prompt": payload.prompt,
            "requested_output_format": payload.output_format,
            "overrides": payload.overrides,
            "metadata": payload.metadata,
        }

        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
            },
        ]


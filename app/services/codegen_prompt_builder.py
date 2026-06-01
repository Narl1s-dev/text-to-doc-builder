import json

from app.schemas.document_spec import DocumentSpec


class CodegenPromptBuilder:
    prompt_version = "docx-codegen-v1"

    def build_docx_codegen_messages(self, document_spec: DocumentSpec) -> list[dict[str, str]]:
        system_prompt = """
You generate safe Python code that creates a DOCX file from document_spec.json.
Return only valid JSON, without markdown fences or explanations.
The JSON must contain exactly these top-level keys:
- python_code
- warnings

Runtime contract:
- Read /input/document_spec.json. It contains a JSON object with a top-level
  "document_spec" key; the value is the document specification to render.
- Write the final DOCX to /output/result.docx.
- Use python-docx and Python standard library only.
- Do not use network, environment variables, secrets, subprocesses, shell commands, or paths outside /input and /output.
- If the spec contains Markdown, render headings, paragraphs, bullet lists, numbered lists, and simple Markdown tables.
- The script must fail loudly with a clear exception if it cannot create /output/result.docx.
""".strip()

        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {"document_spec": document_spec.model_dump(mode="json")},
                    ensure_ascii=False,
                    indent=2,
                ),
            },
        ]

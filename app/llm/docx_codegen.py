import json
import re

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import Settings, get_settings
from app.llm.openrouter_client import OpenRouterClient
from app.schemas.document_spec import DocumentSpec
from app.services.codegen_prompt_builder import CodegenPromptBuilder


class CodegenValidationError(Exception):
    """Raised when a codegen response cannot be parsed into runnable Python."""


class DocxCodegenResult(BaseModel):
    python_code: str
    warnings: list[str] = Field(default_factory=list)
    raw_output: str | None = None

    @field_validator("python_code")
    @classmethod
    def validate_python_code(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("python_code must not be empty.")
        return normalized


class DocxCodeGenerator:
    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenRouterClient | None = None,
        prompt_builder: CodegenPromptBuilder | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.prompt_builder = prompt_builder or CodegenPromptBuilder()

    def generate(self, document_spec: DocumentSpec) -> DocxCodegenResult:
        model = self.settings.openrouter_codegen_model or self.settings.openrouter_model
        client = self.client or OpenRouterClient.from_settings(self.settings, model=model)
        messages = self.prompt_builder.build_docx_codegen_messages(document_spec)
        raw_output = client.create_chat_completion(messages)
        result = parse_docx_codegen_response(raw_output)
        result.raw_output = raw_output
        return result

    def repair(
        self,
        *,
        document_spec: DocumentSpec,
        previous_python_code: str,
        sandbox_result: dict | None = None,
        validation_errors: list[str] | None = None,
    ) -> DocxCodegenResult:
        model = self.settings.openrouter_codegen_model or self.settings.openrouter_model
        client = self.client or OpenRouterClient.from_settings(self.settings, model=model)
        messages = self.prompt_builder.build_docx_repair_messages(
            document_spec=document_spec,
            previous_python_code=previous_python_code,
            sandbox_result=sandbox_result,
            validation_errors=validation_errors,
        )
        raw_output = client.create_chat_completion(messages)
        result = parse_docx_codegen_response(raw_output)
        result.raw_output = raw_output
        return result


def parse_docx_codegen_response(raw_output: str) -> DocxCodegenResult:
    cleaned = _strip_markdown_fence(raw_output)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise CodegenValidationError(f"Codegen response is not valid JSON: {exc}") from exc

    try:
        return DocxCodegenResult.model_validate(payload)
    except ValidationError as exc:
        raise CodegenValidationError(f"Codegen response did not match schema: {exc}") from exc


def _strip_markdown_fence(value: str) -> str:
    text = value.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return text

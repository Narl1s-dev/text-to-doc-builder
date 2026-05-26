from app.llm.openrouter_client import OpenRouterClient
from app.llm.response_validator import LLMResponseValidator
from app.llm.schemas import LLMPlanningResponse
from app.schemas.document import DocumentCreateRequest
from app.services.prompt_builder import PromptBuilder


class LLMRequestParser:
    def __init__(
        self,
        client: OpenRouterClient,
        prompt_builder: PromptBuilder | None = None,
        validator: LLMResponseValidator | None = None,
    ) -> None:
        self.client = client
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.validator = validator or LLMResponseValidator()

    def parse(self, payload: DocumentCreateRequest) -> tuple[LLMPlanningResponse, str]:
        messages = self.prompt_builder.build_planning_messages(payload)
        raw_output = self.client.create_chat_completion(messages)
        return self.validator.parse_planning_response(raw_output), raw_output


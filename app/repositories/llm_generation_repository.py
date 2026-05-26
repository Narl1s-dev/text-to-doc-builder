from typing import Any

from sqlalchemy.orm import Session

from app.db.models import LLMGeneration


class LLMGenerationRepository:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def create(
        self,
        *,
        request_id: str,
        stage: str,
        provider: str,
        model: str | None,
        prompt_version: str,
        input_payload: dict[str, Any],
        raw_output: str | None,
        parsed_output: dict[str, Any] | None,
        error_message: str | None = None,
    ) -> LLMGeneration:
        llm_generation = LLMGeneration(
            request_id=request_id,
            stage=stage,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            input_payload=input_payload,
            raw_output=raw_output,
            parsed_output=parsed_output,
            error_message=error_message,
        )
        self.db_session.add(llm_generation)
        self.db_session.flush()
        return llm_generation


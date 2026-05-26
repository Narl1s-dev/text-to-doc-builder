from app.core.config import Settings, get_settings
from app.core.errors import ConfigurationError
from app.llm.openrouter_client import OpenRouterClient
from app.llm.request_parser import LLMRequestParser
from app.llm.schemas import LLMPlanningResult
from app.schemas.document import DocumentCreateRequest
from app.services.defaults_resolver import DefaultsResolver


class LLMArtifactPlanner:
    def __init__(
        self,
        settings: Settings | None = None,
        parser: LLMRequestParser | None = None,
        defaults_resolver: DefaultsResolver | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.parser = parser
        self.defaults_resolver = defaults_resolver or DefaultsResolver(self.settings)

    def plan(self, payload: DocumentCreateRequest) -> LLMPlanningResult:
        try:
            parser = self.parser or LLMRequestParser(OpenRouterClient.from_settings(self.settings))
        except ConfigurationError as exc:
            fallback = self.defaults_resolver.fallback_plan(payload)
            return LLMPlanningResult(
                generation_spec=fallback.generation_spec,
                artifact_plan=fallback.artifact_plan,
                warnings=[
                    str(exc),
                    "LLM planning was skipped; fallback defaults were used.",
                    *fallback.warnings,
                ],
                skipped_reason=str(exc),
            )

        parsed_response, raw_output = parser.parse(payload)
        spec, spec_warnings = self.defaults_resolver.resolve_generation_spec(
            payload,
            parsed_response.generation_spec,
        )
        plan, plan_warnings = self.defaults_resolver.resolve_artifact_plan(
            spec,
            payload,
            parsed_response.artifact_plan,
        )

        return LLMPlanningResult(
            generation_spec=spec,
            artifact_plan=plan,
            warnings=[*parsed_response.warnings, *spec_warnings, *plan_warnings],
            raw_output=raw_output,
        )


from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings


def verify_internal_token(
    settings: Annotated[Settings, Depends(get_settings)],
    x_api_token: Annotated[str | None, Header(alias="X-API-Token")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    configured_token = settings.api_internal_token
    if configured_token is None:
        return

    expected_token = configured_token.get_secret_value().strip()
    if not expected_token:
        return

    bearer_prefix = "Bearer "
    provided_token = x_api_token

    if authorization and authorization.startswith(bearer_prefix):
        provided_token = authorization[len(bearer_prefix) :]

    if provided_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
        )

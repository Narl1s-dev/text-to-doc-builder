from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(tags=["health"])


class RootResponse(BaseModel):
    app: str
    status: Literal["ok"]
    health_url: str
    docs_url: str


class HealthResponse(BaseModel):
    status: Literal["ok"]


@router.get("/", response_model=RootResponse)
async def root() -> RootResponse:
    return RootResponse(
        app="Text To Doc Builder",
        status="ok",
        health_url="/health",
        docs_url="/docs",
    )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok")

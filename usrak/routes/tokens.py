
from dataclasses import dataclass
from typing import Type

from fastapi import Depends
from sqlmodel import select
from pydantic import BaseModel, create_model

from usrak.core.models.user import UserModelBase
from usrak.core.schemas.response import CommonDataResponse
from usrak.core.dependencies import user as user_deps
from usrak.core.dependencies.managers import (
    get_tokens_model,
    get_tokens_read_schema,
)
from usrak.core.managers.tokens.auth import AuthTokensManager

from usrak.core.db import get_db
from usrak.core.schemas.tokens import ApiTokenCreate


@dataclass(frozen=True)
class TokenResponseModels:
    list_data: type[BaseModel]
    list_response: type[CommonDataResponse]
    created_data: type[BaseModel]
    created_response: type[CommonDataResponse]
    empty_data: type[BaseModel]
    empty_response: type[CommonDataResponse]


_token_models: TokenResponseModels | None = None


def configure_token_response_models(tokens_read_schema: Type[BaseModel]) -> TokenResponseModels:
    global _token_models

    tokens_list_data = create_model(
        "ApiTokensListData",
        tokens=(list[tokens_read_schema], ...),
    )
    created_token_data = create_model(
        "ApiTokenCreatedData",
        token=(str, ...),
    )
    empty_data = create_model("ApiTokenEmptyData")

    _token_models = TokenResponseModels(
        list_data=tokens_list_data,
        list_response=CommonDataResponse[tokens_list_data],
        created_data=created_token_data,
        created_response=CommonDataResponse[created_token_data],
        empty_data=empty_data,
        empty_response=CommonDataResponse[empty_data],
    )
    return _token_models


def get_token_response_models() -> TokenResponseModels:
    if _token_models is None:
        configure_token_response_models(get_tokens_read_schema())
    return _token_models


async def get_user_api_tokens(
    user: UserModelBase = Depends(user_deps.get_user_access_only),
    session=Depends(get_db),
):
    models = get_token_response_models()

    Tokens = get_tokens_model()
    TokensRead = get_tokens_read_schema()

    stmt = select(Tokens).where(
        Tokens.owner_identifier == user.user_identifier,
        Tokens.is_deleted == False,
    )
    result = await session.exec(stmt)
    tokens = result.all()

    tokens_data = [TokensRead.model_validate(token) for token in tokens]
    payload = models.list_data(tokens=tokens_data)
    return models.list_response(
        success=True,
        message="Operation completed",
        data=payload,
    )


async def create_api_token(
    token_create_data: ApiTokenCreate,
    user: UserModelBase = Depends(user_deps.get_user_access_only),
    session=Depends(get_db),
    auth_tokens_manager: AuthTokensManager = Depends(AuthTokensManager),
):
    models = get_token_response_models()

    token = await auth_tokens_manager.create_api_token(
        user_identifier=user.user_identifier,
        session=session,
        expires_at=token_create_data.expires_at,
        name=token_create_data.name,
        whitelisted_ip_addresses=token_create_data.whitelisted_ip_addresses,
    )
    payload = models.created_data(token=token)
    return models.created_response(
        success=True,
        message="Operation completed",
        data=payload,
    )


async def delete_api_token(
    token_identifier: str,
    user: UserModelBase = Depends(user_deps.get_user_access_only),
    session=Depends(get_db),
):
    models = get_token_response_models()

    auth_tokens_manager: AuthTokensManager = AuthTokensManager()
    await auth_tokens_manager.delete_api_token(
        token_identifier=token_identifier,
        user_identifier=user.user_identifier,
        session=session,
    )
    return models.empty_response(
        success=True,
        message="Operation completed",
        data=models.empty_data(),
    )

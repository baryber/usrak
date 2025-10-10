from typing import List

from fastapi import Depends
from sqlmodel import select
from pydantic import BaseModel

from usrak.core.models.user import UserModelBase
from usrak.core.schemas.response import CommonDataResponse
from usrak.core.dependencies import user as user_deps
from usrak.core.dependencies.managers import get_tokens_model, get_tokens_read_schema
from usrak.core.managers.tokens.auth import AuthTokensManager

from usrak.core.db import get_db
from usrak.core.schemas.tokens import ApiTokenCreate


async def get_user_api_tokens(
    user: UserModelBase = Depends(user_deps.get_user_access_only),
    session=Depends(get_db),
):
    Tokens = get_tokens_model()
    TokensRead = get_tokens_read_schema()

    stmt = select(Tokens).where(
        Tokens.owner_identifier == user.user_identifier,
        Tokens.is_deleted == False,
    )
    result = await session.exec(stmt)
    tokens = result.all()

    tokens_data = [TokensRead.model_validate(token) for token in tokens]
    return CommonDataResponse(
        success=True,
        message="Operation completed",
        data={"tokens": tokens_data},
    )


async def create_api_token(
    token_create_data: ApiTokenCreate,
    user: UserModelBase = Depends(user_deps.get_user_access_only),
    session=Depends(get_db),
    auth_tokens_manager: AuthTokensManager = Depends(AuthTokensManager)
):
    token = await auth_tokens_manager.create_api_token(
        user_identifier=user.user_identifier,
        session=session,
        expires_at=token_create_data.expires_at,
        name=token_create_data.name,
        whitelisted_ip_addresses=token_create_data.whitelisted_ip_addresses,
    )
    return CommonDataResponse(
        success=True,
        message="Operation completed",
        data={"token": token},
    )


async def delete_api_token(
    token_identifier: str,
    user: UserModelBase = Depends(user_deps.get_user_access_only),
    session=Depends(get_db),
):
    auth_tokens_manager: AuthTokensManager = AuthTokensManager()
    await auth_tokens_manager.delete_api_token(
        token_identifier=token_identifier,
        user_identifier=user.user_identifier,
        session=session,
    )
    return CommonDataResponse(
        success=True,
        message="Operation completed",
        data={},
    )

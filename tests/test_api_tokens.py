import time

import pytest

from usrak import RouterConfig
from usrak.core import exceptions as exc
from usrak.core.dependencies.config_provider import set_app_config, set_router_config
from usrak.core.managers.tokens.auth import AuthTokensManager
from usrak.core.resolvers.api_token import resolve_api_token_record
from usrak.core.security import hash_token
from usrak.routes.tokens import get_user_api_tokens

from .fixtures.tokens import TestTokensModel
from .fixtures.user import TestUserModel


class AsyncSessionAdapter:
    def __init__(self, session):
        self._session = session

    async def exec(self, statement):
        return self._session.exec(statement)

    async def scalar(self, statement):
        return self._session.exec(statement).one()

    def add(self, instance) -> None:
        self._session.add(instance)

    async def commit(self) -> None:
        self._session.commit()


def _configure(app_config, router_config: RouterConfig) -> None:
    set_app_config(app_config)
    set_router_config(router_config)


def _add_token(
    session,
    *,
    user_id: int,
    raw_token: str,
    token_type: str,
    expires_at: int | None = None,
    allowed_ips: list[str] | None = None,
) -> TestTokensModel:
    token = TestTokensModel(
        user_id=user_id,
        token=hash_token(raw_token),
        token_type=token_type,
        expires_at=expires_at,
        whitelisted_ip_addresses=allowed_ips,
    )
    session.add(token)
    session.commit()
    session.refresh(token)
    return token


@pytest.mark.asyncio
async def test_api_token_list_only_returns_usrak_managed_type(
    app_config,
    router_config,
    db_session,
    created_test_user: TestUserModel,
):
    _configure(app_config, router_config)
    assert created_test_user.super_id is not None
    _add_token(
        db_session,
        user_id=created_test_user.super_id,
        raw_token="api-secret",
        token_type="api_token",
    )
    _add_token(
        db_session,
        user_id=created_test_user.super_id,
        raw_token="mcp-secret",
        token_type="MCP",
    )
    _add_token(
        db_session,
        user_id=created_test_user.super_id,
        raw_token="unknown-secret",
        token_type="unknown",
    )

    response = await get_user_api_tokens(
        user=created_test_user,
        session=AsyncSessionAdapter(db_session),
        router_config=router_config,
    )

    assert [token.token_type for token in response.data.tokens] == ["api_token"]


@pytest.mark.asyncio
async def test_custom_usrak_token_type_controls_create_delete_and_resolve(
    app_config,
    router_config,
    db_session,
    created_test_user: TestUserModel,
):
    custom_config_data = router_config.model_dump()
    custom_config_data["PERSISTENT_TOKEN_TYPES"] = (
        {"token_type": "personal_api", "management": "usrak_api"},
        {"token_type": "MCP", "management": "application"},
    )
    custom_config = RouterConfig.model_validate(custom_config_data)
    _configure(app_config, custom_config)
    assert created_test_user.super_id is not None
    session = AsyncSessionAdapter(db_session)
    manager = AuthTokensManager(app_config=app_config, router_config=custom_config)

    raw_token = await manager.create_api_token(
        user_identifier=created_test_user.super_id,
        session=session,
        name="custom",
    )
    resolved = await resolve_api_token_record(
        api_token=raw_token,
        session=session,
        router_config=custom_config,
        user_identifier=created_test_user.super_id,
    )
    assert resolved is not None
    assert resolved.token_type == "personal_api"

    mcp_token = _add_token(
        db_session,
        user_id=created_test_user.super_id,
        raw_token="mcp-secret",
        token_type="MCP",
    )
    with pytest.raises(exc.InvalidTokenException):
        await manager.delete_api_token(
            token_identifier=mcp_token.id,
            user_identifier=created_test_user.super_id,
            session=session,
        )

    await manager.delete_api_token(
        token_identifier=resolved.id,
        user_identifier=created_test_user.super_id,
        session=session,
    )
    assert (
        await resolve_api_token_record(
            api_token=raw_token,
            session=session,
            router_config=custom_config,
            user_identifier=created_test_user.super_id,
        )
        is None
    )


@pytest.mark.asyncio
async def test_api_token_validation_is_fail_closed_and_has_no_auth_cache(
    app_config,
    router_config,
    db_session,
    created_test_user: TestUserModel,
):
    _configure(app_config, router_config)
    assert created_test_user.super_id is not None
    session = AsyncSessionAdapter(db_session)
    token = _add_token(
        db_session,
        user_id=created_test_user.super_id,
        raw_token="allowed-secret",
        token_type="api_token",
        allowed_ips=["10.0.0.1"],
    )

    assert await resolve_api_token_record(
        api_token="allowed-secret",
        session=session,
        router_config=router_config,
        remote_addresses=("10.0.0.1",),
    )
    assert (
        await resolve_api_token_record(
            api_token="allowed-secret",
            session=session,
            router_config=router_config,
            remote_addresses=("10.0.0.2",),
        )
        is None
    )

    token.is_deleted = True
    db_session.add(token)
    db_session.commit()
    assert (
        await resolve_api_token_record(
            api_token="allowed-secret",
            session=session,
            router_config=router_config,
            remote_addresses=("10.0.0.1",),
        )
        is None
    )

    _add_token(
        db_session,
        user_id=created_test_user.super_id,
        raw_token="expired-secret",
        token_type="api_token",
        expires_at=int(time.time()) - 1,
    )
    assert (
        await resolve_api_token_record(
            api_token="expired-secret",
            session=session,
            router_config=router_config,
        )
        is None
    )

    _add_token(
        db_session,
        user_id=created_test_user.super_id,
        raw_token="application-secret",
        token_type="MCP",
    )
    assert (
        await resolve_api_token_record(
            api_token="application-secret",
            session=session,
            router_config=router_config,
        )
        is None
    )

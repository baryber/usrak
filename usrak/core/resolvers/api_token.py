import time
from collections.abc import Collection
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import joinedload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from usrak.core.security import hash_token

if TYPE_CHECKING:
    from usrak.core.config_schemas import RouterConfig


async def resolve_api_token_record(
    *,
    api_token: str,
    session: AsyncSession,
    router_config: "RouterConfig",
    user_identifier: Any | None = None,
    remote_addresses: Collection[str] | None = None,
    load_owner: bool = False,
) -> Any | None:
    """Resolve a valid UsrAK-managed opaque API token, or return ``None``."""

    tokens_model = router_config.TOKENS_MODEL
    owner_column = getattr(tokens_model, tokens_model.__owner_field_name__)
    filters = [
        tokens_model.token == hash_token(api_token),
        tokens_model.token_type == router_config.usrak_api_token_type,
        tokens_model.is_deleted.is_(False),
    ]
    if user_identifier is not None:
        filters.append(owner_column == user_identifier)

    statement = select(tokens_model).where(*filters)
    if load_owner:
        owner_relation = getattr(
            tokens_model,
            router_config.TOKENS_OWNER_RELATION_FIELD_NAME,
        )
        statement = statement.options(joinedload(owner_relation))
    result = await session.exec(statement)
    token = result.one_or_none()
    if token is None:
        return None

    if token.expires_at is not None and token.expires_at <= int(time.time()):
        return None

    if token.whitelisted_ip_addresses:
        candidates = set(remote_addresses or ())
        if not candidates.intersection(token.whitelisted_ip_addresses):
            return None

    return token

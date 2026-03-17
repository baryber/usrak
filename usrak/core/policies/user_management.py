from typing import TYPE_CHECKING

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from usrak.core import exceptions as exc
from usrak.core.db import get_db
from usrak.core.dependencies.config_provider import get_router_config
from usrak.core.enums import UserManagementAction
from usrak.core.roles import normalize_role_reference

if TYPE_CHECKING:
    from usrak.core.config_schemas import RouterConfig

from usrak.core.config_schemas import UserManagementRuleSet


class UserManagementPolicy:
    def __init__(
        self,
        session: AsyncSession = Depends(get_db),
        router_config: "RouterConfig" = Depends(get_router_config),
    ):
        self.session = session
        self.router_config = router_config

    async def authorize(
        self,
        action: UserManagementAction,
        actor_role,
        target_current_role,
        target_new_role=None,
    ) -> None:
        normalized_actor_role = normalize_role_reference(actor_role, self.router_config)
        if normalized_actor_role not in await self.get_known_roles():
            raise exc.AccessDeniedException()

        current_role = None
        if target_current_role is not None:
            current_role = normalize_role_reference(target_current_role, self.router_config)
            await self._ensure_known_target_role(current_role)

        new_role = None
        if target_new_role is not None:
            new_role = normalize_role_reference(target_new_role, self.router_config)
            await self._ensure_known_target_role(new_role)

        if action == UserManagementAction.CREATE:
            if new_role is None:
                raise exc.InvalidRoleException()
            await self._authorize_role_target(normalized_actor_role, action, new_role)
            return

        if current_role is None:
            raise exc.AccessDeniedException()

        await self._authorize_role_target(normalized_actor_role, action, current_role)
        if action == UserManagementAction.UPDATE and new_role is not None and new_role != current_role:
            await self._authorize_role_target(normalized_actor_role, action, new_role)

    async def get_known_roles(self) -> set[str]:
        known_roles = {str(member.value) for member in self.router_config.DEFAULT_ROLES_ENUM}
        role_model = self.router_config.ROLE_MODEL
        if role_model is None:
            return known_roles

        result = await self.session.exec(select(role_model.name))
        known_roles.update(str(role_name) for role_name in result.all())
        return known_roles

    async def get_role_record(self, role_name: str):
        role_model = self.router_config.ROLE_MODEL
        if role_model is None:
            return None

        result = await self.session.exec(select(role_model).where(role_model.name == role_name))
        return result.first()

    async def _ensure_known_target_role(self, role_name: str) -> None:
        if role_name not in await self.get_known_roles():
            raise exc.InvalidRoleException(role_name)

    async def _authorize_role_target(
        self,
        actor_role: str,
        action: UserManagementAction,
        target_role: str,
    ) -> None:
        actor_rules = await self._get_actor_rules(actor_role)
        if actor_rules is None:
            raise exc.AccessDeniedException()

        targets = actor_rules.get_targets(action)
        if targets == "*" or targets == {"*"}:
            return

        if target_role not in targets:
            raise exc.AccessDeniedException()

    async def _get_actor_rules(self, actor_role: str) -> "UserManagementRuleSet | None":
        role_record = await self.get_role_record(actor_role)
        if role_record is not None and role_record.user_management_rules is not None:
            return UserManagementRuleSet.model_validate(role_record.user_management_rules)

        return self.router_config.DEFAULT_USER_MANAGEMENT_RULES.get(actor_role)

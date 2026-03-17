from enum import Enum
from typing import TYPE_CHECKING, Literal

from usrak.core.models.role import RoleModelBase

if TYPE_CHECKING:
    from usrak.core.config_schemas import RouterConfig


def normalize_role_reference(
    role: RoleModelBase | Enum | str | Literal["*"],
    router_config: "RouterConfig",
) -> str:
    if role == "*":
        return role

    if isinstance(role, RoleModelBase):
        return role.name

    if isinstance(role, Enum):
        configured_roles = router_config.DEFAULT_ROLES_ENUM
        if role.name in configured_roles.__members__:
            return str(configured_roles[role.name].value)
        return str(role.value)

    return str(role)


def get_user_role(user) -> str | None:
    role_field_name = getattr(user, "__role_field_name__", "role")
    return getattr(user, role_field_name, None)

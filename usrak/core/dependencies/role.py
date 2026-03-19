from usrak.core import enums
from usrak.core.dependencies.user import RoleRequirement, UserDependency, build_user_dependency


def require_roles(*roles: RoleRequirement) -> UserDependency:
    required_roles = list(roles) if roles else ["*"]
    dependency = build_user_dependency(
        auth_mode=enums.AuthMode.ACCESS_ONLY,
        require_roles=required_roles,
    )
    setattr(dependency, "__name__", "require_roles_dependency")
    return dependency

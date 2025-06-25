from usrak.core.logger import logger

from usrak.core import exceptions as exc, enums
from usrak.core.security import generate_jti
from usrak.core.schemas.security import SecretContext
from usrak.core.managers.tokens.base import TokensManagerBase


class AuthTokensManager(TokensManagerBase):
    """
    AuthTokensManager is responsible for managing authentication tokens.
    It handles the generation, validation, and blacklisting of access and refresh tokens.
    """
    JTI_PREFIX = "jti"
    ACCESS_TOKEN_PREFIX = "access_token"
    REFRESH_TOKEN_PREFIX = "refresh_token"

    async def create_access_token(
            self,
            user_identifier: str,
            password_version: int,
    ) -> str:
        jti = generate_jti()
        token = await self.create_token(
            token_type=enums.TokenTypes.ACCESS.value,
            user_identifier=user_identifier,
            exp=self.app_config.ACCESS_TOKEN_EXPIRE_SEC,
            jti=jti,
            jwt_secret=self.app_config.JWT_ACCESS_TOKEN_SECRET_KEY,
            secret_context=SecretContext(
                password_version=password_version
            ),
        )
        jti_prefix = await self.key_prefix(self.JTI_PREFIX, self.ACCESS_TOKEN_PREFIX, user_identifier)
        await self.kvs.hset(
            key=jti_prefix,
            field="0",
            value=jti,
        )
        await self.kvs.hexpire(
            key=jti_prefix,
            ttl=self.app_config.ACCESS_TOKEN_EXPIRE_SEC,
        )

        return token

    async def create_refresh_token(
            self,
            user_identifier: str,
            password_version: int,
    ) -> str:
        jti = generate_jti()
        token = await self.create_token(
            token_type=enums.TokenTypes.REFRESH.value,
            user_identifier=user_identifier,
            exp=self.app_config.REFRESH_TOKEN_EXPIRE_SEC,
            jti=jti,
            jwt_secret=self.app_config.JWT_REFRESH_TOKEN_SECRET_KEY,
            secret_context=SecretContext(
                password_version=password_version
            ))

        jti_prefix = await self.key_prefix(self.JTI_PREFIX, self.REFRESH_TOKEN_PREFIX, user_identifier)
        await self.kvs.hset(
            key=jti_prefix,
            field="0",
            value=jti,
        )
        await self.kvs.hexpire(
            key=jti_prefix,
            ttl=self.app_config.REFRESH_TOKEN_EXPIRE_SEC,
        )

        return token

    async def validate_access_token(
            self,
            token: str,
            password_version: int,
            user_identifier: str
    ) -> None:
        await self.validate_token(
            token=token,
            jwt_secret=self.app_config.JWT_ACCESS_TOKEN_SECRET_KEY,
            user_identifier=user_identifier,
            secret_context=SecretContext(
                password_version=password_version
            )
        )

    async def handle_refresh_token(
            self,
            refresh_token: str,
            user_identifier: str,
            password_version: int,
            old_access_token: str | None = None
    ) -> str:
        payload = await self.validate_token(
            token=refresh_token,
            jwt_secret=self.app_config.JWT_REFRESH_TOKEN_SECRET_KEY,
            user_identifier=user_identifier,
            secret_context=SecretContext(
                password_version=password_version
            )
        )

        await self.deactivate_token(
            token_type=enums.TokenTypes.REFRESH.value,
            user_identifier=user_identifier
        )

        if old_access_token:
            await self.deactivate_token(
                token_type=enums.TokenTypes.ACCESS.value,
                user_identifier=user_identifier
            )

        if not payload.secret_context or not payload.secret_context.password_version:
            logger.warning(
                "Password version is not provided in the refresh token secret context. "
                "Please check the token generation process."
            )
            await self.terminate_all_user_sessions(user_identifier)
            raise exc.InvalidTokenException

        secret_context = SecretContext(
            password_version=payload.secret_context.password_version
        )
        new_refresh_token = await self.create_refresh_token(
            user_identifier=user_identifier,
            password_version=secret_context.password_version,
        )

        return new_refresh_token

    async def terminate_all_user_sessions(self, user_identifier: str) -> None:
        """
        Terminate all user sessions by deleting all tokens associated with the user.
        """
        await self.deactivate_token(
            token_type=enums.TokenTypes.ACCESS.value,
            user_identifier=user_identifier
        )

        await self.deactivate_token(
            token_type=enums.TokenTypes.REFRESH.value,
            user_identifier=user_identifier
        )


if __name__ == '__main__':
    auth_manager = AuthTokensManager()

    # Example usage
    user_identifier = "user12345"
    password_version = 1

    async def example_usage():
        # access_token = await auth_tokens_manager.create_access_token(user_identifier, password_version)
        # print(f"Access Token: {access_token}")
        #
        # refresh_token = await auth_tokens_manager.create_refresh_token(user_identifier, password_version)
        # print(f"Refresh Token: {refresh_token}")

        access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzX3Rva2VuIiwidXNlcl9pZGVudGlmaWVyIjoidXNlcjEyMzQ1IiwiZXhwIjoxNzQ3OTkzNTQ3LCJqdGkiOiI2YjMxNDFhMC03N2EyLTRmMGMtOTc1Yi05YjEzZjA4ZmZkNjEiLCJzZWNyZXRfY29udGV4dCI6eyJwYXNzd29yZF92ZXJzaW9uIjoxLCJwdXJwb3NlIjpudWxsLCJpcF9hZGRyZXNzIjpudWxsfX0.2FIVt2HUELyRq4Kq1ugM2cHuauk31Xv0T8HOkugMq8A"
        ref = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaF90b2tlbiIsInVzZXJfaWRlbnRpZmllciI6InVzZXIxMjM0NSIsImV4cCI6MTc0ODU5NzUwNSwianRpIjoiZGE4ZTcxN2ItMmQyYi00MjhjLTkxNTItYzM5MjEyZTVhZDNlIiwic2VjcmV0X2NvbnRleHQiOnsicGFzc3dvcmRfdmVyc2lvbiI6MSwicHVycG9zZSI6bnVsbCwiaXBfYWRkcmVzcyI6bnVsbH19._crjd99s_XPjDB1K_JnyJ-fqtPyZWgi-ufN3M15tx-w"

        await auth_manager.validate_access_token(access_token, password_version, user_identifier)
        print("Access token validated successfully.")

        # new_ref = await auth_tokens_manager.handle_refresh_token(
        #     refresh_token=ref,
        #     user_identifier=user_identifier,
        #     old_access_token=access_token,
        #     password_version=password_version
        # )
        # print(new_ref)

    import asyncio

    asyncio.run(example_usage())
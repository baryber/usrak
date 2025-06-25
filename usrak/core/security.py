import uuid
from typing import Optional

import jwt
from usrak.core.logger import logger
from cryptography.fernet import Fernet
from passlib.context import CryptContext

from usrak.core import exceptions as exc
from usrak.core.dependencies.config_provider import get_app_config
from usrak.core.schemas.security import JwtTokenPayloadData, SecretContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_jti() -> str:
    """
    Generate a unique identifier for the JWT token.
    :return: A unique identifier (jti).
    """
    return str(uuid.uuid4())


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def encrypt_token(token: str) -> str:
    """
    Encrypt a token using Fernet symmetric encryption. Use to store tokens.
    :param token:
    :return:
    """
    config = get_app_config()
    cipher = Fernet(config.FERNET_KEY)
    return cipher.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> Optional[str]:
    """
    Decrypt a token using Fernet symmetric encryption.
    :param encrypted_token:
    :return:
    """
    try:
        config = get_app_config()
        cipher = Fernet(config.FERNET_KEY)
        return cipher.decrypt(encrypted_token.encode()).decode()

    except Exception as ex:
        logger.info(f"Token decryption failed: {ex}")
        return None


def create_jwt_token(data: JwtTokenPayloadData, jwt_secret: str) -> str:
    """
    Create a JWT token with the given data and secret.
    :param data:
    :param jwt_secret:
    :return:
    """
    config = get_app_config()
    return jwt.encode(data.model_dump(), jwt_secret, algorithm=config.ALGORITHM)


def decode_jwt_token(token: str, jwt_secret: str) -> JwtTokenPayloadData:
    """
    Decode a JWT token and return the payload data.
    :param token:
    :param jwt_secret:
    :return:
    """
    try:
        config = get_app_config()
        payload = jwt.decode(token, jwt_secret, algorithms=[config.ALGORITHM])
        return JwtTokenPayloadData(**payload)

    except jwt.ExpiredSignatureError:
        raise exc.ExpiredAccessTokenException

    except jwt.PyJWTError:
        raise exc.InvalidAccessTokenException


def verify_secret_context(context: SecretContext, expected: SecretContext) -> bool:
    """
    Verify the secret context against the expected context.
    :param context: The context to verify.
    :param expected: The expected context.
    :return: True if the context matches, False otherwise.
    """
    context_dict = context.model_dump(exclude_none=True)
    expected_dict = expected.model_dump(exclude_none=True)

    for key, value in context_dict.items():
        if key not in expected_dict or expected_dict[key] != value:
            return False

    return True


if __name__ == '__main__':
    print(hash_password("Solbearer07"))
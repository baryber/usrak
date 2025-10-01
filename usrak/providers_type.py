from typing import Type, Generator, Callable

from sqlmodel import Session
from pydantic import BaseModel

from usrak.core.models.user import UserModelBase
from usrak.core.models.tokens import TokensModelBase
from usrak.core.managers.key_value_store import KeyValueStoreABS
from usrak.core.managers.notification.base import NotificationServiceABS
from usrak.core.managers.rate_limiter.interface import IFastApiRateLimiter
from usrak.core.smtp.base import SMTPClientABS


UserModelType = Type[UserModelBase]
UserReadSchemaType = Type[BaseModel]

TokensModelType = Type[TokensModelBase]
TokensReadSchemaType = Type[BaseModel]

KeyValueStoreType = Type[KeyValueStoreABS]
NotificationServiceType = Type[NotificationServiceABS]
FastApiRateLimiterType = Type[IFastApiRateLimiter]
SMTPClientType = Type[SMTPClientABS]
GetSessionType = Callable[[], Generator[Session, None, None]]

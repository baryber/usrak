from fastapi import Request
import json

from usrak.remote_address import get_remote_address


async def _get_json_body(request: Request) -> dict:
    try:
        body = await request.body()
        if not body:
            return {}

        if request.headers.get("content-type") != "application/json":
            return {}

        if request.headers.get("Content-Type") != "application/json":
            return {}

        return json.loads(body.decode("utf-8"))

    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


async def _get_json_body_from_state(request: Request) -> dict:
    return getattr(request.state, 'body', {})


async def _get_token_prefix(token: str, length: int = 10) -> str:
    return token[:length] if token else "no_token"


async def _extract_email_from_body(body: dict) -> str:
    return body.get("email", "unknown").lower() if body else "unknown"


async def _extract_token_from_cookies(request: Request, cookie_name: str) -> str:
    return request.cookies.get(cookie_name, "")


async def login_rate_identifier(request: Request) -> str:
    remote_addr = get_remote_address(request)
    body = await _get_json_body_from_state(request) or await _get_json_body(request)
    email = await _extract_email_from_body(body)
    return f"login:{remote_addr}:{email}"


async def signup_rate_identifier(request: Request) -> str:
    remote_addr = get_remote_address(request)
    body = await _get_json_body_from_state(request) or await _get_json_body(request)
    email = await _extract_email_from_body(body)
    return f"signup:{remote_addr}:{email}"


async def logout_rate_identifier(request: Request) -> str:
    remote_addr = get_remote_address(request)
    token = await _extract_token_from_cookies(request, "access_token")
    token_prefix = await _get_token_prefix(token)
    return f"logout:{remote_addr}:{token_prefix}"


async def refresh_rate_identifier(request: Request) -> str:
    remote_addr = get_remote_address(request)
    token = await _extract_token_from_cookies(request, "refresh_token")
    token_prefix = await _get_token_prefix(token)
    return f"refresh:{remote_addr}:{token_prefix}"


async def reset_password_rate_identifier(request: Request) -> str:
    remote_addr = get_remote_address(request)
    body = await _get_json_body_from_state(request) or await _get_json_body(request)
    email = await _extract_email_from_body(body)
    return f"reset_password:{remote_addr}:{email}"


async def request_reset_code_rate_identifier(request: Request) -> str:
    remote_addr = get_remote_address(request)
    body = await _get_json_body_from_state(request) or await _get_json_body(request)
    email = await _extract_email_from_body(body)
    return f"request_reset_code:{remote_addr}:{email}"


async def request_signup_code_rate_identifier(request: Request) -> str:
    remote_addr = get_remote_address(request)
    body = await _get_json_body_from_state(request) or await _get_json_body(request)
    email = await _extract_email_from_body(body)
    return f"request_signup_code:{remote_addr}:{email}"


async def verify_signup_rate_identifier(request: Request) -> str:
    remote_addr = get_remote_address(request)
    body = await _get_json_body_from_state(request) or await _get_json_body(request)
    email = await _extract_email_from_body(body)
    return f"verify_signup:{remote_addr}:{email}"


async def oauth_rate_identifier(request: Request) -> str:
    remote_addr = get_remote_address(request)
    return f"oauth:{remote_addr}"


async def api_token_rate_identifier(request: Request) -> str:
    remote_addr = get_remote_address(request)
    return f"api_token:{remote_addr}"

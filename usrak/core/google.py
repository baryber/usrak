import httpx

from usrak.core.dependencies.config_provider import get_app_config


async def exchange_code_for_token(code: str) -> dict:
    config = get_app_config()

    data = {
        "client_id": config.GOOGLE_CLIENT_ID,
        "client_secret": config.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": config.GOOGLE_REDIRECT_URI,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(config.GOOGLE_TOKEN_URL, data=data)
        resp.raise_for_status()
        return resp.json()


async def get_userinfo(access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    config = get_app_config()
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(config.GOOGLE_USERINFO_URL, headers=headers)
        resp.raise_for_status()
        return resp.json()

from httpx import AsyncClient


async def login_user(client: AsyncClient, email: str, password: str, fingerprint: str = "test-device") -> dict:
    response = await client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"X-Client-Fingerprint": fingerprint},
    )
    assert response.status_code == 200, response.text
    return response.json()

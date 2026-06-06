from httpx import AsyncClient


async def create_project(client: AsyncClient, name: str = "Project", is_private: bool = True) -> dict:
    response = await client.post(
        "/projects/",
        json={"name": name, "about": "About the project", "is_private": is_private},
    )
    assert response.status_code == 201, response.text
    return response.json()

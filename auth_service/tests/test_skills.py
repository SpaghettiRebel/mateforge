from uuid import uuid4

import pytest

from auth_service.tests.helpers import login_user


async def create_skill(client, headers, *, name: str, slug: str, group: str = "backend") -> dict:
    response = await client.post(
        "/skills/",
        json={"name": name, "slug": slug, "group": group},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_skill_catalog_create_search_and_uniqueness(client, verified_user):
    user_data, _ = verified_user
    tokens = await login_user(client, user_data["email"], user_data["password"])
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    python = await create_skill(client, headers, name="  Python  ", slug=" PyThon ", group=" BackEnd ")
    await create_skill(client, headers, name="FastAPI", slug="fastapi")
    await create_skill(client, headers, name="Pixel Art", slug="pixel-art", group="art")

    assert python["name"] == "Python"
    assert python["group"] == "backend"

    duplicate = await client.post(
        "/skills/",
        json={"name": "Python", "slug": "python-duplicate", "group": "backend"},
        headers=headers,
    )
    assert duplicate.status_code == 409

    search = await client.get("/skills/", params={"search": "py", "group": "backend"})
    assert search.status_code == 200
    assert [item["slug"] for item in search.json()] == ["python"]

    art = await client.get("/skills/", params={"group": "art"})
    assert [item["slug"] for item in art.json()] == ["pixel-art"]


@pytest.mark.asyncio
async def test_user_skill_lifecycle_and_public_profile(client, verified_user):
    user_data, user = verified_user
    tokens = await login_user(client, user_data["email"], user_data["password"])
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    python = await create_skill(client, headers, name="Python", slug="python")
    fastapi = await create_skill(client, headers, name="FastAPI", slug="fastapi")

    added = await client.post(
        "/users/me/skills",
        json={"skill_id": python["id"], "level": 3},
        headers=headers,
    )
    assert added.status_code == 201
    assert added.json() == [{"skill": python, "level": 3}]

    duplicate = await client.post(
        "/users/me/skills",
        json={"skill_id": python["id"], "level": 2},
        headers=headers,
    )
    assert duplicate.status_code == 409

    replaced = await client.put(
        "/users/me/skills",
        json={
            "skills": [
                {"skill_id": python["id"], "level": 4},
                {"skill_id": fastapi["id"], "level": 2},
            ]
        },
        headers=headers,
    )
    assert replaced.status_code == 200
    assert [(item["skill"]["slug"], item["level"]) for item in replaced.json()] == [
        ("fastapi", 2),
        ("python", 4),
    ]

    profile = await client.get(f"/users/{user.id}")
    assert profile.status_code == 200
    assert [(item["skill"]["slug"], item["level"]) for item in profile.json()["skills"]] == [
        ("fastapi", 2),
        ("python", 4),
    ]

    edited_profile = await client.patch(
        "/users/me",
        json={"bio": "I build backend systems"},
        headers=headers,
    )
    assert edited_profile.status_code == 200
    assert [(item["skill"]["slug"], item["level"]) for item in edited_profile.json()["skills"]] == [
        ("fastapi", 2),
        ("python", 4),
    ]

    updated = await client.patch(
        f"/users/me/skills/{fastapi['id']}",
        json={"level": 3},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()[0]["level"] == 3

    deleted = await client.delete(
        f"/users/me/skills/{python['id']}",
        headers=headers,
    )
    assert deleted.status_code == 204

    current = await client.get("/users/me/skills", headers=headers)
    assert [(item["skill"]["slug"], item["level"]) for item in current.json()] == [
        ("fastapi", 3),
    ]


@pytest.mark.asyncio
async def test_replace_user_skills_validates_all_ids_before_mutation(client, verified_user):
    user_data, _ = verified_user
    tokens = await login_user(client, user_data["email"], user_data["password"])
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    python = await create_skill(client, headers, name="Python", slug="python")

    await client.post(
        "/users/me/skills",
        json={"skill_id": python["id"], "level": 2},
        headers=headers,
    )

    unknown = await client.put(
        "/users/me/skills",
        json={"skills": [{"skill_id": str(uuid4()), "level": 1}]},
        headers=headers,
    )
    assert unknown.status_code == 404

    unchanged = await client.get("/users/me/skills", headers=headers)
    assert unchanged.json() == [{"skill": python, "level": 2}]

    duplicate_ids = await client.put(
        "/users/me/skills",
        json={
            "skills": [
                {"skill_id": python["id"], "level": 1},
                {"skill_id": python["id"], "level": 4},
            ]
        },
        headers=headers,
    )
    assert duplicate_ids.status_code == 422

    invalid_level = await client.post(
        "/users/me/skills",
        json={"skill_id": python["id"], "level": 5},
        headers=headers,
    )
    assert invalid_level.status_code == 422


@pytest.mark.asyncio
async def test_user_skill_missing_resources_return_404(client, verified_user):
    user_data, _ = verified_user
    tokens = await login_user(client, user_data["email"], user_data["password"])
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    missing_skill_id = uuid4()

    add_missing = await client.post(
        "/users/me/skills",
        json={"skill_id": str(missing_skill_id), "level": 1},
        headers=headers,
    )
    assert add_missing.status_code == 404

    update_missing = await client.patch(
        f"/users/me/skills/{missing_skill_id}",
        json={"level": 2},
        headers=headers,
    )
    assert update_missing.status_code == 404

    delete_missing = await client.delete(
        f"/users/me/skills/{missing_skill_id}",
        headers=headers,
    )
    assert delete_missing.status_code == 404

    unknown_user = await client.get(f"/users/{uuid4()}/skills")
    assert unknown_user.status_code == 404

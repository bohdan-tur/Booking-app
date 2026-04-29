import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):

    user_payload = {
        "username": "Bohdan",
        "email": "test_user@example.com",
        "password": "password12345"
    }


    response = await client.post("/users/new", json=user_payload)

    assert response.status_code == 201
    assert response.json()["email"] == "test_user@example.com"


@pytest.mark.asyncio
async def test_login_user(client: AsyncClient):
    user_payload = {
        "username": "test_user@example.com",
        "password": "password12345"
    }
    await client.post("/users/new", json=user_payload)


    response = await client.post("/auth/login", data=user_payload)

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


from httpx import AsyncClient
import pytest
from sqlalchemy import insert
from app.models.user_model import Users
from app.core.security import create_access_token
from datetime import timedelta



@pytest.mark.asyncio
async def test_get_user_me(authenticated_client: AsyncClient):

    response = await authenticated_client.get("/users/me")

    assert response.status_code == 200

    assert response.json()["username"] == "AdminTest"


@pytest.mark.asyncio
async def test_get_user_by_id(authenticated_client: AsyncClient):

    new_user_data = {
        "email": "test_person@example.com",
        "username": "TestPerson",
        "password": "securepassword123"
    }

    create_res = await authenticated_client.post("/users/new", json=new_user_data)
    assert create_res.status_code == 201

    new_user_id = create_res.json()["id"]


    response = await authenticated_client.get(f"/users/{new_user_id}")

    assert response.status_code == 200
    assert response.json()["username"] == "TestPerson"




@pytest.mark.asyncio
async def test_create_user(authenticated_client: AsyncClient):


    new_user_data = {
         "email": "ivan.tech@example.com",
         "username": "IvanDeveloper",
         "password": "SuperSecretPassword123!"}


    response = await authenticated_client.post("/users/new",json=new_user_data)

    assert response.status_code == 201




@pytest.mark.asyncio
async def test_get_all_users(authenticated_client: AsyncClient):
    response = await authenticated_client.get("/users/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_change_user_role(client: AsyncClient):

    user_token = create_access_token(data={"sub": "user@test.com", "role": "user"}, expires_delta=timedelta(minutes=5))
    headers = {"Authorization": f"Bearer {user_token}"}

    response = await client.patch("/users/admin", headers=headers)
    assert response.status_code in [403, 401]


@pytest.mark.asyncio
async def test_delete_user_by_admin(authenticated_client: AsyncClient, db_session):

    new_user_id = (await db_session.execute(
        insert(Users).values(
            username="to_delete",
            email="delete@me.com",
            password_hash="hash",
            role="user"
        ).returning(Users.id)
    )).scalar()
    await db_session.commit()


    response = await authenticated_client.delete(f"/usersremove/{new_user_id}")
    assert response.status_code in [200, 204]


    check = await authenticated_client.get(f"/users/{new_user_id}")
    assert check.status_code == 404


@pytest.mark.asyncio
async def test_change_password(authenticated_client: AsyncClient):

    password_param = {"new_password": "new_secure_password123"}
    response = await authenticated_client.patch("/users/me/password", params=password_param)


    assert response.status_code == 200
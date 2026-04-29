from httpx import AsyncClient
import pytest
from sqlalchemy import insert,delete
from app.models.room_model import  Rooms
from app.models.booking_model import Bookings


@pytest.mark.asyncio
async def test_room_creation(authenticated_client):




    room_data = {
        "amenities": "Free Wi-Fi, Air Conditioning, Flat-screen TV, Daily Housekeeping",
        "capacity": 2,
        "description": "A comfortable and quiet room perfect for couples or business travelers.",
        "location": "Lviv, Svobody Avenue, 15",
        "name": "Standard Double Room",
        "price": 1200,
        "quantity": 10
    }

    response = await authenticated_client.post("/rooms/",json=room_data)


    assert response.status_code == 201

@pytest.mark.asyncio
async def test_rooms_acquirement(client: AsyncClient, db_session):
    await db_session.execute(delete(Bookings))
    await db_session.execute(delete(Rooms))
    await db_session.commit()
    rooms_data = [
        {
            "name": "Economy Single Room",
            "price": 600,
            "capacity": 1,
            "description": "Small and cozy",
            "location": "Lviv",
            "amenities": "WiFi",
            "quantity": 5
        },
        {
            "name": "Luxury Double Room",
            "price": 2500,
            "capacity": 2,
            "description": "King size bed",
            "location": "Lviv",
            "amenities": "WiFi, Jacuzzi",
            "quantity": 2
        }
    ]


    await db_session.execute(insert(Rooms), rooms_data)
    await db_session.commit()


    response = await client.get("/rooms/available")


    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["name"] == "Economy Single Room"
    assert data[1]["name"] == "Luxury Double Room"





@pytest.mark.asyncio
async def test_get_specific_room_success(client: AsyncClient, db_session):
    await db_session.execute(delete(Bookings))
    await db_session.execute(delete(Rooms))

    room_id = (await db_session.execute(
        insert(Rooms).values(
            name="Specific Room",
            price=1200,
            capacity=2,
            location="Lviv",
            quantity=1,
            amenities="TV, WiFi"
        ).returning(Rooms.id)
    )).scalar()
    await db_session.commit()

    response = await client.get(f"/rooms/{room_id}/available")

    assert response.status_code == 200
    assert response.json()["name"] == "Specific Room"
    assert response.json()["id"] == room_id


@pytest.mark.asyncio
async def test_get_room_not_found(client: AsyncClient):
    response = await client.get("/rooms/99999/available")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_room_as_admin(authenticated_client: AsyncClient, db_session):
    room_id = (await db_session.execute(
        insert(Rooms).values(
            name="Room to Delete",
            price=500,
            capacity=1,
            location="Kyiv",
            quantity=1,
            amenities="None"
        ).returning(Rooms.id)
    )).scalar()
    await db_session.commit()

    response = await authenticated_client.delete(f"/rooms/{room_id}")

    assert response.status_code in [200, 204]

    check_response = await authenticated_client.get(f"/rooms/{room_id}/available")
    assert check_response.status_code == 404


@pytest.mark.asyncio
async def test_update_room_price(authenticated_client: AsyncClient, db_session):
    room_id = (await db_session.execute(
        insert(Rooms).values(
            name="Price Test Room",
            price=1000,
            capacity=2,
            location="Odessa",
            quantity=3,
            amenities="Mini-bar"
        ).returning(Rooms.id)
    )).scalar()
    await db_session.commit()

    update_data = {
        "price": 1500,
        "name": "Updated Price Room",
        "capacity": 2,
        "location": "Odessa",
        "quantity": 3,
        "amenities": "Mini-bar"
    }

    response = await authenticated_client.put(f"/rooms/{room_id}", json=update_data)

    assert response.status_code == 200

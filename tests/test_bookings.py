import pytest
from httpx import AsyncClient
from sqlalchemy import insert, select
from datetime import datetime, timedelta
from app.models.room_model import Rooms
from app.models.booking_model import Bookings


@pytest.mark.asyncio
async def test_book_room_success(authenticated_client: AsyncClient, db_session):
    room_stmt = insert(Rooms).values(
        name="Luxury Double Room",
        price=2500,
        capacity=2,
        description="King size bed",
        location="Lviv",
        amenities="WiFi, Jacuzzi",
        quantity=2
    ).returning(Rooms.id)

    result = await db_session.execute(room_stmt)
    room_id = result.scalar()
    await db_session.commit()

    start = datetime.now() + timedelta(days=1)
    end = datetime.now() + timedelta(days=3)

    params = {
        "room_id_to_book": room_id,
        "start_time": start.isoformat(),
        "end_time": end.isoformat()
    }

    response = await authenticated_client.post("/bookings/book_room/", params=params)

    assert response.status_code == 201
    assert response.json()["room_id"] == room_id

    db_res = await db_session.execute(select(Bookings).where(Bookings.room_id == room_id))
    assert db_res.scalar() is not None


@pytest.mark.asyncio
async def test_get_all_bookings(authenticated_client: AsyncClient):
    response = await authenticated_client.get("/bookings/all_booking/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_single_booking(authenticated_client: AsyncClient, db_session):
    room_id = (await db_session.execute(insert(Rooms).values(
        name="Single Room", price=500, capacity=1, location="Lviv", quantity=1, amenities="WiFi"
    ).returning(Rooms.id))).scalar()

    booking_id = (await db_session.execute(insert(Bookings).values(
        room_id=room_id,
        user_id=1,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(days=1)
    ).returning(Bookings.id))).scalar()
    await db_session.commit()

    response = await authenticated_client.get(f"/bookingssingle/{booking_id}/")
    assert response.status_code == 200
    assert response.json()["id"] == booking_id


@pytest.mark.asyncio
async def test_cancel_booking(authenticated_client: AsyncClient, db_session):
    room_id = (await db_session.execute(insert(Rooms).values(
        name="Room to Delete", price=100, capacity=1, location="Lviv", quantity=1, amenities="None"
    ).returning(Rooms.id))).scalar()

    booking_id = (await db_session.execute(insert(Bookings).values(
        room_id=room_id,
        user_id=1,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(days=1)
    ).returning(Bookings.id))).scalar()
    await db_session.commit()

    response = await authenticated_client.delete(f"/bookings/{booking_id}/")
    assert response.status_code in [200, 204]

    check = await db_session.execute(select(Bookings).where(Bookings.id == booking_id))
    assert check.scalar() is None


@pytest.mark.asyncio
async def test_update_booking(authenticated_client: AsyncClient, db_session):
    room_id = (await db_session.execute(insert(Rooms).values(
        name="Update Room", price=100, capacity=1, location="Lviv", quantity=1, amenities="None"
    ).returning(Rooms.id))).scalar()

    booking_id = (await db_session.execute(insert(Bookings).values(
        room_id=room_id,
        user_id=1,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(days=1)
    ).returning(Bookings.id))).scalar()
    await db_session.commit()

    new_start = datetime.now() + timedelta(days=5)
    new_end = datetime.now() + timedelta(days=7)

    update_data = {
        "start_time": (datetime.now() + timedelta(days=5)).replace(microsecond=0).isoformat(),
        "end_time": (datetime.now() + timedelta(days=7)).replace(microsecond=0).isoformat()
    }
    response = await authenticated_client.patch(f"/bookings/change_booking/{booking_id}/", json=update_data)
    assert response.status_code == 200
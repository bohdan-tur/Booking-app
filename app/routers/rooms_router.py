from datetime import datetime, UTC
from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException, Path
from sqlalchemy import select, update, delete, and_, not_
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import DbSession
from app.db.database import get_db
from app.dependencies import allow_admin
from app.models.booking_model import Bookings
from app.models.room_model import Rooms
from app.schemas.room_schema import RoomCreate, RoomOut

db_dependency = Annotated[AsyncSession, Depends(get_db)]

router = APIRouter(tags=['Rooms'])


@router.get("/available", status_code=status.HTTP_200_OK)
async def get_all_not_booked_rooms(db: db_dependency):
    now = datetime.now(UTC).replace(tzinfo=None)
    occupied_ids = select(Bookings.room_id).filter(
        and_(Bookings.start_time <= now, Bookings.end_time >= now)
    )
    query = select(Rooms).filter(not_(Rooms.id.in_(occupied_ids)))
    rooms = await db.execute(query)
    res = rooms.scalars().all()

    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="There aren't available rooms right now")
    return res


@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_booked_rooms(db: db_dependency):
    now = datetime.now(UTC).replace(tzinfo=None)
    occupied_ids = select(Bookings.room_id).filter(
        and_(Bookings.start_time <= now, Bookings.end_time >= now)
    )
    query = select(Rooms).filter(Rooms.id.in_(occupied_ids))
    rooms = await db.execute(query)
    res = rooms.scalars().all()

    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="There aren't booked rooms right now")
    return res


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=RoomOut)
async def add_room(room_data: RoomCreate, db: db_dependency, current_user=Depends(allow_admin)):
    new_room = Rooms(
        name=room_data.name,
        description=room_data.description,
        price=room_data.price,
        capacity=room_data.capacity,
        amenities=room_data.amenities,
        quantity=room_data.quantity,
        location=room_data.location
    )
    db.add(new_room)
    await db.commit()
    await db.refresh(new_room)
    return new_room


@router.get("/{room_id}/available", status_code=status.HTTP_200_OK)
async def get_not_booked_room(db: db_dependency, room_id: Annotated[int, Path(gt=0)]):
    now = datetime.now(UTC).replace(tzinfo=None)
    is_occupied = select(Bookings.room_id).filter(
        and_(
            Bookings.room_id == room_id,
            Bookings.start_time <= now,
            Bookings.end_time >= now
        )
    )
    query = select(Rooms).filter(and_(Rooms.id == room_id, not_(Rooms.id.in_(is_occupied))))
    res = (await db.execute(query)).scalar()

    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="There isn't such room or it is booked")
    return res


@router.get("/{room_id}", status_code=status.HTTP_200_OK)
async def get_booked_room(db: db_dependency, room_id: Annotated[int, Path(gt=0)]):
    now = datetime.now(UTC).replace(tzinfo=None)
    is_occupied = select(Bookings.room_id).filter(
        and_(
            Bookings.room_id == room_id,
            Bookings.start_time <= now,
            Bookings.end_time >= now
        )
    )
    query = select(Rooms).filter(and_(Rooms.id == room_id, Rooms.id.in_(is_occupied)))
    res = (await db.execute(query)).scalar()

    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room is not booked")
    return res


@router.put('/{room_id}', status_code=status.HTTP_200_OK)
async def change_room(
        db: db_dependency,
        room_id: Annotated[int, Path(gt=0)],
        room_data: RoomCreate,
        current_user=Depends(allow_admin)
):
    changed_room = await db.execute(
        update(Rooms)
        .filter(Rooms.id == room_id)
        .values(
            name=room_data.name,
            description=room_data.description,
            price=room_data.price,
            capacity=room_data.capacity,
            amenities=room_data.amenities,
            quantity=room_data.quantity,
            location=room_data.location
        ).returning(Rooms.id)
    )

    res = changed_room.scalar()
    if res is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    await db.commit()
    return {"status": "success"}


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room_by_id(db: db_dependency, room_id: Annotated[int, Path(gt=0)], current_user=Depends(allow_admin)):
    deleted_room = await db.execute(delete(Rooms).filter(Rooms.id == room_id).returning(Rooms.id))
    res = deleted_room.scalars().first()

    if res is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Room with id {room_id} not found")

    await db.commit()
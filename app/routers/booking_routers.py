from datetime import datetime
from typing import Annotated
from app.dependencies import DbSession
from fastapi import APIRouter,Depends, HTTPException, status
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession


from app.dependencies import get_current_user, allow_admin_and_manager
from app.models.booking_model import Bookings
from app.models.role_model import Role
from app.models.user_model import Users
from app.schemas.booking_schema import BookingOut, BookingUpdate
from app.services.booking_check import create_booking_if_available
from app.tasks import process_booking_creation, process_booking_cancellation

router = APIRouter(tags=['Bookings'])


@router.post("/book_room/", status_code=status.HTTP_201_CREATED, response_model=BookingOut)
async def book_room(
    room_id_to_book: int,
    db: DbSession,
    user: Annotated[Users, Depends(get_current_user)],
    start_time: datetime,
    end_time: datetime
):
    booking = await create_booking_if_available(
        db=db,
        room_id=room_id_to_book,
        user_id=user.id,
        start_time=start_time,
        end_time=end_time
    )
    
    # Запускаємо Celery задачу для відправки email підтвердження
    process_booking_creation.delay(
        booking_id=booking.id,
        user_id=user.id,
        room_id=room_id_to_book,
        start_time=start_time,
        end_time=end_time
    )
    
    return booking


@router.get("/all_booking/", status_code=status.HTTP_200_OK)
async def get_all_bookings(db: DbSession):
    bookings = await db.execute(select(Bookings))
    result = bookings.scalars().all()

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="There are not any bookings.")

    return result


@router.get("/single/{booking_id}/", status_code=status.HTTP_200_OK)
async def get_single_booking(db: DbSession, booking_id: int):
    bookings = await db.execute(select(Bookings).filter(Bookings.id == booking_id))
    result = bookings.scalars().first()

    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

    return result


@router.patch("/change_booking/{booking_id}/", status_code=status.HTTP_200_OK)
async def update_booking(
    booking_to_update: BookingUpdate,
    db: DbSession,
    booking_id: int,
    current_user=Depends(allow_admin_and_manager)
):
    updated_booking = (
        update(Bookings)
        .filter(Bookings.id == booking_id)
        .values(
            start_time=booking_to_update.start_time,
            end_time=booking_to_update.end_time,
        )
    )

    await db.execute(updated_booking)
    await db.commit()
    return {"status": "success"}


@router.delete("/{id}/", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking(
    id: int,
    db: DbSession,
    current_user: Annotated[Users, Depends(get_current_user)]
):
    booking_to_delete = await db.execute(delete(Bookings).where(Bookings.id == id).returning(Bookings))
    result = booking_to_delete.scalars().first()

    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if result.user_id != current_user.id and current_user.role == Role.user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can not cancel others booking")

    await db.commit()
    
    # Запускаємо Celery задачу для відправки email про скасування
    process_booking_cancellation.delay(
        booking_id=id,
        user_id=result.user_id
    )
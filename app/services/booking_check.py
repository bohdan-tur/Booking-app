from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from fastapi import Depends, HTTPException
from app.db.database import get_db
from datetime import datetime
from app.models.booking_model import Bookings
from app.dependencies import DbSession

async def create_booking_if_available(db: DbSession, room_id: int, user_id:int,
                                      start_time: datetime, end_time: datetime):

        room = await  db.execute(select(Bookings)
                                 .filter(
            Bookings.room_id == room_id,
            Bookings.start_time < end_time,
            Bookings.end_time > start_time).with_for_update()

                                 )

        existing = room.scalars().first()


        if  existing:
             raise HTTPException(status_code=400, detail="Room is already booked")

        booking = Bookings(

    room_id=room_id,
    start_time=start_time,
    end_time=end_time,
    user_id=user_id
                         )
        db.add(booking)
        await db.commit()
        await db.refresh(booking)

        return booking


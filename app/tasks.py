from celery import Celery
from app.celery_app import celery_app
from app.core.email import send_booking_confirmation_email, send_booking_cancellation_email, send_booking_reminder_email
from app.db.database import AsyncSessionLocal
from sqlalchemy import select, update, delete
from datetime import datetime, timedelta
from app.models.booking_model import Bookings
from app.models.user_model import Users
from app.models.room_model import Rooms
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def process_booking_creation(self, booking_id: int, user_id: int, room_id: int, start_time: datetime, end_time: datetime):
    """
    Обробка створення бронювання (включаючи email сповіщення)
    """
    async def process_booking():
        async with AsyncSessionLocal() as session:
            try:
                # Отримуємо дані бронювання з бази
                stmt = select(Bookings, Users, Rooms).join(Users).join(Rooms).where(Bookings.id == booking_id)
                result = await session.execute(stmt)
                booking_data = result.first()
                
                if not booking_data:
                    logger.error(f"Бронювання {booking_id} не знайдено")
                    return {"status": "error", "message": "Бронювання не знайдено"}
                
                booking, user, room = booking_data
                
                # Відправляємо email підтвердження
                email_sent = send_booking_confirmation_email(
                    user_email=user.email,
                    user_name=user.username,
                    booking_id=booking.id,
                    room_name=room.name,
                    start_time=booking.start_time,
                    end_time=booking.end_time
                )
                
                if email_sent:
                    logger.info(f"Email підтвердження відправлено для бронювання {booking_id}")
                    return {"status": "success", "email_sent": True}
                else:
                    logger.error(f"Не вдалося відправити email для бронювання {booking_id}")
                    return {"status": "success", "email_sent": False}
                    
            except Exception as exc:
                logger.error(f"Помилка обробки бронювання {booking_id}: {exc}")
                if self.request.retries < self.max_retries:
                    raise self.retry(countdown=60 * (self.request.retries + 1))
                return {"status": "error", "message": str(exc)}
    
    import asyncio
    return asyncio.run(process_booking())

@celery_app.task(bind=True, max_retries=3)
def process_booking_cancellation(self, booking_id: int, user_id: int):
    """
    Обробка скасування бронювання (включаючи email сповіщення)
    """
    async def process_cancellation():
        async with AsyncSessionLocal() as session:
            try:
                # Отримуємо дані користувача
                stmt = select(Users).where(Users.id == user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                if not user:
                    logger.error(f"Користувача {user_id} не знайдено")
                    return {"status": "error", "message": "Користувача не знайдено"}
                
                # Відправляємо email про скасування
                email_sent = send_booking_cancellation_email(
                    user_email=user.email,
                    user_name=user.username,
                    booking_id=booking_id
                )
                
                if email_sent:
                    logger.info(f"Email про скасування відправлено для бронювання {booking_id}")
                    return {"status": "success", "email_sent": True}
                else:
                    logger.error(f"Не вдалося відправити email про скасування {booking_id}")
                    return {"status": "success", "email_sent": False}
                    
            except Exception as exc:
                logger.error(f"Помилка обробки скасування бронювання {booking_id}: {exc}")
                if self.request.retries < self.max_retries:
                    raise self.retry(countdown=60 * (self.request.retries + 1))
                return {"status": "error", "message": str(exc)}
    
    import asyncio
    return asyncio.run(process_cancellation())

@celery_app.task
def update_expired_bookings():
    """
    Оновлення статусів прострочених бронювань (active -> expired)
    """
    async def update_statuses():
        async with AsyncSessionLocal() as session:
            try:
                current_time = datetime.utcnow()
                
                # Оновлюємо статуси прострочених бронювань
                stmt = update(Bookings).where(
                    Bookings.end_time < current_time,
                    Bookings.status == "active"
                ).values(status="expired")
                
                result = await session.execute(stmt)
                await session.commit()
                
                updated_count = result.rowcount
                if updated_count > 0:
                    logger.info(f"Оновлено {updated_count} статусів бронювань на 'expired'")
                
                return updated_count
                
            except Exception as e:
                logger.error(f"Помилка оновлення статусів бронювань: {e}")
                await session.rollback()
                return 0
    
    import asyncio
    return asyncio.run(update_statuses())

@celery_app.task
def send_daily_reminders():
    """
    Відправка щоденних нагадувань про бронювання на завтра
    """
    async def send_reminders():
        async with AsyncSessionLocal() as session:
            try:
                # Бронювання, які починаються завтра
                tomorrow = datetime.utcnow() + timedelta(days=1)
                start_of_tomorrow = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_tomorrow = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                stmt = select(Bookings, Users, Rooms).join(Users).join(Rooms).where(
                    Bookings.start_time >= start_of_tomorrow,
                    Bookings.start_time <= end_of_tomorrow,
                    Bookings.status == "active"
                )
                
                result = await session.execute(stmt)
                bookings_data = result.all()
                
                reminders_sent = 0
                for booking, user, room in bookings_data:
                    try:
                        email_sent = send_booking_reminder_email(
                            user_email=user.email,
                            user_name=user.username,
                            booking_id=booking.id,
                            room_name=room.name,
                            start_time=booking.start_time
                        )
                        
                        if email_sent:
                            reminders_sent += 1
                            logger.info(f"Нагадування відправлено для бронювання {booking.id}")
                        else:
                            logger.error(f"Не вдалося відправити нагадування для бронювання {booking.id}")
                            
                    except Exception as e:
                        logger.error(f"Помилка відправки нагадування для бронювання {booking.id}: {e}")
                
                if reminders_sent > 0:
                    logger.info(f"Відправлено {reminders_sent} нагадувань")
                
                return reminders_sent
                
            except Exception as e:
                logger.error(f"Помилка відправки нагадувань: {e}")
                return 0
    
    import asyncio
    return asyncio.run(send_reminders())

@celery_app.task
def cleanup_old_bookings():
    """
    Очищення старих бронювань (старших 1 року зі статусом 'expired')
    """
    async def cleanup():
        async with AsyncSessionLocal() as session:
            try:
                # Видаляємо бронювання старші 1 року
                one_year_ago = datetime.utcnow() - timedelta(days=365)
                
                stmt = delete(Bookings).where(
                    Bookings.end_time < one_year_ago,
                    Bookings.status == "expired"
                )
                
                result = await session.execute(stmt)
                await session.commit()
                
                deleted_count = result.rowcount
                if deleted_count > 0:
                    logger.info(f"Видалено {deleted_count} старих бронювань")
                
                return deleted_count
                
            except Exception as e:
                logger.error(f"Помилка очищення старих бронювань: {e}")
                await session.rollback()
                return 0
    
    import asyncio
    return asyncio.run(cleanup())

@celery_app.task
def generate_daily_statistics():
    """
    Генерація щоденної статистики для адмінів
    """
    async def generate_stats():
        async with AsyncSessionLocal() as session:
            try:
                today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                tomorrow = today + timedelta(days=1)
                
                # Статистика за сьогодні
                stmt = select(Bookings).where(
                    Bookings.start_time >= today,
                    Bookings.start_time < tomorrow
                )
                result = await session.execute(stmt)
                today_bookings = len(result.scalars().all())
                
                # Активні бронювання
                stmt = select(Bookings).where(Bookings.status == "active")
                result = await session.execute(stmt)
                active_bookings = len(result.scalars().all())
                
                # Завершені бронювання за останні 7 днів
                week_ago = datetime.utcnow() - timedelta(days=7)
                stmt = select(Bookings).where(
                    Bookings.end_time >= week_ago,
                    Bookings.status == "completed"
                )
                result = await session.execute(stmt)
                completed_bookings = len(result.scalars().all())
                
                # Відправляємо звіт адмінам
                stmt = select(Users).where(Users.role == "admin")
                result = await session.execute(stmt)
                admins = result.scalars().all()
                
                report = f"""
📊 Щоденна звіт ({datetime.utcnow().strftime('%d.%m.%Y')})

📈 Статистика:
• Нових бронювань сьогодні: {today_bookings}
• Активних бронювань: {active_bookings}
• Завершено за останні 7 днів: {completed_bookings}

Детальніша статистика доступна в адмін панелі.
"""
                
                from app.core.email import send_email
                
                for admin in admins:
                    try:
                        send_email(
                            to_email=admin.email,
                            subject=f"📊 Щоденна звіт - {datetime.utcnow().strftime('%d.%m.%Y')}",
                            body=report
                        )
                        logger.info(f"Щоденний звіт відправлено адміну {admin.email}")
                    except Exception as e:
                        logger.error(f"Помилка відправки щоденного звіту адміну {admin.email}: {e}")
                
                return {
                    "today_bookings": today_bookings,
                    "active_bookings": active_bookings,
                    "completed_bookings": completed_bookings,
                    "admins_notified": len(admins)
                }
                
            except Exception as e:
                logger.error(f"Помилка генерації щоденної статистики: {e}")
                return {"error": str(e)}
    
    import asyncio
    return asyncio.run(generate_stats())

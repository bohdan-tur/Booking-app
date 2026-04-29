from celery import Celery
from app.core.config import settings
from app.core.email import send_email
from app.db.database import AsyncSessionLocal
from sqlalchemy import select, update
from datetime import datetime, timedelta
from app.models.booking_model import Bookings
from app.models.user_model import Users
import logging

logger = logging.getLogger(__name__)

# Створення Celery інстансу
celery_app = Celery(
    "booking_app",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.tasks']
)

# Налаштування Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        # Щодня о 00:00 оновлюємо статуси бронювань
        'update-booking-statuses': {
            'task': 'app.tasks.update_booking_statuses',
            'schedule': 3600.0,  # Кожну годину
        },
        # Щодня о 09:00 відправляємо нагадування
        'send-booking-reminders': {
            'task': 'app.tasks.send_booking_reminders',
            'schedule': 3600.0,  # Кожну годину
        },
        # Щотижня генеруємо звіти
        'generate-weekly-reports': {
            'task': 'app.tasks.generate_weekly_reports',
            'schedule': 604800.0,  # Кожні 7 днів
        },
    },
)

@celery_app.task(bind=True, max_retries=3)
def send_booking_confirmation_email(self, booking_id: int, user_email: str, user_name: str):
    """Відправка email підтвердження бронювання"""
    try:
        subject = "Підтвердження бронювання"
        body = f"""
        Шановний(а) {user_name},
        
        Ваше бронювання №{booking_id} успішно створено!
        
        Деталі бронювання доступні у вашому особистому кабінеті.
        
        Дякуємо, що обрали наш готель!
        """
        
        send_email(
            to_email=user_email,
            subject=subject,
            body=body
        )
        
        logger.info(f"Email підтвердження відправлено для бронювання {booking_id}")
        return {"status": "success", "message": "Email відправлено"}
        
    except Exception as exc:
        logger.error(f"Помилка відправки email для бронювання {booking_id}: {exc}")
        # Retry логіка
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1))
        return {"status": "error", "message": "Не вдалося відправити email"}

@celery_app.task(bind=True, max_retries=3)
def send_booking_cancellation_email(self, booking_id: int, user_email: str, user_name: str):
    """Відправка email про скасування бронювання"""
    try:
        subject = "Скасування бронювання"
        body = f"""
        Шановний(а) {user_name},
        
        Ваше бронювання №{booking_id} скасовано.
        
        Якщо ви не скасовували бронювання, будь ласка, зв'яжіться з нами.
        
        Дякуємо!
        """
        
        send_email(
            to_email=user_email,
            subject=subject,
            body=body
        )
        
        logger.info(f"Email про скасування відправлено для бронювання {booking_id}")
        return {"status": "success", "message": "Email відправлено"}
        
    except Exception as exc:
        logger.error(f"Помилка відправки email про скасування {booking_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1))
        return {"status": "error", "message": "Не вдалося відправити email"}

@celery_app.task
def update_booking_statuses():
    """Оновлення статусів бронювань (active -> completed)"""
    async def update_statuses():
        async with AsyncSessionLocal() as session:
            try:
                # Знаходимо всі активні бронювання, які вже закінчилися
                current_time = datetime.utcnow()
                
                stmt = update(Bookings).where(
                    Bookings.end_time < current_time,
                    Bookings.status == "active"
                ).values(status="completed")
                
                result = await session.execute(stmt)
                await session.commit()
                
                logger.info(f"Оновлено {result.rowcount} статусів бронювань на 'completed'")
                return result.rowcount
                
            except Exception as e:
                logger.error(f"Помилка оновлення статусів бронювань: {e}")
                await session.rollback()
                return 0
    
    import asyncio
    return asyncio.run(update_statuses())

@celery_app.task
def send_booking_reminders():
    """Відправка нагадувань про майбутні бронювання"""
    async def send_reminders():
        async with AsyncSessionLocal() as session:
            try:
                # Знаходимо бронювання, які починаються через 24 години
                tomorrow = datetime.utcnow() + timedelta(days=1)
                start_of_tomorrow = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_tomorrow = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                stmt = select(Bookings, Users).join(Users).where(
                    Bookings.start_time >= start_of_tomorrow,
                    Bookings.start_time <= end_of_tomorrow,
                    Bookings.status == "active"
                )
                
                result = await session.execute(stmt)
                bookings_users = result.all()
                
                reminders_sent = 0
                for booking, user in bookings_users:
                    try:
                        subject = "Нагадування про бронювання"
                        body = f"""
                        Шановний(а) {user.username},
                        
                        Нагадуємо, що ваше бронювання №{booking.id} починається завтра!
                        
                        Час заїзду: {booking.start_time.strftime('%Y-%m-%d %H:%M')}
                        
                        Чекаємо на вас!
                        """
                        
                        send_email(
                            to_email=user.email,
                            subject=subject,
                            body=body
                        )
                        
                        reminders_sent += 1
                        logger.info(f"Нагадування відправлено для бронювання {booking.id}")
                        
                    except Exception as e:
                        logger.error(f"Помилка відправки нагадування для бронювання {booking.id}: {e}")
                
                logger.info(f"Відправлено {reminders_sent} нагадувань")
                return reminders_sent
                
            except Exception as e:
                logger.error(f"Помилка відправки нагадувань: {e}")
                return 0
    
    import asyncio
    return asyncio.run(send_reminders())

@celery_app.task
def generate_weekly_reports():
    """Генерація щотижневих звітів для адмінів"""
    async def generate_reports():
        async with AsyncSessionLocal() as session:
            try:
                # Звіт за останній тиждень
                week_ago = datetime.utcnow() - timedelta(days=7)
                
                # Кількість нових бронювань
                stmt = select(Bookings).where(Bookings.start_time >= week_ago)
                result = await session.execute(stmt)
                new_bookings = len(result.scalars().all())
                
                # Кількість завершених бронювань
                stmt = select(Bookings).where(
                    Bookings.end_time >= week_ago,
                    Bookings.status == "completed"
                )
                result = await session.execute(stmt)
                completed_bookings = len(result.scalars().all())
                
                # Знаходимо адмінів
                stmt = select(Users).where(Users.role == "admin")
                result = await session.execute(stmt)
                admins = result.scalars().all()
                
                report = f"""
                Щотижневий звіт ({week_ago.strftime('%Y-%m-%d')} - {datetime.utcnow().strftime('%Y-%m-%d')})
                
                📊 Статистика:
                - Нових бронювань: {new_bookings}
                - Завершених бронювань: {completed_bookings}
                
                Детальніша статистика доступна в адмін панелі.
                """
                
                # Відправляємо звіт адмінам
                for admin in admins:
                    try:
                        send_email(
                            to_email=admin.email,
                            subject="Щотижневий звіт - Booking System",
                            body=report
                        )
                        logger.info(f"Звіт відправлено адміну {admin.email}")
                    except Exception as e:
                        logger.error(f"Помилка відправки звіту адміну {admin.email}: {e}")
                
                return {
                    "new_bookings": new_bookings,
                    "completed_bookings": completed_bookings,
                    "admins_notified": len(admins)
                }
                
            except Exception as e:
                logger.error(f"Помилка генерації звітів: {e}")
                return {"error": str(e)}
    
    import asyncio
    return asyncio.run(generate_reports())

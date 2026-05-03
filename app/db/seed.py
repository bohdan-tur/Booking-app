import asyncio
from sqlalchemy import select
from passlib.context import CryptContext

# Зверни увагу на імпорт сесії.
# Якщо у твоєму app.db.database вона називається інакше (напр., async_session або SessionLocal), зміни назву тут:
from app.db.database import AsyncSessionLocal

from app.models.role_model import Role
from app.models.user_model import Users

# Контекст для хешування пароля (типу argon2)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def seed_data():
    # Відкриваємо асинхронну сесію з базою
    async with AsyncSessionLocal() as session:
        print("⏳ Починаємо заповнення бази даних...")

        # 2. Створюємо тестового адміна
        # Шукаємо по username, як вимагає твоя форма авторизації
        result = await session.execute(select(Users).where(Users.username == "admin"))
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            print("👤 Створюємо користувача 'admin'...")
            admin_user = Users(
                username="admin",
                email="admin@booking.com",
                password_hash=get_password_hash("admin"),  # Пароль теж 'admin'
                role=Role.admin,  # Використовуємо enum значення
                is_active=True
            )
            session.add(admin_user)
        else:
            print("✅ Користувач 'admin' вже існує.")

        # Зберігаємо всі зміни в базу
        await session.commit()
        print("🎉 База успішно заповнена! Можеш логінитися в Swagger.")


if __name__ == "__main__":
    # Запускаємо асинхронну функцію
    asyncio.run(seed_data())
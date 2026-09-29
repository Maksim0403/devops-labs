import asyncio
import os
import random
import sys
from datetime import datetime, timedelta

# Додаємо поточну директорію в шлях пошуку модулів, щоб бачити 'app'
sys.path.append(os.getcwd())

from faker import Faker
from sqlmodel import select

from app.core.security import get_password_hash

# Імпорт інструментів БД та енумів
from app.db.session import SessionLocal
from app.enums import OrderStatus, UserRole
from app.models.order import Order
from app.models.route import Route
from app.models.shipment import Shipment

# Імпорт моделей для ініціалізації маперів SQLAlchemy
from app.models.user import User
from app.models.vehicle import Vehicle

# Ініціалізація Faker з українською локалізацією
fake = Faker("uk_UA")


async def seed_db():
    print("🌱 Початок заповнення бази даних...")

    async with SessionLocal() as session:
        # 1. Створення Менеджера
        manager = User(
            email="manager@logiflow.com",
            hashed_password=get_password_hash("password123"),
            role=UserRole.MANAGER,
            full_name="Олександр Адмін",
            phone_number="+380441112233",
        )
        session.add(manager)
        print(
            "👤 Створено менеджера (login: manager@logiflow.com / "
            "pass: password123)"
        )

        # 2. Створення Водіїв та Автомобілів
        drivers = []
        truck_data = [
            ("Volvo", "FH16", 20000),
            ("Scania", "R500", 18000),
            ("MAN", "TGX", 15000),
            ("DAF", "XF", 22000),
            ("Mercedes-Benz", "Actros", 19000),
        ]

        for i, (brand, model, weight) in enumerate(truck_data):
            driver = User(
                email=f"driver{i + 1}@logiflow.com",
                hashed_password=get_password_hash("password123"),
                role=UserRole.DRIVER,
                full_name=fake.name(),
                phone_number=f"+38067{random.randint(1000000, 9999999)}",
            )
            session.add(driver)
            await session.flush()  # Отримуємо ID водія
            drivers.append(driver)

            vehicle = Vehicle(
                driver_id=driver.id,
                brand=brand,
                model=model,
                license_plate=f"AA{random.randint(1000, 9999)}KH",
                max_weight=weight,
                max_volume=round(weight / 250, 1),
                fuel_consumption=random.uniform(28.0, 35.0),
                fuel_price=54.90,
                current_mileage=random.randint(50000, 250000),
                maintenance_interval=30000,
            )
            session.add(vehicle)
        print(f"🚚 Створено {len(drivers)} водіїв та їх вантажівок")

        # 3. Створення Клієнтів
        clients = []
        for i in range(5):
            client = User(
                email=f"client{i + 1}@gmail.com",
                hashed_password=get_password_hash("password123"),
                role=UserRole.CLIENT,
                full_name=fake.name(),
                phone_number=f"+38050{random.randint(1000000, 9999999)}",
            )
            session.add(client)
            await session.flush()
            clients.append(client)
        print(f"👥 Створено {len(clients)} клієнтів")

        # 4. Створення Замовлень та Маршрутів
        cities = [
            "Київ",
            "Львів",
            "Одеса",
            "Дніпро",
            "Харків",
            "Вінниця",
            "Полтава",
            "Житомир",
        ]
        categories = [
            "будматеріалів",
            "продуктів харчування",
            "техніки",
            "меблів",
            "запчастин",
        ]

        for i in range(15):
            origin = random.choice(cities)
            destination = random.choice([c for c in cities if c != origin])
            status = random.choice(list(OrderStatus))

            order = Order(
                title=f"Доставка {random.choice(categories)}",
                description=f"Перевезення вантажу за маршрутом "
                f"{origin} - {destination}. " + fake.sentence(),
                origin_address=f"{origin}, вул. {fake.street_name()}, "
                f"{fake.building_number()}",
                destination_address=f"{destination},"
                f" вул. {fake.street_name()}, "
                f"{fake.building_number()}",
                weight=random.uniform(1000, 10000),
                distance=random.uniform(150, 600),
                status=status,
                owner_id=random.choice(clients).id,
                total_amount=random.uniform(8000, 35000),
            )
            session.add(order)
            await session.flush()

            # Деталі вантажу (Shipment)
            shipment = Shipment(
                order_id=order.id,
                weight=order.weight,
                volume=round(order.weight / 400, 2),
                quantity=random.randint(1, 20),
                description="Паллети, стандартне пакування",
            )
            session.add(shipment)

            # Для замовлень у роботі або завершених створюємо Route
            if status in [OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED]:
                driver = random.choice(drivers)
                # Знаходимо авто цього водія
                vehicle_stmt = select(Vehicle).where(
                    Vehicle.driver_id == driver.id
                )
                vehicle_result = await session.execute(vehicle_stmt)
                vehicle = vehicle_result.scalar_one_or_none()

                route = Route(
                    order_id=order.id,
                    driver_id=driver.id,
                    vehicle_id=vehicle.id if vehicle else None,
                    started_at=datetime.now()
                    - timedelta(days=random.randint(1, 5)),
                    eta=datetime.now()
                    + timedelta(hours=random.randint(10, 48)),
                    completed_at=datetime.now()
                    if status == OrderStatus.COMPLETED
                    else None,
                    fuel_cost=random.uniform(3000, 12000),
                )
                session.add(route)

        await session.commit()
        print("✅ База даних успішно заповнена реалістичними даними!")


if __name__ == "__main__":
    asyncio.run(seed_db())

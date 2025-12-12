import asyncio
from app.db.base import engine, Base
from app.models import Contact, Order, Feedback, Reward, MessageLog

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[SUCCESS] Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())

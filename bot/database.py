"""
SlydAI Bot - MongoDB Database Layer (async with Motor)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import motor.motor_asyncio
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from config import MONGODB_URI, DAILY_LIMIT


logger = logging.getLogger(__name__)


class Database:
    """Async MongoDB wrapper for SlydAI bot."""

    def __init__(self):
        self.client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.db = None
        self.users = None
        self.generations = None

    async def connect(self):
        """Initialize MongoDB connection and ensure indexes."""

        self.client = motor.motor_asyncio.AsyncIOMotorClient(
            MONGODB_URI
        )

        # MongoDB URI ichidagi database nomini oladi.
        # Masalan:
        # mongodb+srv://user:password@cluster.mongodb.net/slydai
        self.db = self.client.get_default_database()

        # ── Collections ──────────────────────────────────────────────────────

        self.users = self.db["users"]
        self.generations = self.db["generations"]

        # ── Indexes ──────────────────────────────────────────────────────────

        await self.users.create_index(
            "telegram_id",
            unique=True
        )

        await self.generations.create_index(
            [
                ("user_id", ASCENDING),
                ("created_at", DESCENDING)
            ]
        )

        logger.info(
            "✅ MongoDB connected: %s",
            self.db.name
        )

    async def disconnect(self):
        """Close MongoDB connection."""

        if self.client:
            self.client.close()
            logger.info("🔌 MongoDB disconnected")

    # ─────────────────────────────────────────────────────────────────────────
    # User Operations
    # ─────────────────────────────────────────────────────────────────────────

    async def get_or_create_user(self, tg_user) -> dict:
        """
        Returns existing user or creates a new one.

        tg_user:
            telegram.User object
        """

        now = datetime.now(timezone.utc)

        update = {
            # Faqat yangi user yaratilganda ishlaydi.
            "$setOnInsert": {
                "telegram_id": tg_user.id,
                "joined_at": now,
                "is_blocked": False,
                "total_generations": 0,
            },

            # Har safar /start yoki user bilan interaction bo'lganda
            # yangilanadigan ma'lumotlar.
            "$set": {
                "last_seen": now,
                "username": tg_user.username,
                "first_name": tg_user.first_name,
                "last_name": tg_user.last_name,
                "language_code": tg_user.language_code,
            },
        }

        result = await self.users.find_one_and_update(
            {"telegram_id": tg_user.id},
            update,
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

        return result

    async def get_user(
        self,
        telegram_id: int
    ) -> Optional[dict]:
        """Get user by Telegram ID."""

        return await self.users.find_one(
            {
                "telegram_id": telegram_id
            }
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Daily Usage
    # ─────────────────────────────────────────────────────────────────────────

    async def get_daily_usage(
        self,
        telegram_id: int
    ) -> int:
        """
        Count how many presentations the user generated today.

        Uses UTC midnight as the start of the day.
        """

        today_start = datetime.now(
            timezone.utc
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        count = await self.generations.count_documents(
            {
                "telegram_id": telegram_id,
                "created_at": {
                    "$gte": today_start
                },
            }
        )

        return count

    async def can_generate(
        self,
        telegram_id: int
    ) -> tuple[bool, int]:
        """
        Returns:

        (
            allowed: bool,
            used_today: int
        )
        """

        used = await self.get_daily_usage(
            telegram_id
        )

        allowed = used < DAILY_LIMIT

        return allowed, used

    # ─────────────────────────────────────────────────────────────────────────
    # Generation Operations
    # ─────────────────────────────────────────────────────────────────────────

    async def record_generation(
        self,
        telegram_id: int,
        topic: str,
        theme: str,
        slide_count: int,
    ) -> str:
        """
        Save a presentation generation record.

        Returns:
            Inserted MongoDB document ID as string.
        """

        now = datetime.now(timezone.utc)

        document = {
            "telegram_id": telegram_id,
            "topic": topic,
            "theme": theme,
            "slide_count": slide_count,
            "created_at": now,
        }

        result = await self.generations.insert_one(
            document
        )

        # Userning umumiy generation counterini oshiramiz.
        await self.users.update_one(
            {
                "telegram_id": telegram_id
            },
            {
                "$inc": {
                    "total_generations": 1
                }
            },
        )

        return str(
            result.inserted_id
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Statistics
    # ─────────────────────────────────────────────────────────────────────────

    async def get_user_stats(
        self,
        telegram_id: int
    ) -> dict:
        """Return user generation statistics."""

        user = await self.get_user(
            telegram_id
        )

        used_today = await self.get_daily_usage(
            telegram_id
        )

        remaining = max(
            0,
            DAILY_LIMIT - used_today
        )

        return {
            "total_generations": (
                user.get(
                    "total_generations",
                    0
                )
                if user
                else 0
            ),

            "used_today": used_today,

            "remaining_today": remaining,

            "joined_at": (
                user.get("joined_at")
                if user
                else None
            ),
        }

    async def get_total_users(self) -> int:
        """Return total number of users."""

        return await self.users.count_documents({})

    async def get_total_generations(self) -> int:
        """Return total number of generated presentations."""

        return await self.generations.count_documents({})


# ─────────────────────────────────────────────────────────────────────────────
# Singleton instance
# ─────────────────────────────────────────────────────────────────────────────

db = Database()
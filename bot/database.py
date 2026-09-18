"""
SlydAI Bot - MongoDB Database Layer (async with Motor)
"""

import logging
from datetime import datetime, timezone, timedelta
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
        user = await self.get_user(telegram_id)
        if user and user.get("is_blocked", False):
            return False, 999

        used = await self.get_daily_usage(
            telegram_id
        )
        bonus = user.get("bonus_limit", 0) if user else 0
        total_limit = DAILY_LIMIT + bonus

        allowed = used < total_limit

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

    # ─────────────────────────────────────────────────────────────────────────
    # Admin Analytics & Operations
    # ─────────────────────────────────────────────────────────────────────────

    async def get_admin_dashboard_stats(self) -> dict:
        """Detailed stats for Admin Panel (today, 7 days, 30 days, total)."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        total_users = await self.users.count_documents({})
        users_today = await self.users.count_documents({"joined_at": {"$gte": today_start}})
        users_week = await self.users.count_documents({"joined_at": {"$gte": week_ago}})
        users_month = await self.users.count_documents({"joined_at": {"$gte": month_ago}})

        # Active users (last_seen)
        active_today = await self.users.count_documents({"last_seen": {"$gte": today_start}})
        active_week = await self.users.count_documents({"last_seen": {"$gte": week_ago}})

        # Generations
        total_gens = await self.generations.count_documents({})
        gens_today = await self.generations.count_documents({"created_at": {"$gte": today_start}})
        gens_week = await self.generations.count_documents({"created_at": {"$gte": week_ago}})
        gens_month = await self.generations.count_documents({"created_at": {"$gte": month_ago}})

        # Blocked users
        blocked_users = await self.users.count_documents({"is_blocked": True})

        # Top 5 popular themes
        pipeline_themes = [
            {"$group": {"_id": "$theme", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        top_themes_cursor = self.generations.aggregate(pipeline_themes)
        top_themes = await top_themes_cursor.to_list(length=5)

        # Average slides per generation
        pipeline_avg = [
            {"$group": {"_id": None, "avg_slides": {"$avg": "$slide_count"}}}
        ]
        avg_cursor = self.generations.aggregate(pipeline_avg)
        avg_res = await avg_cursor.to_list(length=1)
        avg_slides = round(avg_res[0]["avg_slides"], 1) if avg_res and "avg_slides" in avg_res[0] else 0

        return {
            "total_users": total_users,
            "users_today": users_today,
            "users_week": users_week,
            "users_month": users_month,
            "active_today": active_today,
            "active_week": active_week,
            "total_gens": total_gens,
            "gens_today": gens_today,
            "gens_week": gens_week,
            "gens_month": gens_month,
            "blocked_users": blocked_users,
            "top_themes": top_themes,
            "avg_slides": avg_slides,
        }

    async def get_all_user_ids(self) -> list[int]:
        """Get all user telegram IDs (for broadcast)."""
        cursor = self.users.find({}, {"telegram_id": 1, "_id": 0})
        user_ids = []
        async for doc in cursor:
            if "telegram_id" in doc:
                user_ids.append(doc["telegram_id"])
        return user_ids

    async def get_recent_users(self, limit: int = 10) -> list[dict]:
        """Get latest registered users."""
        cursor = self.users.find().sort("joined_at", DESCENDING).limit(limit)
        return await cursor.to_list(length=limit)

    async def search_user(self, query: str) -> Optional[dict]:
        """Search user by ID or Username."""
        if query.isdigit():
            return await self.users.find_one({"telegram_id": int(query)})
        clean_username = query.lstrip("@")
        return await self.users.find_one({"username": {"$regex": f"^{clean_username}$", "$options": "i"}})

    async def toggle_block_user(self, telegram_id: int) -> bool:
        """Toggle user blocked state. Returns new state."""
        user = await self.get_user(telegram_id)
        if not user:
            return False
        new_status = not user.get("is_blocked", False)
        await self.users.update_one({"telegram_id": telegram_id}, {"$set": {"is_blocked": new_status}})
        return new_status

    async def add_bonus_generations(self, telegram_id: int, count: int = 5) -> bool:
        """Add bonus generation limit to user."""
        user = await self.get_user(telegram_id)
        if not user:
            return False
        await self.users.update_one({"telegram_id": telegram_id}, {"$inc": {"bonus_limit": count}})
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Singleton instance
# ─────────────────────────────────────────────────────────────────────────────

db = Database()
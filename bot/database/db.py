import aiosqlite
from typing import List, Dict, Optional, Any
from bot.config import DB_PATH, ADMIN_PHONE, ADMIN_IDS, STORAGE_CHANNEL_ID

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    full_name TEXT,
    username TEXT,
    phone_number TEXT,
    is_admin INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS voices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    tags TEXT NOT NULL,
    file_id TEXT NOT NULL,
    file_unique_id TEXT,
    duration INTEGER DEFAULT 0,
    storage_message_id INTEGER UNIQUE,
    use_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL UNIQUE,
    title TEXT,
    invite_link TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(CREATE_TABLES_SQL)
            
            try:
                await db.execute("ALTER TABLE voices ADD COLUMN storage_message_id INTEGER")
            except Exception:
                pass

            cursor = await db.execute("SELECT value FROM settings WHERE key = 'force_sub'")
            row = await cursor.fetchone()
            if not row:
                await db.execute("INSERT INTO settings (key, value) VALUES ('force_sub', 'off')")

            if STORAGE_CHANNEL_ID:
                cursor = await db.execute("SELECT value FROM settings WHERE key = 'storage_channel'")
                if not await cursor.fetchone():
                    await db.execute("INSERT INTO settings (key, value) VALUES ('storage_channel', ?)", (STORAGE_CHANNEL_ID,))

            await db.commit()

    async def add_or_update_user(self, user_id: int, full_name: str, username: Optional[str] = None, phone_number: Optional[str] = None) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            is_admin = 1 if (user_id in ADMIN_IDS or (phone_number and phone_number.replace("+", "") == ADMIN_PHONE.replace("+", ""))) else 0
            
            cursor = await db.execute("SELECT is_admin, phone_number FROM users WHERE id = ?", (user_id,))
            user = await cursor.fetchone()
            
            if user:
                current_is_admin = user[0] or is_admin
                current_phone = phone_number or user[1]
                await db.execute(
                    "UPDATE users SET full_name = ?, username = ?, phone_number = ?, is_admin = ? WHERE id = ?",
                    (full_name, username, current_phone, current_is_admin, user_id)
                )
            else:
                await db.execute(
                    "INSERT INTO users (id, full_name, username, phone_number, is_admin) VALUES (?, ?, ?, ?, ?)",
                    (user_id, full_name, username, phone_number, is_admin)
                )
            await db.commit()
            return True

    async def is_admin(self, user_id: int) -> bool:
        if user_id in ADMIN_IDS:
            return True
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT is_admin, phone_number FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
            if not row:
                return False
            if row[0] == 1:
                return True
            if row[1] and row[1].replace("+", "") == ADMIN_PHONE.replace("+", ""):
                await db.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
                await db.commit()
                return True
            return False

    async def get_user_stats(self) -> Dict[str, int]:
        async with aiosqlite.connect(self.db_path) as db:
            c1 = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await c1.fetchone())[0]
            
            c2 = await db.execute("SELECT COUNT(*) FROM voices")
            total_voices = (await c2.fetchone())[0]

            c3 = await db.execute("SELECT SUM(use_count) FROM voices")
            sum_uses = (await c3.fetchone())[0] or 0

            c4 = await db.execute("SELECT COUNT(*) FROM channels")
            total_channels = (await c4.fetchone())[0]

            return {
                "users": total_users,
                "voices": total_voices,
                "uses": sum_uses,
                "channels": total_channels
            }

    async def get_all_user_ids(self) -> List[int]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT id FROM users")
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

    # Voice Methods
    async def add_voice(self, title: str, tags: str, file_id: str, file_unique_id: str = "", duration: int = 0, storage_message_id: Optional[int] = None) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO voices (title, tags, file_id, file_unique_id, duration, storage_message_id) VALUES (?, ?, ?, ?, ?, ?)",
                (title.strip(), tags.strip().lower(), file_id, file_unique_id, duration, storage_message_id)
            )
            await db.commit()
            return cursor.lastrowid

    async def update_voice_storage_info(self, voice_id: int, file_id: str, storage_message_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE voices SET file_id = ?, storage_message_id = ? WHERE id = ?",
                (file_id, storage_message_id, voice_id)
            )
            await db.commit()

    async def import_voice_if_not_exists(self, title: str, tags: str, file_id: str, file_unique_id: str = "", duration: int = 0, storage_message_id: Optional[int] = None, custom_id: Optional[int] = None) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            if storage_message_id:
                cursor = await db.execute("SELECT id FROM voices WHERE storage_message_id = ?", (storage_message_id,))
                if await cursor.fetchone():
                    return False

            if custom_id:
                cursor = await db.execute("SELECT id FROM voices WHERE id = ?", (custom_id,))
                if await cursor.fetchone():
                    await db.execute(
                        "UPDATE voices SET title = ?, tags = ?, file_id = ?, file_unique_id = ?, duration = ?, storage_message_id = ? WHERE id = ?",
                        (title.strip(), tags.strip().lower(), file_id, file_unique_id, duration, storage_message_id, custom_id)
                    )
                    await db.commit()
                    return True
                else:
                    await db.execute(
                        "INSERT INTO voices (id, title, tags, file_id, file_unique_id, duration, storage_message_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (custom_id, title.strip(), tags.strip().lower(), file_id, file_unique_id, duration, storage_message_id)
                    )
                    await db.commit()
                    return True

            await db.execute(
                "INSERT INTO voices (title, tags, file_id, file_unique_id, duration, storage_message_id) VALUES (?, ?, ?, ?, ?, ?)",
                (title.strip(), tags.strip().lower(), file_id, file_unique_id, duration, storage_message_id)
            )
            await db.commit()
            return True

    async def search_voices(self, query: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            q = f"%{query.strip().lower()}%"
            cursor = await db.execute(
                "SELECT * FROM voices WHERE LOWER(title) LIKE ? OR LOWER(tags) LIKE ? ORDER BY use_count DESC, id DESC LIMIT ? OFFSET ?",
                (q, q, limit, offset)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_top_voices(self, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM voices ORDER BY use_count DESC, id DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_all_voices(self, offset: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM voices ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_voice(self, voice_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM voices WHERE id = ?", (voice_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_voice(self, voice_id: int, title: str, tags: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE voices SET title = ?, tags = ? WHERE id = ?",
                (title.strip(), tags.strip().lower(), voice_id)
            )
            await db.commit()
            return True

    async def delete_voice(self, voice_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM voices WHERE id = ?", (voice_id,))
            await db.commit()
            return True

    async def increment_voice_usage(self, voice_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE voices SET use_count = use_count + 1 WHERE id = ?", (voice_id,))
            await db.commit()

    # Settings & Storage Channel
    async def get_setting(self, key: str, default: str = "") -> str:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return row[0] if row else default

    async def set_setting(self, key: str, value: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            await db.commit()

    async def add_channel(self, channel_id: str, title: str = "", invite_link: str = "") -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    "INSERT INTO channels (channel_id, title, invite_link) VALUES (?, ?, ?)",
                    (channel_id.strip(), title.strip(), invite_link.strip())
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def remove_channel(self, channel_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM channels WHERE channel_id = ? OR id = ?", (channel_id, channel_id))
            await db.commit()
            return True

    async def get_channels(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM channels ORDER BY id ASC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

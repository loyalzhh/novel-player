"""
数据库管理模块 - SQLite 数据库操作
管理小说、章节、阅读进度、书签、语音配置
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "novel_player.db")


class DatabaseManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS novels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                file_path TEXT,
                author TEXT DEFAULT '',
                total_chars INTEGER DEFAULT 0,
                content TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                last_read_at TEXT
            );

            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id INTEGER NOT NULL,
                chapter_index INTEGER NOT NULL,
                title TEXT NOT NULL,
                start_pos INTEGER NOT NULL,
                end_pos INTEGER NOT NULL,
                FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reading_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id INTEGER NOT NULL UNIQUE,
                chapter_id INTEGER,
                char_position INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE,
                FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id INTEGER NOT NULL,
                chapter_id INTEGER,
                char_position INTEGER DEFAULT 0,
                note TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE,
                FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS voice_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                voice_id TEXT DEFAULT '',
                rate INTEGER DEFAULT 180,
                volume REAL DEFAULT 1.0,
                pitch REAL DEFAULT 1.0,
                is_default INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        self.conn.commit()

    # ==================== 小说操作 ====================

    def add_novel(self, title, file_path="", author="", content="", total_chars=0):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO novels (title, file_path, author, content, total_chars) VALUES (?, ?, ?, ?, ?)",
            (title, file_path, author, content, total_chars)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all_novels(self):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT n.*, rp.char_position as progress_pos FROM novels n "
            "LEFT JOIN reading_progress rp ON n.id = rp.novel_id "
            "ORDER BY n.last_read_at DESC, n.created_at DESC"
        )
        return cursor.fetchall()

    def get_novel(self, novel_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM novels WHERE id = ?", (novel_id,))
        return cursor.fetchone()

    def update_novel_content(self, novel_id, content, total_chars):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE novels SET content = ?, total_chars = ? WHERE id = ?",
            (content, total_chars, novel_id)
        )
        self.conn.commit()

    def update_last_read(self, novel_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE novels SET last_read_at = datetime('now','localtime') WHERE id = ?",
            (novel_id,)
        )
        self.conn.commit()

    def delete_novel(self, novel_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM novels WHERE id = ?", (novel_id,))
        self.conn.commit()

    def search_novels(self, keyword):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM novels WHERE title LIKE ? OR author LIKE ? ORDER BY last_read_at DESC",
            (f"%{keyword}%", f"%{keyword}%")
        )
        return cursor.fetchall()

    # ==================== 章节操作 ====================

    def add_chapter(self, novel_id, chapter_index, title, start_pos, end_pos):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO chapters (novel_id, chapter_index, title, start_pos, end_pos) "
            "VALUES (?, ?, ?, ?, ?)",
            (novel_id, chapter_index, title, start_pos, end_pos)
        )
        self.conn.commit()
        return cursor.lastrowid

    def add_chapters_batch(self, chapters):
        """批量添加章节"""
        cursor = self.conn.cursor()
        cursor.executemany(
            "INSERT INTO chapters (novel_id, chapter_index, title, start_pos, end_pos) "
            "VALUES (?, ?, ?, ?, ?)",
            chapters
        )
        self.conn.commit()

    def get_chapters(self, novel_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM chapters WHERE novel_id = ? ORDER BY chapter_index",
            (novel_id,)
        )
        return cursor.fetchall()

    def get_chapter(self, chapter_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,))
        return cursor.fetchone()

    def delete_chapters(self, novel_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM chapters WHERE novel_id = ?", (novel_id,))
        self.conn.commit()

    # ==================== 阅读进度 ====================

    def save_progress(self, novel_id, chapter_id, char_position):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO reading_progress (novel_id, chapter_id, char_position, updated_at) "
            "VALUES (?, ?, ?, datetime('now','localtime')) "
            "ON CONFLICT(novel_id) DO UPDATE SET "
            "chapter_id = excluded.chapter_id, "
            "char_position = excluded.char_position, "
            "updated_at = datetime('now','localtime')",
            (novel_id, chapter_id, char_position)
        )
        self.conn.commit()

    def get_progress(self, novel_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM reading_progress WHERE novel_id = ?", (novel_id,)
        )
        return cursor.fetchone()

    # ==================== 书签操作 ====================

    def add_bookmark(self, novel_id, chapter_id, char_position, note=""):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO bookmarks (novel_id, chapter_id, char_position, note) "
            "VALUES (?, ?, ?, ?)",
            (novel_id, chapter_id, char_position, note)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_bookmarks(self, novel_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT b.*, c.title as chapter_title FROM bookmarks b "
            "LEFT JOIN chapters c ON b.chapter_id = c.id "
            "WHERE b.novel_id = ? ORDER BY b.created_at DESC",
            (novel_id,)
        )
        return cursor.fetchall()

    def delete_bookmark(self, bookmark_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
        self.conn.commit()

    # ==================== 语音配置操作 ====================

    def add_voice_profile(self, name, voice_id="", rate=180, volume=1.0, pitch=1.0, is_default=0):
        cursor = self.conn.cursor()
        if is_default:
            cursor.execute("UPDATE voice_profiles SET is_default = 0")
        cursor.execute(
            "INSERT INTO voice_profiles (name, voice_id, rate, volume, pitch, is_default) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, voice_id, rate, volume, pitch, is_default)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all_voice_profiles(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM voice_profiles ORDER BY is_default DESC, id ASC")
        return cursor.fetchall()

    def get_default_voice_profile(self):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM voice_profiles WHERE is_default = 1 LIMIT 1"
        )
        row = cursor.fetchone()
        if not row:
            cursor.execute("SELECT * FROM voice_profiles ORDER BY id ASC LIMIT 1")
            row = cursor.fetchone()
        return row

    def update_voice_profile(self, profile_id, name=None, voice_id=None, rate=None,
                             volume=None, pitch=None, is_default=None):
        cursor = self.conn.cursor()
        fields = []
        values = []

        if name is not None:
            fields.append("name = ?")
            values.append(name)
        if voice_id is not None:
            fields.append("voice_id = ?")
            values.append(voice_id)
        if rate is not None:
            fields.append("rate = ?")
            values.append(rate)
        if volume is not None:
            fields.append("volume = ?")
            values.append(volume)
        if pitch is not None:
            fields.append("pitch = ?")
            values.append(pitch)
        if is_default is not None:
            if is_default:
                cursor.execute("UPDATE voice_profiles SET is_default = 0")
            fields.append("is_default = ?")
            values.append(is_default)

        if fields:
            values.append(profile_id)
            cursor.execute(
                f"UPDATE voice_profiles SET {', '.join(fields)} WHERE id = ?",
                values
            )
        self.conn.commit()

    def delete_voice_profile(self, profile_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM voice_profiles WHERE id = ?", (profile_id,))
        self.conn.commit()

    # ==================== 应用设置 ====================

    def get_setting(self, key, default=None):
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value))
        )
        self.conn.commit()

    def close(self):
        self.conn.close()

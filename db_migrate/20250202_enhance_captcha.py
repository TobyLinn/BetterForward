import sqlite3


def upgrade(db_path):
    """Add captcha history table for tracking verification attempts."""
    with sqlite3.connect(db_path) as conn:
        db_cursor = conn.cursor()
        # 创建验证历史表
        db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS captcha_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                success INTEGER NOT NULL,
                timestamp INTEGER NOT NULL
            );
        """)
        # 创建索引以提高查询性能
        db_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_captcha_history_user_timestamp 
            ON captcha_history(user_id, timestamp);
        """)
        conn.commit()


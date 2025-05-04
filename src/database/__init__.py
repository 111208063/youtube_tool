"""
資料庫包初始化檔案

匯出資料庫相關的類和函數供其他模組使用。
"""

from src.database.models import MediaType, MediaFile
from src.database.manager import DatabaseManager
import sqlite3
import os
import enum
import logging
from pathlib import Path

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 確定數據庫文件的位置
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
db_path = os.path.join(project_root, 'database.db')

# 媒體類型枚舉
class MediaType(enum.Enum):
    """媒體類型"""
    AUDIO = "audio"
    VIDEO = "video"

def get_connection():
    """獲取數據庫連接"""
    conn = sqlite3.connect(db_path)
    return conn

def init_db():
    """初始化數據庫表結構"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 檢查media_files表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='media_files'")
    if not cursor.fetchone():
        # 創建媒體文件表
        cursor.execute('''
        CREATE TABLE media_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            file_path TEXT NOT NULL UNIQUE,
            media_type TEXT NOT NULL,
            file_size REAL NOT NULL,
            duration INTEGER DEFAULT 0,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploader TEXT DEFAULT '',
            youtube_id TEXT DEFAULT '',
            play_count INTEGER DEFAULT 0,
            last_played TIMESTAMP,
            thumbnail_path TEXT DEFAULT ''
        )
        ''')
        logging.info("已創建media_files表")
    
    # 檢查表結構是否需要更新（添加縮圖路徑欄位）
    cursor.execute("PRAGMA table_info(media_files)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    
    # 如果沒有縮圖路徑欄位，添加它
    if 'thumbnail_path' not in column_names:
        cursor.execute("ALTER TABLE media_files ADD COLUMN thumbnail_path TEXT DEFAULT ''")
        logging.info("已將thumbnail_path欄位添加到media_files表")
    
    conn.commit()
    conn.close()

# 在模組導入時初始化數據庫
init_db()

# 建立一個全局數據庫管理器實例
db_manager = DatabaseManager()

__all__ = ['MediaType', 'MediaFile', 'DatabaseManager', 'db_manager'] 
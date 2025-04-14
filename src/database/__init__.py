"""
資料庫包初始化檔案

匯出資料庫相關的類和函數供其他模組使用。
"""

from src.database.models import MediaType, MediaFile
from src.database.manager import DatabaseManager

# 建立一個全局數據庫管理器實例
db_manager = DatabaseManager()

__all__ = ['MediaType', 'MediaFile', 'DatabaseManager', 'db_manager'] 
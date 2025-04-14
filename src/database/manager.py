"""
資料庫管理器

處理與資料庫的所有交互，提供統一的資料庫操作介面。
"""
import os
import logging
from typing import List, Optional
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

from src.database.models import Base, MediaFile, MediaType


class DatabaseManager:
    """資料庫管理器，處理所有資料庫操作"""
    
    def __init__(self, db_path: str = None):
        """初始化數據庫管理器
        
        Args:
            db_path: 資料庫檔案路徑，預設為應用程式目錄下的database.db
        """
        if db_path is None:
            # 預設數據庫路徑，在應用程式根目錄下
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database.db')
        
        # 確保資料庫目錄存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 創建資料庫引擎
        self.engine = create_engine(f'sqlite:///{db_path}')
        
        # 創建會話工廠
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
        
        # 初始化資料庫（如果需要）
        self._init_db()
    
    def _init_db(self):
        """初始化資料庫，創建所有表"""
        try:
            Base.metadata.create_all(self.engine)
            logging.info("資料庫表已初始化")
        except SQLAlchemyError as e:
            logging.error(f"初始化資料庫失敗: {str(e)}")
    
    def add_media_file(self, 
                      title: str, 
                      file_path: str, 
                      media_type: MediaType,
                      file_size: float,
                      duration: Optional[float] = None,
                      uploader: Optional[str] = None,
                      youtube_id: Optional[str] = None,
                      thumbnail_path: Optional[str] = None) -> Optional[MediaFile]:
        """新增媒體檔案到資料庫
        
        Args:
            title: 媒體標題
            file_path: 檔案路徑
            media_type: 媒體類型 (AUDIO 或 VIDEO)
            file_size: 檔案大小 (MB)
            duration: 媒體長度（秒）
            uploader: 上傳者/創作者
            youtube_id: YouTube影片ID
            thumbnail_path: 縮圖路徑
            
        Returns:
            新增的MediaFile物件，出錯時返回None
        """
        session = self.Session()
        try:
            # 檢查檔案是否已存在
            existing = session.query(MediaFile).filter_by(file_path=file_path).first()
            if existing:
                logging.warning(f"檔案已存在: {file_path}")
                return existing
            
            # 創建新的媒體檔案記錄
            media_file = MediaFile(
                title=title,
                file_path=file_path,
                media_type=media_type,
                file_size=file_size,
                duration=duration,
                uploader=uploader,
                youtube_id=youtube_id,
                thumbnail_path=thumbnail_path
            )
            
            session.add(media_file)
            session.commit()
            logging.info(f"新增媒體檔案: {title}")
            return media_file
        
        except SQLAlchemyError as e:
            session.rollback()
            logging.error(f"新增媒體檔案失敗: {str(e)}")
            return None
        
        finally:
            session.close()
    
    def get_all_media_files(self) -> List[MediaFile]:
        """獲取所有媒體檔案
        
        Returns:
            所有媒體檔案的列表
        """
        session = self.Session()
        try:
            return session.query(MediaFile).all()
        finally:
            session.close()
    
    def get_media_files_by_type(self, media_type: MediaType) -> List[MediaFile]:
        """按媒體類型獲取檔案
        
        Args:
            media_type: 媒體類型 (AUDIO 或 VIDEO)
            
        Returns:
            符合類型的媒體檔案列表
        """
        session = self.Session()
        try:
            return session.query(MediaFile).filter_by(media_type=media_type).all()
        finally:
            session.close()
    
    def search_media_files(self, search_text: str) -> List[MediaFile]:
        """搜尋媒體檔案
        
        Args:
            search_text: 搜尋文字（在標題或上傳者中）
            
        Returns:
            符合搜尋條件的媒體檔案列表
        """
        session = self.Session()
        try:
            search_pattern = f"%{search_text}%"
            return session.query(MediaFile).filter(
                (MediaFile.title.like(search_pattern)) | 
                (MediaFile.uploader.like(search_pattern))
            ).all()
        finally:
            session.close()
    
    def delete_media_file(self, file_id: int) -> bool:
        """從資料庫刪除媒體檔案
        
        注意: 此方法僅刪除資料庫記錄，不會刪除實際檔案
        
        Args:
            file_id: 媒體檔案ID
            
        Returns:
            是否刪除成功
        """
        session = self.Session()
        try:
            media_file = session.query(MediaFile).filter_by(id=file_id).first()
            if media_file:
                session.delete(media_file)
                session.commit()
                logging.info(f"已刪除媒體檔案記錄: {media_file.title}")
                return True
            return False
        
        except SQLAlchemyError as e:
            session.rollback()
            logging.error(f"刪除媒體檔案記錄失敗: {str(e)}")
            return False
        
        finally:
            session.close()
    
    def delete_media_file_by_path(self, file_path: str) -> bool:
        """從資料庫刪除指定路徑的媒體檔案
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            是否刪除成功
        """
        session = self.Session()
        try:
            media_file = session.query(MediaFile).filter_by(file_path=file_path).first()
            if media_file:
                session.delete(media_file)
                session.commit()
                logging.info(f"已刪除媒體檔案記錄: {file_path}")
                return True
            return False
        
        except SQLAlchemyError as e:
            session.rollback()
            logging.error(f"刪除媒體檔案記錄失敗: {str(e)}")
            return False
        
        finally:
            session.close()
    
    def get_media_file_by_path(self, file_path: str) -> Optional[MediaFile]:
        """根據檔案路徑獲取媒體檔案
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            媒體檔案或None
        """
        session = self.Session()
        try:
            return session.query(MediaFile).filter_by(file_path=file_path).first()
        finally:
            session.close()
            
    def close(self):
        """關閉資料庫連接"""
        self.Session.remove()
        self.engine.dispose()
        
    def cleanup_database(self) -> tuple:
        """清理資料庫，刪除重複記錄和不存在的文件記錄
        
        Returns:
            tuple: (移除的重複記錄數, 移除的不存在檔案記錄數)
        """
        session = self.Session()
        try:
            # 記錄要刪除的項目數量
            removed_duplicates = 0
            removed_nonexistent = 0
            
            # 步驟1：找出並處理重複的檔案路徑
            # 獲取所有媒體檔案
            all_files = session.query(MediaFile).all()
            
            # 用於追踪已處理過的路徑
            processed_paths = {}
            duplicates_to_remove = []
            
            for media_file in all_files:
                path = media_file.file_path
                
                if path in processed_paths:
                    # 已有相同路徑，找出應該保留的記錄(ID較小)
                    existing_id = processed_paths[path]
                    # 保留ID較小的記錄，刪除ID較大的
                    if media_file.id > existing_id:
                        duplicates_to_remove.append(media_file.id)
                    else:
                        duplicates_to_remove.append(existing_id)
                        processed_paths[path] = media_file.id
                else:
                    # 第一次遇到此路徑
                    processed_paths[path] = media_file.id
            
            # 刪除重複記錄
            if duplicates_to_remove:
                removed_duplicates = len(duplicates_to_remove)
                session.query(MediaFile).filter(MediaFile.id.in_(duplicates_to_remove)).delete(synchronize_session='fetch')
            
            # 步驟2：檢查檔案是否存在
            nonexistent_to_remove = []
            
            for media_file in session.query(MediaFile).all():
                if not os.path.exists(media_file.file_path):
                    nonexistent_to_remove.append(media_file.id)
            
            # 刪除不存在的檔案記錄
            if nonexistent_to_remove:
                removed_nonexistent = len(nonexistent_to_remove)
                session.query(MediaFile).filter(MediaFile.id.in_(nonexistent_to_remove)).delete(synchronize_session='fetch')
            
            # 提交更改
            session.commit()
            
            return (removed_duplicates, removed_nonexistent)
        
        except SQLAlchemyError as e:
            session.rollback()
            logging.error(f"清理資料庫失敗: {str(e)}")
            return (0, 0)
        
        finally:
            session.close() 
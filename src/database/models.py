"""
資料庫模型定義

定義與儲存媒體文件相關的資料庫模型。
"""
from __future__ import annotations
from enum import Enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()


class MediaType(Enum):
    """媒體類型枚舉"""
    AUDIO = "audio"
    VIDEO = "video"


class MediaFile(Base):
    """媒體檔案模型"""
    __tablename__ = "media_files"
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    file_path = Column(String, unique=True, nullable=False)  # 檔案在磁碟上的實際路徑
    media_type = Column(SQLEnum(MediaType), nullable=False)
    duration = Column(Float, nullable=True)  # 媒體長度（秒）
    file_size = Column(Float, nullable=False)  # 檔案大小（MB）
    uploader = Column(String, nullable=True)  # 上傳者/創作者
    youtube_id = Column(String, nullable=True)  # YouTube 影片 ID（如果適用）
    thumbnail_path = Column(String, nullable=True)  # 縮圖路徑
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self) -> str:
        return f"<MediaFile(id={self.id}, title='{self.title}', type={self.media_type})>"
    
    @property
    def file_extension(self) -> str:
        """獲取檔案擴展名"""
        return self.file_path.split(".")[-1].lower() if "." in self.file_path else "" 
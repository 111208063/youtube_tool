"""
GUI 統一下載管理器模組

管理與跟踪YouTube下載任務。提供下載佇列，暫停/恢復下載功能及下載狀態更新。
整合YouTubeDownloader處理實際的下載過程。
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from queue import Queue, Empty
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Set, Union

from src.unified_downloader import (
    AudioQuality, 
    DownloadProgress, 
    MediaType, 
    VideoInfo, 
    VideoQuality, 
    YouTubeDownloader,
    is_playlist_url,
    clean_url
)


class DownloadStatus(Enum):
    """下載狀態枚舉"""
    PENDING = "pending"  # 排隊等待
    DOWNLOADING = "downloading"  # 下載中
    PAUSED = "paused"  # 暫停
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失敗
    CANCELLED = "cancelled"  # 已取消


@dataclass
class DownloadTask:
    """下載任務數據類"""
    id: str  # UUID
    url: str
    title: str
    thumbnail_url: str
    status: DownloadStatus
    media_type: MediaType
    quality: Union[VideoQuality, AudioQuality]
    progress: float  # 0-100
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    file_size: Optional[int] = None  # 位元組
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    video_info: Optional[VideoInfo] = None
    is_playlist: bool = False
    playlist_items: List[str] = None  # 只適用於播放清單，存放子任務ID

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now()
        if not self.playlist_items:
            self.playlist_items = []


class UnifiedDownloadManager:
    """統一下載管理器類"""

    def __init__(self, download_path: Union[str, Path], max_concurrent_downloads: int = 2):
        """
        初始化下載管理器

        Args:
            download_path: 下載文件的保存路徑
            max_concurrent_downloads: 最大並行下載數量
        """
        self.download_path = Path(download_path)
        self.download_path.mkdir(parents=True, exist_ok=True)
        
        # 創建子目錄
        (self.download_path / "audio").mkdir(exist_ok=True)
        (self.download_path / "video").mkdir(exist_ok=True)
        
        # 初始化YouTube下載器
        self.audio_downloader = YouTubeDownloader(self.download_path / "audio")
        self.video_downloader = YouTubeDownloader(self.download_path / "video")
        
        # 下載任務管理
        self.tasks: Dict[str, DownloadTask] = {}  # ID -> Task
        self.task_queue: Queue[str] = Queue()  # 任務佇列 (存儲任務ID)
        self.active_downloads: Set[str] = set()  # 活躍的下載任務ID
        self.paused_tasks: Set[str] = set()  # 暫停的任務ID
        
        # 並行控制
        self.max_concurrent_downloads = max_concurrent_downloads
        self.lock = Lock()  # 用於同步訪問tasks和active_downloads
        
        # 工作線程
        self.worker_thread = threading.Thread(target=self._download_worker, daemon=True)
        self.worker_running = True
        self.worker_thread.start()
        
        # 回調
        self._status_callbacks: List[Callable[[str, DownloadTask], None]] = []
        
        # 深色主題樣式設定
        self.dark_theme_styles = {
            "item_widget": """
                QWidget {
                    background-color: #1e1e1e;
                    border-radius: 6px;
                    color: white;
                }
            """,
            "title_label": """
                QLabel {
                    color: white;
                    font-weight: bold;
                    font-size: 14px;
                }
            """,
            "status_label": """
                QLabel {
                    color: #aaaaaa;
                    font-size: 12px;
                }
            """,
            "progress_bar": """
                QProgressBar {
                    border: 1px solid #444444;
                    border-radius: 3px;
                    text-align: center;
                    background-color: #333333;
                    color: white;
                }
                QProgressBar::chunk {
                    background-color: #4f46e5;
                    border-radius: 2px;
                }
            """,
            "action_button": """
                QPushButton {
                    background-color: #333333;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #444444;
                }
                QPushButton:pressed {
                    background-color: #555555;
                }
            """,
            "cancel_button": """
                QPushButton {
                    background-color: #a11;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #c22;
                }
            """
        }
        
    def register_status_callback(self, callback: Callable[[str, DownloadTask], None]) -> None:
        """註冊狀態更新回調函數"""
        self._status_callbacks.append(callback)
    
    def _notify_status_update(self, task_id: str) -> None:
        """通知所有已註冊的回調函數有關任務狀態的更新"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            for callback in self._status_callbacks:
                try:
                    callback(task_id, task)
                except Exception as e:
                    print(f"[錯誤] 呼叫狀態更新回調時出錯: {e}")
    
    def add_download(self, 
                    url: str, 
                    media_type: MediaType, 
                    quality: Union[VideoQuality, AudioQuality],
                    download_playlist: bool = False) -> str:
        """
        添加下載任務到佇列

        Args:
            url: YouTube URL
            media_type: 媒體類型
            quality: 媒體質量
            download_playlist: 是否下載整個播放清單

        Returns:
            任務ID
        """
        # 生成任務ID
        task_id = str(uuid.uuid4())
        
        # 清理 URL
        url = clean_url(url)
        
        # 檢查是否為播放清單
        is_playlist = is_playlist_url(url) and download_playlist
        
        # 獲取下載器
        downloader = self.audio_downloader if media_type == MediaType.AUDIO else self.video_downloader
        
        # 提取媒體信息
        try:
            info = downloader.extract_info(url)
        except Exception as e:
            raise ValueError(f"無法提取視頻信息: {e}")
        
        # 處理播放清單和單個影片
        if isinstance(info, list) and len(info) > 0 and is_playlist:  # 播放清單
            # 獲取播放清單標題
            playlist_title = f"播放清單 ({len(info)} 個項目)"
            
            # 建立主任務 (播放清單)
            task = DownloadTask(
                id=task_id,
                url=url,
                title=playlist_title,
                thumbnail_url=info[0].thumbnail_url if info else "",
                status=DownloadStatus.PENDING,
                media_type=media_type,
                quality=quality,
                progress=0.0,
                is_playlist=True
            )
            
            with self.lock:
                self.tasks[task_id] = task
                self.task_queue.put(task_id)
            
            self._notify_status_update(task_id)
            return task_id
        else:
            # 單個影片 - 無論是單獨URL還是播放清單中的第一個影片
            # 確保我們有一個 VideoInfo 對象
            video_info = info if not isinstance(info, list) else info[0]
            
            task = DownloadTask(
                id=task_id,
                url=url,
                title=video_info.title,
                thumbnail_url=video_info.thumbnail_url,
                status=DownloadStatus.PENDING,
                media_type=media_type,
                quality=quality,
                progress=0.0,
                video_info=video_info,
                is_playlist=False
            )
            
            with self.lock:
                self.tasks[task_id] = task
                self.task_queue.put(task_id)
            
            self._notify_status_update(task_id)
            return task_id
    
    def _download_worker(self) -> None:
        """下載工作線程，處理佇列中的任務"""
        while self.worker_running:
            # 檢查是否有空閒的下載槽
            if len(self.active_downloads) < self.max_concurrent_downloads:
                try:
                    # 嘗試從佇列獲取任務，不阻塞
                    try:
                        task_id = self.task_queue.get(block=False)
                    except Empty:
                        # 如果佇列為空，休眠一會兒
                        time.sleep(0.5)
                        continue
                    
                    # 檢查任務是否存在
                    with self.lock:
                        if task_id not in self.tasks:
                            self.task_queue.task_done()
                            continue
                        
                        # 檢查任務是否已暫停或取消
                        task = self.tasks[task_id]
                        if task.status == DownloadStatus.PAUSED or task.status == DownloadStatus.CANCELLED:
                            self.task_queue.task_done()
                            continue
                        
                        # 標記為活躍下載
                        self.active_downloads.add(task_id)
                    
                    # 執行下載（在單獨的線程中）
                    threading.Thread(
                        target=self._execute_download,
                        args=(task_id,),
                        daemon=True
                    ).start()
                    
                    # 標記任務為完成（從佇列角度，不是下載狀態）
                    self.task_queue.task_done()
                
                except Exception as e:
                    print(f"[錯誤] 下載工作線程執行期間出錯: {e}")
            
            # 休眠一段時間
            time.sleep(0.2)
    
    def _execute_download(self, task_id: str) -> None:
        """執行單個下載任務"""
        with self.lock:
            if task_id not in self.tasks:
                return
            
            task = self.tasks[task_id]
            # 更新狀態為下載中
            task.status = DownloadStatus.DOWNLOADING
            self._notify_status_update(task_id)
        
        try:
            # 製作進度回調
            def progress_callback(progress: Union[DownloadProgress, str]) -> None:
                """處理下載進度更新"""
                with self.lock:
                    if task_id not in self.tasks:
                        return
                    
                    task = self.tasks[task_id]
                    
                    # 檢查是否暫停或取消
                    if task.status == DownloadStatus.PAUSED or task.status == DownloadStatus.CANCELLED:
                        if isinstance(progress, DownloadProgress) and progress.status == 'downloading':
                            raise ValueError("下載已暫停或取消")
                    
                    # 更新進度信息
                    if isinstance(progress, DownloadProgress):
                        if progress.status == 'downloading':
                            task.progress = progress.percent
                        elif progress.status == 'finished':
                            task.progress = 100.0
                        elif progress.status == 'error':
                            task.status = DownloadStatus.FAILED
                            task.error_message = "下載過程中出現錯誤"
                    
                    # 通知更新
                    self._notify_status_update(task_id)
            
            # 選擇下載器
            downloader = self.audio_downloader if task.media_type == MediaType.AUDIO else self.video_downloader
            
            # 確定是否為播放清單下載
            is_playlist = task.is_playlist
            
            # 執行下載
            result = downloader.download(
                url=task.url,
                media_type=task.media_type,
                quality=task.quality,
                download_playlist=is_playlist,
                progress_callback=progress_callback,
                download_thumbnail=True
            )
            
            # 更新任務狀態
            with self.lock:
                if task_id not in self.tasks:
                    return
                
                task = self.tasks[task_id]
                
                # 如果任務被取消或暫停，不要更新
                if task.status in [DownloadStatus.CANCELLED, DownloadStatus.PAUSED]:
                    return
                
                # 更新任務狀態
                task.status = DownloadStatus.COMPLETED
                task.progress = 100.0
                task.completed_at = datetime.now()
                
                # 設置文件路徑
                if isinstance(result, list):
                    # 播放清單結果
                    task.file_path = ";".join(result)  # 用分號分隔多個文件路徑
                else:
                    # 單一文件結果
                    task.file_path = result
                
                # 通知更新
                self._notify_status_update(task_id)
                
                # 從活躍下載中移除
                self.active_downloads.discard(task_id)
        
        except Exception as e:
            # 更新任務狀態為失敗
            with self.lock:
                if task_id not in self.tasks:
                    return
                
                task = self.tasks[task_id]
                
                # 如果任務已經取消，不要標記為失敗
                if task.status == DownloadStatus.CANCELLED:
                    return
                
                task.status = DownloadStatus.FAILED
                task.error_message = str(e)
                self._notify_status_update(task_id)
                
                # 從活躍下載中移除
                self.active_downloads.discard(task_id)
    
    def pause_download(self, task_id: str) -> bool:
        """
        暫停下載任務
        
        Args:
            task_id: 任務ID
            
        Returns:
            操作是否成功
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
                
            task = self.tasks[task_id]
            
            # 只有正在下載的任務才能暫停
            if task.status != DownloadStatus.DOWNLOADING:
                return False
            
            # 更新任務狀態
            task.status = DownloadStatus.PAUSED
            self.paused_tasks.add(task_id)
            self._notify_status_update(task_id)
            
            return True
    
    def resume_download(self, task_id: str) -> bool:
        """
        恢復暫停的下載任務
        
        Args:
            task_id: 任務ID
            
        Returns:
            操作是否成功
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
                
            task = self.tasks[task_id]
            
            # 只有暫停的任務才能恢復
            if task.status != DownloadStatus.PAUSED:
                return False
            
            # 更新任務狀態
            task.status = DownloadStatus.PENDING
            self.paused_tasks.discard(task_id)
            
            # 重新加入佇列
            self.task_queue.put(task_id)
            
            self._notify_status_update(task_id)
            
            return True
    
    def cancel_download(self, task_id: str) -> bool:
        """
        取消下載任務
        
        Args:
            task_id: 任務ID
            
        Returns:
            操作是否成功
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
                
            task = self.tasks[task_id]
            
            # 更新任務狀態
            task.status = DownloadStatus.CANCELLED
            self.paused_tasks.discard(task_id)
            self.active_downloads.discard(task_id)
            self._notify_status_update(task_id)
            
            return True
    
    def get_all_tasks(self) -> List[DownloadTask]:
        """獲取所有下載任務的列表"""
        with self.lock:
            return list(self.tasks.values())
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """獲取指定ID的下載任務"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def clear_completed_tasks(self) -> int:
        """清除所有已完成的任務
        
        Returns:
            被清除的任務數量
        """
        count = 0
        with self.lock:
            # 收集所有已完成或失敗的任務ID
            completed_ids = [
                task_id for task_id, task in self.tasks.items()
                if task.status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED]
            ]
            
            # 從任務字典中移除
            for task_id in completed_ids:
                self.tasks.pop(task_id, None)
                count += 1
        
        return count
    
    def shutdown(self) -> None:
        """關閉下載管理器"""
        # 停止工作線程
        self.worker_running = False
        
        # 取消所有進行中的下載
        with self.lock:
            for task_id in list(self.active_downloads):
                self.cancel_download(task_id)
        
        # 等待工作線程結束
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
        
        print("[INFO] 下載管理器已關閉") 
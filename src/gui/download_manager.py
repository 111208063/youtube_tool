"""
下載管理器模組

管理與跟踪YouTube下載任務。提供下載佇列，暫停/恢復下載功能及下載狀態更新。
整合YouTubeFetcher處理實際的下載過程。
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from queue import Queue
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from src.youtube_fetcher import AudioQuality, DownloadProgress, MediaType, VideoInfo, VideoQuality, YouTubeFetcher


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


class DownloadManager:
    """下載管理器類，負責處理下載佇列和狀態更新"""

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
        
        self.temp_path = self.download_path / "temp"
        self.temp_path.mkdir(exist_ok=True)
        
        # 初始化YouTube抓取器
        self.fetcher = YouTubeFetcher(self.download_path, self.temp_path)
        
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
        
    def register_status_callback(self, callback: Callable[[str, DownloadTask], None]) -> None:
        """註冊下載狀態更新回調函數"""
        self._status_callbacks.append(callback)
        
    def _notify_status_update(self, task_id: str) -> None:
        """通知所有回調下載狀態有更新"""
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                for callback in self._status_callbacks:
                    callback(task_id, task)
    
    def add_download(
        self, 
        url: str, 
        media_type: MediaType, 
        quality: Union[VideoQuality, AudioQuality]
    ) -> str:
        """
        添加一個新的下載任務到佇列
        
        Args:
            url: YouTube URL
            media_type: 媒體類型 (音訊或視訊)
            quality: 品質設定
            
        Returns:
            新創建的任務ID
            
        Raises:
            ValueError: URL無效或無法解析
            RuntimeError: 其他下載過程中的錯誤
        """
        # 提取影片信息
        try:
            info = self.fetcher.extract_info(url)
        except Exception as e:
            raise ValueError(f"無法獲取影片信息: {str(e)}")
        
        # 創建任務ID
        task_id = str(uuid.uuid4())
        
        # 處理播放清單和單個影片
        if isinstance(info, list):  # 播放清單
            # 建立主任務 (播放清單)
            playlist_task = DownloadTask(
                id=task_id,
                url=url,
                title=f"播放清單 ({len(info)} 個項目)",
                thumbnail_url=info[0].thumbnail_url if info else "",
                status=DownloadStatus.PENDING,
                media_type=media_type,
                quality=quality,
                progress=0.0,
                is_playlist=True,
                playlist_items=[]
            )
            
            # 為每個影片創建子任務
            for video_info in info:
                child_id = str(uuid.uuid4())
                child_task = DownloadTask(
                    id=child_id,
                    url=f"https://www.youtube.com/watch?v={video_info.video_id}",
                    title=video_info.title,
                    thumbnail_url=video_info.thumbnail_url,
                    status=DownloadStatus.PENDING,
                    media_type=media_type,
                    quality=quality,
                    progress=0.0,
                    video_info=video_info
                )
                
                with self.lock:
                    self.tasks[child_id] = child_task
                    playlist_task.playlist_items.append(child_id)
                    self.task_queue.put(child_id)
            
            with self.lock:
                self.tasks[task_id] = playlist_task
                
            self._notify_status_update(task_id)
            return task_id
            
        else:  # 單個影片
            task = DownloadTask(
                id=task_id,
                url=url,
                title=info.title,
                thumbnail_url=info.thumbnail_url,
                status=DownloadStatus.PENDING,
                media_type=media_type,
                quality=quality,
                progress=0.0,
                video_info=info
            )
            
            with self.lock:
                self.tasks[task_id] = task
                self.task_queue.put(task_id)
                
            self._notify_status_update(task_id)
            return task_id
    
    def _download_worker(self) -> None:
        """下載工作線程，處理佇列中的下載任務"""
        while self.worker_running:
            # 檢查是否可以開始新的下載
            if len(self.active_downloads) < self.max_concurrent_downloads and not self.task_queue.empty():
                # 從佇列獲取下一個任務
                task_id = self.task_queue.get()
                
                # 檢查任務是否存在且不在暫停狀態
                with self.lock:
                    if task_id not in self.tasks or task_id in self.paused_tasks:
                        self.task_queue.task_done()
                        continue
                    
                    task = self.tasks[task_id]
                    
                    # 若是已取消的任務，直接跳過
                    if task.status == DownloadStatus.CANCELLED:
                        self.task_queue.task_done()
                        continue
                    
                    # 標記為下載中
                    task.status = DownloadStatus.DOWNLOADING
                    self.active_downloads.add(task_id)
                
                self._notify_status_update(task_id)
                
                # 在新線程中執行下載，避免阻塞工作線程
                download_thread = threading.Thread(
                    target=self._execute_download,
                    args=(task_id,),
                    daemon=True
                )
                download_thread.start()
            
            # 等待一段時間再檢查
            time.sleep(0.5)
    
    def _execute_download(self, task_id: str) -> None:
        """執行單個下載任務"""
        with self.lock:
            if task_id not in self.tasks:
                return
            
            task = self.tasks[task_id]
        
        # 根據媒體類型選擇保存目錄
        subdir = "audio" if task.media_type == MediaType.AUDIO else "video"
        output_dir = self.download_path / subdir
        
        try:
            # 建立進度回調函數
            def progress_callback(progress: DownloadProgress) -> None:
                with self.lock:
                    if task_id in self.paused_tasks:
                        raise InterruptedError("下載已暫停")
                    
                    if task_id in self.tasks:
                        self.tasks[task_id].progress = progress.percent
                        
                        # 更新文件大小信息
                        if progress.total_bytes and not self.tasks[task_id].file_size:
                            self.tasks[task_id].file_size = progress.total_bytes
                
                self._notify_status_update(task_id)
            
            # 執行下載
            file_path = self.fetcher.download(
                url=task.url,
                media_type=task.media_type,
                quality=task.quality,
                progress_callback=progress_callback
            )
            
            # 更新任務狀態為已完成
            with self.lock:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    task.status = DownloadStatus.COMPLETED
                    task.progress = 100.0
                    task.file_path = file_path
                    task.completed_at = datetime.now()
                    
                    # 檢查是否為播放清單的子項目，更新主任務的進度
                    self._update_parent_progress(task_id)
                    
                    # 從活躍下載中移除
                    self.active_downloads.discard(task_id)
            
            self._notify_status_update(task_id)
            
        except InterruptedError:
            # 下載被暫停
            with self.lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = DownloadStatus.PAUSED
                    self.active_downloads.discard(task_id)
            
            self._notify_status_update(task_id)
            
        except Exception as e:
            # 下載失敗
            with self.lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = DownloadStatus.FAILED
                    self.tasks[task_id].error_message = str(e)
                    self.active_downloads.discard(task_id)
                    
                    # 檢查是否為播放清單的子項目，更新主任務的進度
                    self._update_parent_progress(task_id)
            
            self._notify_status_update(task_id)
        
        finally:
            # 標記隊列任務為已完成
            self.task_queue.task_done()
    
    def _update_parent_progress(self, child_id: str) -> None:
        """更新播放清單主任務的進度"""
        # 查找此任務的父任務(播放清單)
        parent_id = None
        
        for task_id, task in self.tasks.items():
            if task.is_playlist and child_id in task.playlist_items:
                parent_id = task_id
                break
                
        if not parent_id:
            return
            
        # 計算播放清單總進度
        parent_task = self.tasks[parent_id]
        total_items = len(parent_task.playlist_items)
        if total_items == 0:
            return
            
        completed = 0
        failed = 0
        total_progress = 0.0
        
        for item_id in parent_task.playlist_items:
            if item_id in self.tasks:
                item = self.tasks[item_id]
                if item.status == DownloadStatus.COMPLETED:
                    completed += 1
                elif item.status == DownloadStatus.FAILED:
                    failed += 1
                total_progress += item.progress
        
        # 更新主任務的進度和狀態
        avg_progress = total_progress / total_items
        parent_task.progress = avg_progress
        
        # 如果所有子任務都已完成或失敗，更新主任務狀態
        if completed + failed == total_items:
            if failed == total_items:
                parent_task.status = DownloadStatus.FAILED
                parent_task.error_message = "所有項目下載失敗"
            elif completed == total_items:
                parent_task.status = DownloadStatus.COMPLETED
                parent_task.completed_at = datetime.now()
            else:
                parent_task.status = DownloadStatus.COMPLETED
                parent_task.error_message = f"{failed} 個項目下載失敗"
                parent_task.completed_at = datetime.now()
        
        self._notify_status_update(parent_id)
    
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
            
            # 如果是播放清單，暫停所有子任務
            if task.is_playlist:
                for child_id in task.playlist_items:
                    if child_id in self.tasks and self.tasks[child_id].status == DownloadStatus.DOWNLOADING:
                        self.tasks[child_id].status = DownloadStatus.PAUSED
                        self.paused_tasks.add(child_id)
                        self.active_downloads.discard(child_id)
                        self._notify_status_update(child_id)
                
                task.status = DownloadStatus.PAUSED
                self._notify_status_update(task_id)
                return True
            
            # 單個任務的處理
            if task.status != DownloadStatus.DOWNLOADING:
                return False
                
            self.paused_tasks.add(task_id)
            # 狀態更新將由下載線程處理
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
            
            # 如果是播放清單，恢復所有暫停的子任務
            if task.is_playlist:
                resumed = False
                
                for child_id in task.playlist_items:
                    if child_id in self.tasks and self.tasks[child_id].status == DownloadStatus.PAUSED:
                        self.paused_tasks.discard(child_id)
                        self.tasks[child_id].status = DownloadStatus.PENDING
                        self.task_queue.put(child_id)
                        self._notify_status_update(child_id)
                        resumed = True
                
                if resumed:
                    task.status = DownloadStatus.PENDING
                    self._notify_status_update(task_id)
                
                return resumed
            
            # 單個任務的處理
            if task.status != DownloadStatus.PAUSED:
                return False
                
            self.paused_tasks.discard(task_id)
            task.status = DownloadStatus.PENDING
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
            
            # 如果是播放清單，取消所有子任務
            if task.is_playlist:
                for child_id in task.playlist_items:
                    if child_id in self.tasks:
                        self.tasks[child_id].status = DownloadStatus.CANCELLED
                        self.paused_tasks.discard(child_id)
                        self.active_downloads.discard(child_id)
                        self._notify_status_update(child_id)
            
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
        """
        清除已完成的下載任務
        
        Returns:
            清除的任務數量
        """
        to_remove = []
        
        with self.lock:
            for task_id, task in self.tasks.items():
                if task.status == DownloadStatus.COMPLETED or task.status == DownloadStatus.CANCELLED:
                    # 不要刪除仍有活躍子任務的播放清單
                    if task.is_playlist:
                        has_active_children = False
                        for child_id in task.playlist_items:
                            if child_id in self.tasks and self.tasks[child_id].status not in [
                                DownloadStatus.COMPLETED, DownloadStatus.CANCELLED, DownloadStatus.FAILED
                            ]:
                                has_active_children = True
                                break
                                
                        if not has_active_children:
                            to_remove.append(task_id)
                    else:
                        to_remove.append(task_id)
            
            # 刪除標記的任務
            for task_id in to_remove:
                del self.tasks[task_id]
        
        return len(to_remove)
    
    def shutdown(self) -> None:
        """關閉下載管理器，停止所有下載"""
        self.worker_running = False
        
        with self.lock:
            # 標記所有活躍下載為已取消
            for task_id in self.active_downloads:
                if task_id in self.tasks:
                    self.tasks[task_id].status = DownloadStatus.CANCELLED
            
            self.active_downloads.clear()
        
        # 等待工作線程完成
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)


# 使用範例
if __name__ == "__main__":
    import sys
    
    # 設置下載路徑
    download_folder = Path.home() / "Downloads" / "YouTube"
    
    # 創建下載管理器
    manager = DownloadManager(download_folder, max_concurrent_downloads=3)
    
    # 註冊狀態更新回調
    def status_update(task_id, task):
        if task.is_playlist:
            status_text = f"播放清單: {task.title} - {task.status.value} - {task.progress:.1f}%"
            if task.status == DownloadStatus.COMPLETED:
                status_text += f" - 完成時間: {task.completed_at}"
        else:
            status_text = f"影片: {task.title} - {task.status.value} - {task.progress:.1f}%"
            if task.status == DownloadStatus.COMPLETED:
                status_text += f" - 檔案: {task.file_path}"
            elif task.status == DownloadStatus.FAILED:
                status_text += f" - 錯誤: {task.error_message}"
                
        print(f"\r{status_text}", end="")
        sys.stdout.flush()
        
        if task.status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED]:
            print()  # 新行
    
    manager.register_status_callback(status_update)
    
    try:
        # 獲取用戶輸入
        url = input("請輸入YouTube影片或播放清單URL: ")
        
        media_type_choice = input("下載為 (1) 音訊 或 (2) 視頻? (1/2): ")
        media_type = MediaType.AUDIO if media_type_choice == '1' else MediaType.VIDEO
        
        quality_choice = input("選擇品質 (1) 低 (2) 中 (3) 高: ")
        if media_type == MediaType.AUDIO:
            quality_map = {'1': AudioQuality.LOW, '2': AudioQuality.MEDIUM, '3': AudioQuality.HIGH}
        else:
            quality_map = {'1': VideoQuality.LOW, '2': VideoQuality.MEDIUM, '3': VideoQuality.HIGH}
        quality = quality_map.get(quality_choice, quality_map['2'])  # 默認中等品質
        
        # 添加下載任務
        task_id = manager.add_download(url, media_type, quality)
        print(f"已添加下載任務: {task_id}")
        
        # 等待用戶輸入來控制下載
        while True:
            command = input("\n輸入命令 (p: 暫停, r: 恢復, c: 取消, q: 退出): ")
            
            if command.lower() == 'p':
                if manager.pause_download(task_id):
                    print("下載已暫停")
                else:
                    print("無法暫停下載")
            elif command.lower() == 'r':
                if manager.resume_download(task_id):
                    print("下載已恢復")
                else:
                    print("無法恢復下載")
            elif command.lower() == 'c':
                if manager.cancel_download(task_id):
                    print("下載已取消")
                else:
                    print("無法取消下載")
            elif command.lower() == 'q':
                break
        
    except ValueError as e:
        print(f"錯誤: {e}")
    except Exception as e:
        print(f"未預期的錯誤: {e}")
    finally:
        # 關閉下載管理器
        manager.shutdown()
        print("下載管理器已關閉") 
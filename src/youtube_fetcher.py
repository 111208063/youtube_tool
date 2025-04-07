"""
YouTube內容擷取模組

基於yt-dlp庫的YouTube影片和播放清單下載功能，提供簡單的API
用於獲取影片信息和下載媒體內容。
"""
import os
import enum
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

import yt_dlp

class MediaType(enum.Enum):
    """媒體類型"""
    AUDIO = "audio"
    VIDEO = "video"

class VideoQuality(enum.Enum):
    """視頻質量"""
    LOW = "360p"
    MEDIUM = "720p"
    HIGH = "1080p"

class AudioQuality(enum.Enum):
    """音頻質量"""
    LOW = "128k"
    MEDIUM = "192k"
    HIGH = "320k"

@dataclass
class VideoInfo:
    """視頻信息數據類"""
    id: str
    title: str
    thumbnail_url: str
    duration: int
    channel: str
    upload_date: str
    description: str
    url: str  # 原始URL或網頁URL

@dataclass
class DownloadProgress:
    """下載進度數據類"""
    status: str  # 'downloading', 'finished', 'error'
    percent: float
    downloaded_bytes: int
    total_bytes: Optional[int]
    speed: float
    eta: Optional[int]
    filename: str

class YouTubeFetcher:
    """YouTube內容擷取器"""
    
    def __init__(self, download_path: Union[str, Path], temp_path: Optional[Union[str, Path]] = None):
        """
        初始化YouTube內容擷取器
        
        Args:
            download_path: 下載內容的保存路徑
            temp_path: 臨時文件路徑，默認使用系統臨時目錄
        """
        self.download_path = Path(download_path)
        self.download_path.mkdir(parents=True, exist_ok=True)
        
        self.temp_path = Path(temp_path) if temp_path else Path(tempfile.gettempdir()) / "youtube_dl"
        self.temp_path.mkdir(parents=True, exist_ok=True)
    
    def extract_info(self, url: str) -> Union[VideoInfo, List[VideoInfo]]:
        """
        提取視頻或播放清單的基本信息
        
        Args:
            url: YouTube URL，可以是視頻或播放清單
            
        Returns:
            單個視頻信息或視頻信息列表(播放清單)
            
        Raises:
            ValueError: 如果URL無效或提取過程中出錯
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': False,  # 允許處理播放清單
            'skip_download': True,  # 僅提取信息，不下載
            'extract_flat': 'in_playlist',  # 對於播放清單中的項目不提取完整信息
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # 檢查是否是播放清單
                if 'entries' in info:
                    # 是播放清單
                    videos = []
                    for entry in info['entries']:
                        # 對於播放清單項目，我們需要單獨提取完整信息
                        if entry:
                            try:
                                # 使用視頻ID或URL獲取詳細信息
                                video_url = entry.get('url') or entry.get('webpage_url')
                                if not video_url and 'id' in entry:
                                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                                
                                if video_url:
                                    single_info = ydl.extract_info(video_url, download=False)
                                    videos.append(self._info_to_video_info(single_info))
                            except Exception as e:
                                print(f"無法提取播放清單項目信息: {e}")
                    return videos
                else:
                    # 單個視頻
                    return self._info_to_video_info(info)
        
        except Exception as e:
            raise ValueError(f"無法提取視頻信息: {e}")
    
    def _info_to_video_info(self, info: Dict) -> VideoInfo:
        """將yt-dlp信息轉換為VideoInfo對象"""
        # 確保我們有有效的縮圖URL
        thumbnail_url = info.get('thumbnail')
        if not thumbnail_url and 'thumbnails' in info and info['thumbnails']:
            # 使用最後一個縮圖（通常是最高質量的）
            thumbnail_url = info['thumbnails'][-1].get('url')
        
        # 構造VideoInfo對象
        return VideoInfo(
            id=info.get('id', ''),
            title=info.get('title', '未知標題'),
            thumbnail_url=thumbnail_url or '',
            duration=info.get('duration', 0),
            channel=info.get('uploader', '未知頻道'),
            upload_date=info.get('upload_date', ''),
            description=info.get('description', ''),
            url=info.get('webpage_url', info.get('original_url', ''))
        )
    
    def download(self, url: str, media_type: MediaType, quality: Union[VideoQuality, AudioQuality],
                progress_callback: Optional[Callable[[DownloadProgress], None]] = None) -> str:
        """
        下載單個視頻或音頻
        
        Args:
            url: YouTube URL
            media_type: 媒體類型 (音頻或視頻)
            quality: 媒體質量
            progress_callback: 進度回調函數
            
        Returns:
            下載的文件路徑
            
        Raises:
            ValueError: 如果URL無效或下載過程中出錯
        """
        # 確保URL是單一視頻而非播放清單
        if 'list=' in url and 'watch?' in url:
            # 從URL中提取視頻ID
            video_id = url.split('v=')[1].split('&')[0]
            url = f"https://www.youtube.com/watch?v={video_id}"
        
        # 檢查質量參數類型與媒體類型是否匹配
        if media_type == MediaType.AUDIO and not isinstance(quality, AudioQuality):
            raise ValueError("音頻下載必須使用AudioQuality")
        elif media_type == MediaType.VIDEO and not isinstance(quality, VideoQuality):
            raise ValueError("視頻下載必須使用VideoQuality")
        
        # 根據媒體類型和質量設置下載選項
        filename = None
        
        if media_type == MediaType.AUDIO:
            ydl_opts = self._get_audio_options(quality, progress_callback)
        else:
            ydl_opts = self._get_video_options(quality, progress_callback)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 首先獲取信息以便正確處理結果
                info = ydl.extract_info(url, download=False)
                
                # 檢查是否是播放清單，如果是則只取第一個項目
                if 'entries' in info and info['entries']:
                    # 獲取第一個視頻的URL
                    video_url = info['entries'][0].get('webpage_url', url)
                    ydl_opts['noplaylist'] = True  # 確保只下載單個視頻
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as single_ydl:
                        info = single_ydl.extract_info(video_url, download=True)
                else:
                    # 直接下載單個視頻
                    info = ydl.extract_info(url, download=True)
                
                # 獲取下載的文件名
                if info.get('_filename'):
                    filename = info['_filename']
                elif '_downloader' in info and 'filename' in info['_downloader']:
                    filename = info['_downloader']['filename']
        
        except Exception as e:
            raise ValueError(f"下載失敗: {e}")
        
        if not filename or not os.path.exists(filename):
            raise ValueError("下載完成但找不到文件")
        
        return filename
    
    def download_playlist(self, url: str, media_type: MediaType, quality: Union[VideoQuality, AudioQuality],
                        progress_callback: Optional[Callable[[str, DownloadProgress], None]] = None) -> List[str]:
        """
        下載播放清單中的所有視頻
        
        Args:
            url: YouTube播放清單URL
            media_type: 媒體類型 (音頻或視頻)
            quality: 媒體質量
            progress_callback: 進度回調函數，接收視頻標題和進度信息
            
        Returns:
            下載的文件路徑列表
            
        Raises:
            ValueError: 如果URL無效或下載過程中出錯
        """
        # 檢查質量參數類型與媒體類型是否匹配
        if media_type == MediaType.AUDIO and not isinstance(quality, AudioQuality):
            raise ValueError("音頻下載必須使用AudioQuality")
        elif media_type == MediaType.VIDEO and not isinstance(quality, VideoQuality):
            raise ValueError("視頻下載必須使用VideoQuality")
        
        # 獲取播放清單信息
        try:
            playlist_info = self.extract_info(url)
            if not isinstance(playlist_info, list):
                raise ValueError("URL不是有效的播放清單")
            
            downloaded_files = []
            
            # 為每個視頻創建進度回調
            for i, video_info in enumerate(playlist_info):
                try:
                    # 創建該視頻的進度回調
                    video_progress_callback = None
                    if progress_callback:
                        def make_video_callback(video_title):
                            def callback(progress):
                                progress_callback(video_title, progress)
                            return callback
                        
                        video_progress_callback = make_video_callback(video_info.title)
                    
                    # 下載單個視頻
                    file_path = self.download(
                        video_info.url,
                        media_type,
                        quality,
                        video_progress_callback
                    )
                    
                    downloaded_files.append(file_path)
                
                except Exception as e:
                    print(f"無法下載視頻 '{video_info.title}': {e}")
            
            return downloaded_files
        
        except Exception as e:
            raise ValueError(f"下載播放清單失敗: {e}")
    
    def _get_audio_options(self, quality: AudioQuality,
                         progress_callback: Optional[Callable[[DownloadProgress], None]] = None) -> Dict:
        """獲取音頻下載選項"""
        output_template = str(self.download_path / "%(title)s.%(ext)s")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality.value.replace('k', ''),
            }],
            'outtmpl': output_template,
            'noplaylist': True,  # 預設不下載播放清單
        }
        
        if progress_callback:
            ydl_opts['progress_hooks'] = [self._create_progress_hook(progress_callback)]
        
        return ydl_opts
    
    def _get_video_options(self, quality: VideoQuality,
                         progress_callback: Optional[Callable[[DownloadProgress], None]] = None) -> Dict:
        """獲取視頻下載選項"""
        output_template = str(self.download_path / "%(title)s.%(ext)s")
        
        # 基於質量選擇格式
        quality_format = {
            VideoQuality.LOW: 'bestvideo[height<=360]+bestaudio/best[height<=360]/best',
            VideoQuality.MEDIUM: 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
            VideoQuality.HIGH: 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
        }
        
        ydl_opts = {
            'format': quality_format[quality],
            'merge_output_format': 'mp4',
            'outtmpl': output_template,
            'noplaylist': True,  # 預設不下載播放清單
        }
        
        if progress_callback:
            ydl_opts['progress_hooks'] = [self._create_progress_hook(progress_callback)]
        
        return ydl_opts
    
    def _create_progress_hook(self, callback: Callable[[DownloadProgress], None]):
        """創建進度回調鉤子"""
        def hook(d):
            if d['status'] == 'downloading':
                # 計算下載進度
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                percent = (downloaded / total * 100) if total else 0
                
                # 創建進度對象
                progress = DownloadProgress(
                    status='downloading',
                    percent=percent,
                    downloaded_bytes=downloaded,
                    total_bytes=total,
                    speed=d.get('speed', 0) or 0,
                    eta=d.get('eta', None),
                    filename=d.get('filename', '')
                )
                
                callback(progress)
            
            elif d['status'] == 'finished':
                progress = DownloadProgress(
                    status='finished',
                    percent=100.0,
                    downloaded_bytes=d.get('total_bytes', 0) or d.get('downloaded_bytes', 0),
                    total_bytes=d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0),
                    speed=0,
                    eta=0,
                    filename=d.get('filename', '')
                )
                
                callback(progress)
                
            elif d['status'] == 'error':
                progress = DownloadProgress(
                    status='error',
                    percent=0.0,
                    downloaded_bytes=0,
                    total_bytes=0,
                    speed=0,
                    eta=0,
                    filename=d.get('filename', '')
                )
                
                callback(progress)
        
        return hook


if __name__ == "__main__":
    # 測試代碼
    import time
    
    def print_progress(progress):
        print(f"\r下載進度: {progress.percent:.1f}% - "
              f"{progress.downloaded_bytes / 1024 / 1024:.1f}MB / "
              f"{(progress.total_bytes or 0) / 1024 / 1024:.1f}MB - "
              f"速度: {progress.speed / 1024 / 1024:.1f}MB/s - "
              f"剩餘時間: {progress.eta or 0}秒", end="")
        
        if progress.status == 'finished':
            print("\n下載完成!")
    
    def playlist_progress(title, progress):
        print(f"\r{title} - {progress.percent:.1f}%", end="")
        if progress.status == 'finished':
            print(" - 完成!")
    
    # 使用方法
    print("YouTube影片下載演示")
    print("=" * 30)
    
    url = input("請輸入YouTube URL: ")
    if not url:
        print("未提供URL，退出")
        exit(0)
    
    # 初始化下載器
    download_path = Path.home() / "Downloads" / "YouTube"
    fetcher = YouTubeFetcher(download_path)
    
    try:
        # 提取視頻信息
        print("正在提取視頻信息...")
        info = fetcher.extract_info(url)
        
        if isinstance(info, list):
            # 播放清單
            print(f"檢測到播放清單，共 {len(info)} 個視頻")
            
            # 顯示播放清單中的視頻
            for i, video in enumerate(info[:5], 1):
                print(f"{i}. {video.title} - {video.channel} ({video.duration // 60}:{video.duration % 60:02d})")
            if len(info) > 5:
                print(f"...以及其他 {len(info) - 5} 個視頻")
            
            download_choice = input("是否下載播放清單? (y/n): ").lower()
            if download_choice == 'y':
                media_choice = input("選擇媒體類型 (1=音頻, 2=視頻): ")
                media_type = MediaType.AUDIO if media_choice == '1' else MediaType.VIDEO
                
                quality_choice = input("選擇質量 (1=低, 2=中, 3=高): ")
                if media_type == MediaType.AUDIO:
                    quality_map = [AudioQuality.LOW, AudioQuality.MEDIUM, AudioQuality.HIGH]
                else:
                    quality_map = [VideoQuality.LOW, VideoQuality.MEDIUM, VideoQuality.HIGH]
                
                quality_index = min(max(int(quality_choice) - 1, 0), 2)
                quality = quality_map[quality_index]
                
                print(f"開始下載播放清單 ({media_type.value}, {quality.value})...")
                fetcher.download_playlist(url, media_type, quality, playlist_progress)
            
        else:
            # 單個視頻
            print(f"視頻: {info.title}")
            print(f"頻道: {info.channel}")
            duration_min = info.duration // 60
            duration_sec = info.duration % 60
            print(f"時長: {duration_min}:{duration_sec:02d}")
            
            download_choice = input("是否下載視頻? (y/n): ").lower()
            if download_choice == 'y':
                media_choice = input("選擇媒體類型 (1=音頻, 2=視頻): ")
                media_type = MediaType.AUDIO if media_choice == '1' else MediaType.VIDEO
                
                quality_choice = input("選擇質量 (1=低, 2=中, 3=高): ")
                if media_type == MediaType.AUDIO:
                    quality_map = [AudioQuality.LOW, AudioQuality.MEDIUM, AudioQuality.HIGH]
                else:
                    quality_map = [VideoQuality.LOW, VideoQuality.MEDIUM, VideoQuality.HIGH]
                
                quality_index = min(max(int(quality_choice) - 1, 0), 2)
                quality = quality_map[quality_index]
                
                print(f"開始下載 ({media_type.value}, {quality.value})...")
                file_path = fetcher.download(url, media_type, quality, print_progress)
                print(f"文件已保存至: {file_path}")
    
    except ValueError as e:
        print(f"錯誤: {e}")
    except Exception as e:
        print(f"未處理的錯誤: {e}") 
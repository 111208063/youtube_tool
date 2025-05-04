"""
YouTube 統一下載模組

整合單一媒體和播放清單的下載功能，提供簡潔的 API 接口。
"""
import os
import enum
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union, Any
from urllib.parse import urlparse, parse_qs

import yt_dlp
import requests

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

def clean_url(url: str) -> str:
    """
    清理 URL，移除多餘參數
    
    Args:
        url: 原始 URL
    
    Returns:
        清理後的 URL
    """
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    safe_params = {k: v for k, v in query.items() if k in ['v', 'list']}
    new_query = '&'.join([f"{k}={v[0]}" for k, v in safe_params.items()])
    return f"https://www.youtube.com{parsed.path}?{new_query}"

def is_playlist_url(url: str) -> bool:
    """
    判斷是否為播放清單 URL
    
    Args:
        url: YouTube URL
    
    Returns:
        是否為播放清單 URL
    """
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    return 'list' in query

def get_video_id(url: str) -> Optional[str]:
    """
    從 YouTube URL 中提取視頻 ID
    
    Args:
        url: YouTube URL
    
    Returns:
        視頻 ID 或 None
    """
    parsed_url = urlparse(url)
    if parsed_url.netloc in ('www.youtube.com', 'youtube.com'):
        query = parse_qs(parsed_url.query)
        if 'v' in query:
            return query['v'][0]
    elif parsed_url.netloc == 'youtu.be':
        return parsed_url.path.lstrip('/')
    return None

def fetch_thumbnail(video_id: str, thumbnail_url: str, download_dir: Optional[Union[str, Path]] = None) -> Optional[str]:
    """
    下載影片縮圖
    
    Args:
        video_id: 視頻 ID
        thumbnail_url: 縮圖 URL
        download_dir: 下載目錄
    
    Returns:
        縮圖路徑或 None
    """
    try:
        # 確保下載目錄存在
        if download_dir is None:
            # 使用相對路徑 downloads/thumbnails
            current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            root_dir = current_dir.parent
            download_dir = root_dir / "downloads" / "thumbnails"
        
        download_dir = Path(download_dir)
        download_dir.mkdir(parents=True, exist_ok=True)
        
        # 縮圖檔案路徑
        thumbnail_path = download_dir / f"{video_id}.jpg"
        
        # 如果檔案已存在，返回路徑
        if thumbnail_path.exists():
            return str(thumbnail_path)
        
        # 下載縮圖
        response = requests.get(thumbnail_url, stream=True, timeout=10)
        response.raise_for_status()
        
        with open(thumbnail_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        
        return str(thumbnail_path)
    except Exception as e:
        print(f"[錯誤] 下載縮圖失敗: {e}")
        return None

# 為了向後兼容性，保留舊的函數名稱
download_thumbnail = fetch_thumbnail

class YouTubeDownloader:
    """YouTube 下載器"""
    
    def __init__(self, download_path: Union[str, Path], temp_path: Optional[Union[str, Path]] = None):
        """
        初始化 YouTube 下載器
        
        Args:
            download_path: 下載內容的保存路徑
            temp_path: 臨時文件路徑，默認使用系統臨時目錄
        """
        self.download_path = Path(download_path)
        self.download_path.mkdir(parents=True, exist_ok=True)
        
        # 使用系統臨時目錄或應用目錄下的臨時文件夾
        if temp_path:
            self.temp_path = Path(temp_path)
        else:
            # 使用應用目錄下的臨時文件夾，而非系統臨時目錄
            root_dir = self.download_path.parent
            self.temp_path = root_dir / "temp"
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
        # 縮圖目錄 - 確保使用相對路徑
        self.thumbnail_dir = self.download_path.parent / "thumbnails"
        self.thumbnail_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_info(self, url: str, max_playlist_items: int = 100) -> Union[VideoInfo, List[VideoInfo]]:
        """
        提取視頻或播放清單的基本信息
        
        Args:
            url: YouTube URL，可以是視頻或播放清單
            max_playlist_items: 播放清單最大提取項目數量
            
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
            'playlistend': max_playlist_items,  # 限制播放清單項目數量
        }
        
        url = clean_url(url)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # 檢查是否是播放清單
                if 'entries' in info and info['entries']:
                    # 是播放清單
                    videos = []
                    entries = info.get('entries', [])
                    
                    # 如果條目過多，限制數量避免過度請求
                    if len(entries) > max_playlist_items:
                        entries = entries[:max_playlist_items]
                    
                    for entry in entries:
                        if entry:
                            try:
                                video_info = VideoInfo(
                                    id=entry.get('id', ''),
                                    title=entry.get('title', '未知標題'),
                                    thumbnail_url=entry.get('thumbnail', ''),
                                    duration=entry.get('duration', 0) or 0,
                                    channel=entry.get('uploader', entry.get('channel', '未知頻道')),
                                    upload_date=entry.get('upload_date', ''),
                                    description=entry.get('description', ''),
                                    url=entry.get('webpage_url', '') or f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                                )
                                videos.append(video_info)
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
    
    def _create_progress_hook(self, callback: Optional[Callable[[DownloadProgress], None]] = None):
        """創建下載進度回調函數"""
        def hook(d):
            if d['status'] == 'downloading':
                # 計算下載進度
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                percent = (downloaded / total * 100) if total else 0
                
                # 計算下載速度和剩餘時間
                speed = d.get('speed', 0) or 0
                eta = d.get('eta', 0) or 0
                filename = d.get('filename', '')
                
                # 顯示下載進度在終端
                print(f"\r下載進度: {percent:.1f}% - "
                    f"{downloaded / 1024 / 1024:.1f}MB / {total / 1024 / 1024:.1f}MB - "
                    f"速度: {speed / 1024 / 1024:.1f}MB/s - "
                    f"剩餘時間: {eta}秒", end="")
                
                # 如果提供了進度回調函數，也通過它傳遞進度信息
                if callback:
                    progress_data = DownloadProgress(
                        status='downloading',
                        percent=percent,
                        downloaded_bytes=downloaded,
                        total_bytes=total,
                        speed=speed,
                        eta=eta,
                        filename=filename
                    )
                    callback(progress_data)
            
            elif d['status'] == 'finished':
                print("\n下載完成，正在處理...")
                # 通知下載完成
                if callback:
                    progress_data = DownloadProgress(
                        status='finished',
                        percent=100.0,
                        downloaded_bytes=0,
                        total_bytes=0,
                        speed=0,
                        eta=0,
                        filename=d.get('filename', '')
                    )
                    callback(progress_data)
            
            elif d['status'] == 'error':
                print("\n下載失敗")
                # 通知下載錯誤
                if callback:
                    progress_data = DownloadProgress(
                        status='error',
                        percent=0.0,
                        downloaded_bytes=0,
                        total_bytes=0,
                        speed=0,
                        eta=0,
                        filename=""
                    )
                    callback(progress_data)
        
        return hook
    
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
    
    def download(self, url: str, media_type: MediaType = MediaType.AUDIO, 
                quality: Union[VideoQuality, AudioQuality] = None,
                download_playlist: bool = False,
                progress_callback: Optional[Callable[[Any], None]] = None,
                download_thumbnail: bool = True) -> Union[str, List[str]]:
        """
        統一下載功能 - 支援單一媒體與播放清單
        
        Args:
            url: YouTube URL
            media_type: 媒體類型 (音頻或視頻)
            quality: 媒體質量，如果未指定，則使用默認值：音頻使用 AudioQuality.HIGH，視頻使用 VideoQuality.MEDIUM
            download_playlist: 是否下載播放清單
            progress_callback: 進度回調函數
            download_thumbnail: 是否同時下載縮圖
            
        Returns:
            下載的文件路徑或路徑列表 (播放清單)
            
        Raises:
            ValueError: 如果URL無效或下載過程中出錯
        """
        # 設置默認質量
        if quality is None:
            if media_type == MediaType.AUDIO:
                quality = AudioQuality.HIGH
            else:
                quality = VideoQuality.MEDIUM
        
        # 檢查質量參數類型與媒體類型是否匹配
        if media_type == MediaType.AUDIO and not isinstance(quality, AudioQuality):
            raise ValueError("音頻下載必須使用AudioQuality")
        elif media_type == MediaType.VIDEO and not isinstance(quality, VideoQuality):
            raise ValueError("視頻下載必須使用VideoQuality")
        
        # 清理 URL
        url = clean_url(url)
        
        # 檢查是否為播放清單URL
        is_playlist = is_playlist_url(url)
        
        # 如果是播放清單但不需要下載整個播放清單
        if is_playlist and not download_playlist:
            # 提取視頻ID，只下載單個視頻
            video_id = get_video_id(url)
            if video_id:
                url = f"https://www.youtube.com/watch?v={video_id}"
            is_playlist = False
        
        # 如果是播放清單且需要下載全部
        if is_playlist and download_playlist:
            return self._download_playlist(url, media_type, quality, progress_callback, download_thumbnail)
        
        # 下載單個視頻
        return self._download_single(url, media_type, quality, progress_callback, download_thumbnail)
    
    def _download_single(self, url: str, media_type: MediaType, quality: Union[VideoQuality, AudioQuality],
                    progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
                    download_thumbnail: bool = True) -> str:
        """下載單個視頻"""
        # 根據媒體類型設置下載選項
        if media_type == MediaType.AUDIO:
            ydl_opts = self._get_audio_options(quality, progress_callback)
        else:
            ydl_opts = self._get_video_options(quality, progress_callback)
        
        filename = None
        try:
            # 先獲取視頻信息（不下載）
            info_opts = {
                'quiet': True,
                'skip_download': True,
            }
            
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # 提取視頻ID用於下載縮圖
                video_id = info.get('id')
                thumbnail_url = info.get('thumbnail', '')
                
                # 下載縮圖
                if download_thumbnail and video_id and thumbnail_url:
                    thumbnail_path = fetch_thumbnail(video_id, thumbnail_url, self.thumbnail_dir)
                    if thumbnail_path:
                        print(f"縮圖下載成功: {thumbnail_path}")
            
            # 下載視頻
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"\n開始下載{'音頻' if media_type == MediaType.AUDIO else '視頻'}...")
                info = ydl.extract_info(url, download=True)
                
                # 獲取下載的文件名
                if info.get('_filename'):
                    filename = info['_filename']
                elif '_downloader' in info and 'filename' in info['_downloader']:
                    filename = info['_downloader']['filename']
                else:
                    # 嘗試構造文件名
                    if media_type == MediaType.AUDIO:
                        ext = "mp3"
                    else:
                        ext = "mp4"
                    filename = str(self.download_path / f"{info.get('title', 'unknown')}.{ext}")
        
        except Exception as e:
            if progress_callback:
                progress_data = DownloadProgress(
                    status='error',
                    percent=0.0,
                    downloaded_bytes=0,
                    total_bytes=0,
                    speed=0,
                    eta=0,
                    filename=""
                )
                progress_callback(progress_data)
            raise ValueError(f"下載失敗: {e}")
        
        if not filename or not os.path.exists(filename):
            raise ValueError("下載完成但找不到文件")
        
        return filename
    
    def _download_playlist(self, url: str, media_type: MediaType, quality: Union[VideoQuality, AudioQuality],
                        progress_callback: Optional[Callable[[Union[str, DownloadProgress]], None]] = None,
                        download_thumbnail: bool = True) -> List[str]:
        """下載播放清單"""
        # 獲取播放清單信息
        try:
            playlist_info = self.extract_info(url)
            if not isinstance(playlist_info, list):
                raise ValueError("URL不是有效的播放清單")
            
            downloaded_files = []
            
            # 為每個視頻創建進度回調
            for i, video_info in enumerate(playlist_info):
                try:
                    print(f"\n[{i+1}/{len(playlist_info)}] 下載: {video_info.title}")
                    
                    # 建立針對此視頻的進度回調
                    video_progress_callback = None
                    if progress_callback:
                        def make_video_callback(video_title):
                            def callback(progress):
                                if isinstance(progress, DownloadProgress):
                                    # 將視頻標題添加到進度信息中傳遞
                                    progress_callback(f"[{video_title}] {progress.status}")
                                else:
                                    progress_callback(f"[{video_title}] {progress}")
                            return callback
                        
                        video_progress_callback = make_video_callback(video_info.title)
                    
                    # 下載單個視頻
                    file_path = self._download_single(
                        video_info.url,
                        media_type,
                        quality,
                        video_progress_callback,
                        download_thumbnail
                    )
                    
                    downloaded_files.append(file_path)
                
                except Exception as e:
                    print(f"無法下載視頻 '{video_info.title}': {e}")
            
            return downloaded_files
        
        except Exception as e:
            if progress_callback and callable(progress_callback):
                progress_callback(f"下載播放清單失敗: {e}")
            raise ValueError(f"下載播放清單失敗: {e}")

def main():
    """命令行工具主函數"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube 下載工具")
    parser.add_argument("url", help="YouTube 視頻或播放清單 URL")
    parser.add_argument("--playlist", "-p", action="store_true", help="下載整個播放清單")
    parser.add_argument("--audio-only", "-a", action="store_true", help="只下載音頻")
    parser.add_argument("--quality", "-q", choices=["low", "medium", "high"], default="high", 
                      help="媒體質量 (默認: high)")
    parser.add_argument("--output", "-o", default="downloads", help="輸出目錄 (默認: downloads)")
    parser.add_argument("--no-thumbnail", action="store_true", help="不下載縮圖")
    
    args = parser.parse_args()
    
    # 確定媒體類型
    media_type = MediaType.AUDIO if args.audio_only else MediaType.VIDEO
    
    # 設置質量
    if media_type == MediaType.AUDIO:
        quality_map = {
            "low": AudioQuality.LOW,
            "medium": AudioQuality.MEDIUM,
            "high": AudioQuality.HIGH
        }
    else:
        quality_map = {
            "low": VideoQuality.LOW,
            "medium": VideoQuality.MEDIUM,
            "high": VideoQuality.HIGH
        }
    quality = quality_map[args.quality]
    
    # 設置輸出目錄
    output_dir = Path(args.output) / media_type.value
    
    # 創建下載器並下載
    downloader = YouTubeDownloader(output_dir)
    
    try:
        print(f"開始下載 {'播放清單' if args.playlist else '視頻'}...")
        result = downloader.download(
            args.url,
            media_type,
            quality,
            args.playlist,
            None,  # 無進度回調
            not args.no_thumbnail
        )
        
        if isinstance(result, list):
            print(f"\n下載完成! 共下載了 {len(result)} 個文件到 {output_dir}")
        else:
            print(f"\n下載完成! 文件保存在 {result}")
    
    except ValueError as e:
        print(f"錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
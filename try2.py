"""
YouTube音樂下載工具 - 獨立簡易版

使用yt-dlp庫下載YouTube音樂，將元數據儲存到資料庫，文件存放到指定資料夾。
"""
import os
import sys
from pathlib import Path
import yt_dlp
from typing import Optional, Callable, Any

# 確保src目錄在路徑中以便導入資料庫模組
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from src.database import db_manager, MediaType
    from src.youtube_fetcher import DownloadProgress
except ImportError:
    print("無法導入資料庫模組，請確保src/database目錄存在")
    db_manager = None
    
    # 如果 DownloadProgress 無法導入，創建一個本地版本
    class DownloadProgress:
        def __init__(self, status: str, percent: float, downloaded_bytes: int, total_bytes: int, speed: float, eta: int, filename: str = ""):
            self.status = status
            self.percent = percent
            self.downloaded_bytes = downloaded_bytes
            self.total_bytes = total_bytes
            self.speed = speed
            self.eta = eta
            self.filename = filename

def download_audio(url, output_folder="downloads/audio", progress_callback: Optional[Callable[[Any], None]] = None):
    """
    下載YouTube視頻的音頻並將元數據儲存到資料庫
    
    Args:
        url: YouTube URL
        output_folder: 輸出文件夾
        progress_callback: 進度回調函數，接收 DownloadProgress 對象
    """
    # 確保輸出目錄存在
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 格式化輸出文件名
    output_template = str(output_path / "%(title)s.%(ext)s")
    
    # 創建一個自定義的進度回調函數
    def custom_progress_hook(d):
        """下載進度回調函數"""
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
            if progress_callback:
                progress_data = DownloadProgress(
                    status='downloading',
                    percent=percent,
                    downloaded_bytes=downloaded,
                    total_bytes=total,
                    speed=speed,
                    eta=eta,
                    filename=filename
                )
                progress_callback(progress_data)
        
        elif d['status'] == 'finished':
            print("\n下載完成，正在轉換格式...")
            # 通知下載完成
            if progress_callback:
                progress_data = DownloadProgress(
                    status='finished',
                    percent=100.0,
                    downloaded_bytes=0,
                    total_bytes=0,
                    speed=0,
                    eta=0,
                    filename=d.get('filename', '')
                )
                progress_callback(progress_data)
    
    # 下載選項
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
        'outtmpl': output_template,
        'noplaylist': True,  # 預設不下載播放清單，只取單一影片
        'progress_hooks': [custom_progress_hook],
    }
    
    try:
        # 判斷是否為播放清單URL
        is_playlist = 'list=' in url and 'watch?' in url
        
        # 如果是播放清單，但我們只要下載單一影片，移除播放清單參數
        if is_playlist:
            # 確保不會下載播放清單
            # 移除播放清單參數
            video_id = url.split('v=')[1].split('&')[0]
            url = f"https://www.youtube.com/watch?v={video_id}"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 首先獲取信息（不下載）
            info = ydl.extract_info(url, download=False)
            
            # 單個視頻
            if 'entries' in info and len(info['entries']) > 0:
                # 如果仍然返回多個，只取第一個
                entry = info['entries'][0]
                title = entry.get('title', '未知標題')
                uploader = entry.get('uploader', '未知頻道')
                duration = entry.get('duration', 0)
                video_id = entry.get('id', '')
                # 獲取單一視頻URL
                video_url = entry.get('webpage_url', url)
            else:
                # 直接使用視頻信息
                title = info.get('title', '未知標題')
                uploader = info.get('uploader', '未知頻道')
                duration = info.get('duration', 0)
                video_id = info.get('id', '')
                video_url = url
            
            minutes = duration // 60
            seconds = duration % 60
            print(f"視頻: {title}")
            print(f"頻道: {uploader}")
            print(f"時長: {minutes}:{seconds:02d}")
            
            print("\n開始下載音樂...")
            # 下載視頻
            ydl.download([video_url])
            
            # 確定下載後的檔案路徑
            output_file = output_path / f"{title}.mp3"
            if output_file.exists():
                # 添加到資料庫
                if db_manager is not None:
                    file_size = output_file.stat().st_size / (1024 * 1024)  # 轉換為MB
                    db_manager.add_media_file(
                        title=title,
                        file_path=str(output_file),
                        media_type=MediaType.AUDIO,
                        file_size=file_size,
                        duration=duration,
                        uploader=uploader,
                        youtube_id=video_id
                    )
                    print(f"已將檔案 {title} 添加到資料庫")
    
    except Exception as e:
        print(f"下載過程中發生錯誤: {e}")
        # 通知下載失敗
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
        # 重新拋出異常以便上層處理
        raise

def progress_hook(d):
    """下載進度回調函數（舊版本，保留向後兼容）"""
    if d['status'] == 'downloading':
        # 計算下載進度
        downloaded = d.get('downloaded_bytes', 0)
        total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
        percent = (downloaded / total * 100) if total else 0
        
        # 計算下載速度和剩餘時間
        speed = d.get('speed', 0) or 0
        eta = d.get('eta', 0) or 0
        
        # 顯示下載進度
        print(f"\r下載進度: {percent:.1f}% - "
              f"{downloaded / 1024 / 1024:.1f}MB / {total / 1024 / 1024:.1f}MB - "
              f"速度: {speed / 1024 / 1024:.1f}MB/s - "
              f"剩餘時間: {eta}秒", end="")
    
    elif d['status'] == 'finished':
        print("\n下載完成，正在轉換格式...")

def main():
    """主函數"""
    # 歡迎信息
    print("=" * 50)
    print("YouTube音樂下載工具 - 獨立簡易版")
    print("=" * 50)
    
    # 檢查命令行參數
    if len(sys.argv) > 1:
        # 如果提供了命令行參數，使用第一個參數作為URL
        url = sys.argv[1]
    else:
        # 否則請求用戶輸入URL
        url = input("請輸入YouTube視頻或播放清單URL: ")
    
    if not url:
        print("未提供URL，程序退出")
        return
    
    # 下載音樂
    download_audio(url)
    
    print("\n感謝使用! 程序結束")

if __name__ == "__main__":
    main() 
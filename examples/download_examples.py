"""
YouTube 下載工具使用示例

展示如何使用 unified_downloader 模組下載單一視頻和播放清單
"""
from src.unified_downloader import YouTubeDownloader, MediaType, AudioQuality, VideoQuality, DownloadProgress
from pathlib import Path
import time

def simple_progress_callback(progress):
    """簡單的進度回調函數，適用於單一媒體下載"""
    if isinstance(progress, DownloadProgress):
        if progress.status == 'downloading':
            print(f"\r下載進度: {progress.percent:.1f}% - "
                f"{progress.downloaded_bytes / 1024 / 1024:.1f}MB / {progress.total_bytes / 1024 / 1024:.1f}MB - "
                f"速度: {progress.speed / 1024 / 1024:.1f}MB/s - "
                f"剩餘時間: {progress.eta}秒", end="")
        elif progress.status == 'finished':
            print("\n下載完成!")
    else:
        print(progress)  # 處理播放清單的進度信息

def example_single_audio():
    """下載單一音頻示例"""
    print("\n=== 下載單一音頻示例 ===")
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # 替換為您想下載的視頻URL
    
    # 創建下載目錄
    output_dir = Path("examples/downloads/audio")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 創建下載器
    downloader = YouTubeDownloader(output_dir)
    
    try:
        # 下載音頻
        print(f"下載音頻: {url}")
        file_path = downloader.download(
            url=url,
            media_type=MediaType.AUDIO,
            quality=AudioQuality.HIGH,
            download_playlist=False,
            progress_callback=simple_progress_callback,
            download_thumbnail=True
        )
        print(f"音頻下載完成: {file_path}")
    except Exception as e:
        print(f"下載失敗: {e}")

def example_single_video():
    """下載單一視頻示例"""
    print("\n=== 下載單一視頻示例 ===")
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # 替換為您想下載的視頻URL
    
    # 創建下載目錄
    output_dir = Path("examples/downloads/video")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 創建下載器
    downloader = YouTubeDownloader(output_dir)
    
    try:
        # 下載視頻
        print(f"下載視頻: {url}")
        file_path = downloader.download(
            url=url,
            media_type=MediaType.VIDEO,
            quality=VideoQuality.MEDIUM,
            download_playlist=False,
            progress_callback=simple_progress_callback,
            download_thumbnail=True
        )
        print(f"視頻下載完成: {file_path}")
    except Exception as e:
        print(f"下載失敗: {e}")

def example_playlist():
    """下載播放清單示例"""
    print("\n=== 下載播放清單示例 ===")
    # 替換為您想下載的播放清單URL
    # 這是YouTube Music的熱門音樂播放清單，根據實際情況替換
    url = "https://www.youtube.com/playlist?list=PL4fGSI1pDJn6jXS_Tv_N9B8Z0HTRVJE0m" 
    
    # 創建下載目錄
    output_dir = Path("examples/downloads/playlist_audio")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 創建下載器
    downloader = YouTubeDownloader(output_dir)
    
    try:
        # 首先提取播放清單信息
        print(f"提取播放清單信息: {url}")
        playlist_info = downloader.extract_info(url)
        
        if isinstance(playlist_info, list) and playlist_info:
            print(f"播放清單包含 {len(playlist_info)} 個項目:")
            for i, video in enumerate(playlist_info[:5], 1):
                duration_min = video.duration // 60
                duration_sec = video.duration % 60
                print(f"{i}. {video.title} - {video.channel} ({duration_min}:{duration_sec:02d})")
            
            if len(playlist_info) > 5:
                print(f"...以及其他 {len(playlist_info) - 5} 個項目")
            
            # 詢問用戶是否要下載
            choice = input("是否下載此播放清單? (y/n): ").lower()
            if choice == 'y':
                # 下載播放清單
                file_paths = downloader.download(
                    url=url,
                    media_type=MediaType.AUDIO,
                    quality=AudioQuality.MEDIUM,
                    download_playlist=True,
                    progress_callback=simple_progress_callback,
                    download_thumbnail=True
                )
                print(f"播放清單下載完成! 共下載 {len(file_paths)} 個文件")
        else:
            print("無法提取播放清單信息或URL不是播放清單")
    
    except Exception as e:
        print(f"下載失敗: {e}")

def display_menu():
    """顯示功能選單"""
    print("\n=== YouTube 下載工具示例 ===")
    print("1. 下載單一音頻")
    print("2. 下載單一視頻")
    print("3. 下載播放清單")
    print("0. 退出")
    return input("請選擇功能: ")

if __name__ == "__main__":
    while True:
        choice = display_menu()
        
        if choice == "1":
            example_single_audio()
        elif choice == "2":
            example_single_video()
        elif choice == "3":
            example_playlist()
        elif choice == "0":
            print("感謝使用，再見!")
            break
        else:
            print("無效選擇，請重試!")
        
        # 等待用戶按任意鍵繼續
        input("\n按 Enter 返回主選單...") 
"""
測試統一下載模組的功能
"""
from src.unified_downloader import YouTubeDownloader, MediaType, AudioQuality, VideoQuality, DownloadProgress
import time

def progress_callback(progress: DownloadProgress):
    """處理下載進度更新"""
    if progress.status == 'downloading':
        print(f"\r進度: {progress.percent:.1f}% ({progress.downloaded_bytes/1024/1024:.1f} MB / {progress.total_bytes/1024/1024:.1f} MB) - {progress.filename}", end="")
    elif progress.status == 'finished':
        print(f"\n下載完成！文件: {progress.filename}")
    elif progress.status == 'error':
        print("\n下載失敗")

if __name__ == "__main__":
    print("=== 測試統一下載模組 ===")
    
    # 使用短影片測試（請替換為合適的 YouTube URL）
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - 第一個 YouTube 影片
    
    print(f"開始下載影片: {url}")
    print("進度將顯示在下面:")
    
    try:
        # 創建下載器
        downloader = YouTubeDownloader("downloads/audio")
        
        # 從 url 取得視頻資訊
        info = downloader.extract_info(url)
        print(f"提取到視頻：{info.title} (by {info.channel})")
        
        # 下載音頻
        result = downloader.download(
            url=url,
            media_type=MediaType.AUDIO,
            quality=AudioQuality.HIGH,
            download_playlist=False,
            progress_callback=progress_callback,
            download_thumbnail=True
        )
        
        print(f"\n文件已下載到: {result}")
    except Exception as e:
        print(f"\n下載過程中發生錯誤: {e}")
    
    # 等待一會，確保所有輸出完成
    time.sleep(1)
    print("\n測試完成") 
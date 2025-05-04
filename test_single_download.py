"""
測試 try2.py 的 download_audio 函數進度回調功能
"""
import try2
import time
from src.youtube_fetcher import DownloadProgress

def progress_callback(progress: DownloadProgress):
    """處理下載進度更新"""
    if progress.status == 'downloading':
        print(f"\r進度: {progress.percent:.1f}% ({progress.downloaded_bytes/1024/1024:.1f} MB / {progress.total_bytes/1024/1024:.1f} MB) - {progress.filename}", end="")
    elif progress.status == 'finished':
        print(f"\n下載完成！文件: {progress.filename}")
    elif progress.status == 'error':
        print("\n下載失敗")

if __name__ == "__main__":
    print("=== 測試單一影片下載與進度條 ===")
    
    # 使用短影片測試（請替換為合適的 YouTube URL）
    # 這是一個短影片示例 URL，通常用於測試
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - 第一個 YouTube 影片
    
    print(f"開始下載影片: {url}")
    print("進度將顯示在下面:")
    
    try:
        try2.download_audio(url, "downloads/audio", progress_callback)
    except Exception as e:
        print(f"\n下載過程中發生錯誤: {e}")
    
    # 等待一會，確保所有輸出完成
    time.sleep(1)
    print("\n測試完成") 
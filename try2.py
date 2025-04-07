"""
YouTube音樂下載工具 - 獨立簡易版

不依賴其他模組，直接使用yt-dlp庫下載YouTube音樂，存放到music資料夾。
"""
import os
import sys
from pathlib import Path
import yt_dlp

def download_audio(url, output_folder="music"):
    """
    下載YouTube視頻的音頻
    
    Args:
        url: YouTube URL
        output_folder: 輸出文件夾
    """
    # 確保輸出目錄存在
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 格式化輸出文件名
    output_template = str(output_path / "%(title)s.%(ext)s")
    
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
        'progress_hooks': [progress_hook],
    }
    
    try:
        # 判斷是否為播放清單URL
        is_playlist = 'list=' in url and 'watch?' in url
        
        # 如果是播放清單，詢問使用者是否要下載整個播放清單
        if is_playlist:
            choice = input("檢測到可能是播放清單URL，是否下載整個播放清單? (y/n): ").lower()
            if choice == 'y':
                # 使用者選擇下載整個播放清單
                ydl_opts['noplaylist'] = False
                print("將下載整個播放清單...")
            else:
                print("將只下載單一影片...")
                # 確保不會下載播放清單
                # 移除播放清單參數
                if 'list=' in url and 'watch?' in url:
                    # 只保留影片ID部分
                    video_id = url.split('v=')[1].split('&')[0]
                    url = f"https://www.youtube.com/watch?v={video_id}"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 首先獲取信息（不下載）
            info = ydl.extract_info(url, download=False)
            
            # 檢查是否仍然是播放清單
            if 'entries' in info and ydl_opts['noplaylist'] == False:
                # 這是播放清單
                entries = list(info['entries'])
                print(f"檢測到播放清單: {info.get('title', '未知播放清單')}")
                print(f"共 {len(entries)} 個視頻")
                
                # 顯示播放清單中的前幾個視頻
                for i, entry in enumerate(entries[:5], 1):
                    print(f"{i}. {entry.get('title', '未知標題')}")
                if len(entries) > 5:
                    print(f"...以及其他 {len(entries) - 5} 個視頻")
                
                print("開始下載播放清單...")
                ydl.download([url])
            else:
                # 單個視頻
                if 'entries' in info and len(info['entries']) > 0:
                    # 如果仍然返回多個，只取第一個
                    entry = info['entries'][0]
                    title = entry.get('title', '未知標題')
                    uploader = entry.get('uploader', '未知頻道')
                    duration = entry.get('duration', 0)
                    
                    # 獲取單一視頻URL
                    video_url = entry.get('webpage_url', url)
                else:
                    # 直接使用視頻信息
                    title = info.get('title', '未知標題')
                    uploader = info.get('uploader', '未知頻道')
                    duration = info.get('duration', 0)
                    video_url = url
                
                minutes = duration // 60
                seconds = duration % 60
                print(f"視頻: {title}")
                print(f"頻道: {uploader}")
                print(f"時長: {minutes}:{seconds:02d}")
                
                print("\n開始下載音樂...")
                ydl.download([video_url])
    
    except Exception as e:
        print(f"下載過程中發生錯誤: {e}")

def progress_hook(d):
    """下載進度回調函數"""
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
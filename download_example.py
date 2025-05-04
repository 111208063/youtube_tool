"""
YouTube 下載工具 - 命令行示例

這是一個簡單的命令行工具，展示如何使用統一下載模組下載視頻和播放清單。
"""
import argparse
import sys
from pathlib import Path

from src.unified_downloader import (
    YouTubeDownloader, MediaType, VideoQuality, AudioQuality, 
    DownloadProgress, is_playlist_url, clean_url
)

def progress_callback(progress):
    """進度回調函數"""
    if isinstance(progress, DownloadProgress):
        if progress.status == 'downloading':
            print(f"\r下載進度: {progress.percent:.1f}% - "
                  f"{progress.downloaded_bytes / 1024 / 1024:.1f}MB / {progress.total_bytes / 1024 / 1024:.1f}MB - "
                  f"速度: {progress.speed / 1024 / 1024:.1f}MB/s - "
                  f"剩餘時間: {progress.eta}秒", end="")
        elif progress.status == 'finished':
            print("\n下載完成!")
    else:
        # 處理播放清單的進度信息
        print(f"\r{progress}", end="")

def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="YouTube 下載工具")
    parser.add_argument("url", help="YouTube 視頻或播放清單 URL")
    parser.add_argument("--playlist", "-p", action="store_true", help="下載整個播放清單")
    parser.add_argument("--audio-only", "-a", action="store_true", help="只下載音頻")
    parser.add_argument("--quality", "-q", choices=["low", "medium", "high"], default="high", 
                      help="媒體質量 (默認: high)")
    parser.add_argument("--output", "-o", default="downloads", help="輸出目錄 (默認: downloads)")
    
    args = parser.parse_args()
    
    # 清理 URL
    url = clean_url(args.url)
    
    # 檢查是否為播放清單
    is_playlist = is_playlist_url(url)
    if is_playlist and not args.playlist:
        print("檢測到播放清單 URL。如果要下載整個播放清單，請使用 --playlist 參數。")
        download_playlist = input("是否下載整個播放清單? (y/n): ").lower() == 'y'
    else:
        download_playlist = args.playlist
    
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
    
    print(f"下載設置:")
    print(f"  URL: {url}")
    print(f"  下載播放清單: {'是' if download_playlist else '否'}")
    print(f"  媒體類型: {media_type.value}")
    print(f"  質量: {quality.value}")
    print(f"  輸出目錄: {output_dir}")
    
    # 確認是否繼續
    if input("\n確認以上設置並開始下載? (y/n): ").lower() != 'y':
        print("已取消下載")
        return
    
    # 創建下載器
    downloader = YouTubeDownloader(output_dir)
    
    try:
        # 提取媒體信息
        print(f"\n正在提取媒體信息...")
        info = downloader.extract_info(url)
        
        if isinstance(info, list) and info:
            # 播放清單
            print(f"\n播放清單信息:")
            print(f"  項目數量: {len(info)}")
            for i, video in enumerate(info[:5], 1):
                duration_min = video.duration // 60
                duration_sec = video.duration % 60
                print(f"  {i}. {video.title} - {video.channel} ({duration_min}:{duration_sec:02d})")
            
            if len(info) > 5:
                print(f"  ...以及其他 {len(info) - 5} 個項目")
            
            # 播放清單項目可能很多，再次確認
            if download_playlist and len(info) > 10:
                if input(f"\n播放清單包含 {len(info)} 個項目，確定要下載全部? (y/n): ").lower() != 'y':
                    print("已取消下載")
                    return
        else:
            # 單個視頻
            if not isinstance(info, list):
                video = info
                duration_min = video.duration // 60
                duration_sec = video.duration % 60
                print(f"\n視頻信息:")
                print(f"  標題: {video.title}")
                print(f"  頻道: {video.channel}")
                print(f"  時長: {duration_min}:{duration_sec:02d}")
        
        # 執行下載
        print(f"\n開始下載...")
        result = downloader.download(
            url=url,
            media_type=media_type,
            quality=quality,
            download_playlist=download_playlist,
            progress_callback=progress_callback,
            download_thumbnail=True
        )
        
        # 顯示結果
        if isinstance(result, list):
            print(f"\n下載完成! 共下載了 {len(result)} 個文件到 {output_dir}")
        else:
            print(f"\n下載完成! 文件保存在 {result}")
    
    except Exception as e:
        print(f"\n下載過程中發生錯誤: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
#!/usr/bin/env python
"""
YouTube縮圖管理工具

提供縮圖管理功能，如清理未使用的縮圖、批量下載/更新縮圖等。
"""
import os
import sys
import argparse
from pathlib import Path

# 確保src目錄在路徑中以便導入模組
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    # 導入所需模組
    from src.utils.thumbnail_utils import (
        get_unified_thumbnail_dir, download_thumbnail, 
        cleanup_unused_thumbnails, extract_video_id_from_filename,
        get_thumbnail_url_from_video_id, download_thumbnails_batch
    )
    from src.database import db_manager
except ImportError as e:
    print(f"錯誤: 無法導入所需模組 - {e}")
    sys.exit(1)

def list_thumbnails():
    """列出所有縮圖"""
    thumbnail_dir = get_unified_thumbnail_dir()
    thumbnails = list(thumbnail_dir.glob("*.jpg"))
    
    if not thumbnails:
        print("未找到任何縮圖文件")
        return
    
    print(f"共找到 {len(thumbnails)} 個縮圖文件:")
    for i, thumb in enumerate(thumbnails, 1):
        size_kb = os.path.getsize(thumb) / 1024
        print(f"{i}. {thumb.name} ({size_kb:.1f} KB)")
    print(f"\n縮圖存儲目錄: {thumbnail_dir}")

def clean_thumbnails():
    """清理未使用的縮圖"""
    # 從資料庫獲取所有使用中的YouTube ID
    media_files = db_manager.get_all_media_files()
    used_ids = {
        media.youtube_id for media in media_files 
        if hasattr(media, 'youtube_id') and media.youtube_id
    }
    
    print(f"資料庫中有 {len(used_ids)} 個正在使用的YouTube ID")
    
    # 清理未使用的縮圖
    deleted_files = cleanup_unused_thumbnails(used_ids)
    
    if deleted_files:
        print(f"已刪除 {len(deleted_files)} 個未使用的縮圖:")
        for file in deleted_files:
            print(f"- {os.path.basename(file)}")
    else:
        print("沒有找到未使用的縮圖需要清理")

def download_missing_thumbnails():
    """下載缺失的縮圖"""
    # 獲取所有媒體檔案
    media_files = db_manager.get_all_media_files()
    
    # 識別需要下載縮圖的檔案
    missing_thumbnails = []
    for media in media_files:
        # 跳過已有縮圖的檔案
        if hasattr(media, 'thumbnail_path') and media.thumbnail_path and os.path.exists(media.thumbnail_path):
            continue
        
        # 如果有YouTube ID，直接使用
        if hasattr(media, 'youtube_id') and media.youtube_id:
            missing_thumbnails.append({
                'id': media.youtube_id,
                'thumbnail_url': get_thumbnail_url_from_video_id(media.youtube_id),
                'file_path': media.file_path
            })
        else:
            # 嘗試從檔案名提取YouTube ID
            filename = os.path.basename(media.file_path)
            video_id = extract_video_id_from_filename(filename)
            if video_id:
                missing_thumbnails.append({
                    'id': video_id,
                    'thumbnail_url': get_thumbnail_url_from_video_id(video_id),
                    'file_path': media.file_path
                })
    
    if not missing_thumbnails:
        print("所有媒體檔案都已有縮圖")
        return
    
    print(f"找到 {len(missing_thumbnails)} 個需要下載縮圖的媒體檔案")
    
    # 批量下載縮圖
    result = download_thumbnails_batch(missing_thumbnails)
    
    # 更新資料庫中的縮圖路徑
    for video in missing_thumbnails:
        video_id = video['id']
        if video_id in result:
            # 更新資料庫
            db_manager.update_media_thumbnail(video['file_path'], result[video_id])
            print(f"已更新: {os.path.basename(video['file_path'])} -> {os.path.basename(result[video_id])}")
    
    print(f"縮圖下載完成: {len(result)}/{len(missing_thumbnails)} 個成功")

def main():
    parser = argparse.ArgumentParser(description="YouTube縮圖管理工具")
    
    # 添加子命令
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 列出縮圖命令
    list_parser = subparsers.add_parser("list", help="列出所有縮圖")
    
    # 清理縮圖命令
    clean_parser = subparsers.add_parser("clean", help="清理未使用的縮圖")
    
    # 下載缺失縮圖命令
    download_parser = subparsers.add_parser("download", help="下載缺失的縮圖")
    
    args = parser.parse_args()
    
    # 執行相應命令
    if args.command == "list":
        list_thumbnails()
    elif args.command == "clean":
        clean_thumbnails()
    elif args.command == "download":
        download_missing_thumbnails()
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 
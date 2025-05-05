"""
縮圖匯入/檢查程式

這個腳本用於檢查和修復媒體庫中的縮圖問題。
它會檢查數據庫中所有媒體文件記錄，嘗試尋找對應的縮圖，
並更新數據庫記錄以關聯正確的縮圖。
"""
import os
import sys
import sqlite3
import logging
from pathlib import Path
import traceback

# 將src目錄添加到Python路徑
current_dir = Path(__file__).parent
if current_dir not in sys.path:
    sys.path.insert(0, str(current_dir))

# 導入所需模組
from src.database import db_manager

def print_all_media_files_with_youtube_id():
    """打印所有媒體文件及其 YouTube ID
    
    用於調試目的，顯示資料庫中所有媒體記錄的路徑和YouTube ID
    """
    try:
        # 直接使用 SQLite 連接執行查詢
        db_path = Path("database.db")  # 數據庫在項目根目錄
        if not db_path.exists():
            print(f"數據庫文件不存在: {db_path}")
            return []
        
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row  # 使用命名列訪問
        cursor = conn.cursor()
        
        # 檢查 media_files 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='media_files'")
        if not cursor.fetchone():
            print("media_files 表不存在")
            return []
        
        cursor.execute("SELECT id, title, file_path, media_type, youtube_id, thumbnail_path FROM media_files")
        rows = cursor.fetchall()
        
        print(f"資料庫中共有 {len(rows)} 項媒體記錄:")
        for row in rows:
            print(f"ID: {row['id']}, 標題: {row['title']}")
            print(f"  路徑: {row['file_path']}")
            print(f"  媒體類型: {row['media_type']}")
            print(f"  YouTube ID: {row['youtube_id'] if row['youtube_id'] else '無'}")
            print(f"  縮圖路徑: {row['thumbnail_path'] if row['thumbnail_path'] else '無'}")
            print("---")
        
        conn.close()
        return rows
    except Exception as e:
        print(f"查詢媒體文件時出錯: {e}")
        traceback.print_exc()
        return []

# 直接更新數據庫記錄的函數
def update_media_file_thumbnail(file_path, youtube_id, thumbnail_path):
    """直接更新媒體文件的縮圖路徑和YouTube ID
    
    Args:
        file_path: 媒體文件路徑
        youtube_id: YouTube ID
        thumbnail_path: 縮圖路徑
    
    Returns:
        bool: 是否成功更新
    """
    try:
        db_path = Path("database.db")
        if not db_path.exists():
            print(f"數據庫文件不存在: {db_path}")
            return False
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 檢查記錄是否存在
        cursor.execute("SELECT id FROM media_files WHERE file_path = ?", (file_path,))
        record = cursor.fetchone()
        
        if record:
            # 更新記錄
            cursor.execute(
                "UPDATE media_files SET youtube_id = ?, thumbnail_path = ? WHERE file_path = ?",
                (youtube_id, thumbnail_path, file_path)
            )
            conn.commit()
            conn.close()
            return True
        else:
            print(f"未找到文件記錄: {file_path}")
            conn.close()
            return False
    except Exception as e:
        print(f"更新縮圖信息時出錯: {e}")
        traceback.print_exc()
        return False

def get_all_media_files():
    """從數據庫獲取所有媒體文件記錄
    
    Returns:
        list: 媒體檔案記錄清單
    """
    try:
        db_path = Path("database.db")
        if not db_path.exists():
            print(f"數據庫文件不存在: {db_path}")
            return []
            
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM media_files")
        rows = cursor.fetchall()
        
        # 將數據庫記錄轉換為字典列表
        media_files = []
        for row in rows:
            media_file = {
                'id': row['id'],
                'title': row['title'],
                'file_path': row['file_path'],
                'media_type': row['media_type'],
                'youtube_id': row['youtube_id'],
                'thumbnail_path': row['thumbnail_path'],
                'file_size': row['file_size']
            }
            media_files.append(media_file)
        
        conn.close()
        return media_files
    except Exception as e:
        print(f"獲取媒體文件出錯: {e}")
        traceback.print_exc()
        return []

def main():
    """主函數"""
    print("=== 開始檢查縮圖關聯 ===")
    
    # 打印當前所有媒體記錄
    print("\n--- 當前數據庫記錄 ---")
    print_all_media_files_with_youtube_id()
    
    # 提取縮圖目錄中所有可用的縮圖
    thumbnails_dir = Path("downloads/thumbnails")
    if not thumbnails_dir.exists():
        print(f"\n錯誤：縮圖目錄不存在：{thumbnails_dir}")
        return
    
    thumbnails = {}  # youtube_id -> 縮圖路徑
    for file in thumbnails_dir.glob("*.jpg"):
        youtube_id = file.stem  # 不含副檔名的檔名即為YouTube ID
        thumbnails[youtube_id] = str(file)
    
    print(f"\n找到 {len(thumbnails)} 個縮圖文件:")
    for youtube_id, path in thumbnails.items():
        print(f"  {youtube_id}: {path}")
    
    # 檢查每個縮圖文件是否在數據庫中有對應的記錄
    print("\n--- 檢查縮圖匹配 ---")
    
    # 直接從數據庫獲取所有媒體檔案
    all_media = get_all_media_files()
    updated_count = 0
    
    if not all_media:
        print("未找到任何媒體文件記錄")
        return
        
    print(f"找到 {len(all_media)} 個媒體文件記錄")
    
    for media_file in all_media:
        media_path = media_file['file_path']
        if not os.path.exists(media_path):
            print(f"跳過不存在的文件: {media_path}")
            continue
        
        file_name = os.path.basename(media_path)
        print(f"處理檔案: {file_name}")
        
        # 檢查是否已經有 YouTube ID
        has_youtube_id = media_file['youtube_id'] and media_file['youtube_id'].strip()
        has_thumbnail = media_file['thumbnail_path'] and os.path.exists(media_file['thumbnail_path'])
        
        # 如果已經有正確的縮圖，繼續下一個
        if has_youtube_id and has_thumbnail:
            print(f"檔案 {file_name} 已有正確的縮圖")
            continue
        
        # 嘗試手動關聯
        if len(thumbnails) > 0:
            # 只有一個縮圖，直接使用它
            youtube_id = list(thumbnails.keys())[0]
            thumbnail_path = thumbnails[youtube_id]
            
            # 直接更新數據庫
            updated = update_media_file_thumbnail(media_path, youtube_id, thumbnail_path)
            if updated:
                print(f"成功關聯 {file_name} 與縮圖 {youtube_id}.jpg")
                updated_count += 1
            else:
                print(f"更新失敗: {file_name}")
    
    print(f"\n更新了 {updated_count} 個媒體記錄的縮圖關聯")
    
    # 完成後再次打印所有記錄
    print("\n--- 更新後的數據庫記錄 ---")
    print_all_media_files_with_youtube_id()
    
    print("\n=== 檢查完成 ===")
    
    print("\n手動執行SQL更新（以防萬一）:")
    try:
        db_path = Path("database.db")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        for youtube_id, thumbnail_path in thumbnails.items():
            # 對所有媒體文件設置相同的縮圖和ID
            cursor.execute(
                "UPDATE media_files SET youtube_id = ?, thumbnail_path = ?",
                (youtube_id, thumbnail_path)
            )
            print(f"已執行SQL更新: youtube_id={youtube_id}, thumbnail_path={thumbnail_path}")
        
        conn.commit()
        conn.close()
        print("SQL更新完成")
    except Exception as e:
        print(f"手動SQL更新失敗: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 
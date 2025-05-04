# 添加根據檔案路徑刪除媒體檔案的方法
def delete_media_file_by_path(file_path: str) -> bool:
    """根據檔案路徑刪除媒體檔案記錄
    
    Args:
        file_path: 媒體檔案路徑
    
    Returns:
        bool: 是否成功刪除
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM media_files WHERE file_path = ?", (file_path,))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"刪除媒體檔案記錄時出錯: {e}")
        return False

# 添加對縮圖路徑的支持
def add_media_file(title: str, file_path: str, media_type, file_size: float, duration: int = 0, 
                   uploader: str = "", youtube_id: str = "", thumbnail_path: str = "") -> bool:
    """添加媒體檔案記錄到資料庫
    
    Args:
        title: 媒體標題
        file_path: 檔案路徑
        media_type: 媒體類型
        file_size: 檔案大小(MB)
        duration: 播放時長(秒)
        uploader: 上傳者/頻道
        youtube_id: YouTube影片ID
        thumbnail_path: 縮圖路徑
        
    Returns:
        bool: 是否成功添加
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # 檢查檔案是否已存在
            cursor.execute("SELECT id FROM media_files WHERE file_path = ?", (file_path,))
            existing = cursor.fetchone()
            
            # 處理不同來源的 MediaType
            # 獲取媒體類型的值（字符串）
            media_type_str = media_type.value if hasattr(media_type, 'value') else str(media_type)
            
            # 將字符串轉換為資料庫使用的 MediaType
            from src.database.models import MediaType as DBMediaType
            db_media_type = DBMediaType.AUDIO if media_type_str.lower() == 'audio' else DBMediaType.VIDEO
            
            if existing:
                # 檔案已存在，更新記錄
                cursor.execute(
                    """UPDATE media_files SET 
                            title = ?, 
                            media_type = ?, 
                            file_size = ?, 
                            duration = ?,
                            uploader = ?,
                            youtube_id = ?,
                            thumbnail_path = ?
                        WHERE file_path = ?""",
                    (title, db_media_type.value, file_size, duration, uploader, youtube_id, thumbnail_path, file_path)
                )
            else:
                # 添加新記錄
                cursor.execute(
                    """INSERT INTO media_files 
                        (title, file_path, media_type, file_size, duration, date_added, uploader, youtube_id, thumbnail_path) 
                    VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?, ?)""",
                    (title, file_path, db_media_type.value, file_size, duration, uploader, youtube_id, thumbnail_path)
                )
            
            conn.commit()
            return True
    
    except Exception as e:
        logging.error(f"添加媒體檔案到資料庫失敗: {e}")
        return False 

# 添加更新檔案大小的方法
def update_media_file_size(file_path: str, new_size: float) -> bool:
    """更新媒體檔案的大小
    
    Args:
        file_path: 媒體檔案路徑
        new_size: 新的檔案大小(MB)
    
    Returns:
        bool: 是否成功更新
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE media_files SET file_size = ? WHERE file_path = ?", (new_size, file_path))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"更新媒體檔案大小時出錯: {e}")
        return False 
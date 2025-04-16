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
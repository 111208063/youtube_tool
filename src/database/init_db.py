"""
資料庫初始化程序

掃描現有媒體檔案並將其添加到資料庫中。
用於從舊版存儲方式遷移到新的資料庫存儲。
"""
import os
import sys
import logging
from pathlib import Path

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 確保可以導入 src 目錄
current_dir = Path(__file__).parent
src_dir = current_dir.parent
root_dir = src_dir.parent

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# 導入數據庫模型和管理器
from src.database import db_manager
from src.database.models import MediaType as DBMediaType

# 避免與 unified_downloader 中的 MediaType 衝突
DownloaderMediaType = None
try:
    from src.unified_downloader import MediaType as DownloaderMediaType
except ImportError:
    pass

def scan_directory(directory: str) -> list:
    """掃描目錄尋找媒體檔案
    
    Args:
        directory: 要掃描的目錄
        
    Returns:
        媒體檔案路徑列表
    """
    media_files = []
    dir_path = Path(directory)
    
    if not dir_path.exists():
        logging.warning(f"目錄不存在: {directory}")
        return []
    
    logging.info(f"正在掃描目錄: {directory}")
    
    for file_path in dir_path.glob('**/*'):
        if file_path.is_file() and file_path.suffix.lower() in \
                ('.mp3', '.wav', '.aac', '.ogg', '.flac', '.mp4', '.webm', '.mkv', '.avi'):
            media_files.append(str(file_path))
    
    logging.info(f"在 {directory} 中找到 {len(media_files)} 個媒體檔案")
    return media_files


def add_file_to_database(file_path: str) -> int:
    """將檔案添加到資料庫
    
    Args:
        file_path: 檔案路徑
        
    Returns:
        int: 0=失敗，1=添加成功，2=更新成功
    """
    try:
        # 檢查檔案是否存在
        if not os.path.exists(file_path):
            logging.warning(f"檔案不存在: {file_path}")
            return 0
        
        # 檢查是否已在資料庫中
        existing = db_manager.get_media_file_by_path(file_path)
        if existing:
            # 檢查檔案是否有變更（例如大小變化）
            current_size = os.path.getsize(file_path) / (1024 * 1024)  # 轉換為MB
            if abs(existing.file_size - current_size) > 0.1:  # 允許0.1MB的誤差
                # 檔案大小變更，更新記錄
                db_manager.update_media_file_size(file_path, current_size)
                logging.info(f"檔案大小已更新: {file_path}")
                return 2
            
            logging.debug(f"檔案已在資料庫中: {file_path}")
            return 2  # 已存在並已更新
        
        # 獲取檔案基本資訊
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # 轉換為MB
        
        # 確定媒體類型
        is_audio = file_path.lower().endswith(('.mp3', '.wav', '.aac', '.ogg', '.flac'))
        media_type = DBMediaType.AUDIO if is_audio else DBMediaType.VIDEO
        
        # 尋找相關縮圖
        thumbnail_path = ""
        try:
            # 1. 嘗試從檔名中提取YouTube ID
            import re
            match = re.search(r'([-\w]{11})', file_name)
            if match:
                youtube_id = match.group(1)
                # 2. 查找對應的縮圖
                thumbnail_file = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) / "downloads" / "thumbnails" / f"{youtube_id}.jpg"
                if thumbnail_file.exists():
                    thumbnail_path = str(thumbnail_file)
        except Exception as e:
            logging.warning(f"尋找縮圖時出錯: {e}")
        
        # 添加到資料庫
        db_manager.add_media_file(
            title=file_name,
            file_path=file_path,
            media_type=media_type,
            file_size=file_size,
            thumbnail_path=thumbnail_path
        )
        
        logging.info(f"已添加到資料庫: {file_name}")
        return 1  # 新添加
    
    except Exception as e:
        logging.error(f"添加檔案 {file_path} 到資料庫失敗: {str(e)}")
        return 0  # 失敗


def main():
    """主程序"""
    logging.info("開始執行資料庫初始化")
    
    # 目錄列表
    directories = [
        # 只保留統一存儲位置
        os.path.join(root_dir, "downloads", "audio"),
        os.path.join(root_dir, "downloads", "video")
    ]
    
    # 掃描所有目錄並添加檔案
    total_files = 0
    added_files = 0
    
    for directory in directories:
        media_files = scan_directory(directory)
        total_files += len(media_files)
        
        for file_path in media_files:
            if add_file_to_database(file_path):
                added_files += 1
    
    logging.info(f"資料庫初始化完成")
    logging.info(f"總共掃描: {total_files} 個檔案")
    logging.info(f"成功添加: {added_files} 個檔案")
    

if __name__ == "__main__":
    main() 
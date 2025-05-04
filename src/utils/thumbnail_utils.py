"""
縮圖處理工具模組

提供YouTube縮圖的下載、存儲和管理功能。
"""
import os
import requests
from pathlib import Path
from typing import Optional
import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_thumbnail_path(video_id: str, download_dir: Optional[Path] = None) -> Path:
    """
    取得縮圖檔案路徑
    
    Args:
        video_id: YouTube影片ID
        download_dir: 存儲目錄，默認為 downloads/thumbnails
        
    Returns:
        縮圖存儲路徑
    """
    if download_dir is None:
        # 獲取專案根目錄
        current_dir = Path(__file__).parent
        root_dir = current_dir.parent.parent
        download_dir = root_dir / "downloads" / "thumbnails"
    
    # 確保下載目錄存在
    download_dir.mkdir(parents=True, exist_ok=True)
    
    # 返回檔案路徑
    return download_dir / f"{video_id}.jpg"

def download_thumbnail(video_id: str, thumbnail_url: str, download_dir: Optional[Path] = None) -> Optional[str]:
    """
    下載YouTube影片縮圖
    
    Args:
        video_id: YouTube影片ID
        thumbnail_url: 縮圖URL
        download_dir: 存儲目錄，默認為 downloads/thumbnails
        
    Returns:
        下載成功後的縮圖路徑，失敗則返回None
    """
    try:
        # 檢查URL
        if not thumbnail_url:
            logging.warning(f"影片 {video_id} 無有效縮圖URL")
            return None
        
        # 獲取縮圖存儲路徑
        thumbnail_path = get_thumbnail_path(video_id, download_dir)
        
        # 如果檔案已存在，直接返回路徑
        if thumbnail_path.exists():
            logging.info(f"縮圖已存在: {thumbnail_path}")
            return str(thumbnail_path)
        
        # 下載縮圖
        response = requests.get(thumbnail_url, stream=True, timeout=10)
        response.raise_for_status()
        
        # 儲存縮圖
        with open(thumbnail_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        
        logging.info(f"縮圖下載成功: {thumbnail_path}")
        return str(thumbnail_path)
    
    except Exception as e:
        logging.error(f"下載縮圖失敗: {e}")
        return None

def extract_video_id(url: str) -> Optional[str]:
    """
    從YouTube URL中提取影片ID
    
    Args:
        url: YouTube影片或播放清單URL
        
    Returns:
        影片ID或None
    """
    try:
        from urllib.parse import parse_qs, urlparse
        
        parsed_url = urlparse(url)
        if parsed_url.netloc in ('www.youtube.com', 'youtube.com'):
            query = parse_qs(parsed_url.query)
            if 'v' in query:
                return query['v'][0]
        elif parsed_url.netloc == 'youtu.be':
            return parsed_url.path.lstrip('/')
    except Exception as e:
        logging.error(f"解析YouTube URL失敗: {e}")
    
    return None

def get_thumbnail_url_from_video_id(video_id: str) -> str:
    """
    從影片ID生成縮圖URL
    
    Args:
        video_id: YouTube影片ID
        
    Returns:
        縮圖URL
    """
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg" 
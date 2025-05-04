from yt_dlp import YoutubeDL
from urllib.parse import urlparse, parse_qs
import sys
from pathlib import Path
import os

def clean_url(url):
    # 移除多餘參數（例如 &pp=xxx）
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    safe_params = {k: v for k, v in query.items() if k in ['v', 'list']}
    new_query = '&'.join([f"{k}={v[0]}" for k, v in safe_params.items()])
    return f"https://www.youtube.com{parsed.path}?{new_query}"

def get_playlist_info(url):
    opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': 'in_playlist',  # 更準確的播放清單提取模式
    }

    url = clean_url(url)

    with YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info
        except Exception as e:
            print(f"[錯誤] 無法擷取播放清單資料: {e}")
            return None

def is_playlist_url(url):
    # 透過解析網址參數來判斷是否包含播放清單
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    return 'list' in query

def get_video_id(url):
    """從YouTube URL中提取視頻ID"""
    parsed_url = urlparse(url)
    if parsed_url.netloc in ('www.youtube.com', 'youtube.com'):
        query = parse_qs(parsed_url.query)
        if 'v' in query:
            return query['v'][0]
    elif parsed_url.netloc == 'youtu.be':
        return parsed_url.path.lstrip('/')
    return None

def download_thumbnail(video_id, thumbnail_url, download_dir=None):
    """下載影片縮圖"""
    try:
        # 確保下載目錄存在
        if download_dir is None:
            current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            root_dir = current_dir.parent
            download_dir = root_dir / "downloads" / "thumbnails"
        
        download_dir = Path(download_dir)
        download_dir.mkdir(parents=True, exist_ok=True)
        
        # 縮圖檔案路徑
        thumbnail_path = download_dir / f"{video_id}.jpg"
        
        # 如果檔案已存在，返回路徑
        if thumbnail_path.exists():
            return str(thumbnail_path)
        
        # 下載縮圖
        import requests
        response = requests.get(thumbnail_url, stream=True, timeout=10)
        response.raise_for_status()
        
        with open(thumbnail_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        
        return str(thumbnail_path)
    except Exception as e:
        print(f"[錯誤] 下載縮圖失敗: {e}")
        return None

def download_video_or_playlist(url, download_playlist: bool, output_dir=None, download_thumbnails=True):
    """下載視頻或播放清單
    
    Args:
        url: YouTube視頻或播放清單URL
        download_playlist: 是否下載整個播放清單
        output_dir: 輸出目錄，默認為當前目錄
        download_thumbnails: 是否下載縮圖
    """
    # 設置默認輸出目錄
    if output_dir is None:
        current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        root_dir = current_dir.parent
        output_dir = root_dir / "downloads" / "video"
    elif isinstance(output_dir, str) and output_dir.startswith("downloads"):
        # 如果是相對路徑，使用項目根目錄
        current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        root_dir = current_dir.parent
        output_dir = root_dir / output_dir
    
    # 確保輸出目錄存在
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 縮圖目錄
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    root_dir = current_dir.parent
    thumbnail_dir = root_dir / "downloads" / "thumbnails"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    
    # 下載選項
    ydl_opts = {
        'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
    }

    if not download_playlist:
        ydl_opts['noplaylist'] = True

    # 清理URL
    url = clean_url(url)

    # 下載前先獲取信息
    info_opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': 'in_playlist' if download_playlist else False,
    }
    
    try:
        with YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # 先下載縮圖
            if download_thumbnails:
                if 'entries' in info and download_playlist:
                    # 播放清單：下載每個視頻的縮圖
                    print(f"開始下載播放清單縮圖 ({len(info['entries'])} 個項目)...")
                    for idx, entry in enumerate(info['entries']):
                        video_id = entry.get('id')
                        if not video_id:
                            continue
                        
                        # 獲取縮圖URL
                        thumbnail_url = entry.get('thumbnail')
                        if not thumbnail_url:
                            # 嘗試使用默認縮圖URL格式
                            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                        
                        # 下載縮圖
                        if thumbnail_url:
                            thumbnail_path = download_thumbnail(video_id, thumbnail_url, thumbnail_dir)
                            if thumbnail_path:
                                print(f"下載縮圖 ({idx+1}/{len(info['entries'])}): {os.path.basename(thumbnail_path)}")
                else:
                    # 單個視頻
                    video_id = get_video_id(url)
                    if video_id:
                        # 獲取縮圖URL
                        thumbnail_url = info.get('thumbnail')
                        if not thumbnail_url:
                            # 嘗試使用默認縮圖URL格式
                            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                        
                        # 下載縮圖
                        if thumbnail_url:
                            thumbnail_path = download_thumbnail(video_id, thumbnail_url, thumbnail_dir)
                            if thumbnail_path:
                                print(f"下載縮圖: {os.path.basename(thumbnail_path)}")
        
        # 開始下載視頻
        with YoutubeDL(ydl_opts) as ydl:
            print(f"開始下載{'播放清單' if download_playlist else '視頻'}...")
            ydl.download([url])
    
    except Exception as e:
        print(f"[錯誤] 下載過程中發生錯誤: {e}")

def main():
    url = input("請輸入 YouTube 影片或播放清單網址：\n> ").strip()
    is_playlist = is_playlist_url(url)

    if is_playlist:
        info = get_playlist_info(url)
        if not info:
            sys.exit()
        title = info.get('title', '未知播放清單')
        count = len(info.get('entries', []))
        print(f"偵測到播放清單：『{title}』 共 {count} 部影片。")
        choice = input("是否要下載整個播放清單？(Y/n): ").strip().lower()
        download_all = (choice != 'n')
    else:
        print("偵測為單一影片。")
        download_all = False

    # 詢問輸出目錄
    output_dir = input("請輸入輸出目錄 (按Enter使用默認目錄): ").strip()
    if not output_dir:
        output_dir = None
        
    # 是否下載縮圖
    download_thumbnails = input("是否下載縮圖？(Y/n): ").strip().lower() != 'n'

    download_video_or_playlist(url, download_all, output_dir, download_thumbnails)

if __name__ == '__main__':
    main()

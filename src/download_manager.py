from yt_dlp import YoutubeDL
from urllib.parse import urlparse, parse_qs
import sys
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

def get_playlist_info(url):
    opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': True,  # 不下載，只提取 metadata
    }

    with YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info
        except Exception as e:
            print(f"[錯誤] 無法擷取資料: {e}")
            return None

def download_video_or_playlist(url, download_playlist: bool):
    ydl_opts = {
        'outtmpl': '%(title)s.%(ext)s',
    }

    if not download_playlist:
        ydl_opts['noplaylist'] = True

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

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

    download_video_or_playlist(url, download_all)

if __name__ == '__main__':
    main()

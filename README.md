# YouTube 下載工具

一個簡單易用的 YouTube 影片與播放清單下載工具，提供直觀的圖形界面和強大的下載功能。

## 主要功能

- 下載單個 YouTube 影片或整個播放清單
- 支援下載為 MP3 音訊或 MP4 視訊格式
- 提供多種品質選項：低、中、高
- 直觀的圖形用戶界面
- 下載進度顯示
- 支援暫停、恢復和取消下載
- 自動分類和管理下載的媒體文件

## 安裝步驟

1. 確保已安裝 Python 3.8 或更高版本
2. 克隆或下載此專案
3. 安裝依賴套件:

```bash
pip install -r requirements.txt
```

4. 安裝 FFmpeg (媒體轉換必須):
   - Windows: 可以從[官方網站](https://ffmpeg.org/download.html)下載並添加到系統路徑
   - MacOS: 使用 Homebrew 安裝 `brew install ffmpeg`
   - Linux: 使用套件管理器安裝，例如 `sudo apt install ffmpeg`

## 使用方法

1. 啟動應用程式:

```bash
python src/main.py
```

2. 複製 YouTube 影片或播放清單 URL 並粘貼到程式的輸入框
3. 點擊「分析」按鈕獲取影片資訊
4. 選擇下載類型（音訊或視訊）和品質
5. 點擊「開始下載」按鈕開始下載
6. 下載完成後，可在程式顯示的位置找到文件，或預設保存位置為:
   - `~/Downloads/YouTube/audio` (音訊文件)
   - `~/Downloads/YouTube/video` (視訊文件)

## 注意事項

- 本工具僅供個人學習和研究使用
- 請遵守 YouTube 服務條款
- 請勿下載受版權保護的內容用於商業用途

## 技術堆疊

- Python 3.8+
- PyQt6 (GUI 框架)
- yt-dlp (YouTube 下載庫)
- FFmpeg (媒體處理)

## 未來計劃功能

- 媒體庫管理和播放功能
- 自訂下載格式和參數
- 批量下載和佇列管理
- 更多網站支援

## 授權

此專案採用 MIT 授權條款 - 詳情參見 LICENSE 文件

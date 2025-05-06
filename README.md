# YouTube 下載工具

一個功能豐富的 YouTube 影片與播放清單下載工具，提供直觀的圖形界面、強大的下載功能和媒體管理系統。

## 主要功能

- 下載單個 YouTube 影片或整個播放清單
- 支援下載為 MP3 音訊或 MP4 視訊格式
- 提供多種品質選項
  - 音訊：低 (128k)、中 (192k)、高 (320k)
  - 視訊：低 (360p)、中 (720p)、高 (1080p)
- 內建媒體庫管理功能，自動管理和分類下載的媒體文件
- 直觀美觀的深色主題圖形用戶界面
- 展示下載進度和詳細資訊
- 資料庫支援，保存已下載媒體的資訊
- 支援循環播放、隨機播放功能

## 系統需求

- **作業系統**：Windows 10/11, macOS 10.14+, 或 Linux
- **Python**：Python 3.8 或更高版本 (建議使用 Python 3.10+)
- **記憶體**：至少 4GB RAM
- **空間**：至少 500MB 可用硬碟空間（不含下載的媒體檔案）
- **網路**：穩定的網路連接
- **其他**：FFmpeg（用於媒體轉換，注意：打包版本已內建，無需另外安裝）

## 技術堆疊

- Python 3.10+
- PyQt6 (GUI 框架)
- yt-dlp (YouTube 下載庫)
- pytube (YouTube 擷取功能)
- SQLAlchemy (資料庫 ORM)
- FFmpeg (媒體處理)
- SQLite (本地資料庫)

## 安裝步驟

### 方法一：從源碼運行

1. 確保已安裝 Python 3.8+ (建議 Python 3.10+)
2. 克隆或下載此專案：
   ```bash
   git clone https://github.com/your-username/youtube-downloader.git
   cd youtube-downloader
   ```

3. 安裝依賴套件：
   ```bash
   pip install -r requirements.txt
   ```

4. 安裝 FFmpeg (媒體轉換必須)：
   - Windows: 可以從[官方網站](https://ffmpeg.org/download.html)下載並添加到系統路徑
   - MacOS: 使用 Homebrew 安裝 `brew install ffmpeg`
   - Linux: 使用套件管理器安裝，例如 `sudo apt install ffmpeg`

### 方法二：使用虛擬環境（推薦）

```bash
# 創建虛擬環境
python -m venv .venv

# 啟動虛擬環境
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
```

### 方法三：使用獨立可執行檔（推薦）

1. 從 [release](https://github.com/111208063/youtube_tool/releases) 頁面下載最新的打包版本：
   

2. 解壓縮下載的檔案到任意位置

3. 直接運行可執行檔：
   - Windows: 雙擊 `YouTubetool.exe`
   

4. 無需安裝 Python 或 FFmpeg，所有必要的依賴都已包含在內

## 使用方法

1. 啟動應用程式：
   ```bash
   python src/main.py
   ```

2. 使用下載功能：
   - 複製 YouTube 影片或播放清單 URL 並粘貼到程式的輸入框
   - 點擊「分析」按鈕獲取影片資訊
   - 選擇下載類型（音訊或視訊）和品質
   - 點擊「開始下載」按鈕開始下載
   - 下載過程中可以暫停、恢復或取消下載

3. 媒體庫功能：
   - 切換到「媒體庫」標籤可查看所有已下載的媒體文件
   - 支援依類型（音訊/視訊）篩選和搜尋功能
   - 直接從媒體庫播放或開啟文件所在資料夾

4. 下載完成後，可在程式的媒體庫中找到文件，或預設保存位置為：
   - `downloads/audio` (音訊文件)
   - `downloads/video` (視訊文件)

## 螢幕截圖

### 主界面
![主界面](docs/mainpage.png)
*下載頁面主界面*

### 分析影片
![分析影片](docs/analyzepage.png)
*影片分析結果顯示*

### 下載進度
![下載進度](docs/dlpage.png)
*顯示下載進度與操作選項*

### 媒體庫
![媒體庫](docs/mediapage.png)
*媒體庫界面，顯示已下載內容*

## 打包指南

### 使用 PyInstaller 創建可執行檔

1. 安裝 PyInstaller：
   ```bash
   pip install pyinstaller
   ```

2. 執行打包命令：
   ```bash
   # Windows
   pyinstaller --onefile --windowed --icon=assets/icon.ico --name="YouTube下載工具" src/main.py
   
   # macOS
   pyinstaller --onefile --windowed --icon=assets/icon.icns --name="YouTube下載工具" src/main.py
   
   # Linux
   pyinstaller --onefile --windowed --icon=assets/icon.png --name="YouTube下載工具" src/main.py
   ```

3. 打包後的檔案位於 `dist` 目錄中

### 或使用提供的打包腳本

```bash
# Windows
scripts/build_windows.bat

# macOS/Linux
bash scripts/build_unix.sh
```

## 注意事項

- 本工具僅供個人學習和研究使用
- 請遵守 YouTube 服務條款
- 請勿下載受版權保護的內容用於商業用途
- 本工具不儲存或分享任何受版權保護的內容
- 使用本工具下載內容的風險由使用者自行承擔

## 目錄結構

```
youtube-downloader/
├── src/                  # 源代碼目錄
│   ├── gui/              # 圖形界面相關代碼
│   ├── database/         # 資料庫模組
│   ├── utils/            # 工具函數
│   ├── core/             # 核心功能模組
│   ├── main.py           # 程式入口點
│   └── unified_downloader.py # YouTube 影片下載器
├── downloads/            # 下載文件存儲目錄
│   ├── audio/            # 音訊文件
│   ├── video/            # 視訊文件
│   └── thumbnails/       # 縮圖存儲目錄
├── tests/                # 測試代碼
├── docs/                 # 文檔
├── assets/               # 圖標和資源文件
├── scripts/              # 打包和工具腳本
├── requirements.txt      # 依賴套件列表
└── README.md             # 專案說明
```

## 常見問題解答

1. **下載速度很慢怎麼辦？**
   - YouTube 可能會限制下載速度，請嘗試稍後重新下載
   - 檢查您的網路連接是否穩定

2. **無法下載某些影片？**
   - 某些影片可能有年齡限制或其他限制，本工具可能無法下載
   - 檢查 URL 是否正確，或嘗試使用其他版本的影片 URL

3. **找不到下載的文件？**
   - 檢查預設下載路徑：`downloads/audio` 和 `downloads/video`
   - 使用媒體庫功能查看您的下載歷史

4. **打包後的應用程式無法運行？**
   - 檢查是否有防毒軟件阻止執行
   - 嘗試使用管理員權限運行
   - 對於打包版本，無需額外安裝 FFmpeg，它已經內建

## 未來計劃功能

- 更多格式與編碼選項
- 批量下載和佇列管理改進
- 更多網站支援
- 內建簡易播放器
- 下載排程功能
- 自訂下載格式和參數
- 匯出/匯入下載歷史
- 國際化支援

## 貢獻指南

歡迎提供貢獻！如果您想為專案做出貢獻，請：

1. Fork 這個專案
2. 創建您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟一個 Pull Request

## 開發指南

### 環境設置

建議使用虛擬環境進行開發：

```bash
# 創建虛擬環境
python -m venv .venv

# 啟動虛擬環境
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 安裝開發依賴
pip install -r requirements-dev.txt
```

### 項目結構說明

- `src/gui/`: 包含所有圖形介面相關代碼
  - `main_window.py`: 主視窗實現
  - `download_manager.py`: 下載管理實現
  - `media_library.py`: 媒體庫頁面實現
  
- `src/database/`: 資料庫相關功能
  - `db_manager.py`: 資料庫操作封裝
  - `init_db.py`: 資料庫初始化工具
  
- `src/unified_downloader.py`: 核心下載功能實現

### 測試

在提交之前，請確保進行適當的測試：

```bash
# 運行所有測試
pytest

# 運行特定測試
pytest tests/test_downloader.py
```

## 授權

此專案採用 MIT 授權條款 - 詳情參見 LICENSE 文件

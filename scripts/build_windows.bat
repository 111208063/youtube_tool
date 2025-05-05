@echo off
echo ===== YouTube下載工具打包腳本 =====
echo 正在檢查環境...

REM 檢查 Python 是否已安裝
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo 錯誤: 未找到 Python，請安裝 Python 3.8 或更高版本。
    exit /b 1
)

REM 檢查虛擬環境
if not exist .venv (
    echo 正在創建虛擬環境...
    python -m venv .venv
)

REM 激活虛擬環境
call .venv\Scripts\activate

REM 安裝依賴
echo 正在安裝依賴...
pip install -r requirements.txt
pip install pyinstaller requests

REM 創建 assets 目錄（如果不存在）
if not exist assets mkdir assets

REM 下載 FFmpeg
echo 正在下載 FFmpeg...
if not exist temp mkdir temp
cd temp

REM 使用 Python 下載 FFmpeg
echo from urllib.request import urlretrieve > download_ffmpeg.py
echo import zipfile, os, shutil >> download_ffmpeg.py
echo print("正在下載 FFmpeg...") >> download_ffmpeg.py
echo url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip" >> download_ffmpeg.py
echo zip_path = "ffmpeg.zip" >> download_ffmpeg.py
echo urlretrieve(url, zip_path) >> download_ffmpeg.py
echo print("下載完成，正在解壓...") >> download_ffmpeg.py
echo with zipfile.ZipFile(zip_path, 'r') as zip_ref: >> download_ffmpeg.py
echo     zip_ref.extractall(".") >> download_ffmpeg.py
echo print("尋找 ffmpeg.exe...") >> download_ffmpeg.py
echo ffmpeg_dir = None >> download_ffmpeg.py
echo for root, dirs, files in os.walk("."): >> download_ffmpeg.py
echo     if "ffmpeg.exe" in files: >> download_ffmpeg.py
echo         ffmpeg_dir = root >> download_ffmpeg.py
echo         break >> download_ffmpeg.py
echo if ffmpeg_dir: >> download_ffmpeg.py
echo     print(f"找到 ffmpeg.exe 在 {ffmpeg_dir}") >> download_ffmpeg.py
echo     if not os.path.exists("../ffmpeg"): >> download_ffmpeg.py
echo         os.makedirs("../ffmpeg") >> download_ffmpeg.py
echo     shutil.copy(os.path.join(ffmpeg_dir, "ffmpeg.exe"), "../ffmpeg/ffmpeg.exe") >> download_ffmpeg.py
echo     print("已複製 ffmpeg.exe 到 ffmpeg 目錄") >> download_ffmpeg.py
echo else: >> download_ffmpeg.py
echo     print("無法找到 ffmpeg.exe") >> download_ffmpeg.py

REM 執行 Python 腳本下載 FFmpeg
python download_ffmpeg.py
cd ..

REM 檢查圖標是否存在，如果不存在則使用默認圖標
set ICON_OPTION=
if exist assets\icon.ico (
    set ICON_OPTION=--icon=assets\icon.ico
) else (
    echo 警告: 未找到圖標文件 (assets\icon.ico)，將使用默認圖標。
)

REM 清理舊的打包文件
echo 正在清理舊的打包文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

REM 開始打包
echo 正在打包應用程式...
pyinstaller --onefile --windowed %ICON_OPTION% --name="YouTube下載工具" ^
    --add-data "src;src" ^
    --add-data "ffmpeg;ffmpeg" ^
    --hidden-import=PyQt6 ^
    --hidden-import=PyQt6.QtCore ^
    --hidden-import=PyQt6.QtGui ^
    --hidden-import=PyQt6.QtWidgets ^
    src\main.py

REM 創建打包後需要的目錄結構
if not exist dist\YouTube下載工具\downloads mkdir dist\YouTube下載工具\downloads
if not exist dist\YouTube下載工具\downloads\audio mkdir dist\YouTube下載工具\downloads\audio
if not exist dist\YouTube下載工具\downloads\video mkdir dist\YouTube下載工具\downloads\video
if not exist dist\YouTube下載工具\downloads\thumbnails mkdir dist\YouTube下載工具\downloads\thumbnails

REM 複製必要的檔案
echo 正在複製必要的檔案...
copy README.md dist\YouTube下載工具\
if exist LICENSE copy LICENSE dist\YouTube下載工具\

REM 複製 FFmpeg 到發布目錄
if exist ffmpeg\ffmpeg.exe (
    if not exist dist\YouTube下載工具\ffmpeg mkdir dist\YouTube下載工具\ffmpeg
    copy ffmpeg\ffmpeg.exe dist\YouTube下載工具\ffmpeg\
    echo 已複製 FFmpeg 到發布目錄
)

REM 創建一個簡單的說明文件
echo 感謝您使用 YouTube 下載工具！ > dist\YouTube下載工具\使用說明.txt
echo. >> dist\YouTube下載工具\使用說明.txt
echo 1. 執行 YouTube下載工具.exe 啟動程式 >> dist\YouTube下載工具\使用說明.txt
echo 2. 將 YouTube 影片網址貼入輸入框 >> dist\YouTube下載工具\使用說明.txt
echo 3. 選擇下載類型（音訊或視訊）和品質 >> dist\YouTube下載工具\使用說明.txt
echo 4. 點擊「開始下載」 >> dist\YouTube下載工具\使用說明.txt
echo 5. 下載的檔案將存放在 downloads 資料夾中 >> dist\YouTube下載工具\使用說明.txt
echo. >> dist\YouTube下載工具\使用說明.txt
echo 注意: 本程式已內建 FFmpeg，無需額外安裝 >> dist\YouTube下載工具\使用說明.txt
echo. >> dist\YouTube下載工具\使用說明.txt
echo 如需更多協助，請參閱 README.md 檔案 >> dist\YouTube下載工具\使用說明.txt

REM 打包成ZIP檔案
echo 正在創建ZIP檔案...
cd dist
powershell Compress-Archive -Path "YouTube下載工具" -DestinationPath "YouTube下載工具_Windows.zip" -Force
cd ..

echo ===== 打包完成 =====
echo 可執行檔位於: dist\YouTube下載工具\YouTube下載工具.exe
echo ZIP檔案位於: dist\YouTube下載工具_Windows.zip
echo.
echo 注意: 應用程式已內建 FFmpeg，用戶無需額外安裝

REM 清理臨時文件
if exist temp rmdir /s /q temp
if exist ffmpeg rmdir /s /q ffmpeg

REM 取消激活虛擬環境
call .venv\Scripts\deactivate

pause 
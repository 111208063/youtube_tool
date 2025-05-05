#!/bin/bash

echo "===== YouTube下載工具打包腳本 ====="
echo "正在檢查環境..."

# 檢查 Python 是否已安裝
if ! command -v python3 &> /dev/null; then
    echo "錯誤: 未找到 Python，請安裝 Python 3.8 或更高版本。"
    exit 1
fi

# 判斷作業系統類型
OS_TYPE=$(uname)
if [ "$OS_TYPE" == "Darwin" ]; then
    PLATFORM="macOS"
    ICON_PATH="assets/icon.icns"
    SEP=":"
    FFMPEG_URL="https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"
    FFMPEG_BIN="ffmpeg"
else
    PLATFORM="Linux"
    ICON_PATH="assets/icon.png"
    SEP=":"
    FFMPEG_URL="https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz"
    FFMPEG_BIN="ffmpeg"
fi

# 檢查虛擬環境
if [ ! -d ".venv" ]; then
    echo "正在創建虛擬環境..."
    python3 -m venv .venv
fi

# 激活虛擬環境
source .venv/bin/activate

# 安裝依賴
echo "正在安裝依賴..."
pip install -r requirements.txt
pip install pyinstaller requests

# 創建 assets 目錄（如果不存在）
mkdir -p assets

# 下載 FFmpeg
echo "正在下載 FFmpeg..."
mkdir -p temp
cd temp

# 使用 Python 下載並解壓 FFmpeg
cat > download_ffmpeg.py << 'EOF'
import os
import sys
import shutil
import requests
import tarfile
import zipfile
from urllib.request import urlretrieve

platform = sys.argv[1]
ffmpeg_url = sys.argv[2]
ffmpeg_bin = sys.argv[3]

print(f"正在為 {platform} 下載 FFmpeg...")
if platform == "macOS":
    # macOS
    archive_file = "ffmpeg.zip"
    urlretrieve(ffmpeg_url, archive_file)
    with zipfile.ZipFile(archive_file, 'r') as zip_ref:
        zip_ref.extractall(".")
    if os.path.exists(ffmpeg_bin):
        if not os.path.exists("../ffmpeg"):
            os.makedirs("../ffmpeg")
        shutil.copy(ffmpeg_bin, "../ffmpeg/")
        os.chmod("../ffmpeg/ffmpeg", 0o755)  # Make executable
        print("已複製 ffmpeg 到 ffmpeg 目錄")
    else:
        print("無法找到 ffmpeg 執行檔")
else:
    # Linux
    archive_file = "ffmpeg.tar.xz"
    response = requests.get(ffmpeg_url, stream=True)
    with open(archive_file, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    with tarfile.open(archive_file, 'r:xz') as tar:
        tar.extractall(".")
    
    # 尋找 ffmpeg 執行檔
    ffmpeg_path = None
    for root, dirs, files in os.walk("."):
        if ffmpeg_bin in files:
            ffmpeg_path = os.path.join(root, ffmpeg_bin)
            break
    
    if ffmpeg_path:
        if not os.path.exists("../ffmpeg"):
            os.makedirs("../ffmpeg")
        shutil.copy(ffmpeg_path, "../ffmpeg/")
        os.chmod("../ffmpeg/ffmpeg", 0o755)  # Make executable
        print(f"已複製 ffmpeg 到 ffmpeg 目錄")
    else:
        print("無法找到 ffmpeg 執行檔")
EOF

# 執行 Python 腳本下載 FFmpeg
python3 download_ffmpeg.py "$PLATFORM" "$FFMPEG_URL" "$FFMPEG_BIN"
cd ..

# 檢查圖標是否存在，如果不存在則使用默認圖標
ICON_OPTION=""
if [ -f "$ICON_PATH" ]; then
    ICON_OPTION="--icon=$ICON_PATH"
else
    echo "警告: 未找到圖標文件 ($ICON_PATH)，將使用默認圖標。"
fi

# 清理舊的打包文件
echo "正在清理舊的打包文件..."
rm -rf build dist *.spec

# 開始打包
echo "正在打包應用程式..."
pyinstaller --onefile --windowed $ICON_OPTION --name="YouTube下載工具" \
    --add-data "src${SEP}src" \
    --add-data "ffmpeg${SEP}ffmpeg" \
    --hidden-import=PyQt6 \
    --hidden-import=PyQt6.QtCore \
    --hidden-import=PyQt6.QtGui \
    --hidden-import=PyQt6.QtWidgets \
    src/main.py

# 創建打包後需要的目錄結構
mkdir -p dist/YouTube下載工具/downloads/audio
mkdir -p dist/YouTube下載工具/downloads/video
mkdir -p dist/YouTube下載工具/downloads/thumbnails

# 複製必要的檔案
echo "正在複製必要的檔案..."
cp README.md dist/YouTube下載工具/
if [ -f "LICENSE" ]; then
    cp LICENSE dist/YouTube下載工具/
fi

# 複製 FFmpeg 到發布目錄
if [ -f "ffmpeg/ffmpeg" ]; then
    mkdir -p dist/YouTube下載工具/ffmpeg
    cp ffmpeg/ffmpeg dist/YouTube下載工具/ffmpeg/
    chmod +x dist/YouTube下載工具/ffmpeg/ffmpeg
    echo "已複製 FFmpeg 到發布目錄"
fi

# 創建一個簡單的說明文件
cat > dist/YouTube下載工具/使用說明.txt << EOF
感謝您使用 YouTube 下載工具！

1. 執行 YouTube下載工具 啟動程式
2. 將 YouTube 影片網址貼入輸入框
3. 選擇下載類型（音訊或視訊）和品質
4. 點擊「開始下載」
5. 下載的檔案將存放在 downloads 資料夾中

注意: 本程式已內建 FFmpeg，無需額外安裝

如需更多協助，請參閱 README.md 檔案
EOF

# 打包成壓縮檔案
echo "正在創建壓縮檔案..."
cd dist
if [ "$PLATFORM" == "macOS" ]; then
    zip -r "YouTube下載工具_macOS.zip" "YouTube下載工具"
else
    tar -czvf "YouTube下載工具_Linux.tar.gz" "YouTube下載工具"
fi
cd ..

echo "===== 打包完成 ====="
if [ "$PLATFORM" == "macOS" ]; then
    echo "可執行檔位於: dist/YouTube下載工具/YouTube下載工具"
    echo "ZIP檔案位於: dist/YouTube下載工具_macOS.zip"
else
    echo "可執行檔位於: dist/YouTube下載工具/YouTube下載工具"
    echo "TAR檔案位於: dist/YouTube下載工具_Linux.tar.gz"
fi
echo ""
echo "注意: 應用程式已內建 FFmpeg，用戶無需額外安裝"

# 清理臨時文件
rm -rf temp ffmpeg

# 取消激活虛擬環境
deactivate 
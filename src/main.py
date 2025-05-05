"""
YouTube下載工具主程序

提供應用程式的入口點，啟動主視窗。
"""
import sys
import os
import logging
from pathlib import Path

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 檢測並設定 FFmpeg 路徑
def setup_ffmpeg():
    """檢測並設定 FFmpeg 路徑"""
    # 檢查是否有內建的 FFmpeg
    current_dir = Path(__file__).parent
    parent_dir = current_dir.parent
    bundled_ffmpeg = None
    
    # 檢查打包後的路徑
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
        potential_paths = [
            base_dir / "ffmpeg" / "ffmpeg.exe",  # Windows
            base_dir / "ffmpeg" / "ffmpeg",      # Unix
            base_dir.parent / "ffmpeg" / "ffmpeg.exe",  # Windows 替代路徑
            base_dir.parent / "ffmpeg" / "ffmpeg",      # Unix 替代路徑
        ]
        
        for path in potential_paths:
            if path.exists():
                bundled_ffmpeg = str(path)
                logging.info(f"找到內建 FFmpeg: {bundled_ffmpeg}")
                break
    
    # 檢查開發環境路徑
    if not bundled_ffmpeg:
        potential_paths = [
            parent_dir / "ffmpeg" / "ffmpeg.exe",  # Windows
            parent_dir / "ffmpeg" / "ffmpeg",      # Unix
        ]
        
        for path in potential_paths:
            if path.exists():
                bundled_ffmpeg = str(path)
                logging.info(f"找到開發環境 FFmpeg: {bundled_ffmpeg}")
                break
    
    # 如果找到內建的 FFmpeg，則將其添加到 PATH
    if bundled_ffmpeg:
        ffmpeg_dir = str(Path(bundled_ffmpeg).parent)
        
        # 添加到環境變數 PATH
        if ffmpeg_dir not in os.environ["PATH"]:
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]
            logging.info(f"已將 FFmpeg 目錄添加到 PATH: {ffmpeg_dir}")
        
        return True
    else:
        # 嘗試檢測系統 FFmpeg
        try:
            import subprocess
            subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info("使用系統 FFmpeg")
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            logging.warning("未找到 FFmpeg，某些功能可能不可用")
            return False

# 將src目錄添加到Python路徑
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if parent_dir not in sys.path:
    sys.path.insert(0, str(parent_dir))

# 確保try2.py可以被導入
if parent_dir / "try2.py" not in sys.path:
    sys.path.insert(0, str(parent_dir))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon

from src.gui.main_window import MainWindow
from src.database import db_manager
from src.database.init_db import scan_directory, add_file_to_database


def initialize_database():
    """初始化資料庫，掃描現有媒體檔案"""
    logging.info("初始化資料庫...")
    
    # 清理資料庫中的重複記錄和不存在的檔案記錄
    removed_duplicates, removed_nonexistent = db_manager.cleanup_database()
    if removed_duplicates > 0 or removed_nonexistent > 0:
        logging.info(f"資料庫清理完成：移除了 {removed_duplicates} 個重複記錄和 {removed_nonexistent} 個不存在檔案的記錄")
    
    # 目錄列表 - 只包含標準下載目錄
    directories = [
        # 標準下載目錄
        str(parent_dir / "downloads" / "audio"),
        str(parent_dir / "downloads" / "video"),
    ]
    
    # 確保縮圖目錄存在
    thumbnail_dir = parent_dir / "downloads" / "thumbnails"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    
    # 將縮圖目錄添加到PATH
    os.environ["THUMBNAIL_DIR"] = str(thumbnail_dir)
    logging.info(f"設置縮圖目錄: {thumbnail_dir}")
    
    # 確保目錄存在
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    # 掃描所有目錄並添加檔案
    total_files = 0
    added_files = 0
    updated_files = 0
    
    # 掃描目錄
    for directory in directories:
        logging.info(f"掃描目錄: {directory}")
        media_files = scan_directory(directory)
        total_files += len(media_files)
        
        for file_path in media_files:
            result = add_file_to_database(file_path)
            if result == 1:  # 新增檔案
                added_files += 1
            elif result == 2:  # 更新檔案
                updated_files += 1
    
    logging.info(f"資料庫初始化完成")
    logging.info(f"總共掃描: {total_files} 個檔案")
    logging.info(f"成功添加: {added_files} 個新檔案")
    logging.info(f"成功更新: {updated_files} 個現有檔案")


def main():
    """主程序入口點"""
    # 檢測並設定 FFmpeg
    ffmpeg_available = setup_ffmpeg()
    
    # 初始化資料庫
    initialize_database()
    
    # 創建應用程式
    app = QApplication(sys.argv)
    app.setApplicationName("YouTube 下載工具")
    
    # 設置應用圖標（如果存在）
    # icon_path = current_dir / "assets" / "icon.png"
    # if icon_path.exists():
    #     app.setWindowIcon(QIcon(str(icon_path)))
    
    # 設置應用樣式表
    app.setStyleSheet("""
        QWidget {
            font-family: "微軟正黑體", "Microsoft JhengHei", Arial, sans-serif;
            background-color: #121212;
            color: white;
        }
        QMainWindow, QDialog {
            background-color: #121212;
        }
        QLabel {
            color: white;
        }
        QPushButton {
            background-color: #333333;
            color: white;
            border: 1px solid #444444;
            padding: 5px 10px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #444444;
        }
        QPushButton:pressed {
            background-color: #555555;
        }
        QLineEdit, QTextEdit, QComboBox {
            background-color: #333333;
            color: white;
            border: 1px solid #444444;
            padding: 5px;
            border-radius: 4px;
        }
        QLineEdit:focus, QTextEdit:focus {
            border: 1px solid #6366f1;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox QAbstractItemView {
            background-color: #333333;
            color: white;
            selection-background-color: #4f46e5;
        }
        QScrollArea, QScrollBar {
            background-color: #1a1a1a;
            color: white;
        }
        QScrollBar:horizontal, QScrollBar:vertical {
            background-color: #333333;
            border: none;
        }
        QScrollBar::handle:horizontal, QScrollBar::handle:vertical {
            background-color: #555555;
            border-radius: 4px;
        }
        QScrollBar::handle:horizontal:hover, QScrollBar::handle:vertical:hover {
            background-color: #666666;
        }
        QStatusBar {
            background-color: #1a1c23;
            color: white;
        }
        QMenu {
            background-color: #1e1e1e;
            color: white;
            border: 1px solid #444444;
        }
        QMenu::item:selected {
            background-color: #4f46e5;
        }
    """)
    
    # 如果未找到 FFmpeg，顯示警告
    if not ffmpeg_available:
        QMessageBox.warning(
            None, 
            "FFmpeg 未找到", 
            "未能找到 FFmpeg，部分影片和音訊處理功能可能無法正常工作。\n\n"
            "請安裝 FFmpeg 並確保其可以在命令行中執行。"
        )
    
    # 創建並顯示主視窗
    window = MainWindow()
    window.show()
    
    # 執行應用程式
    exit_code = app.exec()
    
    # 關閉資料庫連接
    db_manager.close()
    logging.info("資料庫連接已關閉")
    
    # 退出程式
    sys.exit(exit_code)


if __name__ == "__main__":
    main() 
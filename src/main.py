"""
YouTube下載工具主程序

提供應用程式的入口點，啟動主視窗。
"""
import sys
import os
from pathlib import Path

# 將src目錄添加到Python路徑
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if parent_dir not in sys.path:
    sys.path.insert(0, str(parent_dir))

# 確保try2.py可以被導入
if parent_dir / "try2.py" not in sys.path:
    sys.path.insert(0, str(parent_dir))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from src.gui.main_window import MainWindow


def main():
    """主程序入口點"""
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
        }
    """)
    
    # 創建並顯示主視窗
    window = MainWindow()
    window.show()
    
    # 執行應用程式
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 
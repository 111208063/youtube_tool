"""
媒體庫模組

提供媒體庫界面，包括顯示媒體列表、搜索媒體和播放媒體的功能。
"""
import os
from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QScrollArea, QMessageBox,
    QFileDialog
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtMultimedia import QMediaPlayer

# 導入資料庫模組
from src.database import db_manager, MediaType
from src.gui.media_player import MediaPlayerWindow


class MediaItem(QWidget):
    """媒體項目元件，用於在媒體庫中顯示單一媒體項目"""
    
    clicked = pyqtSignal(str)  # 發出被點擊的媒體文件路徑
    play_requested = pyqtSignal(str)  # 請求播放指定媒體
    
    def __init__(self, file_path: str, thumbnail_path: Optional[str] = None, parent=None):
        """初始化媒體項目元件
        
        Args:
            file_path: 媒體文件路徑
            thumbnail_path: 縮圖路徑（可選）
            parent: 父元件
        """
        super().__init__(parent)
        self.file_path = file_path
        self.thumbnail_path = thumbnail_path
        self._init_ui()
    
    def _init_ui(self):
        """初始化用戶界面"""
        # 設置佈局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 縮圖區域
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(160, 120)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setStyleSheet("background-color: #1e1e1e; border-radius: 4px;")
        
        # 如果有縮圖，載入縮圖
        if self.thumbnail_path and os.path.exists(self.thumbnail_path):
            pixmap = QPixmap(self.thumbnail_path)
            self.thumbnail.setPixmap(pixmap.scaled(160, 120, Qt.AspectRatioMode.KeepAspectRatio))
        else:
            # 根據檔案類型顯示默認圖標
            if self.file_path.lower().endswith(('.mp3', '.wav', '.aac', '.ogg', '.flac')):
                self.thumbnail.setText("🎵")
            else:
                self.thumbnail.setText("🎬")
            self.thumbnail.setStyleSheet("font-size: 48px; background-color: #1e1e1e; border-radius: 4px;")
        
        # 檔案名稱標籤
        self.title_label = QLabel(os.path.basename(self.file_path))
        self.title_label.setStyleSheet("color: white; font-weight: bold;")
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setMaximumWidth(160)
        
        # 播放按鈕
        self.play_button = QPushButton("播放")
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                border: none;
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #6366f1;
            }
        """)
        self.play_button.clicked.connect(self.on_play_clicked)
        
        # 添加元件到佈局
        layout.addWidget(self.thumbnail)
        layout.addWidget(self.title_label)
        layout.addWidget(self.play_button)
        
        # 設置樣式和大小
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-radius: 8px;
            }
            QWidget:hover {
                background-color: #383838;
            }
        """)
        self.setFixedSize(180, 220)
        
        # 設置鼠標點擊事件
        self.mousePressEvent = self.on_item_clicked
    
    def on_item_clicked(self, event):
        """元件被點擊時發出信號，同時更改樣式"""
        self.clicked.emit(self.file_path)
        event.accept()
    
    def on_play_clicked(self):
        """播放按鈕被點擊時發出播放請求信號"""
        self.play_requested.emit(self.file_path)


class MediaLibrary(QWidget):
    """媒體庫界面，顯示下載的媒體文件"""
    
    def __init__(self, download_dir: str, parent=None):
        """初始化媒體庫界面
        
        Args:
            download_dir: 下載目錄路徑
            parent: 父元件
        """
        super().__init__(parent)
        
        # 設置下載目錄和子目錄
        self.download_dir = Path(download_dir)
        self.audio_dir = self.download_dir / "audio"
        self.video_dir = self.download_dir / "video"
        
        # 確保目錄存在
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化UI
        self._init_ui()
        
        # 刷新媒體庫
        self.refresh_media_library()
    
    def _init_ui(self):
        """初始化用戶界面"""
        # 主佈局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 頂部控制區域
        top_layout = QHBoxLayout()
        
        # 搜尋欄
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜尋媒體...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #333333;
                color: white;
                border: 1px solid #444444;
                padding: 8px;
                border-radius: 4px;
            }
        """)
        
        # 過濾類型下拉菜單
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部媒體", "音訊", "視訊"])
        self.filter_combo.setStyleSheet("""
            QComboBox {
                background-color: #333333;
                color: white;
                border: 1px solid #444444;
                padding: 8px;
                border-radius: 4px;
                min-width: 120px;
            }
        """)
        
        # 搜尋按鈕
        self.search_button = QPushButton("搜尋")
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #6366f1;
            }
        """)
        self.search_button.clicked.connect(self.apply_filter)
        
        # 匯入按鈕
        self.import_button = QPushButton("匯入媒體")
        self.import_button.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border: 1px solid #444444;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
        """)
        self.import_button.clicked.connect(self.import_media)
        
        # 刷新按鈕
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border: 1px solid #444444;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
        """)
        self.refresh_button.clicked.connect(self.refresh_media_library)
        
        # 添加元件到頂部佈局
        top_layout.addWidget(self.search_input, 3)
        top_layout.addWidget(self.filter_combo, 1)
        top_layout.addWidget(self.search_button, 1)
        top_layout.addWidget(self.import_button, 1)
        top_layout.addWidget(self.refresh_button, 1)
        
        # 媒體顯示區域
        media_scroll = QScrollArea()
        media_scroll.setWidgetResizable(True)
        media_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #121212;
                border: none;
            }
        """)
        
        media_container = QWidget()
        self.media_layout = QGridLayout(media_container)
        self.media_layout.setContentsMargins(10, 10, 10, 10)
        self.media_layout.setSpacing(10)
        
        media_scroll.setWidget(media_container)
        
        # 預覽區域
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(10, 10, 10, 10)
        
        self.preview_title = QLabel("未選擇媒體")
        self.preview_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        
        self.preview_info = QLabel("選擇一個媒體文件以查看詳細資訊")
        self.preview_info.setStyleSheet("color: white;")
        self.preview_info.setWordWrap(True)
        
        # 操作按鈕
        action_layout = QHBoxLayout()
        
        self.play_button = QPushButton("播放")
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #6366f1;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
        """)
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play_selected_media)
        
        self.delete_button = QPushButton("刪除")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ef4444;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
        """)
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.delete_selected_media)
        
        action_layout.addWidget(self.play_button)
        action_layout.addWidget(self.delete_button)
        
        # 添加元件到預覽佈局
        preview_layout.addWidget(self.preview_title)
        preview_layout.addWidget(self.preview_info)
        preview_layout.addLayout(action_layout)
        preview_layout.addStretch()
        
        # 創建底部區域（預覽區）
        bottom_container = QWidget()
        bottom_container.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-radius: 8px;
            }
        """)
        bottom_container.setLayout(preview_layout)
        bottom_container.setFixedHeight(200)
        
        # 添加所有佈局到主佈局
        main_layout.addLayout(top_layout)
        main_layout.addWidget(media_scroll, 1)
        main_layout.addWidget(bottom_container)
        
        # 初始化媒體項目列表
        self.media_items = []
        self.selected_media_path = None
        
    def refresh_media_library(self):
        """重新讀取並顯示媒體庫中的所有媒體文件"""
        # 清除當前顯示的媒體項目
        self._clear_media_items()
        
        # 從資料庫獲取所有媒體檔案
        media_files = db_manager.get_all_media_files()
        
        # 將資料庫記錄轉換為路徑列表，並去除重複
        seen_paths = set()
        unique_file_paths = []
        
        for media_file in media_files:
            # 檢查文件是否存在以及路徑是否已處理過
            if os.path.exists(media_file.file_path) and media_file.file_path not in seen_paths:
                unique_file_paths.append(media_file.file_path)
                seen_paths.add(media_file.file_path)
        
        # 顯示媒體項目
        self._display_media_items(unique_file_paths)
    
    def _scan_directory(self, directory: Path) -> List[str]:
        """
        掃描目錄獲取媒體文件列表
        
        這個方法被保留用於向下兼容，但現在主要從資料庫獲取檔案
        """
        if not directory.exists():
            return []
        
        files = []
        for file_path in directory.glob('**/*'):
            if file_path.is_file() and file_path.suffix.lower() in \
                    ('.mp3', '.wav', '.aac', '.ogg', '.flac', '.mp4', '.webm', '.mkv', '.avi'):
                files.append(str(file_path))
        
        return files
    
    def _display_media_items(self, file_paths: List[str]):
        """顯示媒體項目在網格中"""
        # 清除現有項目
        self._clear_media_items()
        
        # 創建並添加新媒體項目
        row, col = 0, 0
        max_cols = 4  # 每行顯示的最大項目數
        
        for file_path in file_paths:
            # 創建媒體項目元件
            media_item = MediaItem(file_path)
            media_item.clicked.connect(self.on_media_selected)
            media_item.play_requested.connect(self.play_media)
            
            # 將項目添加到網格佈局
            self.media_layout.addWidget(media_item, row, col)
            self.media_items.append(media_item)
            
            # 更新行列位置
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def _clear_media_items(self):
        """清除所有媒體項目"""
        # 刪除所有媒體項目
        for item in self.media_items:
            self.media_layout.removeWidget(item)
            item.deleteLater()
        
        self.media_items = []
    
    def on_media_selected(self, file_path: str):
        """處理媒體項目選擇事件"""
        self.selected_media_path = file_path
        
        # 從資料庫獲取檔案信息
        media_file = db_manager.get_media_file_by_path(file_path)
        
        if media_file:
            # 如果資料庫中有記錄，使用資料庫中的信息
            self.preview_title.setText(media_file.title)
            
            # 格式化時間
            if media_file.duration:
                minutes = int(media_file.duration) // 60
                seconds = int(media_file.duration) % 60
                duration_str = f"{minutes}:{seconds:02d}"
            else:
                duration_str = "未知"
            
            self.preview_info.setText(
                f"檔案大小: {media_file.file_size:.2f} MB\n"
                f"持續時間: {duration_str}\n"
                f"上傳者: {media_file.uploader or '未知'}\n"
                f"類型: {'音訊' if media_file.media_type == MediaType.AUDIO else '視訊'}\n"
                f"路徑: {file_path}"
            )
        else:
            # 如果資料庫中沒有記錄，顯示基本文件信息
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # 轉換為MB
            
            self.preview_title.setText(file_name)
            self.preview_info.setText(f"檔案大小: {file_size:.2f} MB\n"
                                      f"路徑: {file_path}")
        
        # 啟用操作按鈕
        self.play_button.setEnabled(True)
        self.delete_button.setEnabled(True)
    
    def play_media(self, file_path: str):
        """播放指定的媒體文件"""
        # 使用新的媒體播放器視窗播放媒體
        self.player_window = MediaPlayerWindow(file_path)
        self.player_window.show()
        
        # 當視窗關閉時清除引用
        self.player_window.destroyed.connect(self.clear_player_reference)
    
    def clear_player_reference(self):
        """清除播放器視窗的引用"""
        if hasattr(self, 'player_window'):
            self.player_window = None
    
    def play_selected_media(self):
        """播放當前選中的媒體"""
        if self.selected_media_path:
            self.play_media(self.selected_media_path)
    
    def delete_selected_media(self):
        """刪除當前選中的媒體"""
        if not self.selected_media_path:
            return
        
        # 顯示確認對話框
        reply = QMessageBox.question(
            self, "確認刪除",
            f"確定要刪除檔案 {os.path.basename(self.selected_media_path)} 嗎?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 從資料庫中刪除記錄
                db_manager.delete_media_file_by_path(self.selected_media_path)
                
                # 刪除文件
                os.remove(self.selected_media_path)
                
                # 更新UI
                self.selected_media_path = None
                self.preview_title.setText("未選擇媒體")
                self.preview_info.setText("選擇一個媒體文件以查看詳細資訊")
                self.play_button.setEnabled(False)
                self.delete_button.setEnabled(False)
                
                # 重新整理媒體庫
                self.refresh_media_library()
                
                QMessageBox.information(self, "刪除成功", "檔案已成功刪除")
            except Exception as e:
                QMessageBox.critical(self, "刪除失敗", f"無法刪除檔案: {str(e)}")
    
    def import_media(self):
        """匯入外部媒體文件到媒體庫"""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("媒體檔案 (*.mp3 *.wav *.mp4 *.webm *.mkv *.avi)")
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            
            if not selected_files:
                return
            
            for file_path in selected_files:
                try:
                    # 確定目標目錄
                    file_ext = os.path.splitext(file_path)[1].lower()
                    is_audio = file_ext in ('.mp3', '.wav', '.aac', '.ogg', '.flac')
                    
                    target_dir = self.audio_dir if is_audio else self.video_dir
                    target_path = target_dir / os.path.basename(file_path)
                    
                    # 檢查目標路徑是否已存在
                    if os.path.exists(target_path):
                        reply = QMessageBox.question(
                            self, "檔案已存在",
                            f"檔案 {os.path.basename(file_path)} 已存在。是否覆蓋?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        
                        if reply != QMessageBox.StandardButton.Yes:
                            continue
                    
                    # 複製文件
                    import shutil
                    shutil.copy2(file_path, target_path)
                    
                    # 添加到資料庫
                    file_size = os.path.getsize(target_path) / (1024 * 1024)  # 轉換為MB
                    media_type = MediaType.AUDIO if is_audio else MediaType.VIDEO
                    
                    db_manager.add_media_file(
                        title=os.path.basename(target_path),
                        file_path=str(target_path),
                        media_type=media_type,
                        file_size=file_size
                    )
                    
                except Exception as e:
                    QMessageBox.critical(self, "匯入失敗", f"匯入檔案 {os.path.basename(file_path)} 失敗: {str(e)}")
            
            # 重新整理媒體庫
            self.refresh_media_library()
    
    def apply_filter(self):
        """應用過濾條件"""
        filter_type = self.filter_combo.currentText()
        search_text = self.search_input.text().lower()
        
        # 根據過濾類型和搜尋文字從資料庫獲取媒體檔案
        if filter_type == "音訊":
            # 獲取音訊檔案
            media_files = db_manager.get_media_files_by_type(MediaType.AUDIO)
        elif filter_type == "視訊":
            # 獲取視訊檔案
            media_files = db_manager.get_media_files_by_type(MediaType.VIDEO)
        else:
            # 獲取所有媒體檔案
            media_files = db_manager.get_all_media_files()
        
        # 根據搜尋文字過濾
        if search_text:
            # 從資料庫搜尋
            search_results = db_manager.search_media_files(search_text)
            
            # 找出交集
            filtered_files = [media_file for media_file in media_files 
                             if any(media_file.id == sr.id for sr in search_results)]
        else:
            filtered_files = media_files
        
        # 僅保留存在的檔案，並去除重複
        seen_paths = set()
        unique_file_paths = []
        
        for media_file in filtered_files:
            # 檢查文件是否存在以及路徑是否已處理過
            if os.path.exists(media_file.file_path) and media_file.file_path not in seen_paths:
                unique_file_paths.append(media_file.file_path)
                seen_paths.add(media_file.file_path)
        
        # 顯示過濾後的媒體檔案
        self._display_media_items(unique_file_paths) 
"""
媒體庫模組

提供媒體庫的界面和功能，可顯示、播放和管理下載的媒體文件。
"""
import os
from pathlib import Path
from typing import List, Optional, Dict, Tuple

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QUrl, QThread, QMutex, QMutexLocker
from PyQt6.QtGui import QIcon, QPixmap, QImage
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QComboBox, QLineEdit, QScrollArea, QSplitter, QFrame,
    QGridLayout, QFileDialog, QMenu, QMessageBox, QToolButton
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

class MediaItem(QWidget):
    """媒體項目元件，用於在媒體庫中顯示單一媒體項目"""
    
    clicked = pyqtSignal(str)  # 發出被點擊的媒體文件路徑
    play_requested = pyqtSignal(str)  # 請求播放指定媒體
    
    def __init__(self, file_path: str, thumbnail_path: Optional[str] = None, parent=None):
        """
        初始化媒體項目元件
        
        Args:
            file_path: 媒體文件的完整路徑
            thumbnail_path: 縮圖文件的路徑，如果沒有則使用默認圖標
            parent: 父元件
        """
        super().__init__(parent)
        self.file_path = file_path
        self.thumbnail_path = thumbnail_path
        
        # 獲取文件名和媒體類型
        self.file_name = os.path.basename(file_path)
        self.is_audio = file_path.lower().endswith(('.mp3', '.wav', '.aac', '.ogg', '.flac'))
        
        self._init_ui()
        
    def _init_ui(self):
        """初始化用戶界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # 縮圖容器
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(QSize(160, 90))
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet("""
            background-color: #f0f0f0;
            border-radius: 4px;
        """)
        
        # 設置縮圖
        if self.thumbnail_path and os.path.exists(self.thumbnail_path):
            pixmap = QPixmap(self.thumbnail_path)
            self.thumbnail_label.setPixmap(pixmap.scaled(
                self.thumbnail_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            # 使用默認圖標
            icon_name = "audio-file.png" if self.is_audio else "video-file.png"
            self.thumbnail_label.setText(icon_name)  # 實際使用中應該設置一個真實的圖標
        
        # 文件名標籤
        self.name_label = QLabel(self.file_name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet("font-size: 12px;")
        
        # 按鈕
        button_layout = QHBoxLayout()
        
        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon.fromTheme("media-playback-start"))  # 使用系統圖標
        self.play_button.setFixedSize(QSize(24, 24))
        self.play_button.setToolTip("播放")
        self.play_button.clicked.connect(self.on_play_clicked)
        
        self.info_button = QPushButton()
        self.info_button.setIcon(QIcon.fromTheme("dialog-information"))
        self.info_button.setFixedSize(QSize(24, 24))
        self.info_button.setToolTip("檔案資訊")
        
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.info_button)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 將所有元件加入佈局
        layout.addWidget(self.thumbnail_label)
        layout.addWidget(self.name_label)
        layout.addLayout(button_layout)
        
        # 設置樣式和行為
        self.setMinimumWidth(180)
        self.setMaximumWidth(200)
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 8px;
            }
            QWidget:hover {
                background-color: #f8f8f8;
                border: 1px solid #e0e0e0;
            }
        """)
        
        # 連接信號
        self.mousePressEvent = self.on_item_clicked
    
    def on_item_clicked(self, event):
        """處理點擊事件"""
        self.clicked.emit(self.file_path)
    
    def on_play_clicked(self):
        """處理播放按鈕點擊事件"""
        self.play_requested.emit(self.file_path)


class MediaLibrary(QWidget):
    """媒體庫主界面"""
    
    def __init__(self, download_dir: str, parent=None):
        """
        初始化媒體庫
        
        Args:
            download_dir: 下載目錄的路徑
            parent: 父元件
        """
        super().__init__(parent)
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # 音訊和視訊子目錄
        self.audio_dir = self.download_dir / "audio"
        self.video_dir = self.download_dir / "video"
        self.audio_dir.mkdir(exist_ok=True)
        self.video_dir.mkdir(exist_ok=True)
        
        # 初始化播放器
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # 初始化UI
        self._init_ui()
        
        # 載入媒體文件
        self.refresh_media_library()
        
    def _init_ui(self):
        """初始化用戶界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 頂部工具欄
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(10, 10, 10, 10)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部媒體", "音訊", "視訊"])
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜尋媒體檔案...")
        self.search_input.textChanged.connect(self.apply_filter)
        
        self.refresh_button = QPushButton("重新整理")
        self.refresh_button.clicked.connect(self.refresh_media_library)
        
        self.import_button = QPushButton("匯入檔案")
        self.import_button.clicked.connect(self.import_media)
        
        toolbar_layout.addWidget(QLabel("顯示:"))
        toolbar_layout.addWidget(self.filter_combo)
        toolbar_layout.addWidget(self.search_input)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.refresh_button)
        toolbar_layout.addWidget(self.import_button)
        
        # 主內容區域的背景色設置為灰色
        self.setStyleSheet("background-color: #bbbbbb;")
        
        # 創建分割器：媒體庫 + 預覽面板
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 媒體網格容器
        self.media_container = QWidget()
        self.media_container.setStyleSheet("background-color: #bbbbbb;")
        self.media_layout = QGridLayout(self.media_container)
        self.media_layout.setContentsMargins(15, 15, 15, 15)
        self.media_layout.setSpacing(15)
        
        # 創建可滾動區域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.media_container)
        scroll_area.setStyleSheet("background-color: #bbbbbb; border: none;")
        
        # 預覽面板
        preview_panel = QFrame()
        preview_panel.setFrameShape(QFrame.Shape.StyledPanel)
        preview_panel.setStyleSheet("background-color: #bbbbbb; border: 1px solid #aaaaaa;")
        preview_layout = QVBoxLayout(preview_panel)
        
        self.preview_title = QLabel("未選擇媒體")
        self.preview_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        self.preview_info = QLabel("選擇一個媒體文件以查看詳細資訊")
        self.preview_info.setWordWrap(True)
        
        self.play_button = QPushButton("播放")
        self.play_button.setIcon(QIcon.fromTheme("media-playback-start"))
        self.play_button.clicked.connect(self.play_selected_media)
        self.play_button.setEnabled(False)
        
        self.delete_button = QPushButton("刪除")
        self.delete_button.setIcon(QIcon.fromTheme("edit-delete"))
        self.delete_button.clicked.connect(self.delete_selected_media)
        self.delete_button.setEnabled(False)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.delete_button)
        
        preview_layout.addWidget(self.preview_title)
        preview_layout.addWidget(self.preview_info)
        preview_layout.addStretch()
        preview_layout.addLayout(button_layout)
        
        # 添加到分割器
        splitter.addWidget(scroll_area)
        splitter.addWidget(preview_panel)
        splitter.setSizes([700, 300])  # 設置初始大小比例
        
        # 添加到主佈局
        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(splitter)
        
        # 初始化成員變數
        self.media_items = []
        self.selected_media_path = None
        
    def refresh_media_library(self):
        """重新讀取並顯示媒體庫中的所有媒體文件"""
        # 清除當前顯示的媒體項目
        self._clear_media_items()
        
        # 讀取媒體文件
        audio_files = self._scan_directory(self.audio_dir)
        video_files = self._scan_directory(self.video_dir)
        
        # 也掃描music目錄，try2.py下載的文件保存在這裡
        music_dir = Path("music")
        music_files = []
        if music_dir.exists():
            music_files = self._scan_directory(music_dir)
        
        # 合併文件列表
        all_files = audio_files + video_files + music_files
        self._display_media_items(all_files)
    
    def _scan_directory(self, directory: Path) -> List[str]:
        """掃描目錄獲取媒體文件列表"""
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
        
        # 更新預覽面板
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
        # 設置媒體源並播放
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.media_player.play()
    
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
                    if target_path.exists():
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
                    
                except Exception as e:
                    QMessageBox.critical(self, "匯入失敗", f"匯入檔案 {os.path.basename(file_path)} 失敗: {str(e)}")
            
            # 重新整理媒體庫
            self.refresh_media_library()
    
    def apply_filter(self):
        """應用過濾條件"""
        filter_type = self.filter_combo.currentText()
        search_text = self.search_input.text().lower()
        
        # 讀取並過濾媒體文件
        audio_files = self._scan_directory(self.audio_dir)
        video_files = self._scan_directory(self.video_dir)
        
        # 也掃描music目錄
        music_dir = Path("music")
        music_files = []
        if music_dir.exists():
            music_files = self._scan_directory(music_dir)
        
        # 合併音訊文件
        audio_files = audio_files + music_files
        
        filtered_files = []
        
        # 根據類型過濾
        if filter_type == "音訊":
            all_files = audio_files
        elif filter_type == "視訊":
            all_files = video_files
        else:  # 全部媒體
            all_files = audio_files + video_files
        
        # 根據搜尋文字過濾
        if search_text:
            filtered_files = [
                file_path for file_path in all_files
                if search_text in os.path.basename(file_path).lower()
            ]
        else:
            filtered_files = all_files
        
        # 顯示過濾後的結果
        self._display_media_items(filtered_files) 
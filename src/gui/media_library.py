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
    QFileDialog, QSlider, QMenu
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

# 導入資料庫模組
from src.database import db_manager, MediaType
from src.gui.media_player import MediaPlayerWindow


class MediaItem(QWidget):
    """媒體項目元件，用於在媒體庫中顯示單一媒體項目"""
    
    clicked = pyqtSignal(str)  # 發出被點擊的媒體文件路徑
    play_requested = pyqtSignal(str)  # 請求播放指定媒體
    delete_requested = pyqtSignal(str)  # 請求刪除指定媒體
    
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
        self.is_playing = False
        self.is_checked = False
        self.delete_mode = False
        self._init_ui()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def _init_ui(self):
        """初始化用戶界面"""
        # 設置佈局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 勾選框（初始時隱藏）- 使用QCheckBox而非QLabel
        self.check_box = QPushButton()
        self.check_box.setFixedSize(30, 30)
        self.check_box.setCheckable(True)
        self.check_box.setChecked(False)
        self.check_box.clicked.connect(self.on_checkbox_clicked)
        self.check_box.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid #6366f1;
                border-radius: 15px;
            }
            QPushButton:checked {
                background-color: #6366f1;
                border: 2px solid white;
                border-radius: 15px;
                text-align: center;
            }
        """)
        self.check_box.hide()  # 初始時隱藏
        
        # 縮圖區域
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(60, 60)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setStyleSheet("background-color: #1e1e1e; border-radius: 4px;")
        
        # 如果有縮圖，載入縮圖
        if self.thumbnail_path and os.path.exists(self.thumbnail_path):
            pixmap = QPixmap(self.thumbnail_path)
            self.thumbnail.setPixmap(pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio))
        else:
            # 根據檔案類型顯示默認圖標
            if self.file_path.lower().endswith(('.mp3', '.wav', '.aac', '.ogg', '.flac')):
                self.thumbnail.setText("🎵")
            else:
                self.thumbnail.setText("🎬")
            self.thumbnail.setStyleSheet("font-size: 24px; background-color: #1e1e1e; border-radius: 4px;")
        
        # 訊息區域
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        # 檔案名稱標籤
        self.title_label = QLabel(os.path.basename(self.file_path))
        self.title_label.setStyleSheet("color: white; font-weight: bold;")
        self.title_label.setWordWrap(True)
        
        # 檔案路徑標籤
        path_label = QLabel(os.path.dirname(self.file_path))
        path_label.setStyleSheet("color: #999; font-size: 12px;")
        path_label.setWordWrap(True)
        
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(path_label)
        
        # 播放按鈕 - 使用圖標而非文字
        self.play_button = QPushButton("▶")  # 預設播放圖標
        self.play_button.setFixedWidth(80)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                border: none;
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #6366f1;
            }
        """)
        self.play_button.clicked.connect(self.on_play_clicked)
        
        # 添加元件到佈局
        layout.addWidget(self.check_box)
        layout.addWidget(self.thumbnail)
        layout.addWidget(info_widget, 1)
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
        self.setFixedHeight(80)
        
        # 設置鼠標點擊事件
        self.mousePressEvent = self.on_item_clicked
    
    def on_item_clicked(self, event):
        """元件被點擊時發出信號，同時更改樣式"""
        self.clicked.emit(self.file_path)
        event.accept()
    
    def on_play_clicked(self):
        """播放按鈕被點擊時發出播放請求信號或切換播放狀態"""
        self.play_requested.emit(self.file_path)
    
    def update_play_state(self, is_playing: bool):
        """更新播放狀態
        
        Args:
            is_playing: 是否正在播放
        """
        self.is_playing = is_playing
        self.play_button.setText("❚❚" if is_playing else "▶")  # 根據狀態顯示暫停或播放圖標
    
    def set_delete_mode(self, enabled: bool):
        """設置刪除模式
        
        Args:
            enabled: 是否啟用刪除模式
        """
        self.delete_mode = enabled
        self.check_box.setVisible(enabled)
        self.play_button.setVisible(not enabled)
        # 重置選中狀態
        if not enabled:
            self.is_checked = False
            self.check_box.setChecked(False)
    
    def toggle_checked(self):
        """切換勾選狀態"""
        self.is_checked = not self.is_checked
        self.check_box.setChecked(self.is_checked)
    
    def on_checkbox_clicked(self):
        """處理勾選框點擊事件"""
        self.is_checked = self.check_box.isChecked()
        self.clicked.emit(self.file_path)  # 發出點擊信號
    
    def mousePressEvent(self, event):
        """鼠標點擊事件處理"""
        if self.delete_mode:
            self.toggle_checked()
            # 發出點擊信號，但需要區分是否處於刪除模式
            self.clicked.emit(self.file_path)
        else:
            # 原有的點擊處理
            self.on_item_clicked(event)

    def show_context_menu(self, position):
        """顯示上下文菜單
        
        Args:
            position: 菜單顯示位置
        """
        # 創建菜單
        context_menu = QMenu(self)
        context_menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e1e;
                color: white;
                border: 1px solid #444444;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #4f46e5;
            }
        """)
        
        # 添加菜單項
        play_action = context_menu.addAction("播放")
        delete_action = context_menu.addAction("刪除")
        
        # 顯示菜單並獲取所選擇的動作
        action = context_menu.exec(self.mapToGlobal(position))
        
        # 處理動作
        if action == play_action:
            self.play_requested.emit(self.file_path)
        elif action == delete_action:
            # 發出刪除請求信號
            # 我們需要在MediaLibrary類中添加一個刪除單個文件的方法
            # 先定義一個刪除信號
            from PyQt6.QtCore import pyqtSignal
            if not hasattr(self.__class__, 'delete_requested'):
                self.__class__.delete_requested = pyqtSignal(str)
            self.delete_requested.emit(self.file_path)


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
        
        # 當前播放的媒體
        self.current_player = None
        self.current_media_path = None
        self.current_media_title = None
        
        # 初始化UI
        self._init_ui()
        
        # 刷新媒體庫
        self.refresh_media_library()
    
    def _init_ui(self):
        """初始化用戶界面"""
        # 主佈局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 頂部控制區域
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(10, 10, 10, 10)
        
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
        
        # 刪除按鈕
        self.delete_button = QPushButton("批量刪除")  # 修改按鈕文本
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
                background-color: #7f1d1d;
                color: #d1d5db;
            }
        """)
        self.delete_button.clicked.connect(self.toggle_delete_mode)
        
        # 確認刪除按鈕（初始時隱藏）
        self.confirm_delete_button = QPushButton("確認刪除")
        self.confirm_delete_button.setStyleSheet("""
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
        """)
        self.confirm_delete_button.clicked.connect(self.delete_selected_media)
        self.confirm_delete_button.hide()
        
        # 取消刪除按鈕（初始時隱藏）
        self.cancel_delete_button = QPushButton("取消")
        self.cancel_delete_button.setStyleSheet("""
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
        self.cancel_delete_button.clicked.connect(self.cancel_delete_mode)
        self.cancel_delete_button.hide()
        
        # 添加元件到頂部佈局
        top_layout.addWidget(self.search_input, 3)
        top_layout.addWidget(self.filter_combo, 1)
        top_layout.addWidget(self.search_button, 1)
        top_layout.addWidget(self.import_button, 1)
        top_layout.addWidget(self.refresh_button, 1)
        top_layout.addWidget(self.delete_button, 1)
        top_layout.addWidget(self.confirm_delete_button, 1)
        top_layout.addWidget(self.cancel_delete_button, 1)
        
        # 媒體顯示區域
        self.media_scroll = QScrollArea()
        self.media_scroll.setWidgetResizable(True)
        self.media_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #121212;
                border: none;
            }
        """)
        
        media_container = QWidget()
        self.media_layout = QVBoxLayout(media_container)
        self.media_layout.setContentsMargins(10, 10, 10, 10)
        self.media_layout.setSpacing(10)
        self.media_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.media_scroll.setWidget(media_container)
        
        # 播放進度界面（常駐顯示）
        self.player_bar = QWidget()
        self.player_bar.setFixedHeight(80)
        self.player_bar.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border-top: 1px solid #333333;
            }
        """)
        
        player_layout = QHBoxLayout(self.player_bar)
        player_layout.setContentsMargins(15, 10, 15, 10)
        
        # 當前播放的媒體信息
        self.now_playing_icon = QLabel("🎵")
        self.now_playing_icon.setStyleSheet("font-size: 24px;")
        self.now_playing_icon.setFixedSize(40, 40)
        self.now_playing_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.now_playing_title = QLabel("未播放任何媒體")
        self.now_playing_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        # 播放控制
        self.play_pause_button = QPushButton("播放")
        self.play_pause_button.setFixedSize(40, 40)
        self.play_pause_button.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                border-radius: 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6366f1;
            }
        """)
        self.play_pause_button.clicked.connect(self.toggle_playback)
        
        self.prev_button = QPushButton("⏮")
        self.prev_button.setFixedSize(36, 36)
        self.prev_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #6366f1;
            }
        """)
        
        self.next_button = QPushButton("⏭")
        self.next_button.setFixedSize(36, 36)
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #6366f1;
            }
        """)
        
        # 進度條
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(5)
        
        progress_bar_layout = QHBoxLayout()
        
        self.time_elapsed = QLabel("00:00")
        self.time_elapsed.setStyleSheet("color: #999; font-size: 12px;")
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #333333;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #6366f1;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
        """)
        # 連接進度條的拖動事件
        self.progress_slider.sliderMoved.connect(self.seek_position)
        self.progress_slider.sliderPressed.connect(self.slider_pressed)
        self.progress_slider.sliderReleased.connect(self.slider_released)
        
        self.time_total = QLabel("00:00")
        self.time_total.setStyleSheet("color: #999; font-size: 12px;")
        
        progress_bar_layout.addWidget(self.time_elapsed)
        progress_bar_layout.addWidget(self.progress_slider, 1)
        progress_bar_layout.addWidget(self.time_total)
        
        progress_layout.addLayout(progress_bar_layout)
        
        # 添加元件到播放控制佈局
        player_layout.addWidget(self.now_playing_icon)
        player_layout.addWidget(self.now_playing_title, 1)
        player_layout.addWidget(self.prev_button)
        player_layout.addWidget(self.play_pause_button)
        player_layout.addWidget(self.next_button)
        player_layout.addWidget(progress_widget, 2)
        
        # 添加元件到主佈局
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.media_scroll, 1)
        main_layout.addWidget(self.player_bar)
        
        # 選中的媒體項目
        self.selected_media_path = None
        self.selected_item = None
        
        # 刪除模式標誌
        self.is_delete_mode = False
        self.selected_for_deletion = set()
    
    def refresh_media_library(self):
        """重新讀取並顯示媒體庫中的所有媒體文件"""
        # 清除當前顯示的媒體項目
        self._clear_media_items()
        
        # 從資料庫獲取所有媒體檔案
        media_files = db_manager.get_all_media_files()
        
        # 使用字典按檔案的名稱去重（而不僅僅是路徑）
        # 這樣即使相同檔案存在於不同路徑，也只會顯示一次
        unique_files_by_name = {}
        
        for media_file in media_files:
            # 檢查文件是否存在
            if os.path.exists(media_file.file_path):
                # 獲取檔案名作為主要鍵
                file_name = os.path.basename(media_file.file_path)
                
                # 如果這個檔案名還沒有記錄，或者當前記錄的ID更小，則更新
                if file_name not in unique_files_by_name or media_file.id < unique_files_by_name[file_name].id:
                    unique_files_by_name[file_name] = media_file
        
        # 提取唯一檔案的路徑
        unique_file_paths = [media_file.file_path for media_file in unique_files_by_name.values()]
        
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
        """顯示媒體項目
        
        Args:
            file_paths: 媒體文件路徑列表
        """
        # 清除現有項目
        self._clear_media_items()
        
        # 添加媒體項目
        for file_path in file_paths:
            media_item = MediaItem(file_path)
            media_item.clicked.connect(self.on_media_selected)
            media_item.play_requested.connect(self.play_media)
            # 連接刪除信號
            if hasattr(media_item.__class__, 'delete_requested'):
                media_item.delete_requested.connect(self.delete_single_media)
            self.media_layout.addWidget(media_item)
        
        # 如果沒有媒體文件，顯示提示
        if not file_paths:
            empty_label = QLabel("沒有找到媒體文件")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #999; font-size: 16px; padding: 20px;")
            self.media_layout.addWidget(empty_label)
    
    def _clear_media_items(self):
        """清除所有媒體項目"""
        # 完全重建媒體容器，確保所有舊項目都被刪除
        # 首先刪除舊的容器
        old_container = self.media_scroll.takeWidget()
        if old_container:
            old_container.deleteLater()
        
        # 創建新的容器
        new_container = QWidget()
        self.media_layout = QVBoxLayout(new_container)
        self.media_layout.setContentsMargins(10, 10, 10, 10)
        self.media_layout.setSpacing(10)
        self.media_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 設置新容器為滾動區域的窗口部件
        self.media_scroll.setWidget(new_container)
    
    def on_media_selected(self, file_path: str):
        """處理媒體項目選擇事件"""
        if self.is_delete_mode:
            # 在刪除模式下，將文件路徑添加到/從刪除集合中移除
            if file_path in self.selected_for_deletion:
                self.selected_for_deletion.remove(file_path)
            else:
                self.selected_for_deletion.add(file_path)
            
            # 更新確認刪除按鈕狀態
            self.confirm_delete_button.setEnabled(len(self.selected_for_deletion) > 0)
            return
        
        # 非刪除模式下的原有行為
        self.selected_media_path = file_path
        
        # 從資料庫獲取檔案信息
        media_file = db_manager.get_media_file_by_path(file_path)
        
        if media_file:
            # 如果資料庫中有記錄，使用資料庫中的信息
            self.now_playing_title.setText(media_file.title)
            
            # 格式化時間
            if media_file.duration:
                minutes = int(media_file.duration) // 60
                seconds = int(media_file.duration) % 60
                duration_str = f"{minutes}:{seconds:02d}"
            else:
                duration_str = "未知"
            
            self.time_elapsed.setText(duration_str)
            self.time_total.setText(duration_str)
            self.progress_slider.setValue(0)
            self.progress_slider.setRange(0, int(media_file.duration) if media_file.duration else 0)
        else:
            # 如果資料庫中沒有記錄，顯示基本文件信息
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # 轉換為MB
            
            self.now_playing_title.setText(file_name)
            self.time_elapsed.setText("00:00")
            self.time_total.setText("00:00")
            self.progress_slider.setValue(0)
            self.progress_slider.setRange(0, 0)
        
        # 啟用操作按鈕
        self.play_pause_button.setEnabled(True)
    
    def play_media(self, file_path: str):
        """播放指定的媒體文件
        
        Args:
            file_path: 媒體文件路徑
        """
        try:
            # 如果現有播放器正在播放同一個文件，則切換播放/暫停狀態
            if hasattr(self, 'media_player') and self.current_media_path == file_path:
                from PyQt6.QtMultimedia import QMediaPlayer
                if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                    self.media_player.pause()
                else:
                    self.media_player.play()
                return
            
            # 先停止和釋放現有播放器資源
            if hasattr(self, 'media_player'):
                try:
                    # 先暫停並停止播放
                    self.media_player.pause()
                    self.media_player.stop()
                    
                    # 斷開所有信號連接
                    self.media_player.positionChanged.disconnect()
                    self.media_player.durationChanged.disconnect()
                    self.media_player.playbackStateChanged.disconnect()
                except Exception:
                    # 忽略可能的錯誤（例如，信號未連接）
                    pass
            
            # 關閉現有播放器窗口（如果存在）
            if self.current_player:
                try:
                    self.current_player.close()
                except Exception:
                    pass
            
            # 創建新的媒體播放器 - 但不顯示視窗
            from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
            from PyQt6.QtCore import QUrl
            
            # 直接創建媒體播放器和音訊輸出
            self.media_player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.media_player.setAudioOutput(self.audio_output)
            
            # 連接信號
            self.media_player.positionChanged.connect(self.update_progress)
            self.media_player.durationChanged.connect(self.update_duration)
            self.media_player.playbackStateChanged.connect(self.update_play_state)
            
            # 設置媒體源
            self.media_url = QUrl.fromLocalFile(file_path)
            self.media_player.setSource(self.media_url)
            
            # 設置音量
            self.audio_output.setVolume(0.7)
            
            # 保存當前播放器引用
            self.current_player = self.media_player
            
            # 保存當前播放媒體的信息
            self.current_media_path = file_path
            media_file = db_manager.get_media_file_by_path(file_path)
            if media_file:
                self.current_media_title = media_file.title
            else:
                self.current_media_title = os.path.basename(file_path)
            
            # 更新播放進度界面
            self.update_player_bar()
            
            # 選中當前播放的媒體項目
            self.selected_media_path = file_path
            
            # 更新所有媒體項的播放狀態
            self._update_all_media_items_play_state()
            
            # 自動開始播放 - 放在最後，確保一切設置完成後再播放
            self.media_player.play()
        
        except Exception as e:
            import traceback
            print(f"播放媒體發生錯誤: {e}")
            print(traceback.format_exc())
            # 重置播放狀態
            self.reset_player_bar()

    def update_player_bar(self):
        """更新播放進度界面"""
        if self.current_media_path:
            self.now_playing_title.setText(self.current_media_title)
            self.play_pause_button.setText("❚❚")  # 暫停圖標
        else:
            self.now_playing_title.setText("未播放任何媒體")
            self.play_pause_button.setText("▶")  # 播放圖標
            self.time_elapsed.setText("00:00")
            self.time_total.setText("00:00")
            self.progress_slider.setValue(0)
            self.progress_slider.setRange(0, 0)

    def update_progress(self, position):
        """更新播放進度
        
        Args:
            position: 當前播放位置（毫秒）
        """
        if not self.progress_slider.isSliderDown():  # 如果滑塊不是被用戶拖動
            self.progress_slider.setValue(position)
            
        # 更新已播放時間
        seconds = position // 1000
        minutes = seconds // 60
        seconds %= 60
        self.time_elapsed.setText(f"{minutes:02d}:{seconds:02d}")

    def update_duration(self, duration):
        """更新媒體總時長
        
        Args:
            duration: 媒體總時長（毫秒）
        """
        self.progress_slider.setRange(0, duration)
        
        # 更新總時長
        seconds = duration // 1000
        minutes = seconds // 60
        seconds %= 60
        self.time_total.setText(f"{minutes:02d}:{seconds:02d}")

    def update_play_state(self, state):
        """更新播放狀態
        
        Args:
            state: 播放狀態
        """
        from PyQt6.QtMultimedia import QMediaPlayer
        
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_button.setText("❚❚")  # 暫停圖標
        else:
            self.play_pause_button.setText("▶")  # 播放圖標
        
        # 同步更新所有媒體項的播放狀態
        self._update_all_media_items_play_state()

    def toggle_playback(self):
        """切換播放/暫停狀態"""
        if hasattr(self, 'media_player'):
            from PyQt6.QtMultimedia import QMediaPlayer
            
            if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.media_player.pause()
            else:
                self.media_player.play()
        elif self.selected_media_path:
            # 如果沒有正在播放的媒體，但有選中的媒體，播放選中的媒體
            self.play_media(self.selected_media_path)
            
    def reset_player_bar(self):
        """重置播放進度界面"""
        self.current_media_path = None
        self.current_media_title = None
        self.update_player_bar()
        
    def seek_position(self, position):
        """設置播放位置
        
        Args:
            position: 目標播放位置（毫秒）
        """
        if hasattr(self, 'media_player'):
            self.media_player.setPosition(position)
            
    def slider_pressed(self):
        """進度條被按下時暫停播放"""
        if hasattr(self, 'media_player'):
            from PyQt6.QtMultimedia import QMediaPlayer
            self.was_playing = self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
            if self.was_playing:
                self.media_player.pause()
                
    def slider_released(self):
        """進度條釋放時恢復播放"""
        if hasattr(self, 'media_player') and hasattr(self, 'was_playing') and self.was_playing:
            self.media_player.play()
     
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
        
        # 按檔案名稱去重
        unique_files_by_name = {}
        
        for media_file in filtered_files:
            if os.path.exists(media_file.file_path):
                # 獲取檔案名作為主要鍵
                file_name = os.path.basename(media_file.file_path)
                
                # 如果這個檔案名還沒有記錄，或者當前記錄的ID更小，則更新
                if file_name not in unique_files_by_name or media_file.id < unique_files_by_name[file_name].id:
                    unique_files_by_name[file_name] = media_file
        
        # 提取唯一檔案的路徑
        unique_file_paths = [media_file.file_path for media_file in unique_files_by_name.values()]
        
        # 更新顯示
        self._display_media_items(unique_file_paths)

    def _update_all_media_items_play_state(self):
        """更新所有媒體項的播放狀態"""
        # 遍歷佈局中的所有媒體項
        for i in range(self.media_layout.count()):
            widget = self.media_layout.itemAt(i).widget()
            if isinstance(widget, MediaItem):
                # 更新媒體項的播放狀態
                is_playing = (hasattr(self, 'media_player') and 
                             widget.file_path == self.current_media_path and
                             self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)
                widget.update_play_state(is_playing)

    def toggle_delete_mode(self):
        """切換刪除模式"""
        self.is_delete_mode = not self.is_delete_mode
        
        # 顯示/隱藏相關按鈕
        self.delete_button.setVisible(not self.is_delete_mode)
        self.confirm_delete_button.setVisible(self.is_delete_mode)
        self.cancel_delete_button.setVisible(self.is_delete_mode)
        
        # 禁用/啟用其他按鈕
        self.search_button.setEnabled(not self.is_delete_mode)
        self.import_button.setEnabled(not self.is_delete_mode)
        self.refresh_button.setEnabled(not self.is_delete_mode)
        self.filter_combo.setEnabled(not self.is_delete_mode)
        self.search_input.setEnabled(not self.is_delete_mode)
        
        # 重置刪除選擇
        self.selected_for_deletion.clear()
        
        # 更新所有媒體項的顯示狀態
        for i in range(self.media_layout.count()):
            widget = self.media_layout.itemAt(i).widget()
            if isinstance(widget, MediaItem):
                widget.set_delete_mode(self.is_delete_mode)

    def cancel_delete_mode(self):
        """取消刪除模式"""
        if self.is_delete_mode:
            self.toggle_delete_mode()

    def delete_selected_media(self):
        """刪除選中的媒體文件"""
        if not self.selected_for_deletion:
            return
        
        # 顯示確認對話框
        count = len(self.selected_for_deletion)
        reply = QMessageBox.question(
            self, "確認刪除",
            f"確定要刪除選中的 {count} 個媒體文件嗎？此操作不可撤銷。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 遍歷執行刪除
        deleted_count = 0
        for file_path in list(self.selected_for_deletion):  # 使用list創建副本，因為我們會在循環中修改集合
            try:
                # 停止播放（如果正在播放的文件被刪除）
                if hasattr(self, 'current_media_path') and self.current_media_path == file_path:
                    if hasattr(self, 'media_player'):
                        self.media_player.stop()
                    self.reset_player_bar()
                
                # 從資料庫中移除
                db_manager.delete_media_file_by_path(file_path)
                
                # 從檔案系統刪除
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                deleted_count += 1
                self.selected_for_deletion.remove(file_path)
            except Exception as e:
                QMessageBox.warning(self, "刪除失敗", f"檔案 {os.path.basename(file_path)} 刪除失敗: {str(e)}")
        
        # 顯示成功訊息
        if deleted_count > 0:
            QMessageBox.information(self, "刪除成功", f"成功刪除 {deleted_count} 個媒體文件。")
        
        # 刷新媒體庫
        self.refresh_media_library()
        
        # 退出刪除模式
        self.toggle_delete_mode()

    def delete_single_media(self, file_path: str):
        """刪除單個媒體文件
        
        Args:
            file_path: 要刪除的文件路徑
        """
        # 顯示確認對話框
        file_name = os.path.basename(file_path)
        reply = QMessageBox.question(
            self, "確認刪除",
            f"確定要刪除 {file_name} 嗎？此操作不可撤銷。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # 停止播放（如果正在播放的文件被刪除）
            if hasattr(self, 'current_media_path') and self.current_media_path == file_path:
                if hasattr(self, 'media_player'):
                    self.media_player.stop()
                self.reset_player_bar()
            
            # 從資料庫中移除
            db_manager.delete_media_file_by_path(file_path)
            
            # 從檔案系統刪除
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # 顯示成功訊息
            QMessageBox.information(self, "刪除成功", f"成功刪除 {file_name}。")
            
            # 刷新媒體庫
            self.refresh_media_library()
        
        except Exception as e:
            QMessageBox.warning(self, "刪除失敗", f"檔案 {file_name} 刪除失敗: {str(e)}")
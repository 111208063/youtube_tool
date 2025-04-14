"""
主視窗模組

提供YouTube下載工具的主視窗界面，整合下載和媒體庫功能。
"""
import os
import sys
from pathlib import Path
from typing import Optional
import threading

from PyQt6.QtCore import Qt, QSize, pyqtSignal, pyqtSlot, QObject, QMetaObject, Q_ARG, QTimer
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QComboBox, QStackedWidget, 
    QStatusBar, QSplitter, QFileDialog, QMessageBox, QProgressBar, QFrame
)

from src.youtube_fetcher import YouTubeFetcher, MediaType, VideoQuality, AudioQuality
from src.gui.media_library import MediaLibrary

# 導入try2.py中的功能
try:
    import try2
except ImportError:
    try2 = None
    print("警告：無法導入try2模組")


class VideoAnalyzer(QObject):
    """影片分析器，使用try2.py的功能在背景執行緒分析YouTube影片"""
    analysis_finished = pyqtSignal(dict)  # 分析完成後發出信號
    analysis_error = pyqtSignal(str)      # 分析出錯時發出信號
    
    def analyze_video(self, url: str):
        """分析影片信息"""
        try:
            # 使用yt-dlp提取影片信息但不下載
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,  # 不下載，只提取信息
                'noplaylist': True,     # 不處理播放列表
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # 準備影片信息
                video_info = {
                    'title': info.get('title', '未知標題'),
                    'uploader': info.get('uploader', '未知頻道'),
                    'duration': info.get('duration', 0),
                    'webpage_url': info.get('webpage_url', url),
                    'thumbnail': info.get('thumbnail', '')
                }
                
                self.analysis_finished.emit(video_info)
        except Exception as e:
            self.analysis_error.emit(str(e))


class DownloadWidget(QWidget):
    """下載頁面元件"""
    
    def __init__(self, youtube_fetcher: YouTubeFetcher, parent=None):
        """
        初始化下載頁面
        
        Args:
            youtube_fetcher: YouTube資料獲取器實例
            parent: 父元件
        """
        super().__init__(parent)
        self.youtube_fetcher = youtube_fetcher
        self.analyzer = VideoAnalyzer()
        self.analyzer.analysis_finished.connect(self.on_analysis_finished)
        self.analyzer.analysis_error.connect(self.on_analysis_error)
        
        # 初始化下載管理器
        from src.gui.download_manager import DownloadManager, DownloadStatus
        self.DownloadStatus = DownloadStatus  # 存儲為實例變數方便使用
        download_path = Path.home() / "Downloads" / "YouTube"
        self.download_manager = DownloadManager(download_path)
        self.download_manager.register_status_callback(self.on_download_status_update)
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化用戶界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 頂部標題
        title_label = QLabel("下載 YouTube 影片")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        
        # URL輸入區域
        url_layout = QHBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("輸入 YouTube 影片或播放清單網址")
        self.url_input.setMinimumHeight(36)
        self.url_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                padding: 0 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #6366f1;
            }
        """)
        
        self.analyze_button = QPushButton("分析")
        self.analyze_button.setMinimumHeight(36)
        self.analyze_button.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                border-radius: 4px;
                padding: 0 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4f46e5;
            }
        """)
        self.analyze_button.clicked.connect(self.on_analyze_clicked)
        
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.analyze_button)
        
        # 視頻預覽區域
        self.preview_widget = QWidget()
        self.preview_widget.setVisible(False)
        preview_layout = QHBoxLayout(self.preview_widget)
        
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(QSize(240, 135))
        self.thumbnail_label.setStyleSheet("background-color: #f0f0f0; border-radius: 8px;")
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.title_label.setWordWrap(True)
        
        self.channel_label = QLabel()
        self.channel_label.setStyleSheet("color: #666; font-size: 12px;")
        
        # 下載選項
        options_layout = QHBoxLayout()
        
        type_layout = QVBoxLayout()
        type_label = QLabel("下載類型")
        type_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        
        type_buttons_layout = QHBoxLayout()
        self.audio_button = QPushButton("音訊 (MP3)")
        self.audio_button.setCheckable(True)
        self.audio_button.setChecked(True)
        self.audio_button.clicked.connect(lambda: self.on_type_changed(True))
        
        self.video_button = QPushButton("視訊")
        self.video_button.setCheckable(True)
        self.video_button.clicked.connect(lambda: self.on_type_changed(False))
        
        # 樣式化按鈕
        for btn in [self.audio_button, self.video_button]:
            btn.setStyleSheet("""
                QPushButton {
                    padding: 5px 15px;
                    border: 1px solid #d1d5db;
                    border-radius: 4px;
                    background-color: white;
                }
                QPushButton:checked {
                    background-color: #6366f1;
                    color: white;
                    border-color: #6366f1;
                }
            """)
        
        type_buttons_layout.addWidget(self.audio_button)
        type_buttons_layout.addWidget(self.video_button)
        
        type_layout.addWidget(type_label)
        type_layout.addLayout(type_buttons_layout)
        
        # 品質選擇
        quality_layout = QVBoxLayout()
        quality_label = QLabel("品質")
        quality_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        
        self.quality_combo = QComboBox()
        self.quality_combo.setMinimumWidth(150)
        self.quality_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: white;
            }
        """)
        
        # 初始化音訊品質選項
        self.update_quality_options(True)
        
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_combo)
        
        options_layout.addLayout(type_layout)
        options_layout.addSpacing(20)
        options_layout.addLayout(quality_layout)
        options_layout.addStretch()
        
        # 下載按鈕
        self.download_button = QPushButton("開始下載")
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4f46e5;
            }
        """)
        self.download_button.clicked.connect(self.on_download_clicked)
        
        # 下載選項和按鈕佈局
        download_options_layout = QVBoxLayout()
        download_options_layout.addLayout(options_layout)
        download_options_layout.addStretch()
        download_options_layout.addWidget(self.download_button, 0, Qt.AlignmentFlag.AlignRight)
        
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.channel_label)
        info_layout.addSpacing(10)
        info_layout.addLayout(download_options_layout)
        
        preview_layout.addWidget(self.thumbnail_label)
        preview_layout.addWidget(info_widget)
        
        # 進行中的下載
        downloads_title = QLabel("進行中的下載")
        downloads_title.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 20px;")
        
        self.downloads_container = QWidget()
        self.downloads_layout = QVBoxLayout(self.downloads_container)
        self.downloads_layout.setContentsMargins(0, 0, 0, 0)
        
        # 將所有元件加入主佈局
        main_layout.addWidget(title_label)
        main_layout.addLayout(url_layout)
        main_layout.addWidget(self.preview_widget)
        main_layout.addWidget(downloads_title)
        main_layout.addWidget(self.downloads_container)
        main_layout.addStretch()
    
    def on_type_changed(self, is_audio: bool):
        """處理下載類型變更"""
        if is_audio:
            self.audio_button.setChecked(True)
            self.video_button.setChecked(False)
        else:
            self.audio_button.setChecked(False)
            self.video_button.setChecked(True)
        
        self.update_quality_options(is_audio)
    
    def update_quality_options(self, is_audio: bool):
        """更新品質選項"""
        self.quality_combo.clear()
        
        if is_audio:
            self.quality_combo.addItem("高品質 (320kbps)", AudioQuality.HIGH)
            self.quality_combo.addItem("中等品質 (192kbps)", AudioQuality.MEDIUM)
            self.quality_combo.addItem("一般品質 (128kbps)", AudioQuality.LOW)
        else:
            self.quality_combo.addItem("高品質 (1080p)", VideoQuality.HIGH)
            self.quality_combo.addItem("中等品質 (720p)", VideoQuality.MEDIUM)
            self.quality_combo.addItem("一般品質 (360p)", VideoQuality.LOW)
    
    def on_analyze_clicked(self):
        """處理分析按鈕點擊事件"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "URL錯誤", "請輸入有效的YouTube影片或播放清單URL")
            return
        
        # 禁用分析按鈕，顯示加載狀態
        self.analyze_button.setEnabled(False)
        self.analyze_button.setText("分析中...")
        
        # 在背景執行緒中分析影片
        threading.Thread(
            target=self.analyzer.analyze_video,
            args=(url,),
            daemon=True
        ).start()
    
    @pyqtSlot(dict)
    def on_analysis_finished(self, video_info):
        """當影片分析完成時被呼叫"""
        # 更新UI
        self.title_label.setText(video_info['title'])
        
        # 計算時長
        duration = video_info['duration']
        minutes = duration // 60
        seconds = duration % 60
        
        # 設置頻道和時長信息
        self.channel_label.setText(f"頻道：{video_info['uploader']} • {minutes}:{seconds:02d}")
        
        # 顯示預覽區域
        self.preview_widget.setVisible(True)
        
        # 重置分析按鈕
        self.analyze_button.setEnabled(True)
        self.analyze_button.setText("分析")
    
    @pyqtSlot(str)
    def on_analysis_error(self, error_msg):
        """當影片分析出錯時被呼叫"""
        # 顯示錯誤消息
        QMessageBox.critical(self, "分析失敗", f"無法解析影片資訊：{error_msg}")
        
        # 重置分析按鈕
        self.analyze_button.setEnabled(True)
        self.analyze_button.setText("分析")
    
    def on_download_clicked(self):
        """處理下載按鈕點擊事件"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "URL錯誤", "請輸入有效的YouTube影片或播放清單URL")
            return
        
        # 檢測是否是播放清單URL
        is_playlist = 'list=' in url and 'watch?' in url
        download_playlist = False
        
        # 如果是播放清單，詢問用戶是否下載整個播放清單
        if is_playlist:
            reply = QMessageBox.question(
                self, 
                "播放清單檢測", 
                "檢測到可能是播放清單URL，是否下載整個播放清單？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            download_playlist = reply == QMessageBox.StandardButton.Yes
            
            # 如果不下載播放清單，修改URL只保留視頻ID
            if not download_playlist:
                video_id = url.split('v=')[1].split('&')[0]
                url = f"https://www.youtube.com/watch?v={video_id}"
        
        # 獲取下載選項
        is_audio = self.audio_button.isChecked()
        media_type = MediaType.AUDIO if is_audio else MediaType.VIDEO
        quality = self.quality_combo.currentData()
        
        # 使用try2.py的功能下載音訊
        if is_audio and try2 is not None and not download_playlist:
            # 對於單一音訊下載，繼續使用try2.py
            threading.Thread(
                target=try2.download_audio,
                args=(url,),
                daemon=True
            ).start()
            QMessageBox.information(self, "開始下載", "下載已開始，檔案將存放到downloads/audio目錄並記錄在資料庫中")
        else:
            # 使用DownloadManager進行下載
            try:
                task_id = self.download_manager.add_download(url, media_type, quality)
                QMessageBox.information(self, "開始下載", "下載已添加到佇列，可在下方查看進度。檔案將記錄在資料庫中")
            except Exception as e:
                QMessageBox.critical(self, "下載失敗", f"無法添加下載任務：{str(e)}")
    
    @pyqtSlot(str, object)
    def on_download_status_update(self, task_id, task):
        """處理下載狀態更新"""
        # 檢查是否已經存在此任務的UI項目
        download_item = self.findChild(QWidget, f"download_item_{task_id}")
        
        if download_item is None and task.status != self.DownloadStatus.COMPLETED:
            # 創建新的下載項目UI
            download_item = self._create_download_item(task_id, task)
            self.downloads_layout.addWidget(download_item)
        elif download_item is not None:
            # 更新現有的下載項目UI
            self._update_download_item(download_item, task)
            
            # 如果任務已完成或失敗，在一段時間後移除項目
            if task.status in [self.DownloadStatus.COMPLETED, self.DownloadStatus.FAILED, self.DownloadStatus.CANCELLED]:
                # 使用計時器，延遲移除項目
                QTimer.singleShot(5000, lambda: self._remove_download_item(download_item))
    
    def _create_download_item(self, task_id, task):
        """創建下載項目UI"""
        # 創建下載項目容器
        item = QWidget()
        item.setObjectName(f"download_item_{task_id}")
        item.setMinimumHeight(80)
        item.setMaximumHeight(80)
        item.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                border-radius: 8px;
                margin: 5px 0;
            }
        """)
        
        # 項目佈局
        layout = QHBoxLayout(item)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 標題和狀態
        info_layout = QVBoxLayout()
        
        title_label = QLabel(task.title)
        title_label.setObjectName(f"title_{task_id}")
        title_label.setStyleSheet("font-weight: bold;")
        title_label.setWordWrap(True)
        
        status_label = QLabel(self._get_status_text(task.status))
        status_label.setObjectName(f"status_{task_id}")
        status_label.setStyleSheet("color: #666;")
        
        info_layout.addWidget(title_label)
        info_layout.addWidget(status_label)
        
        # 進度條
        progress_bar = QProgressBar()
        progress_bar.setObjectName(f"progress_{task_id}")
        progress_bar.setRange(0, 100)
        progress_bar.setValue(int(task.progress))
        progress_bar.setTextVisible(True)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #6366f1;
                border-radius: 3px;
            }
        """)
        
        # 控制按鈕（暫停/繼續、取消）
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(5)
        
        # 暫停/繼續按鈕
        pause_button = QPushButton("暫停")
        pause_button.setObjectName(f"pause_{task_id}")
        pause_button.setFixedSize(80, 30)
        pause_button.clicked.connect(lambda: self._toggle_pause(task_id))
        
        # 取消按鈕
        cancel_button = QPushButton("取消")
        cancel_button.setFixedSize(80, 30)
        cancel_button.clicked.connect(lambda: self._cancel_download(task_id))
        
        buttons_layout.addWidget(pause_button)
        buttons_layout.addWidget(cancel_button)
        
        # 設置佈局
        layout.addLayout(info_layout, 3)
        layout.addWidget(progress_bar, 2)
        layout.addLayout(buttons_layout, 1)
        
        return item
    
    def _update_download_item(self, item, task):
        """更新下載項目UI"""
        # 更新標題（如果需要）
        title_label = item.findChild(QLabel, f"title_{task.id}")
        if title_label:
            title_label.setText(task.title)
        
        # 更新狀態
        status_label = item.findChild(QLabel, f"status_{task.id}")
        if status_label:
            status_label.setText(self._get_status_text(task.status))
        
        # 更新進度條
        progress_bar = item.findChild(QProgressBar, f"progress_{task.id}")
        if progress_bar:
            progress_bar.setValue(int(task.progress))
        
        # 更新暫停/繼續按鈕
        pause_button = item.findChild(QPushButton, f"pause_{task.id}")
        if pause_button:
            if task.status == self.DownloadStatus.PAUSED:
                pause_button.setText("繼續")
            else:
                pause_button.setText("暫停")
            
            # 禁用或啟用按鈕
            pause_button.setEnabled(task.status in [self.DownloadStatus.DOWNLOADING, self.DownloadStatus.PAUSED])
    
    def _remove_download_item(self, item):
        """移除下載項目UI"""
        if item:
            self.downloads_layout.removeWidget(item)
            item.deleteLater()
    
    def _toggle_pause(self, task_id):
        """切換下載任務的暫停/繼續狀態"""
        task = self.download_manager.get_task(task_id)
        if not task:
            return
        
        if task.status == self.DownloadStatus.PAUSED:
            self.download_manager.resume_download(task_id)
        else:
            self.download_manager.pause_download(task_id)
    
    def _cancel_download(self, task_id):
        """取消下載任務"""
        self.download_manager.cancel_download(task_id)
    
    def _get_status_text(self, status):
        """獲取下載狀態的顯示文本"""
        status_texts = {
            self.DownloadStatus.PENDING: "等待中...",
            self.DownloadStatus.DOWNLOADING: "下載中...",
            self.DownloadStatus.PAUSED: "已暫停",
            self.DownloadStatus.COMPLETED: "下載完成",
            self.DownloadStatus.FAILED: "下載失敗",
            self.DownloadStatus.CANCELLED: "已取消"
        }
        return status_texts.get(status, "未知狀態")


class MainWindow(QMainWindow):
    """主視窗"""
    
    def __init__(self):
        super().__init__()
        
        # 設置下載目錄
        self.download_dir = Path.home() / "Downloads" / "YouTube"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # 創建YouTube下載器
        self.youtube_fetcher = YouTubeFetcher(self.download_dir)
        
        # 設置視窗屬性
        self.setWindowTitle("YouTube 下載工具")
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化主視窗界面"""
        # 設置視窗標題和大小
        self.setWindowTitle("YouTube 下載工具")
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)
        
        # 創建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主佈局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左側側邊欄
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("""
            #sidebar {
                background-color: #1a1a1a;
                border-right: 1px solid #333333;
            }
        """)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(10)
        
        # 標題標籤
        title_label = QLabel("YouTube 下載工具")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
            padding: 10px;
        """)
        
        # 分隔線
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #333333;")
        
        # 側邊欄按鈕
        self.home_button = self._create_sidebar_button("下載頁面", "download", 0)
        self.library_button = self._create_sidebar_button("媒體庫", "library", 1)
        
        # 活動按鈕
        self.active_sidebar_button = self.home_button
        self.home_button.setStyleSheet(self.home_button.styleSheet() + """
            QPushButton {
                background-color: #2d2d2d;
                border-left: 4px solid #6366f1;
            }
        """)
        
        # 添加元件到側邊欄
        sidebar_layout.addWidget(title_label)
        sidebar_layout.addWidget(separator)
        sidebar_layout.addWidget(self.home_button)
        sidebar_layout.addWidget(self.library_button)
        sidebar_layout.addStretch()
        
        # 右側內容區域
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 創建堆疊部件
        self.stacked_widget = QStackedWidget()
        
        # 添加下載頁面
        self.download_widget = DownloadWidget(self.youtube_fetcher)
        self.stacked_widget.addWidget(self.download_widget)
        
        # 添加媒體庫頁面
        download_dir = str(Path.home() / "Downloads" / "YouTube")
        self.media_library = MediaLibrary(download_dir)
        self.stacked_widget.addWidget(self.media_library)
        
        # 添加堆疊部件到內容區域
        content_layout.addWidget(self.stacked_widget)
        
        # 創建狀態欄
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #1a1c23;
                color: white;
            }
        """)
        self.setStatusBar(self.status_bar)
        
        # 添加所有部件到主佈局
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_area, 1)
        
        # 初始顯示下載頁面
        self.stacked_widget.setCurrentIndex(0)
    
    def _create_sidebar_button(self, text: str, icon_name: str, page_index: int) -> QPushButton:
        """創建側邊欄按鈕"""
        button = QPushButton(text)
        button.setCheckable(True)
        button.setFixedHeight(48)
        button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 0;
                text-align: left;
                padding: 10px 20px;
                color: #9ca3af;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2d3748;
            }
            QPushButton:checked {
                background-color: #4f46e5;
                color: white;
                font-weight: bold;
            }
        """)
        
        # 設置圖標（實際使用需載入正確的圖標）
        # button.setIcon(QIcon(f"icons/{icon_name}.png"))
        # button.setIconSize(QSize(20, 20))
        
        # 設置為第一個按鈕初始為選中狀態
        if page_index == 0:
            button.setChecked(True)
        
        # 連接點擊事件
        button.clicked.connect(lambda: self._on_sidebar_button_clicked(button, page_index))
        
        return button
    
    def _on_sidebar_button_clicked(self, button: QPushButton, page_index: int):
        """處理側邊欄按鈕點擊事件
        
        Args:
            button: 被點擊的按鈕
            page_index: 對應的頁面索引
        """
        # 如果點擊的不是當前活動按鈕
        if button != self.active_sidebar_button:
            # 設置新的活動按鈕
            self.active_sidebar_button.setStyleSheet(self.active_sidebar_button.styleSheet().replace("""
                QPushButton {
                    background-color: #2d2d2d;
                    border-left: 4px solid #6366f1;
                }
            """, ""))
            
            button.setStyleSheet(button.styleSheet() + """
                QPushButton {
                    background-color: #2d2d2d;
                    border-left: 4px solid #6366f1;
                }
            """)
            
            self.active_sidebar_button = button
            
            # 更換頁面
            self.stacked_widget.setCurrentIndex(page_index)
            
            # 如果切換到媒體庫頁面，刷新媒體庫
            if page_index == 1:
                self.media_library.refresh_media_library()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 設置應用樣式表
    app.setStyleSheet("""
        QWidget {
            font-family: "微軟正黑體", "Microsoft JhengHei", Arial, sans-serif;
        }
    """)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec()) 
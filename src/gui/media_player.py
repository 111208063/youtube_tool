"""
媒體播放器模組

提供媒體播放界面，支持音頻和視頻播放，包含完整的播放控制。
"""
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSlider, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from src.database import db_manager, MediaType


class MediaPlayerWindow(QMainWindow):
    """媒體播放器視窗，用於播放音頻和視頻"""
    
    # 添加信號
    playback_started = pyqtSignal(str)  # 播放開始時發出信號
    playback_stopped = pyqtSignal()     # 播放停止時發出信號
    
    def __init__(self, file_path: str, parent=None):
        """初始化媒體播放器視窗
        
        Args:
            file_path: 要播放的媒體文件路徑
            parent: 父元件
        """
        super().__init__(parent)
        self.file_path = file_path
        self.is_audio = file_path.lower().endswith(('.mp3', '.wav', '.aac', '.ogg', '.flac'))
        self.parent = parent
        
        # 從資料庫獲取媒體詳情
        self.media_info = db_manager.get_media_file_by_path(file_path)
        
        # 設置視窗標題和大小
        if self.media_info:
            self.setWindowTitle(f"播放: {self.media_info.title}")
        else:
            self.setWindowTitle(f"播放: {os.path.basename(file_path)}")
        
        # 設置視窗大小 (視頻較大，音頻較小)
        if self.is_audio:
            self.setMinimumSize(500, 200)
            self.resize(500, 200)
        else:
            self.setMinimumSize(800, 600)
            self.resize(800, 600)
        
        # 創建媒體播放器
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # 連接信號槽
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.playbackStateChanged.connect(self.update_player_state)
        self.media_player.errorOccurred.connect(self.handle_error)
        
        # 初始化界面
        self._setup_ui()
        
        # 設置媒體源並播放
        self.media_url = QUrl.fromLocalFile(self.file_path)
        self.media_player.setSource(self.media_url)
        
        # 設置初始音量
        self.audio_output.setVolume(0.7)
        self.volume_slider.setValue(70)
        
        # 定時器用於更新播放進度
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(500)  # 每500毫秒更新一次
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start()
    
    def _setup_ui(self):
        """設置用戶界面"""
        # 創建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主佈局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 視頻區域 (只在播放視頻時顯示)
        if not self.is_audio:
            self.video_widget = QVideoWidget()
            self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.video_widget.setStyleSheet("background-color: black;")
            self.media_player.setVideoOutput(self.video_widget)
            main_layout.addWidget(self.video_widget, 1)
        else:
            # 音頻播放時顯示專輯封面或音樂圖標
            self.album_art = QLabel()
            self.album_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.album_art.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.album_art.setStyleSheet("""
                background-color: #2d2d2d;
                border-radius: 8px;
                font-size: 72px;
            """)
            self.album_art.setText("🎵")
            main_layout.addWidget(self.album_art, 1)
        
        # 媒體信息區域
        info_layout = QHBoxLayout()
        
        # 標題和藝術家
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        if self.media_info:
            self.title_label.setText(self.media_info.title)
            
            # 如果有上傳者信息，顯示上傳者
            if self.media_info.uploader:
                self.title_label.setText(f"{self.media_info.title} - {self.media_info.uploader}")
        else:
            self.title_label.setText(os.path.basename(self.file_path))
        
        info_layout.addWidget(self.title_label)
        info_layout.addStretch()
        
        # 音量控制
        volume_label = QLabel("音量:")
        volume_label.setStyleSheet("color: white;")
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)  # 默認音量70%
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self.change_volume)
        
        info_layout.addWidget(volume_label)
        info_layout.addWidget(self.volume_slider)
        
        main_layout.addLayout(info_layout)
        
        # 進度條
        progress_layout = QHBoxLayout()
        
        self.position_label = QLabel("00:00")
        self.position_label.setStyleSheet("color: white;")
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.sliderMoved.connect(self.set_position)
        self.progress_slider.sliderPressed.connect(self.pause_while_sliding)
        self.progress_slider.sliderReleased.connect(self.resume_after_sliding)
        
        self.duration_label = QLabel("00:00")
        self.duration_label.setStyleSheet("color: white;")
        
        progress_layout.addWidget(self.position_label)
        progress_layout.addWidget(self.progress_slider)
        progress_layout.addWidget(self.duration_label)
        
        main_layout.addLayout(progress_layout)
        
        # 控制按鈕
        controls_layout = QHBoxLayout()
        
        # 播放/暫停按鈕
        self.play_button = QPushButton("播放")
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #6366f1;
            }
        """)
        self.play_button.clicked.connect(self.toggle_playback)
        
        # 停止按鈕
        self.stop_button = QPushButton("停止")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #ef4444;
            }
        """)
        self.stop_button.clicked.connect(self.stop_playback)
        
        # 靜音按鈕
        self.mute_button = QPushButton("靜音")
        self.mute_button.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border: 1px solid #444444;
                padding: 8px 15px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
        """)
        self.mute_button.setCheckable(True)
        self.mute_button.clicked.connect(self.toggle_mute)
        
        controls_layout.addStretch()
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.mute_button)
        controls_layout.addStretch()
        
        main_layout.addLayout(controls_layout)
        
        # 狀態列
        self.statusBar().showMessage("準備就緒")
        
        # 設置視窗樣式
        self.setStyleSheet("""
            QMainWindow, QDialog, QWidget {
                background-color: #121212;
            }
            QLabel {
                color: white;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: #333333;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4f46e5;
                border: 1px solid #4f46e5;
                width: 18px;
                margin: -2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal:hover {
                background: #6366f1;
                border: 1px solid #6366f1;
            }
            QStatusBar {
                background-color: #1a1c23;
                color: white;
            }
        """)
    
    def toggle_playback(self):
        """切換播放/暫停狀態"""
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
            # 發出播放開始信號
            self.playback_started.emit(self.file_path)
    
    def stop_playback(self):
        """停止播放"""
        self.media_player.stop()
        # 發出播放停止信號
        self.playback_stopped.emit()
    
    def update_player_state(self, state):
        """根據播放器狀態更新界面"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setText("暫停")
            self.statusBar().showMessage("正在播放")
        else:
            self.play_button.setText("播放")
            if state == QMediaPlayer.PlaybackState.PausedState:
                self.statusBar().showMessage("已暫停")
            else:
                self.statusBar().showMessage("已停止")
    
    def update_position(self, position):
        """更新播放位置"""
        self.progress_slider.setValue(position)
        
        # 更新時間標籤
        seconds = position // 1000
        minutes = seconds // 60
        seconds %= 60
        self.position_label.setText(f"{minutes:02d}:{seconds:02d}")
    
    def update_duration(self, duration):
        """更新媒體總時長"""
        self.progress_slider.setRange(0, duration)
        
        # 更新時間標籤
        seconds = duration // 1000
        minutes = seconds // 60
        seconds %= 60
        self.duration_label.setText(f"{minutes:02d}:{seconds:02d}")
    
    def set_position(self, position):
        """設置播放位置"""
        self.media_player.setPosition(position)
    
    def update_ui(self):
        """定時更新界面"""
        # 可以在這裡添加額外的界面更新邏輯
        pass
    
    def change_volume(self, value):
        """調整音量"""
        volume = value / 100.0
        self.audio_output.setVolume(volume)
        
        # 更新靜音按鈕狀態
        if value == 0:
            self.mute_button.setChecked(True)
        elif self.mute_button.isChecked():
            self.mute_button.setChecked(False)
    
    def toggle_mute(self, checked):
        """切換靜音狀態"""
        if checked:
            self.prev_volume = self.volume_slider.value()
            self.volume_slider.setValue(0)
            self.audio_output.setVolume(0)
            self.mute_button.setText("取消靜音")
        else:
            self.volume_slider.setValue(self.prev_volume if hasattr(self, 'prev_volume') else 70)
            self.audio_output.setVolume(self.prev_volume / 100.0 if hasattr(self, 'prev_volume') else 0.7)
            self.mute_button.setText("靜音")
    
    def pause_while_sliding(self):
        """拖動進度條時暫停播放"""
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.was_playing = True
            self.media_player.pause()
        else:
            self.was_playing = False
    
    def resume_after_sliding(self):
        """拖動進度條後恢復播放"""
        if hasattr(self, 'was_playing') and self.was_playing:
            self.media_player.play()
    
    def handle_error(self, error, error_string):
        """處理播放錯誤"""
        self.statusBar().showMessage(f"播放錯誤: {error_string}")
        print(f"播放錯誤: {error} - {error_string}")
    
    def closeEvent(self, event):
        """窗口關閉事件"""
        self.update_timer.stop()
        self.media_player.stop()
        # 發出播放停止信號
        self.playback_stopped.emit()
        event.accept() 
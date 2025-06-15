import sys
import os
import json
import threading

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QFileDialog, QListWidget,
    QVBoxLayout, QWidget, QHBoxLayout, QMessageBox, QStyle, QSlider, QLabel
)
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from pydub import AudioSegment
import whisper

class SubtitlePlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("语音字幕播放器")
        self.setMinimumSize(600, 400)

        self.audio_file = None
        self.subtitles = []
        self.model = whisper.load_model("large")

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        # 界面控件
        self.open_btn = QPushButton("打开音频文件")
        self.play_btn = QPushButton("播放")
        self.play_btn.setEnabled(False)

        self.save_btn = QPushButton("保存字幕 JSON")
        self.save_btn.setEnabled(False)
        self.load_btn = QPushButton("加载字幕 JSON")

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.status_label = QLabel("状态：等待操作")

        self.subtitle_list = QListWidget()

        # 布局
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.open_btn)
        control_layout.addWidget(self.load_btn)
        control_layout.addWidget(self.save_btn)
        control_layout.addWidget(self.play_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.slider)
        main_layout.addWidget(self.subtitle_list)
        main_layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # 信号连接
        self.open_btn.clicked.connect(self.open_audio)
        self.play_btn.clicked.connect(self.toggle_play)
        self.save_btn.clicked.connect(self.save_json)
        self.load_btn.clicked.connect(self.load_json)
        self.subtitle_list.itemClicked.connect(self.subtitle_clicked)
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.slider.sliderMoved.connect(self.set_position)

        self.timer = QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.highlight_current_subtitle)
        self.timer.start()

    def log(self, message):
        self.status_label.setText(f"状态：{message}")

    def open_audio(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择音频文件", filter="音频文件 (*.mp3 *.wav)")
        if path:
            self.audio_file = path
            self.log("开始识别音频...")
            self.play_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            self.subtitles.clear()
            self.subtitle_list.clear()
            threading.Thread(target=self.run_whisper).start()

    def run_whisper(self):
        try:
            self.log("加载模型并识别音频中...")
            result = self.model.transcribe(self.audio_file, language='zh', verbose=True)
            self.subtitles = result['segments']
            self.populate_subtitles()
            self.log("识别完成。可以播放。")
            self.save_btn.setEnabled(True)
            self.play_btn.setEnabled(True)
            self.player.setSource(QUrl.fromLocalFile(self.audio_file))
        except Exception as e:
            self.log(f"识别出错：{e}")
            QMessageBox.critical(self, "识别错误", str(e))

    def populate_subtitles(self):
        self.subtitle_list.clear()
        for seg in self.subtitles:
            start = seg['start']
            text = seg['text'].strip()
            self.subtitle_list.addItem(f"[{start:.1f}s] {text}")
        self.log(f"共识别 {len(self.subtitles)} 条字幕。")

    def toggle_play(self):
        if self.player.isPlaying():
            self.player.pause()
            self.play_btn.setText("播放")
        else:
            self.player.play()
            self.play_btn.setText("暂停")

    def subtitle_clicked(self, item):
        index = self.subtitle_list.currentRow()
        if 0 <= index < len(self.subtitles):
            start_time = self.subtitles[index]['start'] * 1000
            self.player.setPosition(int(start_time))
            self.player.play()
            self.play_btn.setText("暂停")

    def update_position(self, position):
        self.slider.setValue(position)

    def update_duration(self, duration):
        self.slider.setRange(0, duration)

    def set_position(self, position):
        self.player.setPosition(position)

    def highlight_current_subtitle(self):
        if not self.subtitles:
            return
        current_time = self.player.position() / 1000
        for i, seg in enumerate(self.subtitles):
            if seg['start'] <= current_time < seg['end']:
                self.subtitle_list.setCurrentRow(i)
                break

    def save_json(self):
        if not self.subtitles:
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存字幕 JSON", filter="JSON 文件 (*.json)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.subtitles, f, ensure_ascii=False, indent=2)
            self.log("字幕已保存。")

    def load_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "加载字幕 JSON", filter="JSON 文件 (*.json)")
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                self.subtitles = json.load(f)
            self.populate_subtitles()
            self.log("字幕加载成功。请选择音频文件进行播放。")
            self.audio_file = QFileDialog.getOpenFileName(self, "选择对应的音频文件", filter="音频文件 (*.mp3 *.wav)")[0]
            if self.audio_file:
                self.player.setSource(QUrl.fromLocalFile(self.audio_file))
                self.play_btn.setEnabled(True)
            else:
                self.log("未选择音频文件，无法播放。")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = SubtitlePlayer()
    player.show()
    sys.exit(app.exec())

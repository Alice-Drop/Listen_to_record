# 我们分步骤构建这个 PySide6 应用：
# - 选择音频文件（支持 .wav 和 .mp3）
# - 转换成文本和时间戳（使用 whisper）
# - 播放音频（使用 pydub 和 simpleaudio）
# - 展示字幕和进度条（QListWidget + QSlider）
# - 点击字幕跳转到对应时间播放

# 请先确保安装以下依赖：
# pip install PySide6 pydub openai-whisper simpleaudio

import sys
import threading
import whisper
from pydub import AudioSegment
import simpleaudio as sa
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout,
    QWidget, QListWidget, QSlider, QLabel
)
from PySide6.QtCore import QTimer, Qt

class SubtitlePlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("语音识别字幕播放器")
        self.resize(600, 400)

        # 初始化UI组件
        self.button = QPushButton("选择音频文件")
        self.label = QLabel("未选择音频")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.subtitles = QListWidget()

        layout = QVBoxLayout()
        layout.addWidget(self.button)
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        layout.addWidget(self.subtitles)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 初始化变量
        self.audio = None
        self.play_obj = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_slider)
        self.model = whisper.load_model("base")
        self.result = None
        self.start_time = 0
        self.playback_start_time = 0
        self.audio_data = None
        self.selected_audio_path = None

        # 信号连接
        self.button.clicked.connect(self.open_file)
        self.subtitles.itemClicked.connect(self.jump_to)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择音频文件", "", "音频文件 (*.wav *.mp3)"
        )
        if not path:
            return

        self.label.setText(f"加载中：{path}")
        self.selected_audio_path = path

        threading.Thread(target=self.process_audio, args=(path,), daemon=True).start()

    def process_audio(self, path):
        # 载入音频（转为wav格式以便播放）
        if path.endswith(".mp3"):
            audio = AudioSegment.from_mp3(path)
        else:
            audio = AudioSegment.from_wav(path)
        audio = audio.set_channels(1).set_frame_rate(16000)
        self.audio_data = audio.raw_data
        self.audio = audio
        self.duration_ms = len(audio)

        # 语音识别
        self.result = self.model.transcribe(path)

        self.subtitles.clear()
        for seg in self.result["segments"]:
            self.subtitles.addItem(f"[{seg['start']:.2f}s] {seg['text']}")

        self.label.setText(f"已加载：{path}")

        # 播放音频
        self.play_audio()

    def play_audio(self, start_time=0):
        if self.play_obj:
            self.play_obj.stop()
        self.start_time = start_time
        raw = self.audio[start_time * 1000:]
        self.playback_start_time = sa.get_stream_time()
        self.play_obj = sa.play_buffer(
            raw.raw_data, 1, 2, raw.frame_rate
        )
        self.timer.start(200)

    def update_slider(self):
        elapsed = sa.get_stream_time() - self.playback_start_time + self.start_time
        progress = int((elapsed * 1000 / self.duration_ms) * 1000)
        self.slider.setValue(progress)

    def jump_to(self, item):
        text = item.text()
        if text.startswith("["):
            time_str = text.split("]")[0][1:-1]
            try:
                time_val = float(time_str)
                self.play_audio(time_val)
            except ValueError:
                pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SubtitlePlayer()
    window.show()
    sys.exit(app.exec())


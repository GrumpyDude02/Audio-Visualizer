import threading, time, pyaudio
import numpy as np
import pygame as pg
import soundfile as sf
import globals as gp
from Bar import Bar
from scipy.fft import fft
from scipy.signal.windows import hann


# TODO: replace audio backend from pg.mixer to pyaudio or pyminiaudio


class AudioFileTypeError(Exception):
    def __init__(self):
        self.message = "File is not a valid audio file or does not exist"


class AudioFile:  # struct everything should be public
    IDLE = 0
    PLAYING = 1
    PAUSED = 2
    FINISHED = 3

    def __init__(self, filepath: str, fft_size):
        try:
            t = time.perf_counter()
            self.filepath = filepath
            self.file = sf.SoundFile(filepath)
            self.state = AudioFile.IDLE

            self.sample_rate = self.file.samplerate
            self.channels = self.file.channels
            self.stream: pyaudio.Stream = None
            self.cache = None
            self.fft_size = fft_size

            self.chunks_queue = []
            print(f"loaded in:{time.perf_counter()-t}")

        except Exception as e:
            print("Failed to load the file; An exception has accurred: ")
            print(e)
            raise AudioFileTypeError

    def open_stream_output(self, loader: pyaudio.PyAudio, callback):
        return loader.open(
            rate=self.sample_rate,
            channels=self.channels,
            format=pyaudio.paInt16,
            output=True,
            frames_per_buffer=self.fft_size,
            stream_callback=callback,
        )

    def start(self, stream):
        self.stream = stream
        self.stream.start_stream()
        self.state = AudioFile.PLAYING
        return 0

    def toggle_pause(self):
        if self.state == AudioFile.PLAYING:
            self.state = AudioFile.PAUSED
            # self.stream.stop_stream()
        elif self.state == AudioFile.PAUSED:
            self.state = AudioFile.PLAYING
            # self.stream.start_stream()

    def stop(self):
        self.stream.stop_stream()
        self.stream.close()
        self.state = AudioFile.FINISHED
        print("terminated")


class AudioManager:

    def __init__(self, app, fft_size: int = 2048, sample_rate: int = 44100):
        self.app = app
        self.lock = threading.Lock()
        self.audio_queue = []
        self.current: AudioFile = None
        self.fft_size = fft_size
        self.sample_rate = sample_rate
        self.hanning_window = hann(fft_size)
        self.bars = None
        self.bar_width = None
        self.usable_freq_indexes = None
        self.num_averages = 0
        self.loader = pyaudio.PyAudio()
        self.init_bars()

    def add(self, filepath):
        try:
            audio = AudioFile(filepath, self.fft_size)
            with self.lock:
                self.audio_queue.append(audio)
            return True
        except AudioFileTypeError:
            return False

    def update_queue(self):
        if self.lock.acquire(blocking=False):
            try:
                if self.current is not None and self.current.state != AudioFile.FINISHED:
                    return

                if self.current is not None and self.current.state == AudioFile.FINISHED:
                    self.current.stop()

                if len(self.audio_queue) == 0:
                    self.current = None
                    return

                self.current = self.audio_queue.pop(0)
                stream = self.current.open_stream_output(self.loader, self.callback_func)
                self.current.start(stream)

            finally:
                self.lock.release()

    def init_bars(self):
        step = 1.06
        konst = 1
        f = 1
        i = 0
        self.usable_freq_indexes = [i]
        bands = np.fft.fftfreq(n=self.fft_size, d=1 / self.sample_rate)
        self.fft_bins = bands[: len(bands) // 2]
        while True:
            konst *= step
            next_freq = f * konst
            i = int(next_freq * self.fft_size / self.sample_rate)
            if i > len(self.fft_bins):
                break
            self.usable_freq_indexes.append(i)

        self.usable_freq_indexes = sorted(set(self.usable_freq_indexes))

        self.bar_width = min(gp.min_bar_width, max(self.app.width / (len(self.usable_freq_indexes)), 2))
        self.amps = [0 for _ in range(len(self.fft_bins))]
        offset = (self.app.width - self.bar_width * len(self.usable_freq_indexes)) // 2
        l = len(self.usable_freq_indexes) - 1
        self.bars = [
            Bar(
                {
                    "frequencies": self.fft_bins[self.usable_freq_indexes[i] : self.usable_freq_indexes[min(i + 1, l)]],
                    "index_range": (self.usable_freq_indexes[i], self.usable_freq_indexes[min(i + 1, l)]),
                },
                (100, 0),
                (255, 0, 0),
            )
            for i in range(len(self.usable_freq_indexes))
        ]
        for i in range(len(self.bars)):
            self.bars[i].pos = (i * self.bar_width + offset, self.app.height // 2)

    def resize(self):
        if not self.usable_freq_indexes:
            return

        self.bar_width = min(gp.min_bar_width, max(self.app.width / (len(self.usable_freq_indexes)), 2))

        offset = (self.app.width - self.bar_width * len(self.usable_freq_indexes)) // 2
        for i in range(len(self.bars)):
            self.bars[i].pos = (i * self.bar_width + offset, self.app.height // 2)

    def empty_queue(self):
        if self.current is None or len(self.audio_queue) == 0:
            return
        self.audio_queue.clear()

    def skip(self):
        if self.current is not None:
            self.current.stop()
            self.amps = [0 for _ in range(self.fft_size)]

    def toggle_pause(self):
        if self.current is not None:
            self.current.toggle_pause()

    def draw_bars(self, window):
        if self.bars is None:
            return
        for bar in self.bars:
            bar.draw(window, self.bar_width - 1)

    def callback_func(self, in_data, frame_count, time_info, status):
        if self.current.state == AudioFile.PAUSED:
            return (np.zeros((frame_count, self.current.channels), dtype=np.int16), pyaudio.paContinue)

        data = self.current.file.read(frames=frame_count, dtype=gp.dtype)
        data_len = len(data)

        if data_len == 0:
            self.current.state = AudioFile.FINISHED
            return (None, pyaudio.paComplete)

        if data_len < self.fft_size:
            pad_width = self.fft_size - data_len
            data = np.pad(data, (0, pad_width), mode="constant")

        mono_data = np.mean(data, axis=1) if len(data.shape) > 1 else data
        ffted_chunk = fft(mono_data * self.hanning_window, norm="forward", n=self.fft_size)
        avg = ffted_chunk
        if self.num_averages > 1:
            self.current.chunks_queue.append(ffted_chunk)
            avg = np.average(self.current.chunks_queue, axis=0)
            if len(self.current.chunks_queue) > self.num_averages:
                self.current.chunks_queue.pop(0)

        self.amps = np.log10(np.abs(avg) + 1e-6)

        m = np.max(self.amps)
        if m < 1e-6:
            self.amps *= 0
        else:
            self.amps /= m
        return (data, pyaudio.paContinue)

    def update(self):
        self.update_queue()
        for i in range(len(self.bars)):
            self.bars[i].update(self.amps, self.app.dt, self.app.bar_min_height, self.app.bar_max_height)

    def terminate(self):
        if self.current is not None and self.current.stream is not None:
            self.current.stop()
        self.audio_queue.clear()
        self.loader.terminate()

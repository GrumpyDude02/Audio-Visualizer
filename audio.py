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

    Stream: pyaudio.Stream = None

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

            bands = np.fft.fftfreq(n=fft_size, d=1 / self.sample_rate)
            self.fft_bins = bands[: len(bands) // 2]

            self.start_index = round(gp.start_frequency * fft_size / self.sample_rate)
            self.end_index = min(round(gp.end_frequency * fft_size / self.sample_rate), len(bands))

            self.amps = [0 for _ in range(len(self.fft_bins))]
            self.amps_queue = []
            print(f"loaded in:{time.perf_counter()-t}")

        except Exception as e:
            print("Failed to load the file; An exception has accurred: ")
            print(e)
            raise AudioFileTypeError

    def start(self, loader: pyaudio.PyAudio, callback):
        AudioFile.Stream = loader.open(
            channels=self.channels,
            format=pyaudio.paInt16,
            rate=self.sample_rate,
            output=True,
            frames_per_buffer=self.fft_size,
            stream_callback=callback,
        )
        AudioFile.Stream.start_stream()
        self.state = AudioFile.PLAYING
        return 0

    def toggle_pause(self):
        if self.state == AudioFile.PLAYING:
            self.state = AudioFile.PAUSED
            AudioFile.Stream.stop_stream()
        elif self.state == AudioFile.PAUSED:
            self.state = AudioFile.PLAYING
            AudioFile.Stream.start_stream()

    def stop(self):
        AudioFile.Stream.stop_stream()
        AudioFile.Stream.close()
        self.state = AudioFile.FINISHED
        print("terminated")


class AudioManager:

    def __init__(self, fft_size: int):

        self.lock = threading.Lock()
        self.logarithmic = True
        self.stream: pyaudio.Stream = None
        self.audio_queue = []
        self.current: AudioFile = None
        self.fft_size = fft_size
        self.hanning_window = hann(fft_size)
        self.bars = None
        self.bar_width = None
        self.usable_freq_indexes = None
        self.num_averages = 1
        self.loader = pyaudio.PyAudio()

    def add(self, filepath):
        try:
            audio = AudioFile(filepath, self.fft_size)
            with AudioManager.lock:
                self.audio_queue.append(audio)
            return True
        except AudioFileTypeError:
            return False

    def update_queue(self, window_width, window_height):
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

                if self.logarithmic:
                    self.calculate_freq_indexes_log()
                    self.bar_width = min(gp.min_bar_width, max(window_width / (len(self.usable_freq_indexes)), 2))
                else:
                    self.calculate_freq_indexes_linear()
                    self.bar_width = min(
                        gp.min_bar_width,
                        max(int(window_width / gp.bands_number), window_width / len(self.usable_freq_indexes)),
                    )

                offset = (window_width - self.bar_width * len(self.usable_freq_indexes)) // 2
                l = len(self.usable_freq_indexes) - 1
                self.bars = [
                    Bar(
                        {
                            "frequencies": self.current.fft_bins[
                                self.usable_freq_indexes[i] : self.usable_freq_indexes[min(i + 1, l)]
                            ],
                            "index_range": (self.usable_freq_indexes[i], self.usable_freq_indexes[min(i + 1, l)]),
                        },
                        (100, 0),
                        (255, 0, 0),
                    )
                    for i in range(len(self.usable_freq_indexes))
                ]
                for i in range(len(self.bars)):
                    self.bars[i].pos = (i * self.bar_width + offset, window_height // 2)

                self.current.start(self.loader, self.callback_func)

            finally:
                AudioManager.lock.release()

    def calculate_freq_indexes_log(self):
        step = 1.06
        konst = 1
        f = 1
        i = 0
        self.usable_freq_indexes = [i]
        while True:
            konst *= step
            next_freq = f * konst
            i = int(next_freq * self.fft_size / self.current.sample_rate)
            if i > len(self.current.fft_bins):
                break
            self.usable_freq_indexes.append(i)
        self.usable_freq_indexes = sorted(set(self.usable_freq_indexes))

    def calculate_freq_indexes_linear(self):
        step = int(len(self.current.fft_bins) / gp.bands_number)
        self.usable_freq_indexes = [i for i in range(0, len(self.current.fft_bins), step)]

    def resize(self, window_width, window_height):
        if not self.usable_freq_indexes:
            return
        if AudioManager.Logarithmic:
            self.bar_width = min(gp.min_bar_width, max(window_width / (len(self.usable_freq_indexes)), 2))
        else:
            self.bar_width = min(
                gp.min_bar_width, max(int(window_width / gp.bands_number), window_width / len(self.usable_freq_indexes))
            )
        offset = (window_width - self.bar_width * len(self.usable_freq_indexes)) // 2
        for i in range(len(self.bars)):
            self.bars[i].pos = (i * self.bar_width + offset, window_height // 2)

    def empty_queue(self):
        if self.current is None or len(self.audio_queue) == 0:
            return
        self.audio_queue.clear()

    def skip(self):
        if self.current is not None:
            self.current.stop()

    def toggle_pause(self):
        if self.current is not None:
            self.current.toggle_pause()

    def draw_bars(self, window):
        if self.bars is None:
            return
        for bar in self.bars:
            bar.draw(window, self.bar_width - 1)

    def callback_func(self, in_data, frame_count, time_info, status):
        if status == pyaudio.paComplete:
            self.current.state = AudioFile.FINISHED
            return (None, pyaudio.paComplete)

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
            self.current.amps_queue.append(ffted_chunk)
            avg = np.average(self.current.amps_queue, axis=0)
            if len(self.current.amps_queue) > self.num_averages:
                self.current.amps_queue.pop(0)

        self.current.amps = np.log10(np.abs(avg) + 1e-6)

        m = np.max(self.current.amps)
        if m < 1e-6:
            self.current.amps *= 0
        else:
            self.current.amps /= m
        return (data, pyaudio.paContinue)

    def update(self, window_width, window_height, min_height, max_height, dt):
        self.update_queue(window_width, window_height)
        if self.current is None:
            return
        for i in range(len(self.bars)):
            self.bars[i].update(self.current.amps, dt, min_height, max_height)

    def terminate(self):
        self.loader.terminate()

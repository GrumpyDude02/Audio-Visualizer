import numpy as np
import pygame as pg
import threading, time, math
import soundfile as sf
import globals as gp
from Bar import Bar
from scipy.fft import fft


class AudioFileTypeError(Exception):
    def __init__(self):
        self.message = "File is not a valid audio file or does not exist"


class AudioFile:
    def __init__(self, filepath: str, hop: int, fft_size, n_fft: int):
        try:
            t = time.perf_counter()
            self.filepath = filepath
            self.started = False
            self.paused = False
            self.finished = False

            data, sr = sf.read(filepath, dtype="int16")

            if len(data.shape) > 1:
                data = np.mean(data, axis=1)

            self.data = data
            self.sample_rate = sr

            self.fft_size = fft_size

            bands = np.fft.fftfreq(n=self.fft_size, d=1 / self.sample_rate)
            bands = bands[: len(bands) // 2]
            self.start_index = round(gp.start_frequency * self.fft_size / self.sample_rate)
            self.end_index = min(round(gp.end_frequency * self.fft_size / self.sample_rate), len(bands))
            self.fft_bins = bands[self.start_index : self.end_index + 1]

            self.chunks = [self.data[i : i + self.fft_size] for i in range(0, len(self.data) - self.fft_size, self.fft_size)]

            self.amps = [0 for _ in range(len(self.fft_bins))]
            self.amps_queue = []
            self.amps_queue_limit = 4
            self.time_window = (self.fft_size / self.sample_rate) * 1000000
            self.last_time_update = 0
            self.pointer = 0
            self.pos = pg.mixer.music.get_pos()
            print(f"loaded in:{time.perf_counter()-t}")
        except Exception as e:
            print(e)
            raise AudioFileTypeError

    def start(self, pos: int = None):
        try:
            pg.mixer.music.stop()
            pg.mixer.music.unload()
            pg.mixer.music.load(self.filepath)
            pg.mixer.music.play()
            if pos is not None:
                pg.mixer.music.set_pos(pos)
            self.started = True
            return 0
        except pg.error:
            print(pg.get_error())
            return -1

    def pause(self):
        self.paused = True
        pg.mixer.music.pause()

    def resume(self):
        self.paused = False
        pg.mixer.music.unpause()

    def update(self, dt):
        self.pos = pg.mixer.music.get_pos()
        chunk_index = int(((self.pos + dt * 500) * 1000 / self.time_window))
        if not pg.mixer.music.get_busy() and not self.paused:
            self.finished = True
            return
        if len(self.chunks) <= chunk_index:
            return
        ffted_chunk = np.abs(fft(self.chunks[chunk_index]))
        max = np.max(ffted_chunk) + 1e-20
        ffted_chunk /= max
        self.amps_queue.append(ffted_chunk[self.start_index : self.end_index])
        if len(self.amps_queue) == 1:
            self.amps = self.amps_queue[0]
        else:
            self.amps = []
            for i in range(len(self.amps_queue[0])):
                avg = 0
                for j in range(len(self.amps_queue)):
                    avg += self.amps_queue[j][i]
                avg /= len(self.amps_queue)
                self.amps.append(avg)
        if len(self.amps_queue) >= self.amps_queue_limit:
            self.amps_queue.pop(0)

    def get_pos(self):
        return pg.mixer.music.get_pos()

    def get_amps(self):
        return self.amps

    def get_decibel(self, frequency):
        pos = self.get_pos() * 0.001
        try:
            return self.spectrogram[int(frequency * self.frequencies_ratio)][int(self.time_ratio * pos)]
        except IndexError:
            return gp.min_val


class AudioManager:
    lock = threading.Lock()

    def __init__(self, fft_size: int):
        self.audio_queue = []
        self.current = None
        self.fft_size = fft_size
        self.bars = None
        self.bar_width = None

    def add(self, filepath, hops, n_fft):
        try:
            print(filepath)
            audio = AudioFile(filepath, hops, self.fft_size, n_fft)
            with AudioManager.lock:
                self.audio_queue.append(audio)
            return True
        except AudioFileTypeError:
            return False

    def update_queue(self, window_width, window_height):
        if AudioManager.lock.acquire(blocking=False):
            try:
                if self.current is None or self.current.finished:
                    if len(self.audio_queue) == 0:
                        self.current = None
                        return
                    self.current = self.audio_queue.pop(0)
                    step = 1.06
                    konst = 1
                    f = self.current.fft_bins[0]
                    i = 0
                    self.usable_freq_indexes = [i]
                    while 1:
                        konst *= step
                        next_freq = f * konst
                        i = int(next_freq * self.fft_size / self.current.sample_rate)
                        if i > len(self.current.fft_bins):
                            break
                        self.usable_freq_indexes.append(i)

                    self.usable_freq_indexes = sorted(set(self.usable_freq_indexes))
                    self.bar_width = max(window_width / len(self.usable_freq_indexes), 2)
                    self.bars = [
                        Bar(
                            {
                                "frequencies": self.current.fft_bins[
                                    self.usable_freq_indexes[i] : self.usable_freq_indexes[i + 1]
                                ],
                                "index_range": (self.usable_freq_indexes[i], self.usable_freq_indexes[i + 1]),
                            },
                            (i * self.bar_width, window_height // 2),
                            (255, 0, 0),
                        )
                        for i in range(len(self.usable_freq_indexes) - 1)
                    ]

                    self.current.start()
            finally:
                AudioManager.lock.release()

    def get_decibel(self, frequency):
        if self.current is None:
            return gp.min_val
        return self.current.get_decibel(frequency)

    def get_amps(self):
        if self.current is not None:
            return self.current.get_amps()
        return [gp.min_val for _ in range(len(self.fft_size) // 2)]

    def draw_bars(self, window):
        if self.bars is None:
            return
        for bar in self.bars:
            bar.draw(window, self.bar_width - 1)

    def update(self, window_width, window_height, min_height, max_height, dt):
        self.update_queue(window_width, window_height)
        if self.current is None:
            return
        self.current.update(dt)
        amps = self.get_amps()
        for i in range(len(self.bars)):
            self.bars[i].update(amps, dt, min_height, max_height)

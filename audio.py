import librosa as lr
import numpy as np
import pygame as pg
import threading, time
import soundfile as sf
import matplotlib.pyplot as plt


min_db = -80


class AudioFileTypeError(Exception):
    def __init__(self):
        self.message = "File is not a valid audio file or does not exist"


class AudioFile:
    def __init__(self, filepath: str, hop: int, n_fft: int):
        try:
            self.filepath = filepath
            self.started = False
            self.paused = False
            self.finished = False

            data, sr = sf.read(filepath)

            if len(data.shape) > 1:
                data = np.mean(data, axis=1)

            self.time_series = data
            self.sample_rate = sr

            self.samples = len(data)

            self.pos = pg.mixer.music.get_pos()
            self.hop = hop
            self.n_fft = n_fft

            self.spectrogram = lr.amplitude_to_db(
                np.abs(lr.stft(self.time_series, hop_length=self.hop, n_fft=self.n_fft)), ref=np.max
            )

            self.frequencies = lr.fft_frequencies(sr=self.sample_rate, n_fft=self.n_fft)
            self.times = lr.core.frames_to_time(
                np.arange(self.spectrogram.shape[1]), sr=self.sample_rate, hop_length=self.hop, n_fft=self.n_fft
            )

            self.frequencies_ratio = len(self.frequencies) / self.frequencies[len(self.frequencies) - 1]
            self.time_ratio = len(self.times) / self.times[len(self.times) - 1]

            print("loaded")
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

    def update(self):
        if pg.mixer.music.get_busy() == False and self.paused == False:
            self.finished = True
        self.pos = pg.mixer.music.get_pos()

    def get_pos(self):
        return pg.mixer.music.get_pos()

    def get_decibel(self, frequency):
        pos = self.get_pos() * 0.001
        try:
            return self.spectrogram[int(frequency * self.frequencies_ratio)][int(self.time_ratio * pos)]
        except IndexError:
            return min_db


class AudioManager:
    lock = threading.Lock()

    def __init__(self):
        self.audio_queue = []
        self.current = None

    def add(self, filepath, hops, n_fft):
        try:
            print(filepath)
            audio = AudioFile(filepath, hops, n_fft)
            with AudioManager.lock:
                self.audio_queue.append(audio)
            return True
        except AudioFileTypeError:
            return False

    def update_queue(self):
        if AudioManager.lock.acquire(blocking=False):
            try:
                if self.current is None or self.current.finished:
                    if len(self.audio_queue) == 0:
                        self.current = None
                        return
                    self.current = self.audio_queue.pop(0)
                    self.current.start()
            finally:
                AudioManager.lock.release()

    def get_decibel(self, frequency):
        if self.current is None:
            return min_db
        return self.current.get_decibel(frequency)

    def update(self):
        self.update_queue()
        if self.current is None:
            return
        self.current.update()

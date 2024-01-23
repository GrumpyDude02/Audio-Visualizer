import librosa as lr
import numpy as np
import pygame as pg
import threading


class AudioFileTypeError(Exception):
    def __init__(self):
        self.message = "File is not a valid audio file or does not exist"


class AudioFile:
    def __init__(self, filepath: str, hop: int, n_fft: int):
        try:
            self.filepath = filepath
            t, sr = lr.load(filepath, sr=None)
            self.time_series = t
            self.sample_rate = sr
            self.pos = pg.mixer.music.get_pos()
            self.hop = hop
            self.n_fft = n_fft
            self.started = False
            self.paused = False
            self.finished = False
            self.stft = lr.stft(self.time_series, hop_length=self.hop, n_fft=self.n_fft)
            print("loaded")
        except:
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
        pg.mixer.music.get_pos()


class AudioManager:
    lock = threading.Lock()

    def __init__(self):
        self.audio_queue = []
        self.current = None

    def add(self, filepath, hops, n_stft):
        with AudioManager.lock:
            try:
                print(filepath)
                audio = AudioFile(filepath, hops, n_stft)
                self.audio_queue.append(audio)
                return True
            except AudioFileTypeError:
                return False

    def update_queue(self):
        with AudioManager.lock:
            if self.current is None or self.current.finished == True:
                if len(self.audio_queue) == 0:
                    self.current = None
                    return
                self.current = self.audio_queue.pop(0)
                self.current.start()

    def update(self):
        self.update_queue()
        if self.current is None:
            return
        self.current.update()

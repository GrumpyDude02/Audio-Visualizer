import threading, time, pyaudio, numpy as np, soundfile as sf, globals as gp
from scipy.fft import fft
from scipy.signal.windows import hann

# TODO: replace audio backend from pg.mixer to pyaudio or pyminiaudio


class AudioFileTypeError(Exception):
    def __init__(self):
        self.message = "File is not a valid audio file or does not exist"


class AudioFile:  # struct everything should be public
    IDLE = "IDLE"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    SEEKING = "SEEKING"
    FINISHED = "FINISHED"

    def __init__(self, filepath: str, fft_size):
        try:
            t = time.perf_counter()
            self.filepath = filepath
            self.file = sf.SoundFile(filepath)
            self.state = AudioFile.IDLE
            info = sf.info(filepath)
            self.format = info.format
            self.duration = info.duration
            self.sample_rate = self.file.samplerate
            self.channels = self.file.channels
            self.stream: pyaudio.Stream = None
            self.cache = None
            self.fft_size = fft_size
            self.samples_passed = 0
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

    def seek_to(self, seconds: float):
        self.samples_passed = seconds * self.sample_rate
        self.file.seek(int(seconds * self.sample_rate))

    def get_pos(self):
        """returns time pass from a song in seconds"""
        return int(self.samples_passed / self.sample_rate)

    def toggle_pause(self):
        if self.state == AudioFile.PLAYING:
            self.state = AudioFile.PAUSED
        elif self.state == AudioFile.PAUSED:
            self.state = AudioFile.PLAYING

    def stop(self):
        self.stream.stop_stream()
        self.stream.close()
        self.state = AudioFile.FINISHED
        self.file.close()
        print("terminated")


class AudioManager:

    NONE = "NONE"
    SKIP = "SKIP"
    QUEUE_FULL = "QUEUE_FULL"
    QUEUE_EMPTY = "QUEUE_EMPTY"

    def __init__(self, app, fft_size: int = 2048, sample_rate: int = 44100, bands_number: int = None):
        self.app = app
        self.lock = threading.Lock()
        self.seeking_lock = threading.Lock()
        self.audio_queue = []
        self.current: AudioFile = None
        self.fft_size = fft_size
        self.sample_rate = sample_rate
        self.hanning_window = hann(fft_size)
        self.bars = None
        self.num_averages = 0
        self.amps = [0 for _ in range(self.fft_size // 2)]
        self.loader = pyaudio.PyAudio()
        self.update_timeline = True

    def add(self, filepath):
        try:
            audio = AudioFile(filepath, self.fft_size)
            with self.lock:
                self.audio_queue.append(audio)
            return True
        except AudioFileTypeError:
            return False

    def update_queue(self, pause_button, skip_button):
        if self.lock.acquire(blocking=False):
            try:
                if self.current is not None and self.current.state != AudioFile.FINISHED:
                    return None

                if self.current is not None and self.current.state == AudioFile.FINISHED:
                    self.current.stop()

                if len(self.audio_queue) == 0:
                    self.current = None
                    skip_button.update(self.get_queue_state())
                    return None

                skip_button.update(self.get_queue_state())
                self.current = self.audio_queue.pop(0)
                stream = self.current.open_stream_output(self.loader, self.callback_func)
                self.current.start(stream)
                pause_button.update(self.get_audio_state())
                return self.current.duration
            finally:
                self.lock.release()

    def get_usable_freq(self, bands_number: int = None) -> dict:
        usable_freq_indexes = []

        usable_range = self.fft_size // 2
        if bands_number is not None:
            step = (gp.end_frequency / gp.start_frequency) ** (1 / bands_number)
            curr_freq = gp.start_frequency
        else:
            step = 1.06
            curr_freq = 1
        frequencies = []
        while True:
            index = int(curr_freq * self.fft_size / self.sample_rate)
            if index > usable_range:
                break
            usable_freq_indexes.append(index)
            frequencies.append(curr_freq)
            curr_freq *= step

        usable_freq_indexes = sorted(set(usable_freq_indexes))
        return {"frequencies": frequencies, "indexes": usable_freq_indexes}

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

    def callback_func(self, in_data, frame_count, time_info, status):

        if (
            (self.update_timeline[1] or self.current.state == AudioFile.PAUSED) and not self.update_timeline[0]
        ) or not self.seeking_lock.acquire(blocking=False):
            return (np.zeros((frame_count, self.current.channels), dtype=np.int16), pyaudio.paContinue)

        data = self.current.file.read(frames=frame_count, dtype=gp.dtype)
        self.current.samples_passed += frame_count
        data_len = len(data)

        if data_len == 0:
            self.current.state = AudioFile.FINISHED
            self.seeking_lock.release()
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
        self.seeking_lock.release()
        if self.update_timeline[0]:
            return (np.zeros((frame_count, self.current.channels), dtype=np.int16), pyaudio.paContinue)

        return (data, pyaudio.paContinue)

    def get_audio_state(self):
        return AudioManager.NONE if self.current is None else self.current.state

    def get_audio_duration(self):
        return 0 if self.current is None else self.current.duration

    def set_audio_state(self, state):
        if self.current is None or state is AudioManager.NONE:
            return
        self.current.state = state

    def get_current_audio_pos(self):
        return 0 if self.current is None else self.current.get_pos()

    def set_pos(self, seconds: float):
        if self.current is None:
            return -1
        if self.seeking_lock.acquire(blocking=True):
            try:
                self.current.seek_to(seconds)
            finally:
                self.seeking_lock.release()
                return 0
        return -2

    def get_queue_state(self):
        return AudioManager.QUEUE_EMPTY if (len(self.audio_queue) == 0 and self.current is None) else AudioManager.QUEUE_FULL

    def get_amps(self):
        return self.amps

    def terminate(self):
        if self.current is not None and self.current.stream is not None:
            self.current.stop()
        self.audio_queue.clear()
        self.loader.terminate()

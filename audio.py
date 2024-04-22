import threading, time, io, pyaudio, pygame as pg, numpy as np, soundfile as sf, globals as gp
import m_platform as pf
from scipy.fft import fft
from scipy.signal.windows import hann
from mutagen.mp3 import MP3
from mutagen.flac import FLAC


class AudioFileTypeError(Exception):
    def __init__(self):
        self.message = "File is not a valid audio file or does not exist"


class AudioFile:  # struct everything should be public
    IDLE = "IDLE"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    SEEKING = "SEEKING"
    FINISHED = "FINISHED"
    STOPPED = "STOPPED"

    mp3_tag_to_flac_tag = {
        "TIT2": "title",
        "TPE1": "artist",
        "TALB": "album",
        "TDRC": "date",
        "TCON": "genre",
        "TBPM": "bpm",
    }

    @staticmethod
    def get_flac_img(filepath):
        audio = FLAC(filepath)
        for p in audio.pictures:
            if p.type == 3:
                return p.data
        return None

    @staticmethod
    def get_mp3_img(filepath):
        audio = MP3(filepath)
        for t in list(audio.tags.keys()):
            if "APIC" in t:
                return audio.tags[t].data
        return None

    @staticmethod
    def get_meta_data(filepath: str, format: str):
        d = {}
        if format == "MP3":
            audio = MP3(filepath)
            for k in AudioFile.mp3_tag_to_flac_tag.keys():
                val = audio.get(k)
                d[AudioFile.mp3_tag_to_flac_tag[k]] = val[0] if val is not None else None
        if format == "FLAC":
            audio = FLAC(filepath)
            for k in AudioFile.mp3_tag_to_flac_tag.values():
                val = audio.get(k)
                if val:
                    d[k] = val[0]
        if d["title"] == None:
            d["title"] = filepath.split("\\" if pf.PLATFORM == "Windows" else "/")[-1]
        return d

    def __init__(self, filepath: str, fft_size):
        try:
            t = time.perf_counter()
            self.filepath = filepath
            self.file = sf.SoundFile(filepath)
            self.state = AudioFile.IDLE
            info = sf.info(filepath)
            self.format = info.format
            self.meta_data = AudioFile.get_meta_data(self.filepath, self.format)
            print(self.meta_data)
            self.og_img = None
            self.resized_img = None
            self.duration = info.duration
            self.sample_rate = self.file.samplerate
            self.channels = self.file.channels
            self.stream: pyaudio.Stream = None
            self.samples_passed = 0
            self.fft_size = fft_size
            print(f"loaded in:{time.perf_counter()-t}")

        except Exception as e:
            print("Failed to load the file; An exception has accurred: ")
            print(e)
            raise AudioFileTypeError

    def load_img(self):
        if self.og_img is not None:
            return 0
        if self.format == "FLAC":
            og_img = AudioFile.get_flac_img(self.filepath)
        elif self.format == "MP3":
            og_img = AudioFile.get_mp3_img(self.filepath)
        try:
            self.og_img = pg.image.load(io.BytesIO(og_img)).convert_alpha()
            return 0
        except pg.error:
            self.og_img = None
            return -1

    def resize_img(self, size: tuple):
        if self.load_img() == 0:
            self.resized_img = pg.transform.smoothscale(self.og_img, size)

    def get_resized_img(self):
        return self.resized_img

    def get_og_img(self):
        return self.og_img

    def open_stream_output(self, loader: pyaudio.PyAudio, callback):
        return loader.open(
            rate=self.sample_rate,
            channels=self.channels,
            format=pyaudio.paInt16,
            output=True,
            frames_per_buffer=self.fft_size,
            stream_callback=callback,
            start=False,
        )

    def start(self, stream: pyaudio.Stream):
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

    def terminate(self):
        self.stream.stop_stream()
        self.stream.close()
        self.state = AudioFile.FINISHED
        self.file.close()
        print("terminated")

    def stop_stream(self):
        self.stream.stop_stream()
        self.stream.close()
        self.state = AudioFile.STOPPED


class AudioManager:

    NONE = "NONE"
    SKIP = "SKIP"
    QUEUE_FULL = "QUEUE_FULL"
    QUEUE_EMPTY = "QUEUE_EMPTY"
    END_OF_LIST = "END_OF_LIST"
    START_OF_LIST = "START_OF_LIST"
    NEXT_AVAILABLE = "NEXT_AVAILABLE"
    PREV_AVAILABLE = "PREV_AVAILABLE"

    REACHED_END = 0
    UPDATED = 1
    PENDING = 2
    ERROR = 3

    def __init__(self, app, fft_size: int = 2048, sample_rate: int = 44100, bands_number: int = None):
        self.app = app
        self.seeking_lock = threading.Lock()
        self.lock = threading.Lock()
        self.audio_queue = []
        self.current: AudioFile = None
        self.fft_size = fft_size
        self.sample_rate = sample_rate
        self.hanning_window = hann(fft_size)
        self.bars = None
        self.num_averages = 0
        self.amps = [0 for _ in range(self.fft_size // 2)]
        self.init_pyaudio()
        pf.init_platform_audio(self.check_output_change)
        self.timeline_update_status = (False, False)  # (updated,pressed)
        self.cache = {}
        self.current_index = 0

    def init_pyaudio(self):
        self.loader = pyaudio.PyAudio()
        self.default_output_device = self.loader.get_default_output_device_info()["name"]

    def add(self, filepaths):
        """should be called by another thread"""
        for filepath in filepaths:
            self.audio_queue.append(filepath)
        print(self.audio_queue)

    def check_output_change(self):
        while True:
            if self.default_output_device != pf.get_default_output_device()[0]:
                self.terminate(clear=False)
                self.init_pyaudio()
                if self.current is not None:
                    self.current.start(self.current.open_stream_output(self.loader, self.callback_func))
            time.sleep(1)

    def get_audio_file(self, filepath) -> None | AudioFile:
        try:
            if self.cache.get(filepath) is None:
                self.cache[filepath] = AudioFile(filepath, self.fft_size)
        except AudioFileTypeError:
            self.cache[filepath] = None
        return self.cache[filepath]

    def del_audio_cache(self, filepath):
        if self.cache.get(filepath) is not None:
            del self.cache[filepath]

    def update(self, img_size):
        if self.current is not None and self.current.state != AudioFile.FINISHED:
            return 2

        if self.current is not None and self.current.state == AudioFile.FINISHED:
            self.current.terminate()

        if self.current_index == len(self.audio_queue):
            self.current = None
            return 0

        if self.current_index > 0:
            self.del_audio_cache(self.audio_queue[self.current_index - 1])

        self.current = self.get_audio_file(self.audio_queue[self.current_index])
        if self.current is None:
            self.audio_queue.pop(self.current_index)
            print("error loading file")
            return 3
        stream = self.current.open_stream_output(self.loader, self.callback_func)
        self.current.start(stream)
        self.current_index += 1
        self.current.resize_img(img_size)
        return 1

    def get_buttons_state(self):
        if self.current is not None:
            duration = self.current.duration
            cover = self.current.get_resized_img()
            title = self.current.meta_data["title"]
            artist = self.current.meta_data["artist"]
            toggle = AudioFile.PLAYING
        else:
            duration = 0
            artist = title = cover = None
            toggle = AudioFile.PAUSED
        return {
            "duration": duration,
            "artist": artist,
            "title": title,
            "cover": cover,
            "next": self.get_next_button_state(),
            "toggle": toggle,
        }

    def resize_preview(self, size):
        if self.current is None:
            return None
        self.current.resize_img(size)
        return self.current.get_resized_img()

    def empty_queue(self):
        if self.current is None or len(self.audio_queue) == 0:
            return
        self.audio_queue.clear()

    def skip(self):
        if self.current is not None:
            self.current.terminate()
            self.amps = [0 for _ in range(self.fft_size)]

    def previous(self):
        if self.current is not None:
            self.current.terminate()
            self.del_audio_cache(self.audio_queue[self.current_index - 1])
            self.current_index = max(self.current_index - 2, 0)
            self.amps = [0 for _ in range(self.fft_size)]

    def toggle_pause(self):
        if self.current is not None:
            self.current.toggle_pause()

    def terminate(self, clear: bool = True):
        if clear and self.current is not None and self.current.stream is not None:
            self.audio_queue.clear()
            self.current.terminate()
            pf.uninit_platform_audio()
        elif self.current is not None and self.current.stream is not None:
            self.current.stop_stream()
        if clear:
            self.audio_queue.clear()
        self.loader.terminate()

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

    def get_audio_state(self):
        return AudioManager.NONE if self.current is None else self.current.state

    def get_audio_duration(self):
        return 0 if self.current is None else self.current.duration

    def get_current_audio_pos(self):
        return 0 if self.current is None else self.current.get_pos()

    def get_next_button_state(self):
        return AudioManager.END_OF_LIST if self.current_index == len(self.audio_queue) else AudioManager.NEXT_AVAILABLE

    def get_previous_button_state(self):
        return (
            AudioManager.START_OF_LIST
            if (len(self.audio_queue) <= 1 or self.current_index == 0)
            else AudioManager.PREV_AVAILABLE
        )

    def get_amps(self):
        return self.amps

    def set_audio_state(self, state):
        if self.current is None or state is AudioManager.NONE:
            return
        self.current.state = state

    def set_timeline_update_status(self, status: tuple[bool]):
        self.timeline_update_status = status

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

    def callback_func(self, in_data, frame_count, time_info, status):

        if (
            (self.timeline_update_status[1] or self.current.state == AudioFile.PAUSED) and not self.timeline_update_status[0]
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
        # if self.num_averages > 1:
        #     self.current.chunks_queue.append(ffted_chunk)
        #     avg = np.average(self.current.chunks_queue, axis=0)
        #     if len(self.current.chunks_queue) > self.num_averages:
        #         self.current.chunks_queue.pop(0)

        self.amps = np.log10(np.abs(avg) + 1e-6)

        m = np.max(self.amps)
        if m < 1e-6:
            self.amps *= 0
        else:
            self.amps /= m
        self.seeking_lock.release()
        if self.timeline_update_status[0]:
            return (np.zeros((frame_count, self.current.channels), dtype=np.int16), pyaudio.paContinue)

        return (data, pyaudio.paContinue)

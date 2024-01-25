import sys, threading
from audio import AudioManager
import pygame as pg
import numpy


WIDTH = 600
HEIGHT = 600

bar_number = 40


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


class Application:
    base_resolution = (600, 600)
    min_decibel = -80
    max_decibel = 0

    class Bar:
        def __init__(self, frequency, pos, color) -> None:
            self.pos = pos
            self.frequency = frequency
            self.height = 0
            self.color = color

        def update(self, db, min_height, max_height, dt):
            normalized_db = (db - Application.min_decibel) / (Application.max_decibel - Application.min_decibel)
            scaled_height = normalized_db * (max_height - min_height) + min_height
            target_height = min(max_height, max(scaled_height, min_height))
            self.height = int(self.height + (target_height - self.height) * ease_out_cubic(min(dt * 5, 1)))

        def draw(self, window, width):
            rect = pg.Rect(self.pos[0], self.pos[1], width, self.height)
            pg.draw.rect(window, self.color, rect)

    def __init__(self, font_size, fps, size, resizable: bool, name: str, min_size: tuple = [100, 100]):
        pg.init()
        pg.mixer.init()

        self.display_loading_lock = threading.Lock()

        self.fps = fps
        self.dt = 1 / self.fps
        self.width = size[0]
        self.height = size[1]

        self.flags = pg.HWACCEL
        self.resizable = resizable

        if self.resizable:
            self.flags |= pg.RESIZABLE
        self.window = pg.display.set_mode(size, flags=self.flags)
        pg.display.set_caption(name)
        self.clock = pg.time.Clock()
        self.am = AudioManager()
        self.audio_loader_threads = []
        self.thread_limit = 50
        self.min_size = min_size
        self.base_font_size = font_size
        self.font_size = int(
            self.base_font_size
            * min(self.width / Application.base_resolution[0], self.height / Application.base_resolution[1])
        )
        self.font = pg.font.SysFont("Arial", self.font_size)
        self.bar_width = self.width / bar_number

        start_freq = 50
        end_freq = 12000

        self.frequencies = [i for i in range(start_freq, end_freq, int((end_freq - start_freq) / bar_number))]
        self.bars = [Application.Bar(self.frequencies[i], (i * self.bar_width, 0), (255, 0, 0)) for i in range(bar_number)]

        self.bar_min_height = self.width * 0.02
        self.bar_max_height = self.height

    def resize(self, n_size: tuple):
        scale_x = n_size[0] / Application.base_resolution[0]
        scale_y = n_size[1] / Application.base_resolution[1]
        self.width = n_size[0]
        self.height = n_size[1]
        self.font_size = int(self.base_font_size * min(scale_x, scale_y))
        self.font = pg.font.SysFont("Arial", self.font_size)

    def add_file(self, filepath):
        if len(self.audio_loader_threads) < self.thread_limit:
            self.audio_loader_threads.append(threading.Thread(target=self.am.add, args=[filepath, 256, 2048 * 2]))
            self.audio_loader_threads[-1].start()

    def display_loading(self):
        if len(self.audio_loader_threads) > 0:
            pg.draw.circle(self.window, (0, 255, 255), (100, 100), 50)

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()
            if event.type == pg.DROPFILE:
                self.add_file(event.file)

    def update(self):
        for thread in self.audio_loader_threads:
            if not thread.is_alive():
                self.audio_loader_threads.remove(thread)
        self.am.update()
        for bar in self.bars:
            bar.update(self.am.get_decibel(bar.frequency), self.bar_min_height, self.height, self.dt)
        self.dt = self.clock.tick(self.fps) * 0.001

    def draw_bars(self):
        for bar in self.bars:
            bar.draw(self.window, self.bar_width - 1)

    def draw(self):
        self.window.fill((255, 255, 255))
        self.draw_bars()
        self.display_loading()
        pg.display.flip()

    def run(self):
        while 1:
            self.handle_events()
            self.update()
            self.draw()


if __name__ == "__main__":
    # main()
    app = Application(10, 60, (600, 600), True, "Audio Visualizer")
    app.run()

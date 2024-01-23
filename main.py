import sys, threading
from audio import AudioManager
import pygame as pg


WIDTH = 600
HEIGHT = 600


class Application:
    base_resolution = (600, 600)

    def __init__(self, font_size, fps, size, resizable: bool, name: str, min_size: tuple = [100, 100]):
        pg.init()
        pg.mixer.init()

        self.display_loading_lock = threading.Lock()

        self.fps = fps
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

    def resize(self, n_size: tuple):
        scale_x = n_size[0] / Application.base_resolution[0]
        scale_y = n_size[1] / Application.base_resolution[1]
        self.width = n_size[0]
        self.height = n_size[1]
        self.font_size = int(self.base_font_size * min(scale_x, scale_y))
        self.font = pg.font.SysFont("Arial", self.font_size)

    def add_file(self, filepath):
        with self.display_loading_lock:
            if len(self.audio_loader_threads) < self.thread_limit:
                self.audio_loader_threads.append(threading.Thread(target=self.am.add, args=[filepath, 512, 2048 * 4]))
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
        with self.display_loading_lock:
            for thread in self.audio_loader_threads:
                if not thread.is_alive():
                    self.audio_loader_threads.remove(thread)
        self.am.update()
        self.clock.tick(self.fps)

    def draw(self):
        self.window.fill((255, 255, 255))
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

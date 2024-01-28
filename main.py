import sys, threading
from audio import AudioManager
import pygame as pg
import globals as gp


bar_number = 40


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


bluish_grey = (54, 69, 79)


class Application:
    def __init__(self, font_size, fps, size, resizable: bool, name: str, min_size: tuple = [100, 100]):
        pg.init()
        pg.mixer.init()

        self.display_loading_lock = threading.Lock()

        self.fps = fps
        self.dt = 1 / (self.fps + 1e-16)
        self.width = size[0]
        self.height = size[1]

        self.flags = pg.HWACCEL
        self.resizable = resizable

        if self.resizable:
            self.flags |= pg.RESIZABLE
        self.window = pg.display.set_mode(size, flags=self.flags)
        pg.display.set_caption(name)
        self.clock = pg.time.Clock()
        self.am = AudioManager(gp.fft_size)
        self.audio_loader_threads = []
        self.thread_limit = 50
        self.min_size = min_size
        self.base_font_size = font_size
        self.font_size = int(
            self.base_font_size * min(self.width / gp.base_resolution[0], self.height / gp.base_resolution[1])
        )
        self.font = pg.font.SysFont("Arial", self.font_size)

        self.bar_min_height = self.height * 0.01
        self.bar_max_height = self.height

    def resize(self, n_size: tuple):
        scale_x = n_size[0] / gp.base_resolution[0]
        scale_y = n_size[1] / gp.base_resolution[1]
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
            rect = pg.Rect(self.width * 0.05, self.height * 0.05, self.width * 0.2, self.height * 0.15)
            pos = (rect.center[0], rect.center[1])
            text_render = self.font.render("Loading file...", color=(255, 255, 255), antialias=True)
            pg.draw.rect(self.window, (0, 0, 0), rect, border_radius=8)
            pg.draw.rect(self.window, (255, 255, 255), rect, 5, border_radius=8)
            pos = text_render.get_rect(center=pos)
            self.window.blit(text_render, pos)

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_n:
                    self.am.skip()
                if event.key == pg.K_p:
                    self.am.toggle_pause()
            if event.type == pg.DROPFILE:
                self.add_file(event.file)

    def update(self):
        for thread in self.audio_loader_threads:
            if not thread.is_alive():
                self.audio_loader_threads.remove(thread)
        self.am.update(self.width, self.height, self.bar_min_height, self.bar_max_height, self.dt)
        self.dt = self.clock.tick(self.fps) * 0.001

    def draw(self):
        self.window.fill(bluish_grey)
        self.am.draw_bars(self.window)
        self.display_loading()
        pg.display.flip()

    def run(self):
        while 1:
            self.handle_events()
            self.update()
            self.draw()


if __name__ == "__main__":
    # main()
    app = Application(20, 60, (gp.WIDTH, gp.HEIGHT), True, "Audio Visualizer")
    app.run()

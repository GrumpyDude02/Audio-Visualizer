import sys, threading, time
import pygame as pg
import globals as gp
from audio import AudioManager, AudioFile
from Bar import Bar, SplitBars
from Tools.Buttons import ToggleButtons, ButtonTemplate
import Tools.Slider as sl
from math import ceil
from Tools.functions import fill


ToggleTemplate = ButtonTemplate(
    (255, 255, 255), (240, 240, 240), (200, 200, 200), (180, 180, 180), 2, 4, 2, (240, 240, 240), 5, -1, None
)

slider_template = ButtonTemplate((0, 0, 0), (255, 165, 0), (200, 200, 200), (20, 20, 20), 2, 3, 2, (20, 20, 20), 5, -1, None)

bluish_grey = (14, 29, 39)

toggle_button_size = (0.05, 0.1)
toggle_button_pos = (0.5 - toggle_button_size[0] / 2, 1.07)

skip_button_size = (0.03, 0.07)
skip_button_pos = (0.58, 1.08)

slider_pos = (0.3, 1.214)
slider_size = (0.4, 0.025)


def time_format(time: int) -> str:
    t = int(time)

    return f"{t//60:02d}:{t%60:02d}"


class Application:

    def __init__(
        self,
        font_path: str,
        font_size,
        fps,
        size,
        resizable: bool,
        name: str,
        min_size: tuple = [100, 100],
        style="WhiteBars",
    ):
        pg.init()
        pg.mixer.init()

        self.display_loading_lock = threading.Lock()
        self.style = style
        self.fps = fps
        self.dt = 1 / (self.fps + 1e-16)
        self.width = size[0]
        self.height = size[1]

        self.control_time = 3000  # miliseconds
        self.last_update_time = 0

        self.flags = pg.HWACCEL
        self.resizable = resizable

        if self.resizable:
            self.flags |= pg.RESIZABLE
        self.window = pg.display.set_mode(size, flags=self.flags)
        pg.display.set_caption(name)
        self.clock = pg.time.Clock()
        self.am = AudioManager(self, fft_size=gp.fft_size, bands_number=gp.bands_number)
        self.audio_loader_threads = []
        self.thread_limit = 50
        self.min_size = min_size
        self.base_font_size = font_size
        self.font_size = int(
            self.base_font_size * min(self.width / gp.base_resolution[0], self.height / gp.base_resolution[1])
        )
        self.init_font(font_size, font_path, False)
        self.font_path = font_path
        self.bar_min_height = int(self.height * 0.01)
        self.bar_max_height = self.height
        self.bar_width = None
        self.init_bars(style=self.style)
        self.calculate_pos(self.width, self.height, self.style)

        self.images = {
            AudioFile.PAUSED: pg.image.load("Assets/images/play.png").convert_alpha(),
            AudioFile.PLAYING: pg.image.load("Assets/images/pause.png").convert_alpha(),
            AudioManager.QUEUE_FULL: pg.image.load("Assets/images/skip_to_end.png").convert_alpha(),
            AudioManager.QUEUE_EMPTY: pg.image.load("Assets/images/skip_to_end.png").convert_alpha(),
        }
        fill(self.images[AudioManager.QUEUE_EMPTY], (150, 150, 150, 255))

        self.play_pause_toggle = ToggleButtons(
            self.images,
            ToggleTemplate,
            toggle_button_size,
            toggle_button_pos,
            (self.width, self.height),
            keys=[AudioFile.PAUSED, AudioFile.PLAYING],
            scale=0.5,
        )

        self.skip_button = ToggleButtons(
            self.images,
            ToggleTemplate,
            skip_button_size,
            skip_button_pos,
            (self.width, self.height),
            keys=[AudioManager.QUEUE_EMPTY, AudioManager.QUEUE_FULL],
            current_key=self.am.get_queue_state(),
            scale=0.5,
        )

        # self.slider = Slider(slider_template, slider_pos, slider_size, None, (self.width, self.height))
        self.slider = sl.TimeSlider(
            slider_template, slider_pos, slider_size, self.font, time_format, [0, 1], (self.width, self.height)
        )

        self.show_control_bar = False

    def init_bars(self, style, bars_number: int = None):
        if style == "RectBars" and bars_number == None:
            bars_number = 31
        dic = self.am.get_usable_freq(bars_number)
        frequencies = dic["frequencies"]
        self.indexes = dic["indexes"]
        l = len(self.indexes) - 1

        self.bar_width = min(gp.min_bar_width, max(self.width / (l + 1), 2))

        offset = (self.width - self.bar_width * (l + 1)) // 2
        self.bars = (
            [
                Bar(
                    {
                        "frequencies": (frequencies[self.indexes[i] : self.indexes[min(i + 1, l)]]),
                        "index_range": (self.indexes[i], self.indexes[min(i + 1, l)]),
                    },
                    (100, 0),
                    gp.bar_color,
                    (215, 231, 235),
                )
                for i in range(len(self.indexes))
            ]
            if style == "WhiteBars"
            else [
                SplitBars(
                    {
                        "frequencies": (frequencies[self.indexes[i] : self.indexes[min(i + 1, l)]]),
                        "index_range": (self.indexes[i], self.indexes[min(i + 1, l)]),
                    },
                    (100, 0),
                    gp.bar_color,
                    (235, 251, 255),
                )
                for i in range(len(self.indexes))
            ]
        )

        for i in range(len(self.bars)):
            self.bars[i].pos = (i * self.bar_width + offset, self.height // 2)

    def calculate_pos(self, width, height, style):
        self.rect_target_pos = (width * 0.1, height * 0.75)
        self.rect_lower_pos = (width * 0.1, height * 1.04)
        self.control_bar_rect = pg.Rect(
            self.rect_lower_pos[0],
            self.rect_lower_pos[1],
            width * 0.80,
            height * 0.4,
        )
        SplitBars.scale = Bar.scale = self.height // 2
        SplitBars.rect_height = self.height * 0.025
        print(SplitBars.rect_height)
        if style == "WhiteBars":
            self.upper_bars_height = height // 2
            self.target_bars_height = height * 0.35
        else:
            self.upper_bars_height = height * 0.85
            self.target_bars_height = height * 0.65

    def init_font(self, font_size, font_path: str, bold: bool = False):
        try:
            self.font = pg.font.Font(font_path, font_size)
        except FileNotFoundError:
            self.font = pg.font.SysFont("Arial Black", size=font_size)
        self.font.set_bold(bold)

    def resize(self, n_size: tuple):
        scale_x = n_size[0] / gp.base_resolution[0]
        scale_y = n_size[1] / gp.base_resolution[1]
        self.width = n_size[0]
        self.height = n_size[1]
        self.calculate_pos(self.width, self.height, self.style)
        self.font_size = int(self.base_font_size * min(scale_x, scale_y))
        self.init_font(self.font_size, self.font_path, False)

        if not self.indexes:
            return
        self.bar_width = min(gp.min_bar_width, max(self.width / (len(self.indexes)), 2))

        offset = (self.width - self.bar_width * len(self.indexes)) // 2
        for i in range(len(self.bars)):
            self.bars[i].pos = (i * self.bar_width + offset, self.height // 2)
        self.play_pause_toggle.resize(self.images, (self.width, self.height), self.am.get_audio_state())
        self.skip_button.resize(self.images, (self.width, self.height), self.am.get_queue_state())
        self.slider.resize((self.width, self.height), self.font)

    def add_file(self, filepath):
        if len(self.audio_loader_threads) < self.thread_limit:
            self.audio_loader_threads.append(threading.Thread(target=self.am.add, args=[filepath]))
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
                self.am.terminate()
                pg.quit()
                sys.exit()
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_n:
                    self.am.skip()
                if event.key in (pg.K_p, pg.K_SPACE):
                    self.am.toggle_pause()
                    self.play_pause_toggle.update(self.am.get_audio_state())
                if event.key == pg.K_LEFT:
                    current = self.am.get_current_audio_pos()
                    duration = self.am.get_audio_duration()
                    self.am.set_pos(min(duration, max(current - 10, 0)))
                if event.key == pg.K_RIGHT:
                    current = self.am.get_current_audio_pos()
                    duration = self.am.get_audio_duration()
                    self.am.set_pos(min(duration, max(current + 10, 0)))
                if event.key == pg.K_s:
                    self.am.set_pos(50)
            if event.type == pg.MOUSEMOTION:
                self.show_control_bar = True
                self.last_update_time = time.time() * 1000

            if event.type == pg.VIDEORESIZE:
                self.resize(event.size)
            if event.type == pg.DROPFILE:
                self.add_file(event.file)

        if self.play_pause_toggle.check_input():
            self.am.toggle_pause()
            self.skip_button.update(self.am.get_queue_state())
            self.play_pause_toggle.update(self.am.get_audio_state())

        if self.skip_button.check_input():
            self.am.skip()

    def update(self):
        for thread in self.audio_loader_threads:
            if not thread.is_alive():
                self.audio_loader_threads.remove(thread)
        self.play_pause_toggle.check_input()
        current_song_time = self.am.update_queue(self.play_pause_toggle, self.skip_button)
        if current_song_time is not None:
            self.slider.set_range((0, current_song_time))

        self.slider.update_elapsed_time(self.am.get_current_audio_pos())

        t = time.time() * 1000
        if t - self.last_update_time >= 1500 and not self.control_bar_rect.collidepoint(pg.mouse.get_pos()):
            self.show_control_bar = False
        v = 0
        if self.show_control_bar:
            self.am.update_timeline = self.slider.update()
            if self.am.update_timeline[0]:
                self.am.set_pos(self.slider.output)
            v = (self.control_bar_rect.top - self.rect_target_pos[1]) * self.dt * self.dt * 250
            k = (self.bars[0].pos[1] - self.target_bars_height) * self.dt * self.dt * 450
        elif self.control_bar_rect.top <= self.rect_lower_pos[1] * 0.979:
            v = (self.control_bar_rect.top - self.rect_lower_pos[1]) * self.dt * self.dt * 250
            k = (self.bars[0].pos[1] - self.upper_bars_height) * self.dt * self.dt * 450
        if v != 0:
            for bar in self.bars:
                bar.pos = (bar.pos[0], (bar.pos[1] - k))
            self.control_bar_rect.top = self.control_bar_rect.top - v
            self.play_pause_toggle.outline_rect.top = self.play_pause_toggle.outline_rect.top - v
            self.play_pause_toggle.rectangle.top = self.play_pause_toggle.rectangle.top - v
            self.skip_button.outline_rect.top = self.skip_button.outline_rect.top - v
            self.skip_button.rectangle.top = self.skip_button.rectangle.top - v
            self.slider.button_rect.top = self.slider.button_rect.top - v
            self.slider.button_outline.top = self.slider.button_outline.top - v
            self.slider.rectangle_bar.top = self.slider.rectangle_bar.top - v

        amps = self.am.get_amps()
        for bar in self.bars:
            bar.update(amps, self.dt, self.bar_min_height, self.bar_max_height)
        self.dt = min(self.clock.tick(self.fps) * 0.001, 0.066)

    def draw(self):
        self.window.fill(bluish_grey)
        for bar in self.bars:
            bar.draw(self.window, self.bar_width - 1)

        # drawing control bar----------------------------
        if self.control_bar_rect.top < self.height:
            pg.draw.rect(
                self.window,
                (15, 15, 15),
                (
                    self.control_bar_rect[0] + 8,
                    self.control_bar_rect[1] - 4,
                    self.control_bar_rect[2] - 4,
                    self.control_bar_rect[3],
                ),
                border_radius=4,
            )
            pg.draw.rect(self.window, (200, 200, 200), self.control_bar_rect, border_radius=4)
            pg.draw.rect(self.window, (160, 160, 160), self.control_bar_rect, border_radius=4, width=6)
            pg.draw.rect(self.window, (0, 0, 0), self.control_bar_rect, border_radius=4, width=3)
            pg.draw.rect(
                self.window,
                (35, 35, 35),
                (
                    self.play_pause_toggle.outline_rect[0] + 4,
                    self.play_pause_toggle.outline_rect[1] - 3,
                    self.play_pause_toggle.outline_rect[2],
                    self.play_pause_toggle.outline_rect[3],
                ),
                border_radius=2,
            )
            self.play_pause_toggle.draw(self.window)
            pg.draw.rect(self.window, (0, 0, 0), self.play_pause_toggle.outline_rect, border_radius=2, width=2)

            pg.draw.rect(
                self.window,
                (35, 35, 35),
                (
                    self.skip_button.outline_rect[0] + 4,
                    self.skip_button.outline_rect[1] - 3,
                    self.skip_button.outline_rect[2],
                    self.skip_button.outline_rect[3],
                ),
                border_radius=2,
            )
            self.skip_button.draw(self.window)
            pg.draw.rect(self.window, (0, 0, 0), self.skip_button.outline_rect, border_radius=2, width=2)
            self.slider.draw(self.window)
        # ---------------------------
        self.display_loading()
        pg.display.flip()

    def run(self):
        while 1:
            self.handle_events()
            self.update()
            self.draw()


if __name__ == "__main__":
    # main()
    app = Application("Assets/Fonts/PixCon.ttf", 12, 60, (gp.WIDTH, gp.HEIGHT), True, "Audio Visualizer", style="WhiteBars")
    app.run()

import sys, threading, time, enum
import pygame as pg
import globals as gp
from audio import AudioManager, AudioFile
from Bar import Bar, SoundMeterBar
from Tools.Buttons import ToggleButtons, ButtonTemplate, Buttons
import Tools.Slider as sl
from math import ceil


ToggleTemplate = ButtonTemplate(
    (255, 255, 255), (240, 240, 240), (200, 200, 200), (180, 180, 180), 4, 4, 2, (240, 240, 240), 5, -1, None
)

slider_template = ButtonTemplate((0, 0, 0), (255, 165, 0), (200, 200, 200), (20, 20, 20), 2, 3, 2, (20, 20, 20), 5, -1, None)

bluish_grey = (14, 29, 39)

control_bar_upper_pos = 0.7
control_bar_lower_pos = 1.04
control_bar_height = 0.5

toggle_button_size = (0.05, 0.1)
toggle_button_pos = (0.5 - toggle_button_size[0] / 2, 1.17)

skip_button_size = (0.03, 0.07)
skip_button_pos = (0.58, 1.18)

slider_pos = (0.1, 1.07)
slider_size = (0.8, 0.025)

preview_size = 110
lower_preview_scale = (0.025, 1.13)

white_bars_target_pos = 0.5
white_bars_upper_pos = 0.35
white_bars_scale_perc = 0.6

soundmeter_rect_height = 0.025
soundmeter_scale_perc = 0.8
soundmeter_bars_upper_pos = 0.687
soundmeter_bars_target_pos = 1


song_info_pos = (0.15, 0.85)

smoothing_speed = 5


def time_format(time: int) -> str:
    t = int(time)

    return f"{t//60:02d}:{t%60:02d}"


class Styles(enum.Enum):
    WhiteBars = "WhiteBars"
    MinimalistSoundMeter = "MinimalistSoundMeter"
    SoundMeter = "MinimalistSoundMeter"


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
        style=Styles.WhiteBars,
        spacing: int = 2,
    ):
        self.bar_spacing = spacing
        pg.init()
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
        self.files_queue = []
        self.temp_queue = []

        self.preview_img = None

        self.display_loading_lock = threading.Lock()
        self.reading_from_queue_lock = threading.Lock()
        self.audio_loader_thread = threading.Thread(target=self.add_file)
        self.audio_loader_thread.daemon = True
        self.audio_loader_thread.start()

        self.images = {
            AudioFile.PAUSED: pg.image.load("Assets/images/play.png").convert_alpha(),
            AudioFile.PLAYING: pg.image.load("Assets/images/pause.png").convert_alpha(),
            AudioManager.QUEUE_FULL: pg.image.load("Assets/images/skip_to_end.png").convert_alpha(),
            AudioManager.QUEUE_EMPTY: pg.image.load("Assets/images/grayed_skip.png").convert_alpha(),
            "NoImage": pg.image.load("Assets/images/no_image.png"),
        }

        self.min_size = min_size
        self.base_font_size = font_size
        scale = min(self.width / gp.base_resolution[0], self.height / gp.base_resolution[1])
        self.font_size = int(self.base_font_size * scale)
        self.init_font(font_size, font_path, False)
        self.font_path = font_path
        self.bar_min_height = int(self.height * 0.01)
        self.bar_max_height = self.height
        self.bar_width = None
        self.init_bars(style=self.style)
        self.calculate_pos(self.width, self.height, self.style, scale)

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

        self.slider = sl.TimeSlider(
            slider_template, slider_pos, slider_size, self.font, time_format, [0, 1], (self.width, self.height)
        )
        self.show_control_bar = False
        self.show_settings_bar = False
        self.running = True

        self.rendered_text = {"song_name": None, "artist_name": None}

    def init_bars(self, style, bars_number: int = None):
        if style == Styles.SoundMeter and bars_number == None:
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
                    (i * self.bar_width + offset + self.bar_spacing / 2, self.height),
                    gp.bar_color,
                    (225, 241, 245),
                )
                for i in range(len(self.indexes))
            ]
            if style == Styles.WhiteBars
            else [
                SoundMeterBar(
                    {
                        "frequencies": (frequencies[self.indexes[i] : self.indexes[min(i + 1, l)]]),
                        "index_range": (self.indexes[i], self.indexes[min(i + 1, l)]),
                    },
                    (i * self.bar_width + offset + self.bar_spacing / 2, self.height),
                )
                for i in range(len(self.indexes))
            ]
        )

    def calculate_pos(self, width, height, style, scale):
        SoundMeterBar.calculate_class_dim(
            self.height * soundmeter_rect_height, self.height * soundmeter_scale_perc, self.height
        )
        self.rect_target_pos = (0, height * control_bar_upper_pos)
        self.rect_lower_pos = (0, height * control_bar_lower_pos)
        self.control_bar_rect = pg.Rect(
            self.rect_lower_pos[0],
            self.rect_lower_pos[1],
            width,
            height * control_bar_height,
        )
        resized_no_image = pg.transform.smoothscale(self.images["NoImage"], (50 * scale, 50 * scale))
        self.lower_preview_pos = (lower_preview_scale[0] * self.width, lower_preview_scale[1] * self.height)
        self.preview_pos = (lower_preview_scale[0] * self.width, lower_preview_scale[1] * self.height)

        Bar.scale = self.height * white_bars_scale_perc
        self.preview_size = (scale * preview_size, scale * preview_size)

        white_surf = pg.Surface(self.preview_size, pg.SRCALPHA)
        pg.draw.rect(white_surf, (255, 255, 255), white_surf.get_rect(), border_radius=4)
        self.place_holder_preview = pg.Surface(self.preview_size, pg.SRCALPHA)
        self.place_holder_preview.fill((150, 150, 150))
        self.place_holder_preview.blit(white_surf, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
        center_pos = resized_no_image.get_rect(center=self.place_holder_preview.get_rect().center)
        self.place_holder_preview.blit(resized_no_image, center_pos)

        preview_img = self.am.resize_preview(self.preview_size)
        if preview_img is not None:
            white_surf = pg.Surface(preview_img.get_size(), pg.SRCALPHA)
            pg.draw.rect(white_surf, (255, 255, 255), white_surf.get_rect(), border_radius=4)
            preview_img.blit(white_surf, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
            self.preview_img = preview_img
        else:
            self.preview_img = self.place_holder_preview

        if style == Styles.WhiteBars:
            self.target_bars_height = height * white_bars_target_pos
            self.upper_bars_height = height * white_bars_upper_pos
        else:
            self.upper_bars_height = height * soundmeter_bars_upper_pos
            self.target_bars_height = height * soundmeter_bars_target_pos

    def init_font(self, font_size, font_path: str, bold: bool = False):
        try:
            self.font = pg.font.Font(font_path, font_size)
        except FileNotFoundError:
            self.font = pg.font.SysFont("Arial Black", size=font_size)
        self.font.set_bold(bold)

    def resize(self, n_size: tuple):
        s = min(n_size[0] / gp.base_resolution[0], n_size[1] / gp.base_resolution[1])
        self.width = n_size[0]
        self.height = n_size[1]
        self.calculate_pos(self.width, self.height, self.style, s)
        self.font_size = int(self.base_font_size * s)
        self.init_font(self.font_size, self.font_path, False)

        if not self.indexes:
            return
        self.bar_width = min(gp.min_bar_width, max(self.width / (len(self.indexes)), 2))

        offset = (self.width - self.bar_width * len(self.indexes)) // 2
        for i in range(len(self.bars)):
            self.bars[i].pos = (i * self.bar_width + offset + self.bar_spacing / 2, self.height // 2)
        self.play_pause_toggle.resize(self.images, (self.width, self.height), self.am.get_audio_state())
        self.skip_button.resize(self.images, (self.width, self.height), self.am.get_queue_state())
        self.slider.resize((self.width, self.height), self.font)

    def display_loading(self):
        rect = pg.Rect(self.width * 0.05, self.height * 0.05, self.width * 0.2, self.height * 0.15)
        pos = (rect.center[0], rect.center[1])
        text_render = self.font.render("Loading file...", color=(255, 255, 255), antialias=True)
        pg.draw.rect(self.window, (0, 0, 0), rect, border_radius=8)
        pg.draw.rect(self.window, (255, 255, 255), rect, 5, border_radius=8)
        pos = text_render.get_rect(center=pos)
        self.window.blit(text_render, pos)

    def add_file(self):
        with self.reading_from_queue_lock:
            while self.files_queue:
                self.am.add(self.files_queue.pop(0))

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_n:
                    self.am.skip()
                if event.key == pg.K_a:
                    self.am.previous()
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
                self.temp_queue.append(event.file)

        if self.temp_queue:
            self.am.add(self.temp_queue)
            update_dict = self.am.get_buttons_state()
            toggle_icon_key = update_dict["toggle"]
            next_icon_key = update_dict["next"]
            self.play_pause_toggle.update(toggle_icon_key)
            self.skip_button.update(next_icon_key)
            self.temp_queue.clear()

        if self.play_pause_toggle.check_input():
            self.am.toggle_pause()
            self.skip_button.update(self.am.get_queue_state())
            self.play_pause_toggle.update(self.am.get_audio_state())

        if self.skip_button.check_input():
            self.am.skip()

    def update(self):
        self.play_pause_toggle.check_input()

        if self.am.update(self.preview_size) in (1, 0):
            update_dict = self.am.get_buttons_state()
            preview_img = update_dict["cover"]
            duration = update_dict["duration"]
            toggle_icon_key = update_dict["toggle"]
            next_icon_key = update_dict["next"]
            self.play_pause_toggle.update(toggle_icon_key)
            self.skip_button.update(next_icon_key)
            if preview_img is not None:
                white_surf = pg.Surface(preview_img.get_size(), pg.SRCALPHA)
                pg.draw.rect(white_surf, (255, 255, 255), white_surf.get_rect(), border_radius=4)
                preview_img.blit(white_surf, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
                self.preview_img = preview_img
            else:
                self.preview_img = self.place_holder_preview
            self.slider.set_range((0, duration))

        self.slider.update_elapsed_time(self.am.get_current_audio_pos())

        t = time.time() * 1000
        if t - self.last_update_time >= 1500 and (
            not self.control_bar_rect.collidepoint(pg.mouse.get_pos()) or not pg.mouse.get_focused()
        ):
            self.show_control_bar = False
        v = 0
        if self.show_control_bar:
            slider_update_status = self.slider.update()
            self.am.set_timeline_update_status(slider_update_status)
            if slider_update_status[0]:
                self.am.set_pos(self.slider.output)
            v = (self.control_bar_rect.top - self.rect_target_pos[1]) * self.dt * 6
            k = (self.bars[0].pos[1] - self.upper_bars_height) * self.dt * 7
        elif self.control_bar_rect.top <= self.rect_lower_pos[1] * 0.98:
            v = (self.control_bar_rect.top - self.rect_lower_pos[1]) * self.dt * 6
            k = (self.bars[0].pos[1] - self.target_bars_height) * self.dt * 7
        if v != 0:
            for bar in self.bars:
                bar.pos = (bar.pos[0], bar.pos[1] - k)
            self.control_bar_rect.top = self.control_bar_rect.top - v
            self.play_pause_toggle.outline_rect.top = self.play_pause_toggle.outline_rect.top - v
            self.play_pause_toggle.rectangle.top = self.play_pause_toggle.rectangle.top - v
            self.skip_button.outline_rect.top = self.skip_button.outline_rect.top - v
            self.skip_button.rectangle.top = self.skip_button.rectangle.top - v
            self.slider.button_rect.top = self.slider.button_rect.top - v
            self.slider.button_outline.top = self.slider.button_outline.top - v
            self.slider.rectangle_bar.top = self.slider.rectangle_bar.top - v
            self.preview_pos = (self.preview_pos[0], int(self.preview_pos[1] - v))
            height = self.height - (self.height - self.control_bar_rect.top)
            SoundMeterBar.calculate_class_dim(height * soundmeter_rect_height, height * soundmeter_scale_perc, height)

        amps = self.am.get_amps()
        for bar in self.bars:
            bar.update(amps, self.dt, self.bar_min_height, self.bar_max_height)

        self.dt = min(self.clock.tick(self.fps) * 0.001, 0.066)

    def draw(self):
        self.window.fill(bluish_grey)

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
                border_radius=4,
            )
            self.play_pause_toggle.draw(self.window)
            pg.draw.rect(self.window, (0, 0, 0), self.play_pause_toggle.outline_rect, border_radius=4, width=2)

            pg.draw.rect(
                self.window,
                (35, 35, 35),
                (
                    self.skip_button.outline_rect[0] + 4,
                    self.skip_button.outline_rect[1] - 3,
                    self.skip_button.outline_rect[2],
                    self.skip_button.outline_rect[3],
                ),
                border_radius=4,
            )
            self.skip_button.draw(self.window)
            pg.draw.rect(self.window, (0, 0, 0), self.skip_button.outline_rect, border_radius=4, width=2)
            self.slider.draw(self.window)
            r = self.preview_img.get_rect()
            pg.draw.rect(
                self.window,
                (35, 35, 35),
                (
                    self.preview_pos[0] + 4,
                    self.preview_pos[1] - 3,
                    r[2],
                    r[3],
                ),
                border_radius=4,
            )
            self.window.blit(self.preview_img, self.preview_pos)
            pg.draw.rect(
                self.window,
                (160, 160, 160),
                (
                    self.preview_pos[0],
                    self.preview_pos[1],
                    r[2],
                    r[3],
                ),
                width=3,
                border_radius=4,
            )
            pg.draw.rect(
                self.window,
                (0, 0, 0),
                (
                    self.preview_pos[0],
                    self.preview_pos[1],
                    r[2],
                    r[3],
                ),
                width=2,
                border_radius=4,
            )
        # ---------------------------
        # pg.draw.circle(self.window, (0, 255, 0), pg.mouse.get_pos(), 50)
        for bar in self.bars:
            bar.draw(self.window, self.bar_width - self.bar_spacing)
        if len(self.files_queue) > 0:
            self.display_loading()
        pg.display.flip()

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
        self.am.terminate()
        pg.quit()
        sys.exit()


if __name__ == "__main__":
    # main()
    app = Application(
        "Assets/Fonts/PixCon.ttf",
        12,
        60,
        (gp.WIDTH, gp.HEIGHT),
        True,
        "Audio Visualizer",
        style=Styles.WhiteBars,
    )
    app.run()

import sys, threading, time, enum
import pygame as pg
import globals as gp
import m_platform as pf
from audio import AudioManager, AudioFile
from bar import Bar, SoundMeterBar
from utilities.Buttons import ToggleButtons, ButtonTemplate
import utilities.Slider as sl


ToggleTemplate = ButtonTemplate(
    (255, 255, 255), (240, 240, 240), (200, 200, 200), (180, 180, 180), 4, 4, 2, (240, 240, 240), 5, -1, None
)

slider_template = ButtonTemplate((0, 0, 0), (255, 165, 0), (200, 200, 200), (20, 20, 20), 2, 3, 2, (20, 20, 20), 5, -1, None)

bluish_grey = (14, 29, 39)

control_bar_upper_pos = 420
control_bar_lower_pos = 625
control_bar_height = 350

toggle_button_size = (60, 60)
toggle_button_pos = (540 - toggle_button_size[0] / 2, 702)

skip_button_size = (42, 42)
skip_button_pos = (603, 711)

prev_button_pos = (436, 711)

slider_pos = (108, 642)
slider_size = (864, 15)

preview_size = 110
lower_preview_scale = (27, 678)

white_bars_target_pos = 300
white_bars_upper_pos = 210
white_bars_scale_perc = 360

soundmeter_rect_height = 15
soundmeter_scale_perc = 480
soundmeter_bars_upper_pos = 412
soundmeter_bars_target_pos = 600


smoothing_speed = 5

song_info_summary_pos = (145, 672)


def time_format(time: int) -> str:
    t = int(time)

    return f"{t//60:02d}:{t%60:02d}"


def draw_expend_rect(rect: tuple, color, offset_x, offset_y, width, border_radius, surface: pg.Surface):
    """using this function to expend rect, thus avoiding long lines of code"""
    pg.draw.rect(surface, color, (rect[0] + offset_x, rect[1] + offset_y, rect[2], rect[3]), width, border_radius)


class Styles(enum.Enum):
    WhiteBars = "WhiteBars"
    MinimalistSoundMeter = "MinimalistSoundMeter"
    SoundMeter = "MinimalistSoundMeter"


class Application:
    HWIND = None
    TIMER_ID = None

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

        self.flags = 0
        self.resizable = resizable

        if self.resizable:
            self.flags |= pg.RESIZABLE
        pg.display.set_icon(pg.image.load("assets/images/icon32x32.png"))
        self.window = pg.display.set_mode(size, flags=self.flags)
        pg.display.set_caption(name)
        pf.init_resize_function(self.resize_win32)

        self.images = {
            AudioFile.PAUSED: pg.image.load("assets/images/play.png").convert_alpha(),
            AudioFile.PLAYING: pg.image.load("assets/images/pause.png").convert_alpha(),
            AudioManager.NEXT_AVAILABLE: pg.image.load("assets/images/skip_to_end.png").convert_alpha(),
            AudioManager.END_OF_LIST: pg.image.load("assets/images/grayed_skip.png").convert_alpha(),
            "NoImage": pg.image.load("assets/images/no_image.png"),
        }
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
        self.images[AudioManager.PREV_AVAILABLE] = pg.transform.flip(self.images[AudioManager.NEXT_AVAILABLE], True, False)
        self.images[AudioManager.START_OF_LIST] = pg.transform.flip(self.images[AudioManager.END_OF_LIST], True, False)

        self.min_size = min_size
        self.base_font_size = font_size
        self.scales = [self.width / gp.base_resolution[0], self.height / gp.base_resolution[1]]
        self.min_scale = min(self.scales)
        self.font_size = int(self.base_font_size * self.min_scale)
        self.font_path = font_path

        self.init_font(font_size, font_path)

        self.bar_min_height = int(self.height * 0.01)
        self.bar_max_height = self.height
        self.bar_width = None
        self.init_bars(style=self.style)
        self.calculate_pos(self.width, self.style, self.scales[0], self.scales[1], self.min_scale)

        self.play_pause_toggle = ToggleButtons(
            self.images,
            ToggleTemplate,
            toggle_button_size,
            toggle_button_pos,
            keys=[AudioFile.PAUSED, AudioFile.PLAYING],
            scale=0.5,
        )

        self.skip_button = ToggleButtons(
            self.images,
            ToggleTemplate,
            skip_button_size,
            skip_button_pos,
            keys=[AudioManager.END_OF_LIST, AudioManager.NEXT_AVAILABLE],
            current_key=self.am.get_next_button_state(),
            scale=0.5,
        )

        self.prev_button = ToggleButtons(
            self.images,
            ToggleTemplate,
            skip_button_size,
            prev_button_pos,
            keys=[AudioManager.START_OF_LIST, AudioManager.PREV_AVAILABLE],
            current_key=self.am.get_previous_button_state(),
            scale=0.5,
        )

        self.slider = sl.TimeSlider(slider_template, slider_pos, slider_size, self.small_font, time_format, [0, 1])
        self.show_control_bar = False
        self.show_settings_bar = False
        self.running = True
        self.rendered_text = {"title": None, "artist_name": None}

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

    def calculate_pos(self, width, style, scalex, scaley, min_scale):
        SoundMeterBar.calculate_class_dim(soundmeter_rect_height, soundmeter_scale_perc, self.height)
        self.rect_target_pos = (0, control_bar_upper_pos * scaley)
        self.rect_lower_pos = (0, control_bar_lower_pos * scaley)
        self.control_bar_rect = pg.Rect(
            self.rect_lower_pos[0],
            self.rect_lower_pos[1],
            width,
            control_bar_height,
        )
        resized_no_image = pg.transform.smoothscale(self.images["NoImage"], (50 * min_scale, 50 * min_scale))
        self.lower_preview_pos = (lower_preview_scale[0] * scalex, lower_preview_scale[1] * scaley)
        self.preview_pos = (lower_preview_scale[0] * scalex, lower_preview_scale[1] * scaley)

        Bar.scale = white_bars_scale_perc * min_scale
        self.preview_size = (min_scale * preview_size, min_scale * preview_size)

        white_surf = pg.Surface(self.preview_size, pg.SRCALPHA)
        pg.draw.rect(white_surf, (255, 255, 255), white_surf.get_rect(), border_radius=4)
        self.place_holder_preview = pg.Surface(self.preview_size, pg.SRCALPHA)
        self.place_holder_preview.fill((150, 150, 150))
        self.place_holder_preview.blit(white_surf, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
        center_pos = resized_no_image.get_rect(center=self.place_holder_preview.get_rect().center)
        self.place_holder_preview.blit(resized_no_image, center_pos)

        self.song_info_summary_surf = pg.Surface((270 * scalex, 120 * scaley), pg.HWSURFACE | pg.SRCALPHA)
        self.song_info_summary_surf.fill((0, 0, 0, 0))
        self.song_summ_pos = [song_info_summary_pos[0] * scalex, song_info_summary_pos[1] * scaley]

        preview_img = self.am.resize_preview(self.preview_size)
        if preview_img is not None:
            white_surf = pg.Surface(preview_img.get_size(), pg.SRCALPHA)
            pg.draw.rect(white_surf, (255, 255, 255), white_surf.get_rect(), border_radius=4)
            preview_img.blit(white_surf, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
            self.preview_img = preview_img
        else:
            self.preview_img = self.place_holder_preview

        if style == Styles.WhiteBars:
            self.target_bars_height = scaley * white_bars_target_pos
            self.upper_bars_height = scaley * white_bars_upper_pos
        else:
            self.upper_bars_height = scaley * soundmeter_bars_upper_pos
            self.target_bars_height = scaley * soundmeter_bars_target_pos

    def init_font(self, font_size, font_path: str):
        try:
            self.font = pg.font.Font(font_path, font_size)
            self.small_font = pg.font.Font(font_path, int(font_size * 0.8))
        except FileNotFoundError:
            self.font = pg.font.SysFont("Arial Black", size=font_size)
            self.small_font = pg.font.SysFont("Arial Black", int(font_size * 0.8))
        self.font.set_bold(True)
        self.small_font.set_bold(False)

    def resize_win32(self):
        new_size = (self.window.get_width(), self.window.get_height())
        if (self.width, self.height) != new_size:
            self.resize(new_size)
        self.draw()
        self.update()

    def resize(self, n_size):
        self.width, self.height = max(n_size[0], gp.MIN_WIDTH), max(n_size[1], gp.MIN_HEIGHT)
        if (self.width, self.height) != n_size:
            self.window = pg.display.set_mode((self.width, self.height), flags=self.flags)
        self.scales = [self.width / gp.base_resolution[0], self.height / gp.base_resolution[1]]
        self.min_scale = min(self.scales)
        self.calculate_pos(self.width, self.style, self.scales[0], self.scales[1], self.min_scale)
        self.font_size = int(self.base_font_size * self.min_scale)
        self.init_font(self.font_size, self.font_path)

        if not self.indexes:
            return
        self.bar_width = min(gp.min_bar_width, max(self.width / (len(self.indexes)), 2))

        offset = (self.width - self.bar_width * len(self.indexes)) // 2
        for i in range(len(self.bars)):
            self.bars[i].pos = (
                i * self.bar_width + offset + self.bar_spacing / 2,
                self.target_bars_height,
            )
        self.play_pause_toggle.resize(self.images, (self.scales[0], self.scales[1]), self.am.get_audio_state())
        self.skip_button.resize(self.images, (self.scales[0], self.scales[1]), self.am.get_next_button_state())
        self.prev_button.resize(self.images, (self.scales[0], self.scales[1]), self.am.get_previous_button_state())
        self.slider.resize((self.scales[0], self.scales[1]), self.small_font)

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
                pf.resize(
                    self.resize,
                    event.size,
                )

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
            self.skip_button.update(self.am.get_next_button_state())
            self.prev_button.update(self.am.get_previous_button_state())
            self.play_pause_toggle.update(self.am.get_audio_state())

        if self.skip_button.check_input():
            self.am.skip()
            self.skip_button.update(self.am.get_next_button_state())
            self.prev_button.update(self.am.get_previous_button_state())

        if self.prev_button.check_input():
            self.am.previous()
            self.skip_button.update(self.am.get_next_button_state())
            self.prev_button.update(self.am.get_previous_button_state())

    def update(self):
        self.play_pause_toggle.check_input()

        if self.am.update(self.preview_size) in (1, 0):
            update_dict = self.am.get_buttons_state()
            preview_img = update_dict["cover"]
            duration = update_dict["duration"]
            toggle_icon_key = update_dict["toggle"]
            next_icon_key = update_dict["next"]
            self.rendered_text["artist"] = update_dict["artist"]
            self.rendered_text["title"] = update_dict["title"]
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
        offset = 0
        if self.show_control_bar:
            slider_update_status = self.slider.update()
            self.am.set_timeline_update_status(slider_update_status)
            if slider_update_status[0]:
                self.am.set_pos(self.slider.output)
            offset = (self.control_bar_rect.top - self.rect_target_pos[1]) * self.dt * 6
            offset_bars = (self.bars[0].pos[1] - self.upper_bars_height) * self.dt * 7
        elif self.control_bar_rect.top <= self.rect_lower_pos[1] * 0.98:
            offset = (self.control_bar_rect.top - self.rect_lower_pos[1]) * self.dt * 6
            offset_bars = (self.bars[0].pos[1] - self.target_bars_height) * self.dt * 7
        if offset != 0:
            for bar in self.bars:
                bar.pos = (bar.pos[0], bar.pos[1] - offset_bars)
            self.control_bar_rect.top = self.control_bar_rect.top - offset
            self.play_pause_toggle.move_by(-offset)

            self.skip_button.move_by(-offset)

            self.prev_button.move_by(-offset)

            self.slider.move_by(-offset)

            self.preview_pos = (self.preview_pos[0], int(self.preview_pos[1] - offset))
            self.song_summ_pos[1] = int(self.song_summ_pos[1] - offset)
            if self.style == Styles.SoundMeter:
                height = self.height - (self.height - self.control_bar_rect.top)
                ratio = height / self.height
                SoundMeterBar.calculate_class_dim(ratio * soundmeter_rect_height, soundmeter_scale_perc * ratio, height)

        amps = self.am.get_amps()
        for bar in self.bars:
            bar.update(amps, self.dt, self.bar_min_height, self.bar_max_height)

        self.dt = min(self.clock.tick(self.fps) * 0.001, 0.066)

    def draw_button(self, button: ToggleButtons):
        draw_expend_rect(button.outline_rect, (35, 35, 35), 4, -3, 0, 4, self.window)
        button.draw(self.window)
        draw_expend_rect(button.outline_rect, (0, 0, 0), 0, 0, 2, 4, self.window)

    def draw(self):
        self.window.fill(bluish_grey)
        self.song_info_summary_surf.fill((0, 0, 0, 0))

        # drawing control bar----------------------------
        if self.control_bar_rect.top < self.height:
            draw_expend_rect(self.control_bar_rect, (15, 15, 15), 8, -4, 4, 4, self.window)
            pg.draw.rect(self.window, (200, 200, 200), self.control_bar_rect, border_radius=4)
            pg.draw.rect(self.window, (160, 160, 160), self.control_bar_rect, border_radius=4, width=6)
            draw_expend_rect(self.control_bar_rect, (15, 15, 15), 0, 0, 3, 4, self.window)  # control bar outline

            # DRAWING PLAY_PAUSE_BUTTON
            self.draw_button(self.play_pause_toggle)

            # DRAWING NEXT_BUTTON
            self.draw_button(self.skip_button)

            # DRAWING PREV_BUTTON
            self.draw_button(self.prev_button)

            self.slider.draw(self.window)

            # DRAWING PREVIEW IMAGE
            r = self.preview_img.get_rect(top=self.preview_pos[1], left=self.preview_pos[0])
            draw_expend_rect(r, (35, 35, 35), 4, -3, 0, 4, self.window)
            self.window.blit(self.preview_img, self.preview_pos)
            draw_expend_rect(r, (160, 160, 160), 0, 0, 3, 4, self.window)  # outline
            draw_expend_rect(r, (0, 0, 0), 0, 0, 2, 4, self.window)  # outline
        # ---------------------------

        for bar in self.bars:
            bar.draw(self.window, self.bar_width - self.bar_spacing)
        if len(self.files_queue) > 0:
            self.display_loading()
        title = self.font.render(self.rendered_text["title"], True, (0, 0, 0))
        artist = self.small_font.render(self.rendered_text["artist"], True, (0, 0, 0))
        self.song_info_summary_surf.blit(title, (5 * self.scales[0], 20 * self.scales[1]))
        self.song_info_summary_surf.blit(artist, (5 * self.scales[0], 45 * self.scales[1]))
        self.window.blit(self.song_info_summary_surf, self.song_summ_pos)
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
        "assets/fonts/PixCon.ttf",
        13,
        60,
        (gp.WIDTH, gp.HEIGHT),
        True,
        "Audio Visualizer",
        style=Styles.SoundMeter,
    )
    app.run()

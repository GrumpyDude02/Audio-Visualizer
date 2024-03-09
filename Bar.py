import pygame as pg
from pygame import gfxdraw
import globals as gp
import Tools.functions as fn
from math import ceil


class Bar:
    scale = 300
    smoothing_scale = 12
    smoothing_color_scale = 75

    def __init__(self, frequency_index: tuple, pos, original_color, target_color: tuple = (255, 255, 255)) -> None:
        self.pos = pos
        self.frequency_index = frequency_index
        self.height = 0
        self.original_color = original_color
        self.color = original_color
        self.target_color = target_color
        self.amplitude = 0

    def update(self, amps, dt, min_height, max_height):
        if len(amps[self.frequency_index["index_range"][0] : self.frequency_index["index_range"][1]]) == 0:
            self.amplitude = amps[self.frequency_index["index_range"][0]]
        else:
            self.amplitude = max(amps[self.frequency_index["index_range"][0] : self.frequency_index["index_range"][1]])
        self.amplitude = fn.clamp(0, 1, self.amplitude)
        target_height = int(self.amplitude * Bar.scale)

        self.color = fn.color_interpolation(self.original_color, self.target_color, 1 - (1 - self.amplitude) ** 0.3)
        self.height = fn.clamp(
            min_height, max_height, self.height + (target_height - self.height) * dt * Bar.smoothing_scale
        )

    def draw(self, window, width):
        rect = pg.Rect(self.pos[0], self.pos[1] - self.height // 2, width, self.height)
        pg.draw.rect(window, self.color, rect, border_radius=3)


class SoundMeterBar:
    scale = 0
    smoothing_scale = 0
    rect_height = 0
    rects_number = 0
    default_color_pallet = [(8, 126, 0), (127, 159, 8), (167, 147, 41), (182, 101, 0), (169, 1, 1)]
    color_pallet = default_color_pallet
    color_pallet_len = len(color_pallet)
    step = 0
    max_smooth_scale = 0.13

    @staticmethod
    def calculate_class_dim(rect_height, scale, window_height):
        SoundMeterBar.rect_height = rect_height
        SoundMeterBar.rects_number = round(window_height / rect_height)
        SoundMeterBar.scale = scale
        SoundMeterBar.step = len(SoundMeterBar.color_pallet) / (SoundMeterBar.scale / SoundMeterBar.rect_height)

    def __init__(self, frequency_index: tuple, pos) -> None:
        self.pos = pos
        self.frequency_index = frequency_index
        self.height = 0
        self.amplitude = 0
        self.rects = 1
        self.max = 0
        self.temp = 0

    def update(self, amps, dt, min_height, max_height):
        if len(amps[self.frequency_index["index_range"][0] : self.frequency_index["index_range"][1]]) == 0:
            self.amplitude = amps[self.frequency_index["index_range"][0]]
        else:
            self.amplitude = max(amps[self.frequency_index["index_range"][0] : self.frequency_index["index_range"][1]])
        self.amplitude = fn.clamp(0, 1, self.amplitude)
        target_height = int(self.amplitude * SoundMeterBar.scale)
        self.height = fn.clamp(
            min_height, max_height, self.height + (target_height - self.height) * dt * Bar.smoothing_scale
        )
        self.temp += (self.max - SoundMeterBar.rects_number) * dt * SoundMeterBar.max_smooth_scale
        if abs(self.temp) >= 1:
            self.max += self.temp
            self.temp = 0
        self.max = max(self.max, int(self.height / SoundMeterBar.rect_height) + 2)
        # self.max += (self.max - SoundMeterBar.rects_number) * dt * SoundMeterBar.max_smooth_scale
        self.rects = ceil(self.height / SoundMeterBar.rect_height)

    def draw(self, window, width):
        x = self.pos[0]
        y = self.pos[1] - (SoundMeterBar.rect_height * self.max)
        h = SoundMeterBar.rect_height - 1
        w = width
        for i in range(1, SoundMeterBar.rects_number):
            gfxdraw.box(
                window,
                (x, self.pos[1] - (SoundMeterBar.rect_height * i), w, h),
                (0, 0, 0),
            )
        if self.max > 2:

            gfxdraw.box(
                window,
                (x, y, w, h),
                (25, 25, 25),
            )
            gfxdraw.rectangle(
                window,
                (x, y, w, h),
                (0, 0, 0),
            )
        for i in range(1, self.rects + 1):
            index = min(int((i) * SoundMeterBar.step), SoundMeterBar.color_pallet_len - 1)
            color = SoundMeterBar.color_pallet[index]
            rect = (x, self.pos[1] - (SoundMeterBar.rect_height * i), w, h)
            gfxdraw.box(
                window,
                rect,
                color,
            )
            gfxdraw.rectangle(
                window,
                rect,
                (0, 0, 0),
            )

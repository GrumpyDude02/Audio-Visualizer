import pygame as pg
from pygame import gfxdraw
import globals as gp
import Tools.functions as fn


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

        self.color = fn.color_interpolation(self.original_color, self.target_color, 1 - (1 - self.amplitude) ** (0.85))
        self.height = fn.clamp(
            min_height, max_height, self.height + (target_height - self.height) * dt * Bar.smoothing_scale
        )

    def draw(self, window, width):
        rect = pg.Rect(self.pos[0], self.pos[1] - self.height // 2, width, self.height)
        pg.draw.rect(window, self.color, rect, border_radius=3)

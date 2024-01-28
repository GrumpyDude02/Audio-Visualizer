import pygame as pg
import globals as gp
import numpy as np


def linear(t):
    return 1 - (1 - t)


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


class Bar:
    scale = 300
    smoothing_scale = 12

    def __init__(self, frequency_index: tuple, pos, color) -> None:
        self.pos = pos
        self.frequency_index = frequency_index
        self.height = 0
        self.color = color
        self.amplitude = 0

    def update(self, amps, dt, min_height, max_height):
        if len(amps[self.frequency_index["index_range"][0] : self.frequency_index["index_range"][1]]) == 0:
            self.amplitude = amps[self.frequency_index["index_range"][0]]
        else:
            self.amplitude = max(amps[self.frequency_index["index_range"][0] : self.frequency_index["index_range"][1]])
        target_height = min(max_height, max(self.amplitude * Bar.scale, min_height))
        self.height = int(self.height + (target_height - self.height) * dt * Bar.smoothing_scale)
        # self.height = self.amplitude * Bar.scale

    def draw(self, window, width):
        rect1 = pg.Rect(self.pos[0], self.pos[1] - self.height // 2, width, self.height)
        pg.draw.rect(window, (255, 255, 255), rect1)

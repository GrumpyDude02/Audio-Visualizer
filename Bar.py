import pygame as pg
import globals as gp
import numpy as np


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


class Bar:
    scale = 600 * 1.1

    def __init__(self, frequency_index: tuple, pos, color) -> None:
        self.pos = pos
        self.frequency_index = frequency_index
        self.height = 0
        self.color = color
        self.amplitude = 0

    def update(self, amps, dt, min_height, max_height):
        self.amplitude = 0
        for a in amps[self.frequency_index["index_range"][0] : self.frequency_index["index_range"][1]]:
            self.amplitude += a
        self.amplitude /= len(amps[self.frequency_index["index_range"][0] : self.frequency_index["index_range"][1]])
        target_height = min(max_height, max(self.amplitude * Bar.scale, min_height))
        self.height = int(self.height + (target_height - self.height) * ease_out_cubic(min(dt * 15, 1)))

    def draw(self, window, width):
        rect1 = pg.Rect(self.pos[0], self.pos[1], width, self.height // 2)
        rect2 = pg.Rect(self.pos[0], self.pos[1] - self.height // 2, width, self.height // 2)
        outline1 = pg.Rect(self.pos[0], self.pos[1], width, self.height // 2)
        outline2 = pg.Rect(self.pos[0], self.pos[1] - self.height // 2, width, self.height // 2)
        pg.draw.rect(window, self.color, rect2)
        pg.draw.rect(window, (100, 0, 0), rect1)
        pg.draw.rect(window, (255, 255, 255), outline2, width=1)
        pg.draw.rect(window, (100, 100, 100), outline1, width=1)

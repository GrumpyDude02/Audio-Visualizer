import pygame as pg
import globals as gp
import numpy as np


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


class Bar:
    scale = 1200

    def __init__(self, frequency_indexes: tuple, pos, color) -> None:
        self.pos = pos
        self.frequency_indexes = frequency_indexes
        self.height = 0
        self.color = color
        self.amplitude = 0

    def update(self, amp, min_height, max_val, max_height, dt):
        self.amplitude = 0
        for a in amp[self.frequency_indexes[0] : self.frequency_indexes[1]]:
            self.amplitude += a
        self.amplitude /= len(amp[self.frequency_indexes[0] : self.frequency_indexes[1]])
        # target_height = min(max_height, max(scaled_height, min_height))
        # self.height = int(self.height + (target_height - self.height) * ease_out_cubic(min(dt * 5, 1)))
        self.height = self.amplitude * Bar.scale

    def draw(self, window, width):
        rect1 = pg.Rect(self.pos[0], self.pos[1], width, self.height // 2)
        rect2 = pg.Rect(self.pos[0], self.pos[1] - self.height // 2, width, self.height // 2)
        outline1 = pg.Rect(self.pos[0], self.pos[1], width, self.height // 2)
        outline2 = pg.Rect(self.pos[0], self.pos[1] - self.height // 2, width, self.height // 2)
        pg.draw.rect(window, self.color, rect1)
        pg.draw.rect(window, self.color, rect2)
        pg.draw.rect(window, (255, 255, 255), outline1, width=1)
        pg.draw.rect(window, (255, 255, 255), outline2, width=1)

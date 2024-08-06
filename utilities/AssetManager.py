import pygame as pg


class AssetMan:
    def __init__(self) -> None:
        self.fonts: pg.font.Font = {}
        self.images = {}
        self.sounds = {}

    def load_image(self, path: str, image_id: int | str, callback_function):
        self.images[image_id] = callback_function(pg.image.load(path))

    def load_font(self, path: str, font_id: int | str, size: int):
        try:
            if path is None:
                raise FileNotFoundError
            self.fonts[font_id] = pg.font.Font(filename=path, size=size)
        except FileNotFoundError:
            self.fonts[font_id] = pg.font.SysFont("Arial", size=size)

    def load_sounds(self):
        pass

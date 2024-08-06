base_resolution = (1080, 600)
min_val = 0
max_val = 2**16 - 1
fft_size = 4096
bands_number = 199
bar_color = (64, 79, 89)
start_frequency = 20
end_frequency = 20000
min_bar_width = 50
dtype = "int16"
WIDTH = 1080
HEIGHT = 600

MIN_WIDTH = 600
MIN_HEIGHT = 400

MAIN_FONT_ID = 0
SMALL_FONT_ID = 1


class SmartPosition:
    BASE_RESOLUTION = None  # must be initialized with the app (with the initialization of the function)

    def __init__(self, coordinates) -> None:
        self.original_x = coordinates[0]
        self.original_y = coordinates[1]
        self.coord = [self.original_x, self.original_y]

    def recalculate(self, scale_x, scale_y):
        self.coord[0] = self.original_x * scale_x
        self.coord[1] = self.original_y * scale_y

    def __getitem__(self, index):
        return self.coord[index]

    @property
    def x(self):
        return self.coord[0]

    @property
    def y(self):
        return self.coord[1]


class PositionRange:
    def __init__(self, start_pos: SmartPosition, end_pos: SmartPosition):
        self.start_pos = start_pos
        self.end_pos = end_pos

    def recalculate(self, scale_x, scale_y):
        self.start_pos.recalculate(scale_x, scale_y)
        self.end_pos.recalculate(scale_x, scale_y)


class ElementConfig:
    def __init__(self, start_pos: tuple[int | float], end_pos: tuple[int | float], size: tuple[int]) -> None:
        pass


TOGGLE_BUTTON_SIZE = (60, 60)
TOGGLE_BUTTON_POS = (540 - TOGGLE_BUTTON_SIZE[0] / 2, 702)

NEXT_BUTTON_SIZE = (42, 42)
NEXT_BUTTON_POS = (603, 711)

PREV_BUTTON_POS = (436, 711)

SLIDER_POS = (108, 642)
SLIDER_SIZE = (864, 15)

CONTROL_BAR_START_POS = (0, 625)
CONTROL_BAR_END_POS = (0, 420)

SOUND_METER_START_POS = (0, 412)
SOUND_METER_END_POS = (0, 600)

BARS_START_POS = (0, 300)
BARS_END_POS = (0, 210)

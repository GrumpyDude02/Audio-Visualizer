from dataclasses import dataclass


@dataclass
class UITemplate:
    text_color: tuple
    bg_color: tuple
    hover_color: tuple
    outline_color: tuple
    border_radius: int
    outline_size: int
    outline_radius: int
    slider_bar_color: tuple
    slider_bar_width: int
    slider_bar_radius: int
    secondary_color: tuple = None


DefaultTemplate = UITemplate((255, 255, 255), (0, 0, 0), (0, 50, 200), (255, 255, 255), -1, 4, -1, (96, 96, 96), 5, -1, None)

from utilities.AssetManager import AssetMan
from .UIElements import UIElement


class UIState:
    asset_man: AssetMan = None
    mouse_x: int = -1
    mouse_y: int = -1
    left_mouse_down: bool = False
    right_mouse_down: bool = False
    middle_mouse_down: bool = False

    hot_item: UIElement = None
    active_item: UIElement = None
    captured_keys: list = []

    @staticmethod
    def init(AssetManager):
        UIState.asset_man = AssetManager

    @staticmethod
    def update(mouse_down: bool, mouse_coord: tuple[int], captured_keys):
        UIState.left_mouse_down = mouse_down[0]
        UIState.middle_mouse_down = mouse_down[1]
        UIState.right_mouse_down = mouse_down[2]
        UIState.mouse_x = mouse_coord[0]
        UIState.mouse_y = mouse_coord[1]
        UIState.captured_keys = captured_keys

from .UIElements import UIElement
from .UITemplates import UITemplate
import UI.Buttons as Buttons
import UI.Sliders as Sliders
from .UIMan import UIState
import pygame


class UIContainerRect(UIElement):

    element_types = {
        "button": Buttons.Button,
        "image_button": Buttons.ImageButton,
        "text_button": Buttons.TextButton,
        "slider": Sliders.Slider,
        "time_slider": Sliders.TimeSlider,
        "value_slider": Sliders.ValueSlider,
    }

    @classmethod
    def register_type(cls, element_type_name, element_type_constructor):
        cls.element_types[element_type_name] = element_type_constructor

    def __init__(
        self,
        layer,
        template: UITemplate,
        size: list,
        position: list,
        container_size: list,
        asset_ids: list = None,
    ) -> None:
        super().__init__(layer, template, size, position, container_size, asset_ids)
        self.type = type
        self.rectangle = pygame.Rect(
            position[0] * container_size[0],
            position[1] * container_size[1],
            size[0] * container_size[0],
            size[1] * container_size[1],
        )
        self.children: dict[str | int, UIElement] = {}
        self.child_containers: dict[str | int, UIContainerRect] = {}

    def add_child_container(self, container_name, **kwargs):
        self.child_containers[container_name] = UIContainerRect(**kwargs)

    def add_child(self, element_name: str, element: UIElement = None, element_type: str = None, **kwargs):
        if element:
            self.children[element_name] = element
            return
        constructor = UIContainerRect.element_types.get(element_type)
        if constructor is None:
            raise TypeError("Unsupported type")
        self.children[element_name] = constructor(**kwargs)

    def handle_event(self):
        if not self.rectangle.collidepoint((UIState.mouse_x, UIState.mouse_y)):
            return None
        for container in self.child_containers.values():
            output = container.handle_event()
            if output is not None:
                return output
        return {key: value.handle_event() for key, value in self.children.items()}

    def resize(self, sc_size):
        self.rectangle = pygame.Rect(
            self.position[0] * sc_size[0],
            self.position[1] * sc_size[1],
            self.size[0] * sc_size[0],
            self.size[1] * sc_size[1],
        )
        for child in self.children.values():
            child.resize(sc_size)

    def draw(self, screen):
        for child in self.children.values():
            child.draw(screen)

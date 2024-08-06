from UI.UITemplates import UITemplate
import pygame


class UIElement:

    def __init__(
        self,
        layer,
        template: UITemplate,
        size: list,
        position: list,
        container_size: list,
        asset_ids: list = None,
        position_type: str = "absolute",
    ) -> None:
        self.layer = layer
        self.position = position
        self.position_type = position_type
        self.size = size
        self.template = template
        self.asset_ids = asset_ids

    def resize(self, new_container_size):
        self.rectangle = pygame.Rect(
            self.position[0] * new_container_size[0],
            self.position[1] * new_container_size[1],
            self.size[0] * new_container_size[0],
            self.size[1] * new_container_size[1],
        )
        self.outline_rect = (
            pygame.Rect(
                self.rectangle.left - self.template.outline_size,
                self.rectangle.top - self.template.outline_size,
                self.rectangle.width + self.template.outline_size * 2,
                self.rectangle.height + self.template.outline_size * 2,
            )
            if self.template.outline_size > 0
            else None
        )

    def handle_event(self):
        return None

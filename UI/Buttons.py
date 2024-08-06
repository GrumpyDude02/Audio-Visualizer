import pygame, pygame.gfxdraw
from .UIElements import UIElement, UITemplate
from .UIMan import UIState


class Button(UIElement):
    IDLE = "IDLE"
    ARMED = "ARMED"
    HOVER = "HOVER"

    def __init__(
        self,
        template: UITemplate,
        size: list,
        position: list,
        container_sc_size: list,
        Next: list = None,
        layer: int = 0,
        position_type: str = "absolute",
        asset_ids: list = None,
    ) -> None:
        super().__init__(
            layer, template, size, position, container_sc_size, position_type=position_type, asset_ids=asset_ids
        )
        self.color = self.template.bg_color
        self.next_Button = Next
        self.state = Button.IDLE
        self.resize(container_sc_size)

    def move_cursor(self, cursor):
        mouse_pos = pygame.mouse.get_pos()
        if self.rectangle.collidepoint(mouse_pos):
            cursor.move_to(button=self)
            self.color = self.template.hover_color
        else:
            self.color = self.template.bg_color

    def handle_event(self, mouse_mode: bool = True):
        if not mouse_mode:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_RETURN]:
                self.state = Button.ARMED
            elif self.state == Button.ARMED:
                self.state = Button.IDLE
                return True
            return False
        else:
            mouse_pos = pygame.mouse.get_pos()
            if self.rectangle.collidepoint(mouse_pos):
                UIState.hot_item = self
                self.color = self.template.hover_color
                if pygame.mouse.get_pressed()[0]:
                    if UIState.active_item is None or UIState.active_item == self:
                        self.state = Button.ARMED
                        UIState.active_item = self
                elif self.state == Button.ARMED and UIState.active_item == self:
                    self.state = Button.IDLE
                    UIState.active_item = None
                    return True
            else:
                self.color = self.template.bg_color
                if UIState.active_item == self:
                    if not pygame.mouse.get_pressed()[0]:
                        UIState.active_item = None
                if UIState.hot_item == self:
                    UIState.hot_item = None
            return False

    def draw(self, screen):
        if self.outline_rect:
            pygame.draw.rect(
                screen, self.template.outline_color, self.outline_rect, border_radius=self.template.outline_radius
            )
        pygame.draw.rect(screen, self.color, self.rectangle, border_radius=self.template.border_radius)

    def get_attributes(self):
        return (self.rectangle.center, (self.rectangle.width, self.rectangle.height))

    def move_by(self, offset):
        self.rectangle.top += offset
        self.outline_rect.top += offset


class ImageButton(Button):

    def __init__(
        self,
        template: UITemplate,
        size: list,
        position: list,
        container_sc_size: list,
        Next: list = None,
        layer: int = 0,
        position_type: str = "absolute",
        asset_ids: list = None,
        scale: float = None,
    ) -> None:
        self.current_key = None
        self.image_list = {}
        self.scale = scale
        super().__init__(
            template,
            size,
            position,
            container_sc_size,
            asset_ids=asset_ids,
            Next=Next,
            layer=layer,
            position_type=position_type,
        )
        self.resize(container_sc_size)

    def resize(self, sc_size: tuple):
        super().resize(sc_size)
        if self.scale is None:
            self.image_list = UIState.asset_man.images
        else:
            target_size = (sc_size[1] * self.size[1] * self.scale, sc_size[1] * self.size[1] * self.scale)
            for k in self.asset_ids:
                original_size = UIState.asset_man[k].get_size()
                scaling_factor = min(target_size[0] / original_size[0], target_size[1] / original_size[1])
                self.image_list[k] = pygame.transform.smoothscale(
                    UIState.asset_man[k], (original_size[0] * scaling_factor, original_size[1] * scaling_factor)
                )
        if self.current_key is None:
            self.current_image = self.image_list[self.keys[-1]]
        else:
            self.update(self.current_key)

    def update(self, new_key):
        self.current_key = new_key
        val = self.image_list.get(new_key)
        self.current_image = self.current_image if val is None else val

    def draw(self, screen: pygame.Surface):
        super().draw(screen)
        screen.blit(self.current_image, self.current_image.get_rect(center=self.rectangle.center))


class TextButton(Button):

    def __init__(
        self,
        template: UITemplate,
        size: list,
        position: list,
        container_sc_size: list,
        text: str = "",
        Next: list = None,
        layer: int = 0,
        position_type: str = "absolute",
        asset_ids: list = None,
    ) -> None:
        self.text = text
        super().__init__(
            template,
            size,
            position,
            container_sc_size,
            Next,
            layer,
            position_type,
            asset_ids,
        )
        self.resize(container_sc_size)

    def resize(self, sc_size: tuple):
        super().resize(sc_size)
        self.tex_surf = UIState.asset_man.fonts[self.asset_ids[0]].render(self.text, True, self.template.text_color)
        self.text_rect = self.tex_surf.get_rect(center=self.rectangle.center)

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        surface.blit(self.tex_surf, self.text_rect)


class Arrow(Button):

    def __init__(self, direction: str, template: UITemplate, size: list, pos: list, sc_size: list = (1, 1)):
        super().__init__(template, size, pos, sc_size)
        self.direction = direction
        self.set_vertecies(sc_size[0], sc_size[1])

    def set_vertecies(self, width, height) -> None:
        x = self.pos[0]
        y = self.pos[1]
        size = self.size
        offset = 6
        self.vertecies = []
        if self.direction == "left":
            self.vertecies = [
                (round((x) * width + offset), round((y + size[1] / 2) * height)),
                (round((x + size[0]) * width - offset), round(y * height + offset)),
                (round((x + size[0]) * width - offset), round((y + size[1]) * height - offset)),
            ]
        elif self.direction == "right":
            self.vertecies = [
                (round((x) * width + offset), round(y * height + offset)),
                (round((x + size[0]) * width - offset), round((y + size[1] / 2) * height)),
                (round(x * width + offset), round((y + size[1]) * height - offset)),
            ]
        else:
            raise Exception("Direction must be str and either top, bottom, left or right")
        self.rectangle = pygame.Rect(
            self.pos[0] * width,
            self.pos[1] * height,
            self.size[0] * width,
            self.size[1] * height,
        )

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        pygame.gfxdraw.aapolygon(surface, self.vertecies, self.template.outline_color)
        pygame.draw.polygon(surface, self.template.outline_color, self.vertecies)

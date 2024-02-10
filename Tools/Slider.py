import pygame
from Tools.Buttons import Buttons, ButtonTemplate, DefaultTemplate
import Tools.functions as func


class Slider:
    ARMED = "ARMED"
    HOVER = "HOVER"
    IDLE = "IDLE"

    def __init__(
        self,
        template: ButtonTemplate,
        position: tuple,
        size: tuple,
        slide_range: tuple = None,
        sc_size: tuple = (1, 1),
        rounding: bool = False,
    ) -> None:
        self.position = position
        self.template = template
        self.size = size
        self.state = Slider.IDLE
        self.range = slide_range
        # self.output = self.range[0]
        self.round = rounding
        self.button_color = self.template.bg_color
        self.set_size(sc_size)
        self.prev_pos = (0, 0)

    def set_size(self, sc_size):
        # self.rendered_text = font.render(self.text, True, self.template.text_color)
        self.rectangle_bar = pygame.Rect(
            self.position[0] * sc_size[0],
            self.position[1] * sc_size[1],
            self.size[0] * sc_size[0],
            self.size[1] * sc_size[1],
        )
        button_size = (max(self.rectangle_bar.width * 0.04, 10), max(self.rectangle_bar.height * 1.5, 30))

        button_position = (
            self.rectangle_bar.left - self.rectangle_bar.width * 0.04 / 2,
            self.rectangle_bar.centery - self.rectangle_bar.height * 1.5 / 2 - 1,
        )
        self.button_rect = pygame.Rect(button_position, button_size)

        self.button_outline = (
            pygame.Rect(
                self.button_rect.left - self.template.outline_size,
                self.button_rect.top - self.template.outline_size,
                self.button_rect.width + self.template.outline_size * 2,
                self.button_rect.height + self.template.outline_size * 2,
            )
            if self.template.outline_size > 0
            else None
        )

    def update(self):
        """(updated,pressed)"""
        updated = False
        pressed = False
        mouse_pressed = pygame.mouse.get_pressed()[0]
        mouse_pos = pygame.mouse.get_pos()
        self.button_color = self.template.bg_color
        collision = self.button_rect.collidepoint(mouse_pos) or self.rectangle_bar.collidepoint(mouse_pos)

        if not self.state == Slider.ARMED and collision:
            self.state = Slider.HOVER
            self.button_color = self.template.hover_color
            if mouse_pressed:
                self.state = Slider.ARMED
                pressed = True
                return (updated, pressed)

        if not mouse_pressed:
            self.state = Slider.IDLE
            return (updated, pressed)

        if self.state == Slider.ARMED:
            pressed = True
            self.button_color = self.template.hover_color
            self.button_rect.centerx = max(
                self.rectangle_bar.left,
                min(mouse_pos[0], self.rectangle_bar.width + self.rectangle_bar.left),
            )
            self.output = func.map_values(
                self.button_rect.centerx,
                (self.rectangle_bar.left, self.rectangle_bar.left + self.rectangle_bar.width),
                self.range,
            )
            if self.round:
                self.button_rect.centerx = func.map_values(
                    self.output,
                    self.range,
                    (self.rectangle_bar.left, self.rectangle_bar.left + self.rectangle_bar.width),
                )
            self.button_outline.center = self.button_rect.center
            if self.prev_pos[0] != mouse_pos[0]:
                updated = True
            self.prev_pos = mouse_pos
        return (updated, pressed)

    def set_output(self, value):
        self.output = int(value)
        self.button_rect.centerx = func.map_values(
            self.output,
            self.range,
            (self.rectangle_bar.left, self.rectangle_bar.left + self.rectangle_bar.width),
        )
        self.button_outline.center = self.button_rect.center

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(
            surface,
            self.template.slider_bar_color,
            self.rectangle_bar,
            self.template.slider_bar_width,
            border_radius=self.template.slider_bar_radius,
        )
        if self.button_outline:
            pygame.draw.rect(
                surface,
                self.template.outline_color,
                self.button_outline,
                border_radius=self.template.outline_radius,
                width=self.template.outline_size,
            )
        pygame.draw.rect(surface, self.button_color, self.button_rect, border_radius=self.template.border_radius)
        # surface.blit(
        #     output,
        #     (self.rectangle_bar.left + self.rectangle_bar.width + 10, cy),
        # )
        # surface.blit(
        #     self.rendered_text,
        #     self.text_position,
        # )


class ValueSlider(Slider):

    def __init__(
        self,
        template: ButtonTemplate,
        position: tuple,
        size: tuple,
        font: pygame.font.Font,
        text: str,
        slide_range: tuple,
        sc_size: tuple = (1, 1),
        rounding: bool = False,
    ) -> None:
        super().__init__(template, position, size, slide_range, sc_size, rounding)
        self.range = slide_range
        self.output = self.range[0]
        self.text = text
        self.resize(sc_size, font)  # Pass the font argument here

    def resize(self, sc_size, font: pygame.font.Font):
        self.rendered_text = font.render(self.text, True, self.template.text_color)
        self.font = font
        super().set_size(sc_size)
        self.text_position = (
            self.position[0] * sc_size[0] - self.rendered_text.get_width() - 40,
            self.position[1] * sc_size[1],
        )

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        output = self.font.render(str(self.output), self.template.text_color, True)
        cy = output.get_rect(center=self.rectangle_bar.center).y
        surface.blit(
            output,
            (self.rectangle_bar.left + self.rectangle_bar.width + 10, cy),
        )
        surface.blit(
            self.rendered_text,
            self.text_position,
        )


class TimeSlider(Slider):
    def __init__(
        self,
        template: ButtonTemplate,
        position: tuple,
        size: tuple,
        font: pygame.font,
        format_function,
        time_range: tuple = None,
        sc_size: tuple = (1, 1),
        rounding: bool = False,
    ) -> None:
        super().__init__(template, position, size, time_range, sc_size, rounding)
        self.range = time_range
        self.output = 0 if self.range is None else self.range[0]
        self.format_function = format_function
        self.resize(sc_size, font)

    def resize(self, sc_size, font: pygame.font.Font):
        self.font = font
        self.set_range(self.range)
        super().set_size(sc_size)

    def set_range(self, time_range: tuple | list):
        self.range = time_range
        self.step = self.rectangle_bar.width / self.range[1]

    def update_elapsed_time(self, time):
        if time is None:
            return
        self.output = time
        self.button_rect.centerx = self.rectangle_bar.left + time * self.step
        if self.button_outline is not None:
            self.button_outline.centerx = self.button_rect.centerx

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(
            surface,
            self.template.bg_color,
            (
                self.rectangle_bar.left,
                self.rectangle_bar.top,
                self.button_rect.x - self.rectangle_bar.x,
                self.rectangle_bar.height,
            ),
        )
        super().draw(surface)
        max_time = self.font.render(self.format_function(self.range[-1]), True, color=self.template.text_color)
        elapsed_time = self.font.render(self.format_function(self.output), True, color=self.template.text_color)

        max_time_rect = max_time.get_rect(center=self.rectangle_bar.center)
        elapsed_time_rect = elapsed_time.get_rect(center=self.rectangle_bar.center)

        surface.blit(
            elapsed_time, (self.rectangle_bar.x - elapsed_time_rect.width - self.button_rect.width, elapsed_time_rect.y + 1)
        )
        surface.blit(max_time, (self.rectangle_bar.x + self.rectangle_bar.width + self.button_rect.w, max_time_rect.y))

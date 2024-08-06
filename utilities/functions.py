import random, pygame


def mod(m, n) -> int:
    return (m % n + n) % n


def clamp(minimum, maximum, value):
    return max(minimum, min(value, maximum))


def exclude(dictionary, exception: str) -> str:
    temp = [key for key in dictionary.keys() if key != exception]
    return random.choice(temp)


# found on https://www.akeric.com/blog/?p=720
def blurSurf(surface, amt):
    if amt < 1.0:
        raise ValueError("Arg 'amt' must be greater than 1.0, passed in value is %s" % amt)
    scale = 1.0 / float(amt)
    surf_size = surface.get_size()
    scale_size = (int(surf_size[0] * scale), int(surf_size[1] * scale))
    surf = pygame.transform.smoothscale(surface, scale_size)
    surf = pygame.transform.smoothscale(surf, surf_size)
    return surf


def fill(surface: pygame.Surface, color):
    """Fill all pixels of the surface with color, preserve transparency."""
    w, h = surface.get_size()
    r, g, b, _ = color
    for x in range(w):
        for y in range(h):
            a = surface.get_at((x, y))[3]
            surface.set_at((x, y), pygame.Color(r, g, b, a))


def generate_surf(surf_size: tuple, transparency_amount: int = None, color_key: tuple = None) -> pygame.Surface:
    try:
        surface = pygame.Surface(surf_size, pygame.HWACCEL)
    except pygame.error:
        surface = pygame.Surface(surf_size)
    if color_key is not None:
        surface.set_colorkey(color_key)
    if transparency_amount is not None:
        surface.set_alpha(transparency_amount)
    return surface


def draw_rects(window: pygame.Surface, grid: list[pygame.Rect], color) -> None:
    for rect in grid:
        pygame.draw.rect(window, color, rect)


def map_values(value: float, input_range: tuple[float], output_range: tuple[float]):
    return ((value - input_range[0]) / (input_range[1] - input_range[0])) * (
        output_range[1] - output_range[0]
    ) + output_range[0]


def color_interpolation(c1: tuple, c2: tuple, t):
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def linear(t):
    return 1 - (1 - t)


def ease_out_square(t):
    return 1 - (1 - t) ** 2


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def rounded_image_surf(image: pygame.Surface, color: tuple[3], image_size: tuple[2], border_radius: int):
    white_surf = pygame.Surface(image_size, pygame.SRCALPHA)
    pygame.draw.rect(white_surf, (255, 255, 255), white_surf.get_rect(), border_radius=border_radius)
    target_surface = pygame.Surface(image_size, pygame.SRCALPHA)
    target_surface.fill(color)
    target_surface.blit(white_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    center_pos = image.get_rect(center=target_surface.get_rect().center)
    target_surface.blit(image, center_pos)
    return target_surface

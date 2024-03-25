import pygame
import win32gui
from threading import Thread

GAME_WIDTH, GAME_HEIGHT = 750, 250


class Rect:
    def __init__(self, size, position):
        self.size = size
        self.position = position
        self.rect = pygame.Rect(position, (size, size))
        self.speed = 5

    def update(self):
        self.rect.x += self.speed
        if self.rect.x < 5 or self.rect.x > GAME_WIDTH - self.size - 5:
            self.speed *= -1

    def draw(self, screen):
        pygame.draw.rect(screen, "red", self.rect)


def window_continue(hwnd):
    message = win32gui.GetMessage(hwnd, 0, 0)
    # print(message)
    if message[0] != 0:
        win32gui.TranslateMessage(message[1])
        win32gui.DispatchMessage(message[1])
    # elif message[0] == -1: #handle exit? TODO


def handle_events():
    for event in pygame.event.get():
        if event.type in [pygame.QUIT] or event.type in [pygame.KEYDOWN] and event.key in [pygame.K_ESCAPE]:
            pygame.quit()
            raise SystemExit


def init(screen):
    rect = Rect(20, (150, 150))
    Thread(target=lambda: draw(screen, [rect]), daemon=True).start()


def draw(screen, game_objects):
    clock = pygame.time.Clock()
    while True:
        clock.tick(60)
        screen.fill("black")
        [(game_object.update(), game_object.draw(screen)) for game_object in game_objects]
        pygame.display.flip()


def run():
    hwnd = pygame.display.get_wm_info()["window"]
    # while GetMessage != 0 instead of True? TODO
    while True:
        window_continue(hwnd)
        handle_events()


def main():
    pygame.init()
    init(pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT), flags=pygame.RESIZABLE))

    run()


if __name__ == "__main__":
    main()

import pygame
class InputState:
    captured_element = None  # Stores which element has mouse capture
    
    @classmethod
    def capture_mouse(cls, element):
        if cls.captured_element is None:
            cls.captured_element = element
    
    @classmethod
    def release_mouse(cls, element):
        if cls.captured_element == element:
            cls.captured_element = None
    
    @classmethod
    def is_captured_by_other(cls, element):
        return cls.captured_element is not None and cls.captured_element != element
    
def clear_input_capture():
    # Auto-release if mouse is not pressed
    if not pygame.mouse.get_pressed()[0]:
        InputState.captured_element = None
"""
Minimal pygame compatibility shim for Kivy.
Provides enough pygame APIs to make grid.py and engine.py work.
"""
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.graphics.texture import Texture


class _DummyModule:
    """Dummy module for pygame features we don't use."""
    pass


# Create dummy sub-modules
display = _DummyModule()
font = _DummyModule()
mixer = _DummyModule()


class Rect:
    """Minimal Rect implementation."""
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        self.left = x
        self.top = y
        self.right = x + w
        self.bottom = y + h
        self.centerx = x + w // 2
        self.centery = y + h // 2
        self.center = (self.centerx, self.centery)
    
    def inflate(self, dx, dy):
        """Return a new rect with size adjusted."""
        return Rect(self.x - dx // 2, self.y - dy // 2, 
                    self.width + dx, self.height + dy)


class Surface:
    """Dummy Surface - we don't actually use it in Kivy."""
    def __init__(self, size):
        self.width, self.height = size
    
    def get_width(self):
        return self.width
    
    def get_height(self):
        return self.height
    
    def get_size(self):
        return (self.width, self.height)
    
    def subsurface(self, rect):
        """Return a dummy subsurface."""
        return Surface((rect.width, rect.height))
    
    def convert_alpha(self):
        return self
    
    def blit(self, source, dest):
        """Dummy blit - ignored."""
        pass


class _ImageModule:
    """Minimal image module."""
    @staticmethod
    def load(path):
        """Load returns a dummy surface."""
        try:
            # Try to load with Kivy to get dimensions
            img = CoreImage(path)
            return Surface((img.width, img.height))
        except:
            # Fallback to dummy
            return Surface((32, 32))


class _TransformModule:
    """Minimal transform module."""
    @staticmethod
    def scale(surface, size):
        """Return a surface with new size."""
        return Surface(size)


class _TimeModule:
    """Time module using Kivy Clock."""
    @staticmethod
    def get_ticks():
        """Return milliseconds since start."""
        return int(Clock.get_time() * 1000)


class _DrawModule:
    """Dummy draw module - all graphics go through Kivy Canvas now."""
    @staticmethod
    def rect(surface, color, rect, width=0, border_radius=0):
        pass
    
    @staticmethod
    def circle(surface, color, center, radius, width=0):
        pass
    
    @staticmethod
    def polygon(surface, color, points):
        pass
    
    @staticmethod
    def ellipse(surface, color, rect, width=0):
        pass
    
    @staticmethod
    def line(surface, color, start_pos, end_pos, width=1):
        pass


# Module-level objects
image = _ImageModule()
transform = _TransformModule()
time = _TimeModule()
draw = _DrawModule()


def init():
    """Dummy init."""
    pass

"""
Kivy-adapted version of Boulderflash for Android.
Minimal wrapper around existing game logic.
"""
import os
import sys

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Kivy-compatible Pygame Shim
# Kivy-compatible Pygame Shim
class PygameShim:
    class Rect:
        def __init__(self, x=0, y=0, w=0, h=0):
            self.x, self.y, self.w, self.h = x, y, w, h
            self.width, self.height = w, h
        def colliderect(self, other):
            return self.x < other.x + other.w and self.x + self.w > other.x and \
                   self.y < other.y + other.h and self.y + self.h > other.y
    class time:
        @staticmethod
        def get_ticks():
            from kivy.clock import Clock
            return int(Clock.get_time() * 1000)
    class font:
        class SysFont:
            def __init__(self, *args, **kwargs): pass
            def render(self, *args, **kwargs): return None
    class Surface:
        def __init__(self, texture=None, size=(0,0)):
            self.texture = texture
            self.width, self.height = size if texture is None else texture.size
        def convert_alpha(self): return self
        def convert(self): return self
        def get_width(self): return self.width
        def get_height(self): return self.height
        def subsurface(self, rect): return self # Todo if needed
        
    class image:
        @staticmethod
        def load(path):
            from kivy.core.image import Image as CoreImage
            try:
                # remove ./ if present as it might confuse Kivy loader sometimes?
                # actually CoreImage handles paths fairly well.
                img = CoreImage(path)
                return PygameShim.Surface(img.texture)
            except Exception as e:
                print(f"Shim: Failed to load {path}: {e}")
                return PygameShim.Surface()
                
    class transform:
        @staticmethod
        def scale(s, size):
            # We can't easily rescale a texture in Kivy without rendering it.
            # But we can just pretend surface has new size, or return same surface.
            # Grid uses scale for explosion frames.
            # Let's return a new surface with same texture but updated 'size' attribute if we used it?
            # actually grid just stores them. Rendering will determine size.
            return s # Pass-through for now
        @staticmethod
        def flip(s, x, y): return s # Texture flipping handled at render time


sys.modules['pygame'] = PygameShim
import pygame

# Kivy imports
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Ellipse, Line, PushMatrix, PopMatrix, Scale, Translate
from kivy.core.window import Window
from kivy.core.text import Label as CoreLabel

# Game imports
from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HUD_WIDTH, TILE_SIZE, FPS,
    COLOR_BG, COLOR_HACKER, COLOR_DATA, COLOR_WALL, COLOR_FIREWALL,
    COLOR_EMPTY, COLOR_KEY, COLOR_EXIT, COLOR_PREDATOR, COLOR_BUILDER,
    COLOR_GRAVITY, COLOR_BOMB, COLOR_TELEPORTER, COLOR_PILLAR, COLOR_SLUDGE,
    EMPTY, DATA, WALL, FIREWALL, KEY, EXIT, PLAYER, PREDATOR, BUILDER,
    GRAVITY_ZONE, BOMB, TELEPORTER, PILLAR, SLUDGE
)
from grid import Grid
from engine import Engine
from levels import LEVELS
import scores

# Detect Android
IS_ANDROID = "ANDROID_ARGUMENT" in os.environ or "ANDROID_ENTRYPOINT" in os.environ


class GameWidget(Widget):
    """Main game widget handling all game logic and rendering."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize game state (same as pygame version)
        self.grid = Grid(1, 1)
        self.engine = Engine(self.grid)
        self.player_x = 0
        self.player_y = 0
        self.keys_collected = 0
        self.required_keys = 1
        self.bombs_count = 0
        self.pillars_count = 0
        self.game_over = False
        self.won = False
        self.showing_legend = True
        self.lives = 3
        self.player_name = ""
        self.entering_name = False
        self.showing_hof = False
        self.viewing_online = False
        self.high_scores = scores.get_top_scores(online=self.viewing_online)
        self.crush_time = 0
        self.showing_quit_confirm = False
        
        # Animation state
        self.anim_state = "idle"
        self.anim_frame = 0
        self.anim_speed = 0.15  # seconds per frame
        self.last_anim_update = 0
        self.last_move_time = 0
        self.facing_left = False
        
        # Victory/death animation
        self.victory_zoom = 1.0
        self.victory_start_time = 0
        self.death_zoom = 1.0
        self.death_start_time = 0
        
        # Load first level
        self.current_level_index = 0
        self.load_level(self.current_level_index)
        
        # Virtual controls for mobile
        self.is_mobile = IS_ANDROID or True  # Force True for testing
        self.touch_controls = {
            "up": (110, 210, 80, 80),       # x, y_from_bottom, w, h
            "down": (110, 90, 80, 80),
            "left": (20, 150, 80, 80),
            "right": (200, 150, 80, 80),
            "bomb": (SCREEN_WIDTH - HUD_WIDTH - 180, 180, 80, 80),
            "pillar": (SCREEN_WIDTH - HUD_WIDTH - 90, 180, 80, 80),
        }
        
        # Keyboard state
        self.keys_pressed = set()
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_up=self.on_key_up)
        
        # Schedule game update loop
        Clock.schedule_interval(self.update, 1.0 / FPS)
        
        # Request keyboard
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        self._keyboard.bind(on_key_up=self._on_keyboard_up)
    
    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard.unbind(on_key_up=self._on_keyboard_up)
        self._keyboard = None
    
    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        self.keys_pressed.add(keycode[1])
        return True
    
    def _on_keyboard_up(self, keyboard, keycode):
        self.keys_pressed.discard(keycode[1])
        return True
    
    def load_level(self, index):
        """Load a level from the levels list."""
        if index >= len(LEVELS):
            return

        map_str = LEVELS[index].strip()
        lines = map_str.split('\n')
        height = len(lines)
        width = len(lines[0]) if lines else 0
        
        # Create 2D grid
        cells = []
        player_pos = (1, 1)
        keys_count = 0
        
        for y, line in enumerate(lines):
            row = []
            for x, char in enumerate(line):
                if char == '#': row.append(WALL)
                elif char == '*': row.append(DATA)
                elif char == 'F': row.append(FIREWALL)
                elif char == 'K': 
                    row.append(KEY)
                    keys_count += 1
                elif char == 'P':
                    player_pos = (x, y)
                    row.append(EMPTY)
                elif char == 'A': row.append(PREDATOR)
                elif char == 'B': row.append(BUILDER)
                elif char == 'G':
                    row.append(GRAVITY_ZONE)
                elif char == 'X': row.append(EXIT)
                elif char == 'T': row.append(TELEPORTER)
                elif char == 'S': row.append(SLUDGE)
                elif char == '.': row.append(EMPTY)
                else: row.append(EMPTY)
            cells.append(row)
        
        # Create grid from cells
        self.grid = Grid.from_list(cells)
        self.engine = Engine(self.grid)
        self.player_x, self.player_y = player_pos
        self.required_keys = max(1, keys_count)
        self.keys_collected = 0
        self.bombs_count = 5
        self.pillars_count = 3
        self.game_over = False
        self.won = False
        
        # Register gravity zones in engine
        self.engine.gravity_zones.clear()
        for y in range(height):
            for x in range(len(cells[y]) if y < len(cells) else 0):
                if cells[y][x] == GRAVITY_ZONE:
                    self.engine.gravity_zones.add((x, y))
    
    def handle_death(self):
        """Trigger death animation and state."""
        self.lives -= 1
        if self.lives <= 0:
            self.game_over = True
        else:
            # Reload current level
            self.load_level(self.current_level_index)
    
    def move_player(self, dx, dy):
        """Move player if possible."""
        if self.game_over or self.won or self.showing_legend:
            return
        
        new_x = self.player_x + dx
        new_y = self.player_y + dy
        
        # Check bounds
        if not (0 <= new_x < self.grid.width and 0 <= new_y < self.grid.height):
            return
        
        target_cell = self.grid.get_tile(new_x, new_y)
        
        # Handle collisions
        if target_cell == WALL or target_cell == FIREWALL:
            return
        elif target_cell == KEY:
            self.keys_collected += 1
            self.grid.set_tile(new_x, new_y, EMPTY)
        elif target_cell == EXIT:
            if self.keys_collected >= self.required_keys:
                self.won = True
                return
            else:
                return  # Can't exit without all keys
        
        # Move player
        self.player_x = new_x
        self.player_y = new_y
   
    def update(self, dt):
        """Game logic update called every frame."""
        current_time = Clock.get_time()
        
        # Handle input
        if self.showing_legend or self.showing_hof or self.entering_name:
            if 'enter' in self.keys_pressed or 'spacebar' in self.keys_pressed:
                self.showing_legend = False
                self.showing_hof = False
                self.keys_pressed.clear()
        elif not self.game_over and not self.won:
            # Movement
            if 'up' in self.keys_pressed or 'w' in self.keys_pressed:
                self.move_player(0, -1)
            elif 'down' in self.keys_pressed or 's' in self.keys_pressed:
                self.move_player(0, 1)
            elif 'left' in self.keys_pressed or 'a' in self.keys_pressed:
                self.move_player(-1, 0)
                self.facing_left = True
            elif 'right' in self.keys_pressed or 'd' in self.keys_pressed:
                self.move_player(1, 0)
                self.facing_left = False
            
            # Game engine update
            current_time = int(Clock.get_time() * 1000)  # Convert to milliseconds
            player_killed = self.engine.update(current_time, (self.player_x, self.player_y))
            if player_killed:
                self.handle_death()
        
        # Render
        self.render()
    
    def render(self):
        """Render the game using Kivy Canvas."""
        self.canvas.clear()
        
        # Calculate scaling
        win_w, win_h = Window.size
        scale_x = win_w / SCREEN_WIDTH
        scale_y = win_h / SCREEN_HEIGHT
        scale = min(scale_x, scale_y)
        
        # Center the game
        offset_x = (win_w - SCREEN_WIDTH * scale) / 2
        offset_y = (win_h - SCREEN_HEIGHT * scale) / 2
        
        # Store for input ref
        self.game_scale = scale
        self.game_offset_x = offset_x
        self.game_offset_y = offset_y
        
        with self.canvas:
            # Clear background (fill whole screen with black borders)
            Color(0, 0, 0, 1)
            Rectangle(pos=(0, 0), size=(win_w, win_h))
            
            # Apply transformation for game content
            PushMatrix()
            Translate(offset_x, offset_y)
            Scale(scale, scale, 1)
            
            # Background of game area
            Color(*COLOR_BG)
            Rectangle(pos=(0, 0), size=(SCREEN_WIDTH, SCREEN_HEIGHT))
            
            # Draw grid
            for y in range(self.grid.height):
                for x in range(self.grid.width):
                    cell = self.grid.get_tile(x, y)
                    px = x * TILE_SIZE
                    py = (self.grid.height - y - 1) * TILE_SIZE  # Flip Y
                    
                    # Try to get texture from grid
                    texture = None
                    if hasattr(self.grid, 'textures') and cell in self.grid.textures:
                        surface = self.grid.textures[cell]
                        if surface and hasattr(surface, 'texture'):
                            texture = surface.texture
                    
                    if texture:
                        Color(1, 1, 1, 1)
                        # Handle rotation/flip if needed? (For now just basic render)
                        Rectangle(texture=texture, pos=(px, py), size=(TILE_SIZE, TILE_SIZE))
                    else:
                        # Fallback to color
                        color = COLOR_EMPTY
                        if cell == WALL:
                            color = COLOR_WALL
                        elif cell == DATA:
                            color = COLOR_DATA
                        elif cell == FIREWALL:
                            color = COLOR_FIREWALL
                        elif cell == KEY:
                            color = COLOR_KEY
                        elif cell == EXIT:
                            color = COLOR_EXIT
                        elif cell == PREDATOR:
                            color = COLOR_PREDATOR
                        elif cell == BUILDER:
                            color = COLOR_BUILDER
                        elif cell == GRAVITY_ZONE:
                            color = COLOR_GRAVITY
                        elif cell == BOMB:
                            color = COLOR_BOMB
                        elif cell == TELEPORTER:
                            color = COLOR_TELEPORTER
                        elif cell == PILLAR:
                            color = COLOR_PILLAR
                        elif cell == SLUDGE:
                            color = COLOR_SLUDGE
                        
                        Color(*color)
                        Rectangle(pos=(px, py), size=(TILE_SIZE, TILE_SIZE))
            
            # Draw player
            px = self.player_x * TILE_SIZE
            py = (self.grid.height - self.player_y - 1) * TILE_SIZE
            
            # Player texture
            player_texture = None
            if hasattr(self.grid, 'textures') and PLAYER in self.grid.textures:
                s = self.grid.textures[PLAYER]
                if s and hasattr(s, 'texture'): player_texture = s.texture
            
            # Handle flipping
            tex_coords = (0, 0, 1, 0, 1, 1, 0, 1) # Default
            if self.facing_left:
                tex_coords = (1, 0, 0, 0, 0, 1, 1, 1) # Flip horizontal

            if player_texture:
                Color(1, 1, 1, 1)
                Rectangle(texture=player_texture, pos=(px, py), size=(TILE_SIZE, TILE_SIZE), tex_coords=tex_coords)
            else:
                Color(*COLOR_HACKER)
                Ellipse(pos=(px + TILE_SIZE//4, py + TILE_SIZE//4), 
                       size=(TILE_SIZE//2, TILE_SIZE//2))
            
            # Draw HUD
            hud_x = SCREEN_WIDTH - HUD_WIDTH
            Color(0.1, 0.1, 0.1, 1)
            Rectangle(pos=(hud_x, 0), size=(HUD_WIDTH, SCREEN_HEIGHT))
            
            # Draw text (simplified for now)
            self.draw_text(f"Lives: {self.lives}", hud_x + 10, SCREEN_HEIGHT - 30)
            self.draw_text(f"Keys: {self.keys_collected}/{self.required_keys}", 
                          hud_x + 10, SCREEN_HEIGHT - 60)
            self.draw_text(f"Bombs: {self.bombs_count}", hud_x + 10, SCREEN_HEIGHT - 90)
            
            # Draw legend overlay if showing
            if self.showing_legend:
                Color(0, 0, 0, 0.8)
                Rectangle(pos=(0, 0), size=(SCREEN_WIDTH, SCREEN_HEIGHT))
                Color(1, 1, 1, 1)
                self.draw_text("BOULDERFLASH", SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT - 100, size=32)
                self.draw_text("Press SPACE / Tap to start", SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2)
            
            # Draw virtual controls if mobile
            if self.is_mobile:
                self.draw_virtual_controls()
            
            PopMatrix()
    
    def draw_text(self, text, x, y, size=18, color=(1, 1, 1, 1)):
        """Draw text using Kivy CoreLabel."""
        label = CoreLabel(text=text, font_size=size)
        label.refresh()
        texture = label.texture
        Color(*color)
        Rectangle(texture=texture, pos=(x, y), size=texture.size)
    
    def draw_virtual_controls(self):
        """Draw touch control overlays."""
        alpha = 0.5
        for name, (x, y_from_bottom, w, h) in self.touch_controls.items():
            y = SCREEN_HEIGHT - y_from_bottom - h
            Color(1, 1, 1, alpha)
            Line(rectangle=(x, y, w, h), width=2)
            self.draw_text(name[0].upper(), x + w//3, y + h//3, size=14)
    
    def on_touch_down(self, touch):
        """Handle touch input for virtual controls."""
        # Transform touch to game coordinates
        if not hasattr(self, 'game_scale'): return False
        
        game_x = (touch.x - self.game_offset_x) / self.game_scale
        game_y = (touch.y - self.game_offset_y) / self.game_scale
        
        if self.showing_legend:
            self.showing_legend = False
            return True
        
        # Check virtual control zones
        for name, (x, y_from_bottom, w, h) in self.touch_controls.items():
            y = SCREEN_HEIGHT - y_from_bottom - h
            if x <= game_x <= x + w and y <= game_y <= y + h:
                if name == "up":
                    self.move_player(0, -1)
                elif name == "down":
                    self.move_player(0, 1)
                elif name == "left":
                    self.move_player(-1, 0)
                    self.facing_left = True
                elif name == "right":
                    self.move_player(1, 0)
                    self.facing_left = False
                elif name == "bomb" and self.bombs_count > 0:
                    self.bombs_count -= 1
                    self.engine.active_bombs.append((self.player_x, self.player_y, 10))
                    self.grid.set_tile(self.player_x, self.player_y, BOMB)
                elif name == "pillar" and self.pillars_count > 0:
                    self.pillars_count -= 1
                    self.grid.set_tile(self.player_x, self.player_y, PILLAR)
                return True
        
        return super().on_touch_down(touch)

    def on_key_down(self, window, key, scancode, codepoint, modifiers):
        """Handle key press."""
        # Map keycodes to names
        key_name = codepoint
        if key == 273: key_name = 'up'
        elif key == 274: key_name = 'down'
        elif key == 276: key_name = 'left'
        elif key == 275: key_name = 'right'
        elif key == 32: key_name = 'spacebar'
        elif key == 13: key_name = 'enter'
        elif key == 27: key_name = 'escape'
        
        if key_name:
            self.keys_pressed.add(key_name)
        
        # Immediate actions
        if key_name == 'spacebar':
             if self.bombs_count > 0:
                 self.engine.active_bombs.append((self.player_x, self.player_y, 10))
                 self.grid.set_tile(self.player_x, self.player_y, BOMB)
                 self.bombs_count -= 1
        elif key_name == 'lctrl':
             if self.pillars_count > 0:
                 self.grid.set_tile(self.player_x, self.player_y, PILLAR)
                 self.pillars_count -= 1
                 
    def on_key_up(self, window, key, *args):
        """Handle key release."""
        key_name = None
        # Try to match what we added
        if key == 273: key_name = 'up'
        elif key == 274: key_name = 'down'
        elif key == 276: key_name = 'left'
        elif key == 275: key_name = 'right'
        elif key == 32: key_name = 'spacebar'
        elif key == 13: key_name = 'enter'
        elif key == 27: key_name = 'escape'
        elif hasattr(key, 'lower'): # codepoint
             key_name = key
        
        # Remove direct codepoints if they exist (char)
        # Note: Kivy sends codepoint as char in on_key_down, but on_key_up might differ
        # Use simpler approach: clear all related if confused, or just remove if present
        # We'll rely on the update loop checking specifics
        pass
        
        # Better approach: store raw keys in set, map them in update()
        # But we used string names in update()...
        # Let's just remove the mapped name
        if key_name and key_name in self.keys_pressed:
            self.keys_pressed.remove(key_name)
        
        # Remove codepoint if we added it (tricky to get codepoint in key_up)
        # We'll just clear keys on focus loss or something if it gets stuck



class BoulderflashApp(App):
    """Main Kivy App."""
    
    def build(self):
        self.title = "Cyber-Hacker: Hacking the Mainframe"
        game = GameWidget()
        return game


if __name__ == '__main__':
    try:
        BoulderflashApp().run()
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        try:
            with open("error.log", "w") as f:
                f.write(error_msg)
            print("CRASH CAUGHT: " + error_msg)
        except:
            print("CRASH CAUGHT (Write failed): " + error_msg)
        
        # Original Android logging attempt, now nested
        print(error_msg) # Print to console as well
        try:
            if IS_ANDROID:
                from android.storage import app_storage_path
                log_path = os.path.join(app_storage_path(), "crash.log")
            else:
                log_path = os.path.join(current_dir, "crash.log")
            
            with open(log_path, "w") as f:
                f.write(error_msg)
            print(f"Crash log written to {log_path}")
        except:
            pass
        sys.exit(1)

"""
Grid module for Boulderflash.
Handles the map layout and tile rendering.
"""
import pygame
from constants import (
    TILE_SIZE, COLOR_DATA, COLOR_WALL, COLOR_FIREWALL, COLOR_KEY, 
    COLOR_EXIT, COLOR_PREDATOR, COLOR_BUILDER, COLOR_GRAVITY, 
    COLOR_BOMB, COLOR_TELEPORTER, COLOR_PILLAR, COLOR_SLUDGE, COLOR_EMPTY,
    DATA, WALL, FIREWALL, KEY, EXIT, PREDATOR, BUILDER, GRAVITY_ZONE, 
    BOMB, TELEPORTER, PILLAR, SLUDGE, EMPTY
)

import os
from utils import resource_path

class Grid:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.tiles = [[DATA for _ in range(width)] for _ in range(height)]
        
        # Load textures
        self.textures = {}
        self.animated_textures = {}
        self.explosion_frames = []
        self.active_explosions = []
        self.load_textures()
        
        # Add a border of walls
        for x in range(width):
            self.tiles[0][x] = WALL
            self.tiles[height-1][x] = WALL
        for y in range(height):
            self.tiles[y][0] = WALL
            self.tiles[y][width-1] = WALL

    def load_textures(self):
        asset_map = {
            DATA: "wall.png",       # Utilisation de wall.png pour les blocs destructibles
            WALL: "border.png",     # border.png pour les murs indestructibles
            FIREWALL: "rock.png",   # rock.png pour les firewall/rochers
            KEY: "key.png"          # key.png pour les clés
        }
        for tile_type, filename in asset_map.items():
            path = resource_path(os.path.join("assets", filename))
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    self.textures[tile_type] = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        
        # Load Animated Teleporter
        tele_path = resource_path(os.path.join("assets", "teleport.png"))
        if os.path.exists(tele_path):
            try:
                sheet = pygame.image.load(tele_path).convert_alpha()
                # 445x70 / 6 frames ~= 74 pixels par frame
                frame_w = sheet.get_width() // 6
                frame_h = sheet.get_height()
                frames = []
                for i in range(6):
                    rect = pygame.Rect(i * frame_w, 0, frame_w, frame_h)
                    frame = sheet.subsurface(rect)
                    frames.append(pygame.transform.scale(frame, (TILE_SIZE, TILE_SIZE)))
                self.animated_textures[TELEPORTER] = frames
            except Exception as e:
                print(f"Error loading teleport spritesheet: {e}")
        
        # Load Animated Key
        key_frames = []
        for i in range(8):
            path = resource_path(os.path.join("assets", f"key_{i}.png"))
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    key_frames.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)))
                except Exception as e:
                    print(f"Error loading key frame {i}: {e}")
        if key_frames:
            self.animated_textures[KEY] = key_frames

        # Load Animated Exit Red (sortie_red_0.png to sortie_red_6.png)
        exit_red_frames = []
        for i in range(10): # Check up to 10
            path = resource_path(os.path.join("assets", f"sortie_red_{i}.png"))
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    exit_red_frames.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)))
                except Exception as e:
                    print(f"Error loading exit_red frame {i}: {e}")
        self.animated_textures["exit_red"] = exit_red_frames

        # Load Animated Exit Green (sortie_green_0.png to sortie_green_5.png)
        exit_green_frames = []
        for i in range(10):
            path = resource_path(os.path.join("assets", f"sortie_green_{i}.png"))
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    exit_green_frames.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)))
                except Exception as e:
                    print(f"Error loading exit_green frame {i}: {e}")
        # Add sortie_green_.png if it exists (potential missing frame)
        extra_path = resource_path(os.path.join("assets", "sortie_green_.png"))
        if os.path.exists(extra_path):
            try:
                img = pygame.image.load(extra_path).convert_alpha()
                exit_green_frames.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)))
            except: pass
        self.animated_textures["exit_green"] = exit_green_frames

        # Load Animated Firewalls (firewall_0.png to firewall_7.png in assets/firewall/)
        firewall_frames = []
        for i in range(8):
            path = resource_path(os.path.join("assets", "firewall", f"firewall_{i}.png"))
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    firewall_frames.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)))
                except Exception as e:
                    print(f"Error loading firewall frame {i}: {e}")
        if firewall_frames:
            self.animated_textures[FIREWALL] = firewall_frames

        # Load Animated Sludge / Corruption (slime_block_0.png to slime_block_7.png)
        slime_frames = []
        for i in range(10): # Check up to 10
            path = resource_path(os.path.join("assets", f"slime_block_{i}.png"))
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    # slime_block is 80x80 according to decoupeur, we scale to TILE_SIZE
                    slime_frames.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)))
                except Exception as e:
                    print(f"Error loading slime_block frame {i}: {e}")
        if slime_frames:
            self.animated_textures[SLUDGE] = slime_frames

        # Load Animated Virus (enemy) (antivirus_0.png to antivirus_7.png)
        virus_frames = []
        for i in range(10): 
            path = resource_path(os.path.join("assets", f"virus_{i}.png"))
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    virus_frames.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)))
                except Exception as e:
                    print(f"Error loading virus frame {i}: {e}")
        if virus_frames:
            self.animated_textures[PREDATOR] = virus_frames

        # Load Animated Replicator/Builder (replicator_0.png to replicator_7.png)
        replicator_frames = []
        for i in range(8):  # 8 frames for replicator
            path = resource_path(os.path.join("assets", f"replicator_{i}.png"))
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    replicator_frames.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)))
                except Exception as e:
                    print(f"Error loading replicator frame {i}: {e}")
        if replicator_frames:
            self.animated_textures[BUILDER] = replicator_frames

        # Load Animated Gravity Well (gravity_well_0.png to gravity_well_7.png)
        gravity_well_frames = []
        for i in range(8):  # 8 frames for gravity well
            path = resource_path(os.path.join("assets", f"gravity_well_{i}.png"))
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    gravity_well_frames.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)))
                except Exception as e:
                    print(f"Error loading gravity_well frame {i}: {e}")
        if gravity_well_frames:
            self.animated_textures[GRAVITY_ZONE] = gravity_well_frames

        # Load Animated USB Key (replacing Bomb)
        usb_frames = []
        for i in range(6): 
            path = resource_path(os.path.join("assets", f"usb_key_{i}.png"))
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    usb_frames.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)))
                except Exception as e:
                    print(f"Error loading usb_key frame {i}: {e}")
        if usb_frames:
            self.animated_textures[BOMB] = usb_frames

        # Load Animated Pillar (pillar_0.png to pillar_7.png)
        pillar_frames = []
        for i in range(8):
            path = resource_path(os.path.join("assets", f"pillar_{i}.png"))
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    pillar_frames.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)))
                except Exception as e:
                    print(f"Error loading pillar frame {i}: {e}")
        if pillar_frames:
            self.animated_textures[PILLAR] = pillar_frames

        # Load Animated Hardware Wall for Borders (hardware_wall_0.png to 7.png in assets/hardware_wall/)
        hardware_wall_frames = []
        for i in range(8):
            path = resource_path(os.path.join("assets", "hardware_wall", f"hardware_wall_{i}.png"))
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    hardware_wall_frames.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)))
                except Exception as e:
                    print(f"Error loading hardware_wall frame {i}: {e}")
        if hardware_wall_frames:
            self.animated_textures[WALL] = hardware_wall_frames

        # Load Big Explosion (3x3 effect)
        for i in range(12):
            path = resource_path(os.path.join("assets", "big_explosion", f"big_explosion_{i}.png"))
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    # Scale to 3x3 tiles
                    self.explosion_frames.append(pygame.transform.scale(img, (TILE_SIZE*3, TILE_SIZE*3)))
                except Exception as e:
                    print(f"Error loading explosion frame {i}: {e}")

    def get_tile(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return WALL

    def set_tile(self, x, y, tile_type):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y][x] = tile_type

    def add_explosion(self, bx, by):
        self.active_explosions.append({
            "pos": (bx, by),
            "start_time": pygame.time.get_ticks()
        })

    def draw(self, surface, keys_unlocked=False, offset=(0, 0)):
        for y in range(self.height):
            for x in range(self.width):
                rect = pygame.Rect(x * TILE_SIZE + offset[0], y * TILE_SIZE + offset[1], TILE_SIZE, TILE_SIZE)
                tile = self.tiles[y][x]
                
                # Special case for EXIT: choose animation based on keys_unlocked
                if tile == EXIT:
                    anim_key = "exit_green" if keys_unlocked else "exit_red"
                    if anim_key in self.animated_textures and self.animated_textures[anim_key]:
                        frames = self.animated_textures[anim_key]
                        frame_idx = (pygame.time.get_ticks() // 100) % len(frames)
                        surface.blit(frames[frame_idx], rect)
                        continue

                # Try drawing animated texture first
                if tile in self.animated_textures:
                    frames = self.animated_textures[tile]
                    # Animation speeds:
                    # Virus (enemy) and Sludge are faster (70ms)
                    # USB Key (Bomb) has a'sparkle' effect (~80ms = 12.5 FPS)
                    # Others like Teleport/Key are standard (100ms)
                    if tile in [PREDATOR, SLUDGE]: speed = 70
                    elif tile == BOMB: speed = 80
                    else: speed = 100
                    
                    frame_idx = (pygame.time.get_ticks() // speed) % len(frames)
                    surface.blit(frames[frame_idx], rect)
                    continue

                # Try drawing static texture
                if tile in self.textures:
                    surface.blit(self.textures[tile], rect)
                    continue

                if tile == DATA:
                    pygame.draw.rect(surface, COLOR_DATA, rect)
                    pygame.draw.rect(surface, (60, 60, 80), rect, 1) # grid lines
                elif tile == WALL:
                    pygame.draw.rect(surface, COLOR_WALL, rect)
                elif tile == FIREWALL:
                    # Draw a Firewall circle (Cyberpunk style)
                    pygame.draw.circle(surface, COLOR_FIREWALL, rect.center, TILE_SIZE // 2 - 2)
                    pygame.draw.circle(surface, (0, 0, 0), rect.center, TILE_SIZE // 4, 1)
                elif tile == KEY:
                    # Draw an Encryption Key (diamond shape)
                    pygame.draw.polygon(surface, COLOR_KEY, [
                        (rect.centerx, rect.top + 5),
                        (rect.right - 5, rect.centery),
                        (rect.centerx, rect.bottom - 5),
                        (rect.left + 5, rect.centery)
                    ])
                elif tile == EXIT:
                    # Draw the Exit door
                    pygame.draw.rect(surface, COLOR_EXIT, rect)
                    pygame.draw.rect(surface, (255, 255, 255), rect.inflate(-10, -10), 2)
                elif tile == PREDATOR:
                    # Draw the Predator (Virus)
                    pygame.draw.rect(surface, COLOR_PREDATOR, rect.inflate(-6, -6), border_radius=10)
                    pygame.draw.circle(surface, (0, 0, 0), rect.center, 4)
                elif tile == BUILDER:
                    # Draw the Builder
                    pygame.draw.rect(surface, COLOR_BUILDER, rect.inflate(-4, -4))
                    pygame.draw.rect(surface, (255, 255, 255), rect.inflate(-12, -12), 2)
                elif tile == GRAVITY_ZONE:
                    # Draw a Gravity Zone indicator
                    pygame.draw.rect(surface, COLOR_GRAVITY, rect, 1)
                    pygame.draw.line(surface, COLOR_GRAVITY, (rect.centerx, rect.top+5), (rect.centerx, rect.bottom-5), 2)
                    pygame.draw.line(surface, COLOR_GRAVITY, (rect.centerx-5, rect.top+10), (rect.centerx, rect.top+5), 2)
                    pygame.draw.line(surface, COLOR_GRAVITY, (rect.centerx+5, rect.top+10), (rect.centerx, rect.top+5), 2)
                elif tile == BOMB:
                    # Draw a Bomb
                    pygame.draw.circle(surface, COLOR_BOMB, rect.center, TILE_SIZE // 3)
                    pygame.draw.line(surface, (255, 255, 255), rect.center, (rect.centerx+5, rect.top+5), 2)
                elif tile == TELEPORTER:
                    # Draw a Teleporter
                    pygame.draw.ellipse(surface, COLOR_TELEPORTER, rect.inflate(-4, -8), 2)
                    pygame.draw.circle(surface, COLOR_TELEPORTER, rect.center, 4)
                elif tile == PILLAR:
                    # Draw a Pillar (Poteau)
                    pygame.draw.rect(surface, COLOR_PILLAR, rect.inflate(-10, 0))
                    pygame.draw.rect(surface, (0, 0, 0), rect.inflate(-20, 0), 2)
                elif tile == SLUDGE:
                    # Draw sludge (liquid)
                    pygame.draw.rect(surface, COLOR_SLUDGE, rect.inflate(-2, -8))
                    pygame.draw.circle(surface, COLOR_SLUDGE, (rect.centerx-4, rect.centery), 6)
                    pygame.draw.circle(surface, COLOR_SLUDGE, (rect.centerx+4, rect.centery+4), 5)
                elif tile == EMPTY:
                    pygame.draw.rect(surface, COLOR_EMPTY, rect)

        # Draw 3x3 Explosions
        current_time = pygame.time.get_ticks()
        speed = 60 # ms per frame
        duration = len(self.explosion_frames) * speed
        
        remaining_explosions = []
        for expl in self.active_explosions:
            elapsed = current_time - expl["start_time"]
            if elapsed < duration:
                frame_idx = elapsed // speed
                if frame_idx < len(self.explosion_frames):
                    bx, by = expl["pos"]
                    # Center the 3x3 explosion on (bx, by)
                    # Coordinates are (bx-1, by-1) to cover 3x3 area
                    ex = (bx - 1) * TILE_SIZE + offset[0]
                    ey = (by - 1) * TILE_SIZE + offset[1]
                    surface.blit(self.explosion_frames[frame_idx], (ex, ey))
                remaining_explosions.append(expl)
        self.active_explosions = remaining_explosions

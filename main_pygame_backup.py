"""
Main entry point for Boulderflash.
Cyber-Virus: Hacking the Mainframe.
"""
import os
import sys

# Add current directory to path to help some linters and environments
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import pygame
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
from utils import resource_path
import scores

# Detect Android
IS_ANDROID = "ANDROID_ARGUMENT" in os.environ or "ANDROID_ENTRYPOINT" in os.environ

class Game:
    def __init__(self):
        pygame.init()
        
        # Android-adaptive display mode
        if IS_ANDROID:
            # Fullscreen with automatic scaling for different screen sizes
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
        else:
            # Desktop: normal windowed mode
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        
        pygame.display.set_caption("Cyber-Hacker: Hacking the Mainframe")
        self.clock = pygame.time.Clock()
        
        # Initialize attributes
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
        self.crush_time = 0 # Timer pour le délai de grâce (Virus)
        self.showing_quit_confirm = False
        # Load Assets
        self.animations = {
            "idle": [],
            "run": [],
            "death": [],
            "hurt": [],
            "victory": []
        }
        self.background_img = None
        self.load_assets()
        
        # Animation State
        self.anim_state = "idle"
        self.anim_frame = 0
        self.anim_speed = 150 # ms per frame
        self.last_anim_update = 0
        self.last_move_time = 0
        self.facing_left = False
        
        # Victory animation state
        self.victory_zoom = 1.0  # Scale factor for zoom
        self.victory_start_time = 0
        self.victory_particles = []  # Particle effects
        
        # Death animation state
        self.death_zoom = 1.0
        self.death_start_time = 0
        self.death_particles = []
        
        # Initialize UI Font - safer for Android
        try:
            self.ui_font = pygame.font.SysFont("Consolas", 18, bold=True)
            if self.ui_font is None or self.ui_font.get_height() == 0:
                raise Exception("Font not found")
        except:
            self.ui_font = pygame.font.SysFont("sans-serif", 18, bold=True)
        
        self.current_level_index = 0
        self.load_level(self.current_level_index)

        # Virtual controls for mobile
        self.is_mobile = IS_ANDROID or True # Force True for testing on PC
        self.touch_controls = {
            "up": pygame.Rect(110, SCREEN_HEIGHT - 210, 80, 80),
            "down": pygame.Rect(110, SCREEN_HEIGHT - 90, 80, 80),
            "left": pygame.Rect(20, SCREEN_HEIGHT - 150, 80, 80),
            "right": pygame.Rect(200, SCREEN_HEIGHT - 150, 80, 80),
            "bomb": pygame.Rect(SCREEN_WIDTH - HUD_WIDTH - 180, SCREEN_HEIGHT - 180, 80, 80),
            "pillar": pygame.Rect(SCREEN_WIDTH - HUD_WIDTH - 90, SCREEN_HEIGHT - 180, 80, 80),
            "any": pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT) # For general "Press any key"
        }

    def load_assets(self):
        # Helper to load either a spritesheet or individual files
        def load_animation(name, count, frame_w=None, frame_h=None):
            seq = []
            
            # 1. Try loading from spritesheet (e.g., player_run.png)
            # Les fichiers player_*.png semblent être à la racine selon list_dir
            sheet_path = resource_path(f"player_{name}.png")
            if os.path.exists(sheet_path):
                try:
                    sheet = pygame.image.load(sheet_path).convert_alpha()
                    # if frame dimensions aren't provided, assume square or auto-calculate from count
                    w = frame_w if frame_w else (sheet.get_width() // count)
                    h = frame_h if frame_h else sheet.get_height()
                    for i in range(count):
                        rect = pygame.Rect(i * w, 0, w, h)
                        frame = sheet.subsurface(rect)
                        seq.append(pygame.transform.scale(frame, (TILE_SIZE, TILE_SIZE)))
                    return seq
                except Exception as e:
                    print(f"Error slicing sheet {sheet_path}: {e}")
            
            # 2. Fallback to individual files (e.g., player_run_0.png)
            i = 0
            while True:
                path = resource_path(os.path.join("assets", f"player_{name}_{i}.png"))
                if os.path.exists(path):
                    try:
                        img = pygame.image.load(path).convert_alpha()
                        seq.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)))
                    except Exception as e:
                        print(f"Error loading {path}: {e}")
                    i += 1
                else:
                    break
            return seq

        self.animations["idle"] = load_animation("idle", 4, frame_w=72, frame_h=74)
        self.animations["run"] = load_animation("run", 6, frame_w=74, frame_h=70)
        self.animations["death"] = load_animation("death", 6, frame_w=74, frame_h=73)
        self.animations["hurt"] = load_animation("hurt", 2, frame_w=71, frame_h=77)
        # Victory.png (ou fichiers individuels) - Mise à jour à 8 frames
        self.animations["victory"] = load_animation("victory", 8, frame_w=72, frame_h=74)
        
        # Cas spécial pour victory si loader plante car il cherche player_victory.png
        if not self.animations["victory"]:
            vic_path = resource_path("victory.png")
            if os.path.exists(vic_path):
                sheet = pygame.image.load(vic_path).convert_alpha()
                frames = []
                # On utilise 8 frames comme défini par l'utilisateur
                for i in range(min(8, sheet.get_width() // 72)):
                    rect = pygame.Rect(i * 72, 0, 72, 74)
                    frames.append(pygame.transform.scale(sheet.subsurface(rect), (TILE_SIZE, TILE_SIZE)))
                self.animations["victory"] = frames
        
        # Try loading background
        bg_path = resource_path(os.path.join("assets", "background.png"))
        if os.path.exists(bg_path):
            try:
                self.background_img = pygame.image.load(bg_path).convert()
                # Taille de la zone de jeu (800x600)
                self.background_img = pygame.transform.scale(self.background_img, (SCREEN_WIDTH - HUD_WIDTH, SCREEN_HEIGHT))
            except Exception as e:
                print(f"Error loading background: {e}")

    def load_level(self, index):
        if index >= len(LEVELS):
            return

        map_str = LEVELS[index].strip()
        lines = map_str.split('\n')
        height = len(lines)
        width = len(lines[0])
        
        self.grid = Grid(width, height)
        self.engine = Engine(self.grid)
        
        # Reset State
        self.keys_collected = 0
        self.required_keys = 0
        self.game_over = False
        self.won = False
        
        # Reset animation to idle
        self.anim_state = "idle"
        self.anim_frame = 0
        
        # Reset zoom/particles
        self.victory_zoom = 1.0
        self.victory_start_time = 0
        self.victory_particles = []
        self.death_zoom = 1.0
        self.death_start_time = 0
        self.death_particles = []
        
        # Tools
        self.bombs_count = 5
        self.pillars_count = 3
        
        # Parse Level
        self.engine.gravity_zones.clear()
        for y, line in enumerate(lines):
            for x, char in enumerate(line):
                if char == '#': self.grid.set_tile(x, y, WALL)
                elif char == '*': self.grid.set_tile(x, y, DATA)
                elif char == 'F': self.grid.set_tile(x, y, FIREWALL)
                elif char == 'K': 
                    self.grid.set_tile(x, y, KEY)
                    self.required_keys += 1
                elif char == 'P':
                    self.player_x = x
                    self.player_y = y
                    self.grid.set_tile(x, y, EMPTY)
                elif char == 'A': self.grid.set_tile(x, y, PREDATOR)
                elif char == 'B': self.grid.set_tile(x, y, BUILDER)
                elif char == 'G': 
                    self.grid.set_tile(x, y, GRAVITY_ZONE)
                    self.engine.gravity_zones.add((x, y))
                elif char == 'X': self.grid.set_tile(x, y, EXIT)
                elif char == 'T': self.grid.set_tile(x, y, TELEPORTER)
                elif char == 'S': self.grid.set_tile(x, y, SLUDGE)
                elif char == '.': self.grid.set_tile(x, y, EMPTY)
        
        if self.required_keys == 0: self.required_keys = 1

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.showing_quit_confirm = True
                continue

            if self.is_mobile and (event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.FINGERDOWN):
                pos = event.pos if event.type == pygame.MOUSEBUTTONDOWN else (event.x * SCREEN_WIDTH, event.y * SCREEN_HEIGHT)
                
                if self.showing_quit_confirm:
                    # Simple split screen for Yes/No in mobile
                    if pos[0] < SCREEN_WIDTH // 2: # Left = No
                        self.showing_quit_confirm = False
                    else: # Right = Yes
                        pygame.quit()
                        sys.exit()
                    continue

                if self.showing_legend:
                    self.showing_legend = False
                    continue

                if self.showing_hof:
                    # Top right for TAB-equivalent (Swap online/local)
                    if pos[0] > SCREEN_WIDTH - 150 and pos[1] < 100:
                        self.viewing_online = not self.viewing_online
                        self.high_scores = scores.get_top_scores(online=self.viewing_online)
                    else:
                        self.showing_hof = False
                        self.showing_legend = True
                        self.lives = 3
                        self.current_level_index = 0
                        self.load_level(0)
                    continue

                if self.entering_name:
                    # Simplified: Auto-enter Anonymous on mobile if they click
                    self.player_name = "Mobile_User"
                    scores.save_score(self.player_name, self.current_level_index + 1)
                    self.high_scores = scores.get_top_scores()
                    self.entering_name = False
                    self.showing_hof = True
                    continue

                if self.game_over:
                    if self.won:
                        if self.current_level_index < len(LEVELS) - 1:
                            self.current_level_index += 1
                            self.load_level(self.current_level_index)
                        else:
                            self.entering_name = True
                            self.game_over = False
                    else:
                        if self.lives <= 0:
                            self.entering_name = True
                            self.game_over = False
                        else:
                            self.load_level(self.current_level_index)
                    continue

                # Game controls
                dx, dy = 0, 0
                if self.touch_controls["up"].collidepoint(pos): dy = -1
                elif self.touch_controls["down"].collidepoint(pos): dy = 1
                elif self.touch_controls["left"].collidepoint(pos): dx = -1
                elif self.touch_controls["right"].collidepoint(pos): dx = 1
                elif self.touch_controls["bomb"].collidepoint(pos): self.place_bomb()
                elif self.touch_controls["pillar"].collidepoint(pos): self.place_pillar()

                if dx != 0 or dy != 0:
                    if dy > 0 and self.engine.check_crush(self.player_x, self.player_y):
                        self.lives = 1
                        self.crush_time = 1
                    if dx < 0: self.facing_left = True
                    elif dx > 0: self.facing_left = False
                    self.move_player(dx, dy)
                    if not self.game_over:
                        self.anim_state = "run"
                        self.last_move_time = pygame.time.get_ticks()

            if self.showing_quit_confirm:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_y or event.key == pygame.K_RETURN:
                        pygame.quit()
                        sys.exit()
                    if event.key == pygame.K_n or event.key == pygame.K_ESCAPE:
                        self.showing_quit_confirm = False
                continue

            if self.showing_legend:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.showing_quit_confirm = True
                        continue
                    # NEW: Press H to view Hall of Fame
                    if event.key == pygame.K_h:
                        self.showing_legend = False
                        self.showing_hof = True
                        self.viewing_online = False  # Start with local scores
                        self.high_scores = scores.get_top_scores(online=False)
                        continue
                    self.showing_legend = False
                continue

            if self.entering_name:
                if event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_AC_BACK]:
                        self.showing_quit_confirm = True
                        continue
                    if event.key == pygame.K_RETURN:
                        if self.player_name.strip():
                            # Afficher un petit message ?
                            scores.save_score(self.player_name, self.current_level_index + 1)
                            # On recharge les scores après l'upload
                            self.high_scores = scores.get_top_scores()
                        self.entering_name = False
                        self.showing_hof = True
                    elif event.key == pygame.K_BACKSPACE:
                        self.player_name = self.player_name[:-1] if self.player_name else ""
                    else:
                        if len(self.player_name) < 15 and event.unicode.isprintable():
                            self.player_name += event.unicode
                continue

            if self.showing_hof:
                if event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_AC_BACK]:
                        self.showing_quit_confirm = True
                        continue
                    
                    if event.key == pygame.K_TAB:
                        self.viewing_online = not self.viewing_online
                        self.high_scores = scores.get_top_scores(online=self.viewing_online)
                        continue

                    self.showing_hof = False
                    self.showing_legend = True
                    # Reset game
                    self.lives = 3
                    self.current_level_index = 0
                    self.load_level(0)
                continue

            if self.game_over:
                if event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_AC_BACK]:
                        self.showing_quit_confirm = True
                        continue
                    if event.key == pygame.K_r:
                        if self.won:
                            if self.current_level_index < len(LEVELS) - 1:
                                self.current_level_index += 1
                                self.load_level(self.current_level_index)
                            else:
                                # Victoire finale -> Saisie du nom
                                self.entering_name = True
                                self.game_over = False
                        else:
                            if self.lives <= 0:
                                self.entering_name = True
                                self.game_over = False
                            else:
                                self.load_level(self.current_level_index)
                return

            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_ESCAPE, pygame.K_AC_BACK]:
                    self.showing_quit_confirm = True
                    continue
                dx, dy = 0, 0
                if event.key in [pygame.K_UP, pygame.K_z]: dy = -1
                elif event.key in [pygame.K_DOWN, pygame.K_s]: dy = 1
                elif event.key in [pygame.K_LEFT, pygame.K_q]: dx = -1
                elif event.key in [pygame.K_RIGHT, pygame.K_d]: dx = 1
                elif event.key == pygame.K_SPACE:
                    self.place_bomb()
                elif event.key == pygame.K_LCTRL:
                    self.place_pillar()
                
                if dx != 0 or dy != 0:
                    # Si on essaie de descendre pendant un écrasement -> Mort immédiate
                    if dy > 0 and self.engine.check_crush(self.player_x, self.player_y):
                        self.lives = 1 # On force la mort au prochain cycle
                        self.crush_time = 1 # Trigger immédiat
                    
                    if dx < 0: self.facing_left = True
                    elif dx > 0: self.facing_left = False
                    self.move_player(dx, dy)
                    if not self.game_over:
                        self.anim_state = "run"
                        self.last_move_time = pygame.time.get_ticks()
                # Supprimé : l'idle est maintenant géré par le timer dans update()

    def place_bomb(self):
        if self.bombs_count > 0:
            self.engine.active_bombs.append((self.player_x, self.player_y, 10))
            self.grid.set_tile(self.player_x, self.player_y, BOMB)
            self.bombs_count -= 1

    def place_pillar(self):
        if self.pillars_count > 0:
            self.grid.set_tile(self.player_x, self.player_y, PILLAR)
            self.pillars_count -= 1

    def handle_death(self):
        """Unified method to trigger death animation and state."""
        self.lives -= 1
        self.crush_time = 0 # Reset
        self.game_over = True
        self.anim_state = "death"
        self.anim_frame = 0
        self.death_zoom = 1.0
        self.death_start_time = pygame.time.get_ticks()
        
        # Create red particle burst (failure effect)
        import random
        import math
        self.death_particles = []
        for _ in range(30):
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(80, 200)
            self.death_particles.append({
                'x': self.player_x, 'y': self.player_y,
                'vx': speed * math.cos(angle), 'vy': speed * math.sin(angle),
                'life': random.uniform(0.8, 2.0)
            })

    def move_player(self, dx, dy):
        new_x = self.player_x + dx
        new_y = self.player_y + dy
        target_tile = self.grid.get_tile(new_x, new_y)
        
        if target_tile in [WALL, PILLAR]: return

        if target_tile == TELEPORTER:
            for y in range(self.grid.height):
                for x in range(self.grid.width):
                    if self.grid.get_tile(x, y) == TELEPORTER and (x != new_x or y != new_y):
                        self.player_x = x
                        self.player_y = y
                        return
            return

        if target_tile == KEY:
            self.keys_collected += 1
            self.player_x = new_x
            self.player_y = new_y
            self.grid.set_tile(new_x, new_y, EMPTY)
        elif target_tile == EXIT:
            if self.keys_collected >= self.required_keys:
                self.won = True
                self.game_over = True
                self.anim_state = "victory"
                self.anim_frame = 0
                self.player_x = new_x
                self.player_y = new_y
                # Initialize victory animation
                self.victory_zoom = 1.0
                self.victory_start_time = pygame.time.get_ticks()
                # Create particle burst
                import random
                import math
                for _ in range(20):
                    angle = random.uniform(0, 2 * 3.14159)
                    speed = random.uniform(50, 150)
                    self.victory_particles.append({
                        'x': new_x, 'y': new_y,
                        'vx': speed * math.cos(angle), 'vy': speed * math.sin(angle),
                        'life': random.uniform(0.5, 1.5)
                    })
        elif target_tile == PREDATOR or target_tile == SLUDGE:
            # Immediate death on contact
            self.player_x, self.player_y = new_x, new_y
            self.handle_death()
            return
        elif target_tile in [DATA, EMPTY]:
            self.player_x = new_x
            self.player_y = new_y
            self.grid.set_tile(new_x, new_y, EMPTY)
        elif target_tile == FIREWALL and dy == 0:
            next_tile = self.grid.get_tile(new_x + dx, new_y)
            if next_tile in [EMPTY, GRAVITY_ZONE]:
                self.grid.set_tile(new_x + dx, new_y, FIREWALL)
                # Restaurer le tile d'origine s'il s'agissait d'une zone de gravité
                original_tile = GRAVITY_ZONE if (new_x, new_y) in self.engine.gravity_zones else EMPTY
                self.grid.set_tile(new_x, new_y, original_tile)
                self.player_x = new_x
                self.player_y = new_y
        elif target_tile == PREDATOR:
            self.player_x, self.player_y = new_x, new_y
            self.handle_death()
        
    def update(self):
        # Update Animation
        now = pygame.time.get_ticks()
        
        # Revenir en idle après 1 seconde sans mouvement
        if self.anim_state == "run" and now - self.last_move_time > 1000:
            self.anim_state = "idle"
            self.anim_frame = 0

        if now - self.last_anim_update > self.anim_speed:
            if self.anim_state == "death":
                # Stopper sur la dernière frame
                if self.anim_frame < len(self.animations["death"]) - 1:
                    self.anim_frame += 1
            else:
                self.anim_frame = (self.anim_frame + 1) % len(self.animations[self.anim_state]) if self.animations[self.anim_state] else 0
            self.last_anim_update = now

        if not self.game_over and not self.showing_legend and not self.entering_name and not self.showing_hof:
            killed = self.engine.update(now, (self.player_x, self.player_y))
            
            # Gestion du délai de grâce pour l'écrasement (Antivirus)
            is_crushed = self.engine.check_crush(self.player_x, self.player_y)
            if is_crushed:
                if self.crush_time == 0:
                    self.crush_time = now
                elif now - self.crush_time > 500:
                    killed = True
            else:
                self.crush_time = 0

            if killed:
                self.handle_death()
        
        # Update victory animation
        if self.won and self.victory_start_time > 0:
            elapsed = (now - self.victory_start_time) / 1000.0  # seconds
            # Progressive zoom in over 1.5 seconds to x5
            self.victory_zoom = min(5.0, 1.0 + elapsed * 3.0)
            
            # Update particles
            import math
            for particle in self.victory_particles[:]:
                particle['x'] += particle['vx'] * (1/60)
                particle['y'] += particle['vy'] * (1/60)
                particle['life'] -= 1/60
                if particle['life'] <= 0:
                    self.victory_particles.remove(particle)
        
        # Update death animation
        if self.game_over and not self.won and self.death_start_time > 0:
            elapsed = (now - self.death_start_time) / 1000.0  # seconds
            # Progressive zoom in over 1.5 seconds to x5
            self.death_zoom = min(5.0, 1.0 + elapsed * 3.0)
            
            # Update death particles
            import math
            for particle in self.death_particles[:]:
                particle['x'] += particle['vx'] * (1/60)
                particle['y'] += particle['vy'] * (1/60)
                particle['vy'] += 150 * (1/60)  # Gravity effect
                particle['life'] -= 1/60
                if particle['life'] <= 0:
                    self.death_particles.remove(particle)


    def draw_legend(self):
        self.screen.fill(COLOR_BG)
        try:
            title_font = pygame.font.SysFont("Consolas", 32, bold=True)
            text_font = pygame.font.SysFont("Consolas", 14)
            header_font = pygame.font.SysFont("Consolas", 18, bold=True)
        except:
            title_font = pygame.font.SysFont("sans-serif", 32, bold=True)
            text_font = pygame.font.SysFont("sans-serif", 14)
            header_font = pygame.font.SysFont("sans-serif", 18, bold=True)
        
        title = title_font.render("TERMINAL ACCESS: LEGEND", True, COLOR_HACKER)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, 40)))
        
        items = [
            (PLAYER, "HACKER (YOU) - Compromise nodes."),
            (KEY, "ENCRYPTED KEY - Collect all for EXIT."),
            (FIREWALL, "FIREWALL - Pushable stone. Falling hazard!"),
            (WALL, "ENCLOSURE - Indestructible boundary."),
            (DATA, "DATA BLOCK - Destructible storage."),
            (EXIT, "EXIT PORT - Access node after keys."),
            (PREDATOR, "VIRUS - Hunts you. 2 = Crush = Death!"),
            (BUILDER, "REPLICATOR - Leaves data trail."),
            (SLUDGE, "CORRUPTION - Liquid waste. Lethal."),
            (GRAVITY_ZONE, "GRAVITY WELL - Reverses column gravity."),
            (TELEPORTER, "UPLINK - Warp between portals."),
            (BOMB, "USBomb - Blast 3x3 area. [SPACE]"),
            (PILLAR, "PILLAR - Quick-build shield. [CTRL]")
        ]
        
        start_y = 90
        col1_x = 150
        col2_x = 550
        row_height = 42  # Increased spacing to prevent overlap
        
        # Display items in 2 columns with 7 items per column
        for i, (tile_type, desc) in enumerate(items):
            col = i // 7  # 7 items per column instead of 6
            row = i % 7
            x = col1_x if col == 0 else col2_x
            y = start_y + row * row_height
            
            rect = pygame.Rect(x, y, 20, 20)
            
            # Draw from assets if available
            asset_drawn = False
            if tile_type == PLAYER and self.animations["idle"]:
                frames = self.animations["idle"]
                frame_idx = (pygame.time.get_ticks() // 150) % len(frames)
                self.screen.blit(pygame.transform.scale(frames[frame_idx], (20, 20)), rect)
                asset_drawn = True
            elif tile_type == EXIT and "exit_red" in self.grid.animated_textures:
                frames = self.grid.animated_textures["exit_red"]
                frame_idx = (pygame.time.get_ticks() // 150) % len(frames)
                self.screen.blit(pygame.transform.scale(frames[frame_idx], (20, 20)), rect)
                asset_drawn = True
            elif tile_type in self.grid.animated_textures:
                frames = self.grid.animated_textures[tile_type]
                # Animer les icônes même dans la légende
                # Match in-game speed for Virus and Sludge
                speed = 70 if tile_type in [PREDATOR, SLUDGE] else 100
                frame_idx = (pygame.time.get_ticks() // speed) % len(frames)
                self.screen.blit(pygame.transform.scale(frames[frame_idx], (20, 20)), rect)
                asset_drawn = True
            elif tile_type in self.grid.textures:
                self.screen.blit(pygame.transform.scale(self.grid.textures[tile_type], (20, 20)), rect)
                asset_drawn = True
            if not asset_drawn:
                if tile_type == PLAYER:
                    pygame.draw.rect(self.screen, COLOR_HACKER, rect.inflate(-2, -2), border_radius=4)
                elif tile_type == KEY:
                    pygame.draw.polygon(self.screen, COLOR_KEY, [(rect.centerx, rect.top), (rect.right, rect.centery), (rect.centerx, rect.bottom), (rect.left, rect.centery)])
                elif tile_type == FIREWALL:
                    pygame.draw.circle(self.screen, COLOR_FIREWALL, rect.center, 9)
                elif tile_type == WALL:
                    pygame.draw.rect(self.screen, COLOR_WALL, rect)
                elif tile_type == EXIT:
                    pygame.draw.rect(self.screen, COLOR_EXIT, rect)
                    pygame.draw.rect(self.screen, (255, 255, 255), rect.inflate(-6, -6), 1)
                elif tile_type == PREDATOR:
                    pygame.draw.rect(self.screen, COLOR_PREDATOR, rect.inflate(-2, -2), border_radius=5)
                elif tile_type == BUILDER:
                    pygame.draw.rect(self.screen, COLOR_BUILDER, rect.inflate(-2, -2))
                elif tile_type == SLUDGE:
                    pygame.draw.rect(self.screen, COLOR_SLUDGE, rect.inflate(0, -6))
                elif tile_type == GRAVITY_ZONE:
                    pygame.draw.line(self.screen, COLOR_GRAVITY, (rect.centerx, rect.top), (rect.centerx, rect.bottom), 2)
                elif tile_type == TELEPORTER:
                    pygame.draw.ellipse(self.screen, COLOR_TELEPORTER, rect.inflate(0, -6), 2)
                elif tile_type == BOMB:
                    pygame.draw.circle(self.screen, COLOR_BOMB, rect.center, 7)
                elif tile_type == PILLAR:
                    pygame.draw.rect(self.screen, COLOR_PILLAR, rect.inflate(-10, 0))

            desc_text = text_font.render(desc, True, (200, 240, 200))
            self.screen.blit(desc_text, (x + 30, y + 2))

        # --- MISSION TEXT ---
        mission_font = pygame.font.SysFont("Consolas", 16, italic=True)
        m1 = mission_font.render("Collect all keys to open the exit, but beware:", True, (255, 200, 100))
        m2 = mission_font.render("many obstacles will stand in your way to reach it.", True, (255, 200, 100))
        self.screen.blit(m1, (SCREEN_WIDTH//2 - m1.get_width()//2, 395))
        self.screen.blit(m2, (SCREEN_WIDTH//2 - m2.get_width()//2, 415))

        # --- CONTROLS SECTION ---
        controls_y = 455
        header = header_font.render("--- COMMAND INTERFACE (CONTROLS) ---", True, COLOR_HACKER)
        self.screen.blit(header, (SCREEN_WIDTH//2 - header.get_width()//2, controls_y))
        
        control_font = pygame.font.SysFont("Consolas", 15)
        controls = [
            ("ARROWS / ZQSD", ": Move Hacker"),
            ("SPACE", ": Use USBomb"),
            ("L-CTRL Key", ": Build PILLAR"),
            ("R Key", ": Reboot Node / Next Level"),
            ("H Key", ": Hall of Fame (Scores)")  # NEW: Added Hall of Fame hotkey
        ]
        
        controls_start_y = controls_y + 35
        for i, (key, action) in enumerate(controls):
            key_text = control_font.render(key, True, (100, 200, 255))
            action_text = control_font.render(action, True, (200, 240, 200))
            y = controls_start_y + i * 25
            self.screen.blit(key_text, (SCREEN_WIDTH//2 - 250, y))
            self.screen.blit(action_text, (SCREEN_WIDTH//2 - 60, y))

        # --- PROMPT ---
        prompt_font = pygame.font.SysFont("Consolas", 18, bold=True)
        if self.is_mobile:
            prompt = prompt_font.render(">>> TOUCH BUTTONS OR PRESS ANY KEY <<<", True, COLOR_HACKER)
        else:
            prompt = prompt_font.render(">>> PRESS ANY KEY TO INITIALIZE <<<", True, COLOR_HACKER)
        self.screen.blit(prompt, (SCREEN_WIDTH//2 - prompt.get_width()//2, 605))
        
        pygame.display.flip()

    def draw(self):
        if self.showing_hof:
            self.draw_hof()
            if self.showing_quit_confirm: self.draw_quit_confirm()
            pygame.display.flip()
            return
            
        if self.entering_name:
            self.draw_name_input()
            if self.showing_quit_confirm: self.draw_quit_confirm()
            pygame.display.flip()
            return

        if self.showing_legend:
            self.draw_legend()
            if self.showing_quit_confirm: self.draw_quit_confirm()
            pygame.display.flip()
            return

        # --- Game Rendering ---
        self.screen.fill((15, 15, 25)) # Background global sombre
        
        # Game area background
        if self.background_img:
            self.screen.blit(self.background_img, (HUD_WIDTH, 0))
        else:
            pygame.draw.rect(self.screen, COLOR_BG, (HUD_WIDTH, 0, SCREEN_WIDTH - HUD_WIDTH, SCREEN_HEIGHT))
            
        # Grid with offset
        self.grid.draw(self.screen, keys_unlocked=self.keys_collected >= self.required_keys, offset=(HUD_WIDTH, 0))
        
        # Draw Player with possible zoom effect  
        if self.animations["idle"]:
            current_anim = self.animations.get(self.anim_state, self.animations["idle"])
            if current_anim:
                frame = current_anim[self.anim_frame % len(current_anim)]
                if self.facing_left:
                    frame = pygame.transform.flip(frame, True, False)
                
                # Apply zoom on victory
                if self.won and self.victory_zoom > 1.0:
                    # Calculate zoomed size
                    new_size = int(TILE_SIZE * self.victory_zoom)
                    zoomed_frame = pygame.transform.scale(frame, (new_size, new_size))
                    # Center the zoomed image on player position
                    offset = (new_size - TILE_SIZE) // 2
                    player_rect = pygame.Rect(
                        self.player_x * TILE_SIZE + HUD_WIDTH - offset,
                        self.player_y * TILE_SIZE - offset,
                        new_size, new_size
                    )
                    self.screen.blit(zoomed_frame, player_rect)
                    
                    # Draw victory particles
                    for particle in self.victory_particles:
                        px = int(particle['x'] * TILE_SIZE + HUD_WIDTH + TILE_SIZE//2)
                        py = int(particle['y'] * TILE_SIZE + TILE_SIZE//2)
                        alpha = int(255 * min(1.0, particle['life']))
                        color = (255, 255, 100, alpha)  # Yellow-ish
                        pygame.draw.circle(self.screen, color[:3], (px, py), 3)
                
                # Apply zoom on death
                elif self.game_over and not self.won and self.death_zoom > 1.0:
                    # Calculate zoomed size
                    new_size = int(TILE_SIZE * self.death_zoom)
                    zoomed_frame = pygame.transform.scale(frame, (new_size, new_size))
                    # Center the zoomed image on player position
                    offset = (new_size - TILE_SIZE) // 2
                    player_rect = pygame.Rect(
                        self.player_x * TILE_SIZE + HUD_WIDTH - offset,
                        self.player_y * TILE_SIZE - offset,
                        new_size, new_size
                    )
                    self.screen.blit(zoomed_frame, player_rect)
                    
                    # Draw death particles (red failure effect)
                    for particle in self.death_particles:
                        px = int(particle['x'] * TILE_SIZE + HUD_WIDTH + TILE_SIZE//2)
                        py = int(particle['y'] * TILE_SIZE + TILE_SIZE//2)
                        alpha = int(255 * min(1.0, particle['life']))
                        # Red-orange gradient for failure/explosion effect
                        color = (255, int(50 * particle['life']), 0)
                        pygame.draw.circle(self.screen, color, (px, py), 4)
                
                else:
                    player_rect = pygame.Rect(self.player_x * TILE_SIZE + HUD_WIDTH, self.player_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    self.screen.blit(frame, player_rect)
        else:
            player_rect = pygame.Rect(self.player_x * TILE_SIZE + HUD_WIDTH, self.player_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(self.screen, COLOR_HACKER, player_rect.inflate(-4, -4), border_radius=4)
        
        # Sidebar interface
        self.draw_sidebar()
        
        if self.game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))
            big_font = pygame.font.SysFont("Consolas", 50)
            if self.won:
                if self.current_level_index < len(LEVELS) - 1:
                    msg = big_font.render("ACCESS GRANTED", True, (0, 255, 100))
                    sub = self.ui_font.render("PRESS R FOR NEXT NODE", True, (255, 255, 255))
                else:
                    msg = big_font.render("SYSTEM COMPROMISED", True, (0, 255, 100))
                    sub = self.ui_font.render("ALL NODES HACKED. CONGRATULATIONS.", True, (255, 255, 255))
            else:
                msg = big_font.render("CONNECTION LOST", True, (255, 50, 50))
                # Show lives remaining
                if self.lives > 0:
                    lives_text = f"LIVES REMAINING: {self.lives}"
                    sub = self.ui_font.render(lives_text, True, (255, 200, 100))
                    sub2 = self.ui_font.render("PRESS R TO REBOOT NODE", True, (255, 255, 255))
                else:
                    sub = self.ui_font.render("NO LIVES REMAINING - GAME OVER", True, (255, 50, 50))
                    sub2 = self.ui_font.render("PRESS R TO CONTINUE", True, (255, 255, 255))
            
            self.screen.blit(msg, msg.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))
            if self.won or self.lives > 0:
                self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 60)))
                if not self.won and self.lives > 0:
                    self.screen.blit(sub2, sub2.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 100)))
            else:
                self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 60)))
                self.screen.blit(sub2, sub2.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 100)))
            
        if self.showing_quit_confirm:
            self.draw_quit_confirm()
            
        if self.is_mobile and not (self.showing_legend or self.showing_hof or self.entering_name):
            self.draw_virtual_controls()
            
        pygame.display.flip()

    def draw_quit_confirm(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        box_w, box_h = 400, 150
        box_x = (SCREEN_WIDTH - box_w) // 2
        box_y = (SCREEN_HEIGHT - box_h) // 2
        pygame.draw.rect(self.screen, (30, 30, 40), (box_x, box_y, box_w, box_h))
        pygame.draw.rect(self.screen, COLOR_HACKER, (box_x, box_y, box_w, box_h), 2)
        
        text = self.ui_font.render("QUIT GAME?", True, (255, 255, 255))
        self.screen.blit(text, (box_x + (box_w - text.get_width()) // 2, box_y + 30))
        
        hint = self.ui_font.render("YES (Y / Enter)   NO (N / Esc)", True, COLOR_HACKER)
        self.screen.blit(hint, (box_x + (box_w - hint.get_width()) // 2, box_y + 80))

    def draw_sidebar(self):
        # Fond du HUD
        pygame.draw.rect(self.screen, (10, 10, 20), (0, 0, HUD_WIDTH, SCREEN_HEIGHT))
        pygame.draw.line(self.screen, (50, 50, 100), (HUD_WIDTH-1, 0), (HUD_WIDTH-1, SCREEN_HEIGHT), 2)
        
        y_offset = 30
        margin = 25
        
        # --- TITLE ---
        title_font = pygame.font.SysFont("Consolas", 26, bold=True)
        title = title_font.render("--- STATUS ---", True, COLOR_HACKER)
        self.screen.blit(title, (margin, y_offset))
        y_offset += 60
        
        # --- LIVES ---
        icon_size = 24
        pygame.draw.circle(self.screen, (255, 50, 50), (margin + 12, y_offset + 12), 10) # Simple Heart icon
        label = self.ui_font.render(f"LIVES: {self.lives}", True, (255, 100, 100))
        self.screen.blit(label, (margin + 40, y_offset))
        y_offset += 50
        
        # --- LEVEL ---
        label = self.ui_font.render(f"NODE : {self.current_level_index + 1}", True, (255, 255, 255))
        self.screen.blit(label, (margin, y_offset))
        y_offset += 50
        
        # --- KEYS ---
        # Icon Key
        pygame.draw.rect(self.screen, COLOR_KEY, (margin, y_offset + 4, 20, 12), border_radius=2)
        label = self.ui_font.render(f"KEYS : {self.keys_collected}/{self.required_keys}", True, COLOR_KEY)
        self.screen.blit(label, (margin + 40, y_offset))
        y_offset += 50
        
        # --- INVENTORY ---
        pygame.draw.line(self.screen, (50, 50, 100), (margin, y_offset), (HUD_WIDTH - margin, y_offset), 1)
        y_offset += 30
        title_inv = self.ui_font.render("[ INVENTORY ]", True, (150, 150, 200))
        self.screen.blit(title_inv, (margin, y_offset))
        y_offset += 50
        
        # USBomb
        label = self.ui_font.render(f"USBomb: {self.bombs_count}", True, COLOR_BOMB)
        hint = self.ui_font.render("[SPACE]", True, (80, 80, 100))
        self.screen.blit(label, (margin, y_offset))
        self.screen.blit(hint, (HUD_WIDTH - 85, y_offset))
        y_offset += 40
        
        # PILLARS
        label = self.ui_font.render(f"PIL: {self.pillars_count}", True, COLOR_PILLAR)
        hint = self.ui_font.render("[CTRL]", True, (80, 80, 100))
        self.screen.blit(label, (margin, y_offset))
        self.screen.blit(hint, (HUD_WIDTH - 85, y_offset))
        
    def draw_name_input(self):
        self.screen.fill((20, 20, 40))
        font = pygame.font.SysFont("Consolas", 32, bold=True)
        input_font = pygame.font.SysFont("Consolas", 40)
        
        msg = font.render("NEW RECORD! ENTER YOUR UID:", True, COLOR_HACKER)
        name_surface = input_font.render(self.player_name + "_", True, (255, 255, 255))
        prompt = self.ui_font.render("PRESS ENTER TO COMMIT", True, (150, 150, 150))
        
        self.screen.blit(msg, msg.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 60)))
        self.screen.blit(name_surface, name_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))
        self.screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 80)))

    def draw_hof(self):
        self.screen.fill((10, 10, 20))
        title_font = pygame.font.SysFont("Consolas", 40, bold=True)
        list_font = pygame.font.SysFont("Consolas", 24)
        hint_font = pygame.font.SysFont("Consolas", 18)
        
        mode_text = "GLOBAL" if self.viewing_online else "LOCAL"
        title = title_font.render(f"--- {mode_text} HALL OF FAME ---", True, COLOR_HACKER)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, 80)))
        
        toggle_hint = hint_font.render("[TAB] TOGGLE GLOBAL/LOCAL", True, (100, 100, 150))
        self.screen.blit(toggle_hint, toggle_hint.get_rect(center=(SCREEN_WIDTH//2, 120)))
        
        if not self.high_scores:
            loading = list_font.render("CONNECTING...", True, (100, 100, 100))
            self.screen.blit(loading, loading.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))
        elif len(self.high_scores) == 1 and "error" in self.high_scores[0]:
            err_msg = self.high_scores[0]["error"]
            err_surf = list_font.render(f"ERROR: {err_msg}", True, (255, 50, 50))
            self.screen.blit(err_surf, err_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))
            hint = hint_font.render("Check internet connection / Firewall", True, (150, 150, 150))
            self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 40)))
        elif len(self.high_scores) == 0:
            msg = list_font.render("NO RECORDS FOUND ON THIS NODE.", True, (100, 100, 100))
            self.screen.blit(msg, msg.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))
        else:
            start_y = 160
            for i, entry in enumerate(self.high_scores[:12]): # Show top 12
                rank = list_font.render(f"{i+1}.", True, (150, 150, 150))
                name_str = entry['name'][:15].ljust(15)
                name = list_font.render(name_str, True, (255, 255, 255))
                lvl = list_font.render(f"NODE {entry['level']}", True, COLOR_KEY)
                
                y = start_y + i * 35
                self.screen.blit(rank, (SCREEN_WIDTH//2 - 180, y))
                self.screen.blit(name, (SCREEN_WIDTH//2 - 130, y))
                self.screen.blit(lvl, (SCREEN_WIDTH//2 + 80, y))
            
        footer = self.ui_font.render("PRESS ANY KEY TO REBOOT SYSTEM", True, COLOR_HACKER)
        self.screen.blit(footer, footer.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 60)))

    def draw_virtual_controls(self):
        # Semi-transparent overlay for buttons
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        
        # Color for buttons (Neon Blue)
        btn_color = (0, 200, 255, 100)
        
        for name, rect in self.touch_controls.items():
            if name == "any": continue
            pygame.draw.rect(overlay, btn_color, rect, border_radius=10)
            pygame.draw.rect(overlay, (255, 255, 255, 150), rect, 2, border_radius=10)
            
            # Icons/Text
            icon_font = pygame.font.SysFont("Consolas", 30, bold=True)
            label = ""
            if name == "up": label = "^"
            elif name == "down": label = "v"
            elif name == "left": label = "<"
            elif name == "right": label = ">"
            elif name == "bomb": label = "B"
            elif name == "pillar": label = "P"
            
            if label:
                txt = icon_font.render(label, True, (255, 255, 255, 200))
                overlay.blit(txt, txt.get_rect(center=rect.center))

        self.screen.blit(overlay, (0, 0))

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    try:
        game = Game()
        game.run()
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(error_msg)
        try:
            # On Android, write to app's storage directory
            if IS_ANDROID:
                try:
                    from android.storage import app_storage_path
                    log_path = os.path.join(app_storage_path(), "crash_log.txt")
                except ImportError:
                    log_path = "crash_log.txt"
            else:
                log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_log.txt")
            
            with open(log_path, "w") as f:
                f.write(error_msg)
            print(f"Crash log written to {log_path}")
        except:
            pass
        sys.exit(1)

"""
Engine module for Boulderflash.
Handles physics, AI, liquids, and game rules.
"""
import pygame
import random
from constants import (
    EMPTY, DATA, WALL, FIREWALL, KEY, EXIT, PREDATOR, BUILDER, 
    GRAVITY_ZONE, BOMB, TELEPORTER, PILLAR, SLUDGE
)

class Engine:
    def __init__(self, grid):
        self.grid = grid
        self.last_physics_update = 0
        self.physics_delay = 150 # ms between physics ticks
        self.processed_this_tick = set()
        self.active_bombs = []
        self.predator_timers = {} # Cache pour les délais de déplacement par prédateur (x,y) -> last_time
        self.predator_move_delay = 400 # 0.4s par case (plus rapide pour plus de challenge)
        self.gravity_zones = set() # Coordonnées persistantes des puits de gravité

    def update(self, current_time, player_pos):
        killed = False
        if current_time - self.last_physics_update > self.physics_delay:
            killed = self.update_physics(player_pos, current_time)
            if not killed:
                killed = self.update_enemies(player_pos)
            
            bomb_killed = self.update_bombs(player_pos)
            self.update_sludge()
            
            # Check if player is trapped (Stalemate)
            trapped = self.check_trapped(*player_pos)
            
            killed = killed or bomb_killed or trapped
            self.last_physics_update = current_time
        return killed

    def check_trapped(self, px, py):
        # A player is trapped if no adjacent tile allows movement
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = px + dx, py + dy
            tile = self.grid.get_tile(nx, ny)
            if tile in [EMPTY, DATA, KEY, EXIT, TELEPORTER, PREDATOR]:
                return False
            if tile == FIREWALL and dy == 0:
                if self.grid.get_tile(nx + dx, ny) == EMPTY:
                    return False
        return True

    def check_crush(self, px, py):
        # Le joueur meurt s'il y a un Firewall au-dessus de lui (y-1)
        # On retourne True si un Firewall est sur le point de tomber sur lui
        if self.grid.get_tile(px, py - 1) == FIREWALL:
            # Vérifier si le Firewall peut effectivement tomber (sous-jacent est le joueur)
            return True
        return False

    def update_sludge(self):
        expand_targets = []
        for y in range(1, self.grid.height - 1):
            for x in range(1, self.grid.width - 1):
                if self.grid.get_tile(x, y) == SLUDGE:
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        if self.grid.get_tile(x + dx, y + dy) == EMPTY:
                            expand_targets.append((x + dx, y + dy))
        
        for tx, ty in expand_targets:
            if random.random() < 0.0575:
                self.grid.set_tile(tx, ty, SLUDGE)

    def update_bombs(self, player_pos):
        bombs_to_remove = []
        any_killed = False
        for i, (bx, by, timer) in enumerate(self.active_bombs):
            if timer > 0:
                self.active_bombs[i] = (bx, by, timer - 1)
            else:
                bombs_to_remove.append(i)
                if self.explode(bx, by, player_pos):
                    any_killed = True
        
        for i in sorted(bombs_to_remove, reverse=True):
            self.active_bombs.pop(i)
        return any_killed

    def explode(self, bx, by, player_pos):
        # Trigger visual effect
        self.grid.add_explosion(bx, by)
        
        player_killed = False
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                tx, ty = bx + dx, by + dy
                tile = self.grid.get_tile(tx, ty)
                if tile != WALL:
                    self.grid.set_tile(tx, ty, EMPTY)
                    if (tx, ty) == player_pos:
                        player_killed = True
        return player_killed

    def has_line_of_sight(self, ex, ey, px, py):
        # Les Virus détectent TOUJOURS le joueur (vision omnidirectionnelle)
        return True

    def find_path_to_player(self, start_x, start_y, target_x, target_y):
        """BFS pathfinding for viruses to navigate around obstacles to reach player."""
        from collections import deque
        
        # BFS to find shortest path
        queue = deque([(start_x, start_y, [])])
        visited = {(start_x, start_y)}
        
        while queue:
            x, y, path = queue.popleft()
            
            # Found the target
            if x == target_x and y == target_y:
                return path[0] if path else (0, 0)
            
            # Try all 4 directions
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                
                if (nx, ny) in visited:
                    continue
                
                # Check bounds
                if not (0 <= nx < self.grid.width and 0 <= ny < self.grid.height):
                    continue
                
                tile = self.grid.get_tile(nx, ny)
                
                # CRITICAL: Viruses can ONLY move through EMPTY tiles
                # They must navigate around DATA, WALLS, FIREWALLS, etc.
                # Exception: Can move to player position
                if tile != EMPTY and (nx, ny) != (target_x, target_y):
                    continue
                
                visited.add((nx, ny))
                new_path = path + [(dx, dy)]
                queue.append((nx, ny, new_path))
        
        # No path found, return no movement
        return (0, 0)

    def update_physics(self, player_pos, current_time):
        self.processed_this_tick.clear()
        player_killed = False
        
        for y in range(self.grid.height - 2, 0, -1):
            for x in range(1, self.grid.width - 1):
                if (x, y) in self.processed_this_tick:
                    continue
                
                tile = self.grid.get_tile(x, y)
                if tile in [FIREWALL, KEY]:
                    # On passe current_time pour gérer le délai de grâce si au-dessus du joueur
                    if self.process_falling_object(x, y, player_pos, current_time):
                        if player_pos == (x, y + 1) and tile == FIREWALL:
                            player_killed = True
        return player_killed

    def update_enemies(self, player_pos):
        player_killed = False
        enemies = []
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                tile = self.grid.get_tile(x, y)
                if tile in [PREDATOR, BUILDER]:
                    enemies.append((x, y, tile))
        
        for ex, ey, etype in enemies:
            if (ex, ey) in self.processed_this_tick:
                continue
                
            dx, dy = 0, 0
            if etype == PREDATOR:
                # 1. Vérifier si le prédateur voit le joueur
                if not self.has_line_of_sight(ex, ey, player_pos[0], player_pos[1]):
                    continue
                    
                # 2. Vérifier le timer de vitesse (0.4s par case)
                current_time = pygame.time.get_ticks()
                last_move = self.predator_timers.get((ex, ey), 0)
                if current_time - last_move < self.predator_move_delay:
                    continue
                
                # 3. Use pathfinding to navigate around obstacles
                dx, dy = self.find_path_to_player(ex, ey, player_pos[0], player_pos[1])
            
            elif etype == BUILDER:
                dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                random.shuffle(dirs)
                for rdx, rdy in dirs:
                    if self.grid.get_tile(ex + rdx, ey + rdy) == EMPTY:
                        dx, dy = rdx, rdy
                        break
            
            if dx != 0 or dy != 0:
                target_pos = (ex + dx, ey + dy)
                target_tile = self.grid.get_tile(*target_pos)
                
                # Priorité 1 : Collision avec le joueur (Virus seulement)
                if target_pos == player_pos and etype == PREDATOR:
                    # Si un autre prédateur est déjà sur le joueur -> ÉCRASEMENT
                    if self.grid.get_tile(*target_pos) == PREDATOR:
                        player_killed = True
                    
                    # Dans tous les cas, on avance (visuel)
                    self.grid.set_tile(ex, ey, EMPTY)
                    self.grid.set_tile(*target_pos, PREDATOR)
                    self.processed_this_tick.add(target_pos)
                
                # Priorité 2 : Mouvement normal
                elif target_tile == EMPTY:
                    # Effacer l'ancienne position
                    old_tile = GRAVITY_ZONE if (ex, ey) in self.gravity_zones else EMPTY
                    self.grid.set_tile(ex, ey, old_tile)
                    
                    if etype == BUILDER:
                        self.grid.set_tile(ex, ey, DATA) # Le builder laisse de la donnée
                    
                    if etype == PREDATOR:
                        self.predator_timers[target_pos] = pygame.time.get_ticks()
                        # Nettoyer l'ancien timer
                        self.predator_timers.pop((ex, ey), None)
                    
                    self.grid.set_tile(*target_pos, etype)
                    self.processed_this_tick.add(target_pos)
        return player_killed

    def process_falling_object(self, x, y, player_pos, current_time=0):
        tile_type = self.grid.get_tile(x, y)
        # gravity_up: un objet monte s'il y a un puit de gravité ('G') n'importe où en dessous
        # dans la même colonne, tant qu'il n'y a pas d'obstacle solide entre les deux.
        gravity_up = False
        for ty in range(y, self.grid.height):
            if (x, ty) in self.gravity_zones:
                gravity_up = True
                break
                t = self.grid.get_tile(x, ty)
                # Seuls les obstacles solides (murs, terre) bloquent la gravité.
                # Les objets tombables (Firewall, Key) ne bloquent pas la gravité pour les objets au dessus.
                if t in [WALL, PILLAR, DATA, SLUDGE]:
                    break
        
        if gravity_up:
            target_pos = (x, y - 1)
            target = self.grid.get_tile(*target_pos)
            if target in [EMPTY, GRAVITY_ZONE] or target_pos == player_pos:
                # Si le joueur est au-dessus et que c'est une pierre -> Mort (mais on laisse check_crush gérer le délai ?)
                if target_pos == player_pos:
                    if tile_type == FIREWALL:
                        return True 
                    return False 
                
                # Restaurer le tile d'origine s'il s'agissait d'une zone de gravité
                original_tile = GRAVITY_ZONE if (x, y) in self.gravity_zones else EMPTY
                self.grid.set_tile(x, y, original_tile)
                self.grid.set_tile(target_pos[0], target_pos[1], tile_type)
                self.processed_this_tick.add(target_pos)
                return True
            return False

        target_pos = (x, y + 1)
        target_tile = self.grid.get_tile(*target_pos)

        # SI LE JOUEUR EST EN DESSOUS : On ne tombe QUE si le délai de grâce est dépassé (géré dans main.py)
        # Mais le moteur doit quand même savoir s'il doit déplacer l'objet.
        # Pour simplifier, on laisse update_physics déplacer l'objet, mais main.py gère la mort.
        # Cependant, l'utilisateur veut un délai AVANT de mourir.
        # Si on laisse l'objet tomber dans Engine, le joueur meurt tout de suite car player_pos == (x, y+1).
        
        if target_pos == player_pos:
            # On ne fait rien ici, on attend que main.py détecte le risque via check_crush
            # et déclenche la mort après 500ms. L'objet ne tombera physiquement sur le joueur
            # que quand killed deviendra True dans main.py.
            return False

        if target_tile in [EMPTY, PREDATOR, BUILDER, GRAVITY_ZONE]:
            # Restaurer le tile d'origine s'il s'agissait d'une zone de gravité
            original_tile = GRAVITY_ZONE if (x, y) in self.gravity_zones else EMPTY
            self.grid.set_tile(x, y, original_tile)
            self.grid.set_tile(*target_pos, tile_type)
            self.processed_this_tick.add(target_pos)
            return True
            
        below = self.grid.get_tile(x, y + 1)
        if below in [FIREWALL, KEY, WALL, PILLAR]:
            if self.grid.get_tile(x - 1, y) in [EMPTY, GRAVITY_ZONE] and self.grid.get_tile(x - 1, y + 1) in [EMPTY, GRAVITY_ZONE]:
                if (x - 1, y + 1) != player_pos:
                    original_tile = GRAVITY_ZONE if (x, y) in self.gravity_zones else EMPTY
                    self.grid.set_tile(x, y, original_tile)
                    self.grid.set_tile(x - 1, y, tile_type)
                    self.processed_this_tick.add((x - 1, y))
                    return True
            if self.grid.get_tile(x + 1, y) in [EMPTY, GRAVITY_ZONE] and self.grid.get_tile(x + 1, y + 1) in [EMPTY, GRAVITY_ZONE]:
                if (x + 1, y + 1) != player_pos:
                    original_tile = GRAVITY_ZONE if (x, y) in self.gravity_zones else EMPTY
                    self.grid.set_tile(x, y, original_tile)
                    self.grid.set_tile(x + 1, y, tile_type)
                    self.processed_this_tick.add((x + 1, y))
                    return True
        return False

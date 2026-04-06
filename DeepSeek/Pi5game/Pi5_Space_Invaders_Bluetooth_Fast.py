# Pi5_Space_Invaders_Bluetooth_Calibrated_WithSound.py
# Fixed version with joystick calibration, sound effects, connection splash screen, and sprites

import pygame
import struct
import asyncio
import bleak
import sys
import time
import os
from collections import deque

# Game constants
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
PLAYER_SPEED = 8
BULLET_SPEED = 10
ENEMY_SPEED = 4

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
CYAN = (0, 255, 255)
PURPLE = (255, 0, 255)

# Initialize Pygame
pygame.init()

# Load sound effects
bullet_sound = pygame.mixer.Sound('bullet.mp3')
enemy_destroyed_sound = pygame.mixer.Sound('invader_dies.mp3')
player_destroyed_sound = pygame.mixer.Sound('explosion.wav')

class Player:
    """Player's spaceship class with smooth movement and sprite"""
    def __init__(self, x, y):
        self.target_x = x
        self.x = x
        self.y = y
        self.width = 50
        self.height = 50
        
        # Load player sprite (NEW)
        try:
            original_sprite = pygame.image.load("ship.png")
            # Scale sprite to appropriate size
            self.sprite = pygame.transform.scale(original_sprite, (self.width, self.height))
            print("✓ Player sprite loaded: ship.png")
        except Exception as e:
            print(f"✗ Could not load ship.png: {e}")
            # Create fallback sprite
            self.width = 50
            self.height = 30
            self.sprite = pygame.Surface((self.width, self.height))
            self.sprite.fill(GREEN)
            # Draw triangle for fallback
            pygame.draw.polygon(self.sprite, GREEN, [(self.width//2, 0), (0, self.height), (self.width, self.height)])
        
        self.rect = self.sprite.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y + self.height//2
        
        self.speed = PLAYER_SPEED
        
        # Keyboard state tracking
        self.moving_left = False
        self.moving_right = False
        
        # Joystick state tracking
        self.joystick_direction = 0  # -1 for left, 0 for center, 1 for right
        self.joystick_intensity = 0  # 0-100 for smooth movement
    
    def move(self, direction):
        """Set target position based on input"""
        self.target_x += direction * self.speed
        # Keep within bounds
        if self.target_x < self.width//2:
            self.target_x = self.width//2
        elif self.target_x > SCREEN_WIDTH - self.width//2:
            self.target_x = SCREEN_WIDTH - self.width//2
    
    def update(self):
        """Smoothly move towards target position"""
        # Apply keyboard movement if active
        if self.moving_left:
            self.move(-1)
        if self.moving_right:
            self.move(1)
        
        # Apply joystick movement based on intensity
        if self.joystick_direction != 0:
            # Scale movement speed based on joystick intensity (20-100%)
            intensity_factor = max(0.2, self.joystick_intensity / 100)
            move_amount = self.joystick_direction * self.speed * intensity_factor
            self.target_x += move_amount
        
        # Keep within bounds
        if self.target_x < self.width//2:
            self.target_x = self.width//2
        elif self.target_x > SCREEN_WIDTH - self.width//2:
            self.target_x = SCREEN_WIDTH - self.width//2
        
        # Smooth interpolation
        if abs(self.x - self.target_x) > 1:
            self.x += (self.target_x - self.x) * 0.3
        else:
            self.x = self.target_x
        
        self.rect.centerx = self.x
    
    def draw(self, screen):
        """Draw player spaceship with sprite"""
        screen.blit(self.sprite, self.rect)

class Bullet:
    """Bullet class"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 3
        self.height = 10
        self.rect = pygame.Rect(x - 1, y, 3, 10)
        self.speed = BULLET_SPEED
    
    def update(self):
        """Move bullet upward"""
        self.y -= self.speed
        self.rect.y = self.y
        return self.y > 0
    
    def draw(self, screen):
        """Draw bullet"""
        pygame.draw.rect(screen, WHITE, self.rect)

class Enemy:
    """Enemy class with sprite"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 50
        self.height = 50
        
        # Load enemy sprite (NEW)
        try:
            original_sprite = pygame.image.load("spacesprite.png")
            # Scale sprite to appropriate size
            self.sprite = pygame.transform.scale(original_sprite, (self.width, self.height))
        except Exception as e:
            print(f"✗ Could not load spacesprite.png: {e}")
            self.width = 40
            self.height = 30
            # Create fallback sprite
            self.sprite = pygame.Surface((self.width, self.height))
            self.sprite.fill(RED)
        
        self.rect = self.sprite.get_rect()
        self.rect.centerx = x
        self.rect.centery = y
        
        self.direction = 1
        self.speed = ENEMY_SPEED
    
    def update(self):
        """Move enemy horizontally"""
        self.x += self.speed * self.direction
        self.rect.centerx = self.x
    
    def move_down(self):
        """Move enemy down and reverse direction"""
        self.y += 20
        self.rect.centery = self.y
        self.direction *= -1
    
    def draw(self, screen):
        """Draw enemy with sprite"""
        screen.blit(self.sprite, self.rect)

# SplashScreen class with music
class SplashScreen:
    """Splash screen displayed at game start - attempts connection 3 times then offers keyboard option"""
    def __init__(self, screen, joystick):
        self.screen = screen
        self.joystick = joystick
        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 24)
        self.font_tiny = pygame.font.Font(None, 18)
        self.start_time = time.time()
        self.sound_played = False
        self.connection_attempts = 0
        self.max_attempts = 3
        self.scan_animation = 0
        self.keyboard_mode = False
        self.attempt_start_time = time.time()
        self.attempt_timeout = 10
        
        # Load and play background music (NEW)
        self.play_music()
    
    def play_music(self):
        """Load and play background music"""
        try:
            if os.path.exists("music.mp3"):
                pygame.mixer.music.load("music.mp3")
                pygame.mixer.music.set_volume(0.5)  # Set volume to 50%
                pygame.mixer.music.play(-1)  # -1 means loop indefinitely
                print("✓ Background music started: music.mp3")
            else:
                print("✗ music.mp3 not found in game folder")
        except Exception as e:
            print(f"✗ Could not play music: {e}")
    
    def stop_music(self):
        """Stop background music"""
        try:
            pygame.mixer.music.stop()
        except:
            pass
    
    def draw_scanning_animation(self):
        """Draw a scanning/rotating animation"""
        self.scan_animation = (self.scan_animation + 1) % 360
        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2 + 50
        radius = 40
        
        for i in range(0, 360, 30):
            angle = (i + self.scan_animation) % 360
            x = center_x + radius * pygame.math.Vector2(1, 0).rotate(angle).x
            y = center_y + radius * pygame.math.Vector2(1, 0).rotate(angle).y
            color = GREEN if i % 60 == 0 else (100, 100, 100)
            pygame.draw.circle(self.screen, color, (int(x), int(y)), 5)
    
    def draw_keyboard_option(self):
        """Draw keyboard option screen"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        msg_lines = [
            "⚠️  BLUETOOTH CONNECTION FAILED",
            "",
            "Could not connect to Pico W after 3 attempts.",
            "",
            "Press ENTER to play with KEYBOARD controls",
            "Press ESC to exit",
            "",
            "Keyboard Controls:",
            "← → : Move spaceship",
            "SPACE : Fire missile",
            "R : Restart game",
            "ESC : Exit game"
        ]
        
        y_offset = SCREEN_HEIGHT // 2 - 150
        for line in msg_lines:
            if line.startswith("⚠️"):
                color = RED
                font = self.font_medium
            elif line.startswith("Keyboard Controls"):
                color = CYAN
                font = self.font_small
            else:
                color = WHITE
                font = self.font_small
            
            text_surface = font.render(line, True, color)
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH//2, y_offset))
            self.screen.blit(text_surface, text_rect)
            y_offset += 30
    
    def draw(self):
        """Draw the splash screen"""
        if self.keyboard_mode:
            self.draw_keyboard_option()
            pygame.display.flip()
            return
        
        # Create gradient background
        for i in range(SCREEN_HEIGHT):
            color_value = int(50 * (1 - i/SCREEN_HEIGHT))
            pygame.draw.line(self.screen, (color_value, 0, color_value), 
                           (0, i), (SCREEN_WIDTH, i))
        
        # Draw stars
        for _ in range(50):
            x = (pygame.time.get_ticks() + _ * 100) % SCREEN_WIDTH
            y = (_ * 20) % SCREEN_HEIGHT
            brightness = (pygame.time.get_ticks() // 100) % 255
            pygame.draw.circle(self.screen, (brightness, brightness, brightness), 
                             (int(x), int(y)), 1)
        
        # Draw enemy and player sprites in splash screen (NEW)
        try:
            # Load and draw small versions of sprites
            enemy_sprite = pygame.image.load("spacesprite.png")
            enemy_sprite = pygame.transform.scale(enemy_sprite, (100, 100)) 
            enemy_rect = enemy_sprite.get_rect(center=(SCREEN_WIDTH//2 - 120, SCREEN_HEIGHT//2 + 50))
            self.screen.blit(enemy_sprite, enemy_rect)
            
            player_sprite = pygame.image.load("ship.png")
            player_sprite = pygame.transform.scale(player_sprite, (100, 100))
            player_rect = player_sprite.get_rect(center=(SCREEN_WIDTH//2 + 120, SCREEN_HEIGHT//2 + 50))
            self.screen.blit(player_sprite, player_rect)
        except:
            # Fallback if sprites not found
            pygame.draw.rect(self.screen, RED, (SCREEN_WIDTH//2 - 130, SCREEN_HEIGHT//2 + 30, 40, 30))
            pygame.draw.rect(self.screen, GREEN, (SCREEN_WIDTH//2 + 90, SCREEN_HEIGHT//2 + 30, 50, 30))
        
        # Main title
        title_text = "SPACE INVADERS"
        
        # Draw border (yellow)
        for offset_x, offset_y in [(-3,-3), (-3,3), (3,-3), (3,3), (0,-3), (0,3), (-3,0), (3,0)]:
            border_surface = self.font_large.render(title_text, True, YELLOW)
            border_rect = border_surface.get_rect(center=(SCREEN_WIDTH//2 + offset_x, 
                                                          SCREEN_HEIGHT//2 - 100 + offset_y))
            self.screen.blit(border_surface, border_rect)
        
        # Draw main text (red)
        title_surface = self.font_large.render(title_text, True, RED)
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 100))
        self.screen.blit(title_surface, title_rect)
        
        # Subtitle
        subtitle_text = "using Bluetooth Joystick"
        subtitle_surface = self.font_medium.render(subtitle_text, True, CYAN)
        subtitle_rect = subtitle_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 30))
        self.screen.blit(subtitle_surface, subtitle_rect)
        
        # Joystick icon
        joystick_base_rect = pygame.Rect(SCREEN_WIDTH//2 - 50, SCREEN_HEIGHT//1.8 + 20, 100, 20)
        joystick_handle_pos = (SCREEN_WIDTH//2, SCREEN_HEIGHT//1.8)
        
        pygame.draw.rect(self.screen, WHITE, joystick_base_rect)
        pygame.draw.circle(self.screen, WHITE, joystick_handle_pos, 20)
        
        if self.joystick.connected:
            joystick_color = GREEN
        elif self.connection_attempts >= self.max_attempts:
            joystick_color = RED
        else:
            joystick_color = YELLOW
            
        pygame.draw.circle(self.screen, joystick_color, joystick_handle_pos, 10)
        
        # Scanning animation
        if not self.joystick.connected and self.connection_attempts < self.max_attempts:
            self.draw_scanning_animation()
        
        # Connection status
        if self.joystick.connected:
            status_text = "✓ Bluetooth Connected!"
            status_color = GREEN
        elif self.connection_attempts >= self.max_attempts:
            status_text = "✗ Connection Failed - Press ENTER for keyboard mode"
            status_color = RED
        else:
            remaining_time = max(0, self.attempt_timeout - (time.time() - self.attempt_start_time))
            status_text = f"Connection Attempt {self.connection_attempts + 1}/{self.max_attempts} - Timeout: {remaining_time:.0f}s"
            status_color = YELLOW
        
        status_surface = self.font_medium.render(status_text, True, status_color)
        status_rect = status_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 120))
        self.screen.blit(status_surface, status_rect)
        
        # Device info
        if self.joystick.device_address and not self.joystick.connected and self.connection_attempts < self.max_attempts:
            device_text = f"Found device at {self.joystick.device_address}"
            device_surface = self.font_small.render(device_text, True, WHITE)
            device_rect = device_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 150))
            self.screen.blit(device_surface, device_rect)
        
        # Instructions
        if not self.joystick.connected and self.connection_attempts < self.max_attempts:
            instr_text = "Make sure Pico W is powered and running the joystick code"
            instr_surface = self.font_tiny.render(instr_text, True, WHITE)
            instr_rect = instr_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 180))
            self.screen.blit(instr_surface, instr_rect)
        
        instr2_text = "Press ESC to exit"
        instr2_surface = self.font_small.render(instr2_text, True, GREEN)
        instr2_rect = instr2_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 210))
        self.screen.blit(instr2_surface, instr2_rect)
        
        pygame.display.flip()
    
    def should_close(self):
        """Check if splash screen should close"""
        return self.joystick.connected or self.keyboard_mode
    
    def handle_events(self):
        """Handle events during splash screen"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_RETURN and self.connection_attempts >= self.max_attempts:
                    self.keyboard_mode = True
                    return True
        return True
    
    def update_connection_attempts(self):
        """Update connection attempt counter"""
        self.connection_attempts += 1
        self.attempt_start_time = time.time()
        print(f"   Connection attempt {self.connection_attempts}/{self.max_attempts}")
    
    def check_attempt_timeout(self):
        """Check if current attempt has timed out"""
        if not self.joystick.connected and self.connection_attempts < self.max_attempts:
            elapsed = time.time() - self.attempt_start_time
            return elapsed >= self.attempt_timeout
        return False

class SpaceInvadersGame:
    """Main game class with optimized input handling"""
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Space Invaders - Bluetooth Control (Calibrated)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        # Create sound effects
        self.explosion_sound = self.create_explosion_sound()
        self.splash_sound = self.create_splash_sound()
        
        # Joystick calibration
        self.raw_joystick_x = 32768
        self.calibrated_joystick_x = 0
        self.raw_joystick_y = 32768
        self.calibrated_joystick_y = 0
        
        self.joystick_button = 1
        self.button_pressed = False
        self.last_shot_time = 0
        self.shot_cooldown = 200
        
        # Calibration parameters
        self.x_center = 50300
        self.x_min = 20000
        self.x_max = 60000
        self.x_deadzone = 1000
        
        # Performance monitoring
        self.fps_history = deque(maxlen=60)
        self.last_fps_update = time.time()
        
        # Debug variables
        self.last_received_time = time.time()
        self.receive_count = 0
        self.debug_message = "Waiting for data..."
        self.last_raw_x = 32768
        self.last_raw_y = 32768
        self.last_button_display = 1
        
        # Game state
        self.game_started = False
        self.keyboard_mode = False
        self.joystick_connected = False
        
        self.reset_game()
    
    def create_splash_sound(self):
        """Create a classic arcade startup sound"""
        try:
            sample_rate = 22050
            duration = 0.3
            samples = bytearray()
            
            for i in range(int(sample_rate * duration)):
                freq = 220 + (i * 440 / (sample_rate * duration))
                value = int(16384 * ((i * 2) % 2))
                samples.extend(value.to_bytes(2, 'little', signed=True))
            
            return pygame.mixer.Sound(buffer=bytes(samples))
        except Exception as e:
            print(f"Could not create splash sound: {e}")
            return None
    
    def create_explosion_sound(self):
        """Create a simple explosion sound"""
        try:
            sound_file = "invader_dies.mp3"  #"explosion.wav"
            if os.path.exists(sound_file):
                return pygame.mixer.Sound(sound_file)
            
            sample_rate = 22050
            duration = 0.1
            frequency = 440
            
            samples = bytearray()
            for i in range(int(sample_rate * duration)):
                value = int(32767 * (1 if (int(i * frequency / sample_rate) % 2) else -1))
                samples.extend(value.to_bytes(2, 'little', signed=True))
            
            sound = pygame.mixer.Sound(buffer=bytes(samples))
            return sound
            
        except Exception as e:
            print(f"Could not create sound: {e}")
            return None
    
    def reset_game(self):
        """Reset game to initial state"""
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50)
        self.bullets = []
        self.enemies = []
        self.score = 0
        self.game_over = False
        self.win = False
        
        # Create enemies
        for row in range(3):
            for col in range(12):
                enemy = Enemy(100 + col * 70, 50 + row * 60)
                self.enemies.append(enemy)
    
    def calibrate_joystick(self, raw_value):
        """Convert raw joystick value to calibrated value (-100 to 100)"""
        if abs(raw_value - self.x_center) < self.x_deadzone:
            return 0
        
        if raw_value < self.x_center:
            if raw_value <= self.x_min:
                return -100
            return -((self.x_center - raw_value) / (self.x_center - self.x_min)) * 100
        else:
            if raw_value >= self.x_max:
                return 100
            return ((raw_value - self.x_center) / (self.x_max - self.x_center)) * 100
    
    # Joystick input handler - stores state for smooth movement
    def handle_joystick_input(self, x_value, y_value, button_state):
        """Process joystick data - called from Bluetooth thread"""
        self.last_raw_x = x_value
        self.last_raw_y = y_value
        self.last_received_time = time.time()
        self.receive_count += 1
        self.last_button_display = button_state
        
        self.raw_joystick_x = x_value
        self.raw_joystick_y = y_value
        
        self.calibrated_joystick_x = self.calibrate_joystick(x_value)
        
        # Update player joystick state for smooth movement
        if self.joystick_connected:
            if self.calibrated_joystick_x < -20:
                self.player.joystick_direction = -1
                self.player.joystick_intensity = min(100, abs(self.calibrated_joystick_x))
            elif self.calibrated_joystick_x > 20:
                self.player.joystick_direction = 1
                self.player.joystick_intensity = min(100, abs(self.calibrated_joystick_x))
            else:
                self.player.joystick_direction = 0
                self.player.joystick_intensity = 0
        
        # Print occasional debug info
        if self.receive_count % 10 == 0:
            direction = "CENTER"
            if self.calibrated_joystick_x < -10:
                direction = "LEFT"
            elif self.calibrated_joystick_x > 10:
                direction = "RIGHT"
            
            print(f"DEBUG - Raw X={x_value:5d} | Calibrated={self.calibrated_joystick_x:6.1f} | {direction} | Intensity={self.player.joystick_intensity:.0f}%")
        
        # Handle button press for shooting
        if not self.keyboard_mode and button_state == 0 and not self.button_pressed:
            current_time = pygame.time.get_ticks()
            if current_time - self.last_shot_time > self.shot_cooldown:
                self.bullets.append(Bullet(self.player.x, self.player.y - 20))
                self.last_shot_time = current_time
                self.button_pressed = True
        elif button_state == 1:
            self.button_pressed = False
    
    # Handle keyboard input
    def handle_keyboard_input(self, key, pressed):
        """Process keyboard input for player movement"""
        if key == pygame.K_LEFT:
            self.player.moving_left = pressed
            # Disable joystick movement when using keyboard
            if pressed:
                self.player.joystick_direction = 0
        elif key == pygame.K_RIGHT:
            self.player.moving_right = pressed
            # Disable joystick movement when using keyboard
            if pressed:
                self.player.joystick_direction = 0
        elif key == pygame.K_SPACE and pressed:
            # Space bar for shooting
            current_time = pygame.time.get_ticks()
            if current_time - self.last_shot_time > self.shot_cooldown:
                self.bullets.append(Bullet(self.player.x, self.player.y - 20))
                self.last_shot_time = current_time
                bullet_sound.play()  # Play bullet sound when bullet is fired
    
    def update(self):
        """Update game state"""
        if self.game_over or self.win:
            return
        
        # Update player position (handles both keyboard and joystick)
        self.player.update()
        
        # Update bullets
        for bullet in self.bullets[:]:
            if not bullet.update():
                self.bullets.remove(bullet)
        
        # Update enemies
        move_down = False
        for enemy in self.enemies:
            enemy.update()
            if enemy.x > SCREEN_WIDTH - 30 or enemy.x < 30:
                move_down = True
        
        if move_down:
            for enemy in self.enemies:
                enemy.move_down()
        
        # Check collisions
        for bullet in self.bullets[:]:
            bullet_rect = bullet.rect
            for enemy in self.enemies[:]:
                if bullet_rect.colliderect(enemy.rect):
                    if self.explosion_sound:
                        self.explosion_sound.play()
                    
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    self.enemies.remove(enemy)
                    self.score += 10
                    break
        
        # Check game over conditions
        for enemy in self.enemies:
            if enemy.y > SCREEN_HEIGHT - 100:
                player_destroyed_sound.play()  # Play bullet sound when bullet is fired
                self.game_over = True
        
        if len(self.enemies) == 0:
            self.win = True
    
    def draw(self):
        """Draw game elements"""
        self.screen.fill(BLACK)
        
        if self.game_over:
            text = self.font.render("GAME OVER! Press R to restart", True, WHITE)
            text_rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(text, text_rect)
        elif self.win:
            text = self.font.render("YOU WIN! Press R to restart", True, WHITE)
            text_rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(text, text_rect)
        else:
            self.player.draw(self.screen)
            for bullet in self.bullets:
                bullet.draw(self.screen)
            for enemy in self.enemies:
                enemy.draw(self.screen)
            
            # Draw score
            score_text = self.font.render(f"Score: {self.score}", True, WHITE)
            self.screen.blit(score_text, (10, 10))
            
            # Draw mode indicator
            if self.keyboard_mode:
                mode_text = self.small_font.render("KEYBOARD MODE", True, ORANGE)
            elif self.joystick_connected:
                mode_text = self.small_font.render("JOYSTICK MODE", True, GREEN)
            else:
                mode_text = self.small_font.render("NO CONTROLLER", True, RED)
            self.screen.blit(mode_text, (SCREEN_WIDTH - 280, 10))
            
            # Draw debug info
            current_time = time.time()
            time_since_last = current_time - self.last_received_time
            
            if time_since_last < 0.1:
                status_color = GREEN
                status_text = "RECEIVING DATA"
            elif time_since_last < 0.5:
                status_color = YELLOW
                status_text = "INTERMITTENT"
            else:
                status_color = RED
                status_text = "NO DATA"
            
            conn_text = self.small_font.render(f"BLE: {status_text}", True, status_color)
            self.screen.blit(conn_text, (10, SCREEN_HEIGHT - 115))
            
            raw_text = self.small_font.render(
                f"RAW X:{self.last_raw_x:5d} Y:{self.last_raw_y:5d}", 
                True, CYAN
            )
            self.screen.blit(raw_text, (10, SCREEN_HEIGHT - 95))
            
            cal_color = GREEN if abs(self.calibrated_joystick_x) < 20 else YELLOW
            cal_text = self.small_font.render(
                f"CALIB: {self.calibrated_joystick_x:+6.1f}%", 
                True, cal_color
            )
            self.screen.blit(cal_text, (10, SCREEN_HEIGHT - 75))
            
            # Joystick position bar
            bar_width = 200
            bar_height = 15
            bar_x = 10
            bar_y = SCREEN_HEIGHT - 55
            
            pygame.draw.rect(self.screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
            
            pos = int(((self.calibrated_joystick_x + 100) / 200) * bar_width)
            pos = max(0, min(bar_width, pos))
            
            indicator_color = RED if abs(self.calibrated_joystick_x) > 50 else YELLOW
            pygame.draw.rect(self.screen, indicator_color, (bar_x + pos - 2, bar_y - 2, 4, bar_height + 4))
            
            pygame.draw.line(self.screen, WHITE, (bar_x + bar_width//2, bar_y - 2), 
                           (bar_x + bar_width//2, bar_y + bar_height + 2), 1)
            
            # Button state
            btn_text = self.small_font.render(
                f"Button: {'PRESSED' if self.last_button_display == 0 else 'RELEASED'}", 
                True, WHITE
            )
            self.screen.blit(btn_text, (10, SCREEN_HEIGHT - 35))
            
            # Packet count
            pkt_text = self.small_font.render(f"Packets: {self.receive_count}", True, WHITE)
            self.screen.blit(pkt_text, (10, SCREEN_HEIGHT - 15))
            
            # Sound indicator
            if self.explosion_sound:
                sound_text = self.small_font.render("SOUND: ON", True, GREEN)
            else:
                sound_text = self.small_font.render("SOUND: OFF", True, RED)
            self.screen.blit(sound_text, (SCREEN_WIDTH - 120, SCREEN_HEIGHT - 40))
            
            # FPS display
            current_time = time.time()
            if current_time - self.last_fps_update >= 0.5:
                self.fps_history.append(self.clock.get_fps())
                self.last_fps_update = current_time
            
            if self.fps_history:
                avg_fps = sum(self.fps_history) / len(self.fps_history)
                fps_text = self.small_font.render(f"FPS: {avg_fps:.1f}", True, GREEN)
                self.screen.blit(fps_text, (SCREEN_WIDTH - 100, 10))
        
        pygame.display.flip()
    
    # Run splash screen with connection attempts
    async def run_splash(self, joystick):
        """Run the splash screen and attempt connection 3 times, then offer keyboard option"""
        splash = SplashScreen(self.screen, joystick)
        
        if self.splash_sound and not splash.sound_played:
            self.splash_sound.play()
            splash.sound_played = True
        
        print("\n Splash screen active - attempting Bluetooth connection...")
        print("   Will try 3 times, then offer keyboard mode")
        print("   Press ESC to exit\n")
        
        connection_task = None
        
        while not splash.should_close():
            # Start connection attempt if needed
            if not joystick.connected and splash.connection_attempts < splash.max_attempts and (connection_task is None or connection_task.done()):
                if connection_task and connection_task.done():
                    try:
                        await connection_task
                    except:
                        pass
                
                splash.update_connection_attempts()
                connection_task = asyncio.create_task(joystick.connect_and_receive())
            
            # Check for timeout
            if splash.check_attempt_timeout():
                print(f"   Attempt {splash.connection_attempts} timed out")
                if connection_task and not connection_task.done():
                    connection_task.cancel()
                    try:
                        await connection_task
                    except:
                        pass
                connection_task = None
            
            # Draw splash screen
            splash.draw()
            
            # Handle events
            if not splash.handle_events():
                if connection_task and not connection_task.done():
                    connection_task.cancel()
                    try:
                        await connection_task
                    except:
                        pass
                # Stop music when exiting (NEW)
                splash.stop_music()
                return False
            
            # Check max attempts
            if splash.connection_attempts >= splash.max_attempts and not joystick.connected:
                if splash.keyboard_mode:
                    print("\n Keyboard mode selected")
                    self.keyboard_mode = True
                    # Stop music when entering keyboard mode (NEW)
                    splash.stop_music()
                    break
            
            await asyncio.sleep(0.05)
            self.clock.tick(30)
        
        # Stop music when leaving splash screen (NEW)
        splash.stop_music()
        pygame.mixer.music.load('music.mp3')
        pygame.mixer.music.play(-1)  # The -1 makes the music loop indefinitely
        return True

class BluetoothJoystick:
    """Bluetooth handler for joystick data"""
    def __init__(self, game):
        self.game = game
        self.device_address = None
        self.client = None
        self.connected = False
        self.data_count = 0
        self.last_print_time = time.time()
        
    async def scan_for_pico(self):
        """Scan for Pico W Bluetooth device"""
        print("   Scanning for Pico W Joystick...")
        scanner = bleak.BleakScanner()
        devices = await scanner.discover(timeout=2)
        
        for device in devices:
            device_name = getattr(device, 'name', None)
            if device_name and ("Joystick_Pico_Fast" in device_name or "Joystick_Pico" in device_name):
                self.device_address = device.address
                print(f"   ✓ Found Pico W: {device_name} at {device.address}")
                return True
        
        return False
    
    async def notification_handler(self, sender, data):
        """Handle incoming Bluetooth data"""
        try:
            x_value, y_value, button_state = struct.unpack('HHH', data)
            
            self.data_count += 1
            if self.data_count % 50 == 0:
                print(f"BLE Raw: X={x_value}, Y={y_value}, Button={button_state}")
            
            # Update game with joystick data
            self.game.handle_joystick_input(x_value, y_value, button_state)
            
            current_time = time.time()
            if current_time - self.last_print_time > 2:
                rate = self.data_count / 2
                print(f" Joystick data rate: {rate:.0f} Hz")
                self.data_count = 0
                self.last_print_time = current_time
                
        except Exception as e:
            print(f"✗ Error processing data: {e}")
    
    async def connect_and_receive(self):
        """Connect to Pico W and start receiving data"""
        if not self.device_address:
            if not await self.scan_for_pico():
                return False
        
        try:
            print(f"   Connecting to {self.device_address}...")
            self.client = bleak.BleakClient(self.device_address)
            await self.client.connect()
            self.connected = True
            self.game.joystick_connected = True
            print("   ✓ Connected to Pico W!")
            
            await asyncio.sleep(1)
            
            joystick_char_uuid = "12345678-1234-5678-1234-56789abcdef1"
            
            await self.client.start_notify(joystick_char_uuid, self.notification_handler)
            print("   ✓ Started receiving joystick data")
            
            return True
            
        except Exception as e:
            print(f"   ✗ Connection failed: {e}")
            self.device_address = None
            self.game.joystick_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Pico W"""
        if self.client and self.client.is_connected:
            try:
                await self.client.disconnect()
                self.game.joystick_connected = False
                print("Disconnected from Pico W")
            except:
                pass

async def main():
    """Main async function"""
    print("=" * 70)
    print("SPACE INVADERS - Bluetooth Joystick Control (CALIBRATED WITH SOUND)")
    print("=" * 70)
    
    # Check for required files (NEW)
    print("\n Checking for required files:")
    required_files = ["ship.png", "spacesprite.png", "music.mp3"]
    for file in required_files:
        if os.path.exists(file):
            print(f"   ✓ {file} found")
        else:
            print(f"   ⚠️ {file} not found - using fallback")
    
    # Initialize game
    game = SpaceInvadersGame()
    joystick = BluetoothJoystick(game)
    
    # Show splash screen with connection attempts
    if not await game.run_splash(joystick):
        print("\nGame closed from splash screen")
        await joystick.disconnect()
        pygame.quit()
        sys.exit(0)
    
    if game.keyboard_mode:
        print("\n Playing in KEYBOARD MODE")
        print("   Controls: ← → move, SPACE fire, R restart, ESC exit")
    else:
        print("\n Joystick Calibration Info:")
        print("   Based on your Pico W readings:")
        print("   - Resting X value: ~50300 (automatically calibrated)")
        print("   - Dead zone: 1000 (ignores small movements)")
        print("   - Movement threshold: 20%")
        print("   - Intensity-based speed: Moves faster with more joystick tilt")
        print("\n🔊 Sound Effects: Added explosion sounds when enemies are hit!")
    
    print("\n Game started! Press ESC to exit.\n")
    
    # Game loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and (game.game_over or game.win):
                    game.reset_game()
                elif event.key == pygame.K_ESCAPE:
                    running = False
                # Keyboard controls
                elif event.key == pygame.K_LEFT:
                    game.handle_keyboard_input(pygame.K_LEFT, True)
                elif event.key == pygame.K_RIGHT:
                    game.handle_keyboard_input(pygame.K_RIGHT, True)
                elif event.key == pygame.K_SPACE:
                    game.handle_keyboard_input(pygame.K_SPACE, True)
            elif event.type == pygame.KEYUP:
                # Handle key release for smooth movement
                if event.key == pygame.K_LEFT:
                    game.handle_keyboard_input(pygame.K_LEFT, False)
                elif event.key == pygame.K_RIGHT:
                    game.handle_keyboard_input(pygame.K_RIGHT, False)
        
        game.update()
        game.draw()
        game.clock.tick(60)
        await asyncio.sleep(0.001)
    
    await joystick.disconnect()
    pygame.quit()
    print("\nGame ended. Thanks for playing!")
    sys.exit()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nGame interrupted by user")
        pygame.quit()
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        pygame.quit()
        sys.exit(1)

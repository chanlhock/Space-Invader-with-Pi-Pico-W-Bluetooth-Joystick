import pygame
import random

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
PLAYER_SPEED = 3
ENEMY_SPEED = 1
BULLET_SPEED = 5
ENEMY_DROP_HEIGHT = 10
SCORE_PER_ENEMY = 10
FPS = 60

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
pygame.display.set_caption("Space Invaders")

# Clock for controlling frame rate
clock = pygame.time.Clock()

# Load music
pygame.mixer.music.load('music.mp3')
pygame.mixer.music.play(-1)  # The -1 makes the music loop indefinitely

# Load sound effects
bullet_sound = pygame.mixer.Sound('bullet.mp3')
enemy_destroyed_sound = pygame.mixer.Sound('invader_dies.mp3')

# Player Class
class Player:
    def __init__(self):
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT - 60
        self.speed = PLAYER_SPEED
        self.sprite = pygame.image.load('ship.png').convert_alpha()  # Load the ship sprite
        self.sprite = pygame.transform.scale(self.sprite, (50, 50))  # Scale to appropriate size

    def move(self, direction):
        if direction == "LEFT" and self.x > 0:
            self.x -= self.speed
        if direction == "RIGHT" and self.x < SCREEN_WIDTH - 50:
            self.x += self.speed

    def draw(self):
        screen.blit(self.sprite, (self.x, self.y))  # Draw the ship sprite  

# Enemy Class
class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = ENEMY_SPEED
        self.sprite = pygame.image.load('spacesprite.png').convert_alpha()  # Ensure correct path
        self.sprite = pygame.transform.scale(self.sprite, (50, 50))  # Scale as needed

    def draw(self):
        screen.blit(self.sprite, (self.x, self.y))

    def move(self):
        self.y += self.speed

# Bullet Class
class Bullet:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = BULLET_SPEED

    def move(self):
        self.y -= self.speed

    def draw(self):
        pygame.draw.rect(screen, (255, 255, 255), (self.x + 22, self.y, 5, 10))

# Collision Detection
def check_collision(enemy, bullet):
    return enemy.x < bullet.x < enemy.x + 50 and enemy.y < bullet.y < enemy.y + 50

# Create a player instance
player = Player()

# Create enemies in a grid
enemies = [Enemy(x, y) for x in range(100, 700, 60) for y in range(50, 200, 60)]
enemy_direction = 1

# Bullet list
bullets = []

# Score
score = 0

# Main game loop
running = True
game_over = False
while running:
    clock.tick(FPS)  # Control the frame rate
    screen.fill((0, 0, 0))  # Clear the screen

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                bullets.append(Bullet(player.x, player.y))
                bullet_sound.play()  # Play bullet sound when bullet is fired

    # Player movement
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        player.move("LEFT")
    if keys[pygame.K_RIGHT]:
        player.move("RIGHT")

    # Update and draw the player
    player.draw()

    # Move enemies
    for enemy in enemies:
        enemy.x += ENEMY_SPEED * enemy_direction
        if enemy.x <= 0 or enemy.x >= SCREEN_WIDTH - 50:
            enemy_direction *= -1
            for e in enemies:
                e.y += ENEMY_DROP_HEIGHT
            break

    # Update and draw enemies
    for enemy in enemies:
        enemy.draw()

    # Update and draw bullets
    for bullet in bullets[:]:
        bullet.move()
        bullet.draw()
        if bullet.y < 0:
            bullets.remove(bullet)

    # Play enemy destroyed sound when enemy is destroyed
    for bullet in bullets[:]:
        for enemy in enemies[:]:
            if check_collision(enemy, bullet):
                enemies.remove(enemy)
                bullets.remove(bullet)
                score += SCORE_PER_ENEMY
                enemy_destroyed_sound.play()
                break  # Break to avoid modifying list during iteration

    # Winning condition
    if not enemies:
        print("You won!")
        game_over = True
        running = False

    # Check if any enemy has reached the player
    for enemy in enemies:
        if enemy.y >= player.y:
            print("Game Over!")
            game_over = True
            running = False
            break

    # Display score
    font = pygame.font.Font(None, 36)
    text = font.render(f"Score: {score}", 1, (255, 255, 255))
    screen.blit(text, (10, 10))

    pygame.display.update()

# Game over screen
while game_over:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game_over = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                game_over = False

    screen.fill((0, 0, 0))
    font = pygame.font.Font(None, 72)
    if enemies:
        text = font.render("Game Over!", 1, (255, 255, 255))
    else:
        text = font.render("You won!", 1, (255, 255, 255))
    screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - text.get_height() // 2))
    pygame.display.update()

pygame.quit()

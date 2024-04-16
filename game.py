import ast
import math
import os
import sys
from random import randint, uniform
from typing import Union
import random
import pygame
import tkinter as tk
from tkinter import filedialog
import importlib.machinery
import importlib.util
import sys


# from saves.grid import grid as gd
Point = pygame.Vector2
# highscore 25
# INITIAL RUNTIME CONFIGURATIONS

# You can edit these accordingly based on the modules you have

SMOOTH = True  # uses numpy + scipy
TEXTURE = False  # uses texture images
VOLUME_RISE = True
USE_PYMUNK = True  # uses pymunk
FPS = 60
GRAVITY = (0, 500)

import numpy
from scipy.interpolate import interp1d
import pymunk

pygame.init()
# Screen dimensions
infoObject: object = pygame.display.Info()
WIDTH, HEIGHT = infoObject.current_w, infoObject.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Satisfying Movement System")

frame_count = 0  # Count frames for lightning duration
lightning_duration = 10  # Adjust the duration of the lightning effect


raindrops = []
lightning_pos = [(0, 0), (0, 0)]
clouds = []
leaves = []
wind = 0
newwind = 0
weather = "thunderstorm"  # Initial weather\

# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 0, 255)
# Player attributes
player_size = 50
player_speed = 0.0
player_max_speed = 15
score = 0
player_acceleration = 0.2
player_dash_speed = 25.0
player_jump_strength = 15.0
gravity = 0.8
player_x = 9
player_y = HEIGHT // 2 - player_size // 2
player_velocity = [0, 0]
is_dashing = False
dash_cooldown = 60  # Cooldown frames for dash
dash_timer = 0
is_jumping = False
is_on_ground = False
is_on_wall = False
wall_jump_cooldown = 10
wall_jump_timer = 0
splasheffecttimer = 0
rain = 10
newrain = 10
# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (80, 80, 80)
DARK_GRAY = (64, 64, 64)
BLACK = (0, 0, 0)

# Tile attributes
TILE_SIZE = 32
GRID_WIDTH, GRID_HEIGHT = WIDTH // TILE_SIZE, HEIGHT // TILE_SIZE
grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
# grid = gd #might not work with different display sizes or tile sizes
font = pygame.font.SysFont("consolas", 25)

if USE_PYMUNK:
    space = pymunk.Space()
    space.gravity = GRAVITY


def map_to_range(value, from_x, from_y, to_x, to_y):
    return value * (to_y - to_x) / (from_y - from_x)


class Ball:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.height = randint(2, 10)
        self.width = randint(5, 50 + 20)
        self.dy = 0
        self.spring: Union["WaterSpring", None] = None
        self.next_spring: Union["WaterSpring", None] = None
        self.rot = randint(0, 360)
        self.rot = 0
        self.gravity = 0.5
        self.water_force = 2
        self.on_water_surface = False

    def update(self):
        if self.spring:
            if self.on_water_surface:
                self.y = self.spring.height - self.height
            else:
                self.dy -= self.water_force
                self.y += self.dy
                if self.dy < 0 and self.y < self.spring.height:
                    self.on_water_surface = True
        else:
            self.dy += self.gravity
            self.y += self.dy

    def draw(self, surf: pygame.Surface):
        size = 50
        if TEXTURE:
            img = pygame.transform.scale(BALL_IMAGE, (size, size))
            surf.blit(img, img.get_rect(center=(self.x, self.y)))
        else:
            pygame.draw.circle(surf, "green", (self.x, self.y), size / 2)


class WaterSpring:
    def __init__(self, x=0, target_height=None):
        if not target_height:
            self.target_height = HEIGHT // 2 + 150
        else:
            self.target_height = target_height
        self.dampening = 0.05  # adjust accordingly
        self.tension = 0.01
        self.height = self.target_height
        self.vel = 0
        self.x = x

    def update(self):
        dh = self.target_height - self.height
        if abs(dh) < 0.01:
            self.height = self.target_height
        self.vel += self.tension * dh - self.vel * self.dampening
        self.height += self.vel

    def draw(self, surf: pygame.Surface):
        pygame.draw.circle(surf, "white", (self.x, self.height), 1)


class Wave:
    def __init__(self):
        diff = 20
        self.springs = [
            WaterSpring(x=i * diff + 0, target_height=HEIGHT - 100)
            for i in range(WIDTH // diff + 2)
        ]
        self.points = []
        self.diff = diff

    def get_spring_index_for_x_pos(self, x):
        return int(x // self.diff)

    def get_target_height(self):
        return self.springs[0].target_height

    def set_target_height(self, height):
        for i in self.springs:
            i.target_height = height

    def add_volume(self, volume):

        height = volume / WIDTH
        self.set_target_height(self.get_target_height() - height)

    def update(self):
        for i in self.springs:
            i.update()
        self.spread_wave()
        self.points = [Point(i.x, i.height) for i in self.springs]
        if SMOOTH:
            self.points = get_curve(self.points)
        self.points.extend([Point(WIDTH, HEIGHT), Point(0, HEIGHT)])

    def draw(self, surf: pygame.Surface):
        pygame.draw.polygon(surf, (0, 0, 255, 50), self.points)

    def draw_line(self, surf: pygame.Surface):
        pygame.draw.lines(surf, "white", False, self.points[:-2], 5)

    def spread_wave(self):
        spread = 0.1
        for i in range(len(self.springs)):
            if i > 0:
                self.springs[i - 1].vel += spread * (
                    self.springs[i].height - self.springs[i - 1].height
                )
            try:
                self.springs[i + 1].vel += spread * (
                    self.springs[i].height - self.springs[i + 1].height
                )
            except IndexError:
                pass

    def splash(self, index, vel):
        try:
            self.springs[index].vel += vel
            return vel
        except IndexError:
            pass


class FlameParticle:
    alpha_layer_qty = 2
    alpha_glow_difference_constant = 2

    def __init__(self, x=WIDTH // 2, y=HEIGHT // 2, r=5):
        self.x = x
        self.y = y
        self.r = r
        self.original_r = r
        self.alpha_layers = FlameParticle.alpha_layer_qty
        self.alpha_glow = FlameParticle.alpha_glow_difference_constant
        max_surf_size = (
            2 * self.r * self.alpha_layers * self.alpha_layers * self.alpha_glow
        )
        self.surf = pygame.Surface((max_surf_size, max_surf_size), pygame.SRCALPHA)
        self.burn_rate = 0.1 * random.randint(1, 4)

    def update(self, down):
        ychange = -7 + self.r * 2 if down else 7
        self.y -= ychange - self.r
        self.x += random.randint(-self.r, self.r)
        self.original_r -= self.burn_rate
        self.r = int(self.original_r)
        if self.r <= 0:
            self.r = 1

    def draw(self, screen):
        max_surf_size = (
            2 * self.r * self.alpha_layers * self.alpha_layers * self.alpha_glow
        )
        self.surf = pygame.Surface((max_surf_size, max_surf_size), pygame.SRCALPHA)
        for i in range(self.alpha_layers, -1, -1):
            alpha = 255 - i * (255 // self.alpha_layers - 5)
            if alpha <= 0:
                alpha = 0
            radius = self.r * i * i * self.alpha_glow
            if self.r == 4 or self.r == 3:
                r, g, b = (255, 0, 0)
            elif self.r == 2:
                r, g, b = (255, 150, 0)
            else:
                r, g, b = (50, 50, 50)
            # r, g, b = (0, 0, 255)  # uncomment this to make the flame blue
            color = (r, g, b, alpha)
            pygame.draw.circle(
                self.surf,
                color,
                (self.surf.get_width() // 2, self.surf.get_height() // 2),
                radius,
            )
        screen.blit(self.surf, self.surf.get_rect(center=(self.x, self.y)))

    def drawb(self, screen):
        max_surf_size = 2 * self.r
        self.surf = pygame.Surface((max_surf_size, max_surf_size), pygame.SRCALPHA)
        for i in range(self.alpha_layers, -1, -1):
            alpha = 255 - i * (255 // self.alpha_layers - 5)
            if alpha <= 0:
                alpha = 0
            radius = self.r * i * i * self.alpha_glow
            # Color of bubble
            r, g, b = (200, 200, 255)  # Light blue color for bubble
            color = (r, g, b, alpha)
            pygame.draw.circle(
                self.surf,
                color,
                (self.surf.get_width() // 2, self.surf.get_height() // 2),
                int(radius),
            )
        screen.blit(self.surf, self.surf.get_rect(center=(self.x, self.y)))


class Flame:
    def __init__(self, x=WIDTH // 2, y=HEIGHT // 2):
        """Initializes a flame object at the center of the screen.
        Parameters:
            - x (int): x-coordinate of the flame's center.
            - y (int): y-coordinate of the flame's center.
        Returns:
            - None: Does not return anything.
        Processing Logic:
            - Initialize flame at center of screen.
            - Set flame intensity to 2.
            - Create 25 flame particles per intensity.
            - Randomize flame particle coordinates and size."""
        self.x = x
        self.y = y
        self.flame_intensity = 2
        self.flame_particles = []
        for i in range(self.flame_intensity * 25):
            self.flame_particles.append(
                FlameParticle(
                    self.x + random.randint(-5, 5), self.y, random.randint(1, 5)
                )
            )

    def draw_flame(self, screen):
        for i in self.flame_particles:
            if i.original_r <= 0:
                self.flame_particles.remove(i)
                self.flame_particles.append(
                    FlameParticle(
                        self.x + random.randint(-5, 5), self.y, random.randint(1, 5)
                    )
                )
                del i
                continue
            i.update(False)
            i.draw(screen)

    def draw_bubbles(self, screen, maxheight=5, maxspread=5, down=False):
        for i in self.flame_particles:
            if i.original_r <= 0:
                self.flame_particles.remove(i)
                if maxheight == maxspread:
                    if random.choice([True, False]):
                        maxheight += randint(-1, 1)
                    else:
                        maxspread += randint(-1, 1)
                maxheight = min([maxheight, 8])
                maxspread = min([maxspread, 8])
                addx = random.randint(-maxspread, maxspread)
                # if maxheight==1:
                #    maxheight+=randint(-1,1)
                try:
                    r = random.randint(1, maxheight)
                except:
                    r = 1
                self.flame_particles.append(FlameParticle(self.x + addx, self.y, r))
                del i
                continue
            i.update(down)
            i.drawb(screen)


def get_curve(points):
    """Parameters:
        - points (list): A list of Point objects that represent a curve.
    Returns:
        - points (list): A list of Point objects that represent a curve with a higher resolution.
    Processing Logic:
        - Creates a new x array.
        - Creates x and y arrays from points.
        - Uses cubic interpolation to create a new y array.
        - Creates new Point objects from the new x and y arrays."""
    x_new = numpy.arange(points[0].x, points[-1].x, 1)
    x = numpy.array([i.x for i in points[:-1]])
    y = numpy.array([i.y for i in points[:-1]])
    f = interp1d(x, y, kind="cubic", fill_value="extrapolate")
    y_new = f(x_new)
    x1 = list(x_new)
    y1 = list(y_new)
    points = [Point(x1[i], y1[i]) for i in range(len(x1))]
    return points


def draw_speed_lines(screen):
    # Draw lines from the edges to the center
    pygame.draw.line(screen, WHITE, (0, 0), (WIDTH // 2, HEIGHT // 2))
    pygame.draw.line(screen, WHITE, (WIDTH, 0), (WIDTH // 2, HEIGHT // 2))
    pygame.draw.line(screen, WHITE, (0, HEIGHT), (WIDTH // 2, HEIGHT // 2))
    pygame.draw.line(screen, WHITE, (WIDTH, HEIGHT), (WIDTH // 2, HEIGHT // 2))


def create_walls():
    base = pymunk.Body(mass=10**5, moment=0, body_type=pymunk.Body.STATIC)
    base.position = (WIDTH // 2, HEIGHT + 25)
    base_shape = pymunk.Poly.create_box(base, (WIDTH, 50))
    base_shape.friction = 0.2
    space.add(base, base_shape)

    wall_left = pymunk.Body(mass=10**5, moment=0, body_type=pymunk.Body.STATIC)
    wall_left.position = (-50, HEIGHT // 2)
    wall_left_shape = pymunk.Poly.create_box(wall_left, (100, HEIGHT))
    space.add(wall_left, wall_left_shape)

    wall_right = pymunk.Body(mass=10**5, moment=0, body_type=pymunk.Body.STATIC)
    wall_right.position = (WIDTH + 50, HEIGHT // 2)
    wall_right_shape = pymunk.Poly.create_box(wall_right, (100, HEIGHT))
    space.add(wall_right, wall_right_shape)


flames = {}


def LightAlgorithm(colors, x, y, playerX, playerY, TimeOfDay):
    SunPos = [TimeOfDay * 25, TimeOfDay * 10]
    blockPos = [x, y]
    Darken = round(math.dist(blockPos, SunPos) * TimeOfDay)
    num_list = [100, 139, 69, 19, 115, 85, 34, 0, 128, 211, 255, 223, 135, 206, 235]

    colorslist = []
    for num in num_list:
        colorslist.append(
            (
                max(num - Darken, 0),
                max(num - Darken if i % 3 != 1 else num, 0),
                max(num - Darken if i % 3 == 0 else num, 0),
            )
        )
    return colorslist


# Define a function to draw the grid
def draw_grid():
    for row in range(GRID_HEIGHT):
        for col in range(GRID_WIDTH):
            if grid[row][col] == 1 or grid[row][col] == 5:
                pygame.draw.rect(
                    screen,
                    GREEN,
                    (col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE),
                )
            elif grid[row][col] == 2:  # Kill tile (triangle)
                pygame.draw.polygon(
                    screen,
                    RED,
                    [
                        (col * TILE_SIZE, row * TILE_SIZE),
                        ((col + 1) * TILE_SIZE, row * TILE_SIZE),
                        ((col + 0.5) * TILE_SIZE, (row - 1) * TILE_SIZE),
                    ],
                )
            elif grid[row][col] == 3:  # Slider tile (at an angle)
                pygame.draw.polygon(
                    screen,
                    BLUE,
                    [
                        (col * TILE_SIZE, row * TILE_SIZE),
                        ((col + 1) * TILE_SIZE, row * TILE_SIZE),
                        (col * TILE_SIZE, (row + 1) * TILE_SIZE),
                    ],
                )
            elif grid[row][col] == 4:  # Slider tile (at an angle)
                global flames
                if (row, col) not in flames:
                    flame = Flame(col * TILE_SIZE, row * TILE_SIZE)
                    flames[(row, col)] = flame
                if row * TILE_SIZE < wave.get_target_height():
                    flames[(row, col)].draw_flame(screen)
                else:
                    flames[(row, col)].draw_bubbles(screen)

            if isinstance(grid[row][col], list):
                if grid[row][col][0] == 5 or grid[row][col][0] == 6:
                    pygame.draw.rect(
                        screen,
                        (25, 65, 35),
                        (col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE),
                    )
            if isinstance(grid[row][col], list):
                if grid[row][col][0] == 5:
                    grid[row][col][1] += 1
                    if grid[row][col][1] >= 40:
                        grid[row][col][1] = 0

                        # Ensure tile stays within bounds
                        if col + 3 >= GRID_WIDTH:
                            ad = 0
                            add = 1
                        else:
                            ad = col + 1
                            add = col + 2
                            # if grid[row][ad] == 1:
                            #    ad=0
                            # if grid[row][add] == 1:
                            #    add=1
                        # Update grid with new tile position
                        grid[row][ad] = [5, 0]
                        grid[row][add] = [5, 0]
                        grid[row][col] = 0
            if isinstance(grid[row][col], list):
                if grid[row][col][0] == 6:
                    grid[row][col][1] += 1
                    if grid[row][col][1] >= 40:
                        grid[row][col][1] = 0

                        # Ensure tile stays within bounds
                        if row - 1 >= GRID_HEIGHT:
                            ad = 0
                        else:
                            ad = row - 1
                            # if grid[ad][col] == 1:
                            #    ad=0
                        # Update grid with new tile position
                        grid[ad][col] = [6, 0]
                        grid[row][col] = 0


def draw_weather_screen(color):
    screen.fill(color)


def draw_rain(screen, raindrops, wind):
    for drop in raindrops:
        # Update raindrop position based on wind
        drop[0] += wind + uniform(-0.1, 0.1)
        drop[1] += 5  # Move down
        drop[2] -= 5  # Decrease opacity

        # Draw semi-transparent line for a blur effect
        pygame.draw.aaline(
            screen,
            (
                randint(0, 20),
                randint(0, 220),
                randint(220, 255),
                drop[2],
            ),
            (drop[0], drop[1]),
            (drop[0], drop[1] + 5),
        )

    # Remove raindrops that have moved out of the screen or faded completely
    raindrops[:] = [
        drop for drop in raindrops if drop[1] < wave.get_target_height() and drop[2] > 0
    ]


def draw_lightning(screen, lightning_pos, lightning_duration, frame_count):
    if frame_count < lightning_duration:
        # Draw lightning
        pygame.draw.line(screen, (255, 255, 255), lightning_pos[0], lightning_pos[1], 2)

        # Simulate flash by adding a transparent white surface
        flash_surface = pygame.Surface(
            (infoObject.current_w, infoObject.current_h), pygame.SRCALPHA
        )
        flash_surface.fill(
            (255, 255, 255, min(100, frame_count * 10))
        )  # Adjust the transparency level
        screen.blit(flash_surface, (0, 0))

    else:
        # Fading out the lightning effect
        fade_out = min(255, max(0, 255 - (frame_count - lightning_duration) * 5))
        pygame.draw.line(
            screen, (255, 255, 255, fade_out), lightning_pos[0], lightning_pos[1], 2
        )


def draw_clouds(screen, clouds):
    for cloud in clouds:
        pygame.draw.ellipse(screen, (255, 255, 255), cloud)


def draw_leaves(screen, leaves, wind):
    for leaf in leaves:
        pygame.draw.ellipse(screen, (34, 139, 34), leaf)
        # Update raindrop position based on wind
        leaf.x += wind + uniform(-0.1, 0.1)

    # Remove raindrops that have moved out of the screen or faded completely
    leaves[:] = [
        leaf for leaf in leaves if leaf.x < infoObject.current_w and leaf.x > 0
    ]


def update_weather(weather, raindrops, lightning_pos, clouds, leaves, wind, rain):
    if weather == "rain":
        draw_weather_screen(BLUE)
        for i in range(10):
            # Initialize raindrop with random position and full opacity
            raindrops.append(
                [
                    randint(0, infoObject.current_w),
                    randint(0, infoObject.current_h),
                    255,
                ]
            )
    elif weather == "thunderstorm":
        draw_weather_screen(GRAY)
        if randint(0, 100) < 5:  # Probability of lightning occurring
            lightning_pos[0] = (randint(0, infoObject.current_w), 0)
            lightning_pos[1] = (
                randint(0, infoObject.current_w),
                infoObject.current_h,
            )
            frame_count = 0  # Reset frame count for lightning duration
        for i in range(rain):
            # Initialize raindrop with random position and full opacity
            raindrops.append(
                [
                    randint(0, infoObject.current_w),
                    randint(0, infoObject.current_h),
                    255,
                ]
            )
    elif weather == "cloudy":
        draw_weather_screen(GRAY)
        for i in range(5):
            cloud_size = randint(50, 100)
            cloud = pygame.Rect(
                randint(0, infoObject.current_w),
                randint(0, infoObject.current_h),
                cloud_size,
                cloud_size,
            )
            clouds.append(cloud)
    elif weather == "windy":
        draw_weather_screen(WHITE)
        for i in range(5):
            leaf_size = randint(5, 20)
            leaf = pygame.Rect(
                randint(0, infoObject.current_w),
                randint(0, infoObject.current_h),
                leaf_size,
                leaf_size,
            )
            leaves.append(leaf)


# Update collision logic
def check_tile_collision():
    global is_on_ground, is_on_wall, player_x, player_y, player_velocity

    player_rect = pygame.Rect(player_x, player_y, player_size, player_size)

    for row in range(GRID_HEIGHT):
        for col in range(GRID_WIDTH):
            if grid[row][col] != 0:
                tile_rect = pygame.Rect(
                    col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE
                )

                if player_rect.colliderect(tile_rect) and grid[row][col] != 4:
                    # Collision resolution in x-axis
                    if (
                        player_rect.y < tile_rect.top
                        and player_rect.y > tile_rect.bottom
                    ):
                        if player_velocity[0] > 0:
                            if player_rect.x > tile_rect.left:
                                player_x = tile_rect.right + player_size + 4
                            else:
                                player_x = tile_rect.left - player_size - 4
                        elif player_velocity[0] < 0:
                            player_x = tile_rect.right

                    # if grid[row][col] == 2:
                    #    player_x = WIDTH // 2 - player_size // 2
                    #    player_y = HEIGHT // 2 - player_size // 2
                    # Collision resolution in y-axis
                    if player_velocity[1] > 0:
                        player_y = tile_rect.top - player_size
                        player_velocity[1] = 0
                        is_on_ground = True
                    elif player_velocity[1] < 0:
                        player_y = tile_rect.bottom
                        player_velocity[1] = 0
                elif grid[row][col] == 4 and player_rect.colliderect(tile_rect):
                    if row * TILE_SIZE > wave.get_target_height():
                        player_velocity[1] -= 30
                    else:
                        global score
                        player_x = 9
                        player_y = HEIGHT // 2 - player_size // 2
                        score += 1

    # Check screen boundaries
    player_x = max(0, min(player_x, WIDTH - player_size))
    player_y = max(0, min(player_y, HEIGHT - player_size))


ai = pygame.Rect(400, 300, 50, 50)
# Main game loop

wave = Wave()
s = pygame.Surface(screen.get_size(), pygame.SRCALPHA).convert_alpha()
# PyMunk circle body and shape
radius = 20
mass = 1
inwater = False
done = []
splashes = {}
moment = pymunk.moment_for_circle(mass, 0, radius)
body = pymunk.Body(mass, moment)
body.position = (player_x // 1, player_y // 1)  # Starting position
body.splashed = False
shape = pymunk.Circle(body, radius)
shape.elasticity = 9  # Set elasticity for bouncing effect
objects = [shape]
floating_objects = []
tiles = []
current_tile = 1
direction = True
# if USE_PYMUNK:
#    create_walls()
clock = pygame.time.Clock()
running = True
drawing = False  # Indicates whether the user is drawing tiles
erasing = False  # Indicates whether the user is erasing tiles
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                drawing = True
            elif event.button == 3:  # Right mouse button
                erasing = True
            elif event.button == 4:  # Scroll up
                current_tile += 1
                if current_tile > 6:
                    current_tile = 1
            elif event.button == 5:  # Scroll down
                current_tile -= 1
                if current_tile < 1:
                    current_tile = 6
        elif event.type == pygame.MOUSEBUTTONUP:
            drawing = False
            erasing = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_s:
                # Create Tkinter root window
                root = tk.Tk()
                root.withdraw()  # Hide the root window

                # Open a file dialog for saving the map file
                filename = filedialog.asksaveasfilename(
                    defaultextension=".map", filetypes=[("Map files", "*.map")], initialdir="saves"
                )
                root.destroy()  # Close the Tkinter root window

                if filename:  # Check if a file name was selected
                    # Check if the selected file already exists
                    if os.path.exists(filename):
                        print("File already exists. Choose a different name.")
                    else:
                        # Save the grid to the selected file
                        with open(filename, "w") as file:
                            file.write(str(grid))  # Write the grid data to the file
                        print(f"Grid saved to {filename}")
            if event.key == pygame.K_o:
                # Create Tkinter root window
                root = tk.Tk()
                root.withdraw()  # Hide the root window

                # Open a file dialog for opening the map file
                filename= filedialog.askopenfile(defaultextension=".map", filetypes=[("Map files", "*.map")], initialdir="saves")
                grid = ast.literal_eval(filename.read())
                GRID_HEIGHT = len(grid)
                GRID_WIDTH = len(grid[0])

    # Get the mouse position
    mouse_x, mouse_y = pygame.mouse.get_pos()
    # Convert mouse position to grid coordinates
    col = mouse_x // TILE_SIZE
    row = mouse_y // TILE_SIZE
    # Draw or erase tiles based on mouse input
    if drawing:
        if 0 <= col < GRID_WIDTH and 0 <= row < GRID_HEIGHT:
            if grid[row][col] == 0:
                # Create a PyMunk circle at the tile position
                tile_x = col * TILE_SIZE + TILE_SIZE // 2
                tile_y = row * TILE_SIZE + TILE_SIZE // 2
                mass = 1
                if tile_y > wave.get_target_height():
                    wave.add_volume(TILE_SIZE**2 * math.pi)
            if current_tile != 5 and current_tile != 6:
                grid[row][col] = current_tile
            else:
                grid[row][col] = [current_tile, 0]

    elif erasing:
        if 0 <= col < GRID_WIDTH and 0 <= row < GRID_HEIGHT:
            if grid[row][col] != 0:
                tile_y = row * TILE_SIZE + TILE_SIZE // 2
                if tile_y > wave.get_target_height():
                    wave.add_volume(-(TILE_SIZE**2 * math.pi))
                    print()
            grid[row][col] = 0

    keys = pygame.key.get_pressed()

    player_velocity[1] += gravity

    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        direction = False
        if player_speed > 0:
            player_speed /= 1.1
        player_speed -= player_acceleration
    elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        direction = True
        if player_speed < 0:
            player_speed /= 1.1
        player_speed += player_acceleration
    else:
        if player_speed > 0:
            player_speed -= player_acceleration
        elif player_speed < 0:
            player_speed += player_acceleration

    if player_speed > player_max_speed:
        player_speed = player_max_speed
    elif player_speed < -player_max_speed:
        player_speed = -player_max_speed

    is_dashing = False
    if keys[pygame.K_SPACE] and not is_dashing and dash_timer <= 0:
        is_dashing = True
        if not player_speed >= 5:
            if direction:
                player_speed += player_dash_speed
            else:
                player_speed -= player_dash_speed
        else:
            player_speed += (
                player_dash_speed if player_speed >= 0 else -player_dash_speed
            )
        dash_timer = dash_cooldown
    if dash_timer > 0:
        dash_timer -= 1

    if (
        (keys[pygame.K_w] or keys[pygame.K_UP])
        and not is_jumping
        and (is_on_ground or is_on_wall)
    ):
        is_jumping = True
        player_velocity[1] = -player_jump_strength
        if is_on_wall:
            wall_jump_timer = wall_jump_cooldown
            if player_x < WIDTH / 2:
                player_speed = player_max_speed
            else:
                player_speed = -player_max_speed

    player_velocity[0] = player_speed

    body.position = [int(player_x), int(player_y)]
    is_jumping = False
    if not inwater:
        is_on_ground = player_y >= HEIGHT - player_size
    else:
        is_on_ground = True
    is_on_wall = player_x <= 0 or player_x >= WIDTH - player_size

    if player_y + 20 >= wave.get_target_height():
        # player_y += wave.get_target_height() - wave.springs[wave.get_spring_index_for_x_pos(player_x)].height
        inwater = True
        player_acceleration = 0.02
        # player_max_speed = 5
        gravity = 0.2
        player_jump_strength = 3
    else:
        player_acceleration = 0.2
        player_max_speed = 15
        gravity = 0.8
        player_jump_strength = 15
        inwater = False
        body.splashed = False

    player_x += player_velocity[0]
    player_y += player_velocity[1]

    # Inside the game loop, after updating player position
    check_tile_collision()

    # AI movement
    dx = player_x - ai.x
    dy = player_y - ai.y
    dist = math.sqrt((player_x - ai.x) ** 2 + (player_y - ai.y) ** 2)

    if dist > 50:  # Move towards player if not too close
        ai.x += (dx / dist) * 3
        ai.y += (dy / dist) * 3

    if randint(0, 100) < 5:  # Probability of wind direction change occurring
        newwind = randint(-3, 3)  # Introduce wind for raindrops
    if wind < newwind:
        wind += 0.01
    if wind > newwind:
        wind -= 0.01

    if randint(0, 100) < 5:  # Probability of rain density change occurring
        newrain = randint(5, 30)  # Introduce wind for raindrops
    if rain < newrain:
        rain += 1
    if rain > newrain:
        rain -= 1
    # if randint(0,1000) <=5:
    #    weather=random.choice(["rain", "cloudy", "thunderstorm", "windy"])
    # Update and draw weather effects
    update_weather(weather, raindrops, lightning_pos, clouds, leaves, wind, rain)
    draw_rain(screen, raindrops, wind)
    draw_lightning(screen, lightning_pos, lightning_duration, frame_count)
    draw_clouds(screen, clouds)
    draw_leaves(screen, leaves, wind)
    if USE_PYMUNK:
        space.step(1 / FPS)
        # screen.fill('black')
        s.fill(0)
        for i in objects:
            if not i.body.splashed:
                if i.body.position.y + i.radius >= wave.get_target_height():
                    i.body.splashed = True
                    if not (i.body.position[0], i.body.position[0]) in splashes:
                        splash = Flame(
                            i.body.position[0], i.body.position[1] + TILE_SIZE
                        )
                        splash.flame_intensity = 5
                        for index in range(splash.flame_intensity * 25):
                            splash.flame_particles.append(
                                FlameParticle(
                                    splash.x + random.randint(-5, 5),
                                    splash.y,
                                    random.randint(1, 5),
                                )
                            )

                        splashes[(i.body.position[0], i.body.position[1])] = [
                            15,
                            splash,
                            8,
                            player_velocity[1],
                        ]
                    wave.splash(
                        index=wave.get_spring_index_for_x_pos(i.body.position.x),
                        vel=i.radius,
                    )
                    if VOLUME_RISE:
                        if i not in done:
                            wave.add_volume(i.radius**2 * math.pi)
                            done.append(i)
        remove = []
        for key, item in splashes.items():
            splashes[key][0] -= 1
            if splashes[key][0] <= 0:
                remove.append(key)
            else:
                splashes[key][1].draw_bubbles(
                    screen, splashes[key][3] // 1, splashes[key][2] // 1, True
                )
        for key in remove:
            splashes.pop(key)
        for i in tiles:
            if VOLUME_RISE:
                if i not in done:
                    if i[0] + i[1] > wave.get_target_height():
                        wave.add_volume(60**2 * math.pi)
                        done.append(i)
        for i in floating_objects:
            i.update()
            i.draw(screen)
            index = wave.get_spring_index_for_x_pos(i.x)
            if i.y > wave.get_target_height():
                if not i.spring:
                    i.spring = wave.springs[index]
                    try:
                        i.next_spring = wave.springs[index + 1]
                    except IndexError:
                        pass
                    wave.splash(index, 2)
        wave.update()
        wave.draw(s)
        screen.blit(s, (0, 0))
        wave.draw_line(screen)
    if player_y <= wave.get_target_height():
        for i in objects:
            if [i.body.position[0], i.body.position[1]] == [
                player_x // 1,
                player_y // 1,
            ]:
                i.body.splashed = False
    col = RED if not inwater else (200, 40, 150)

    # if is_dashing:
    #    draw_speed_lines(screen)
    pygame.draw.rect(screen, col, (player_x, player_y, player_size, player_size))
    # pygame.draw.rect(screen, GREEN, ai)
    draw_grid()
    text = font.render(f"Points: {score} s to save o to open", False, BLACK)
    screen.blit(text, (0, 0))
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()

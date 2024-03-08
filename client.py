import socket
import math
import sys
from random import randint
import pymunk
import pygame
from game import (
    update_weather,
    Wave,
    check_tile_collision,
    draw_clouds,
    draw_grid,
    draw_leaves,
    draw_lightning,
    draw_rain,
)


def main():
    # Connect to the server
    server_host = "localhost"
    server_port = 12345

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_host, server_port))

    try:
        Point = pygame.Vector2

        # INITIAL RUNTIME CONFIGURATIONS

        # You can edit these accordingly based on the modules you have

        SMOOTH = True  # uses numpy + scipy
        TEXTURE = False  # uses texture images
        VOLUME_RISE = True
        USE_PYMUNK = True  # uses pymunk
        FPS = 60
        GRAVITY = (0, 500)

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
        player_acceleration = 0.2
        player_dash_speed = 25.0
        player_jump_strength = 15.0
        gravity = 0.8
        player_x = WIDTH // 2 - player_size // 2
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

        font = pygame.font.SysFont("consolas", 25)

        if USE_PYMUNK:
            space = pymunk.Space()
            space.gravity = GRAVITY
        ai = pygame.Rect(400, 300, 50, 50)
        # Main game loop

        wave = Wave()
        s = pygame.Surface(screen.get_size(), pygame.SRCALPHA).convert_alpha()
        # PyMunk circle body and shape
        radius = 20
        mass = 1
        inwater = False
        done = []
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
                        if current_tile > 3:
                            current_tile = 1
                    elif event.button == 5:  # Scroll down
                        current_tile -= 1
                        if current_tile < 1:
                            current_tile = 3
                elif event.type == pygame.MOUSEBUTTONUP:
                    drawing = False
                    erasing = False
                elif event.type == pygame.KEYDOWN:
                    if (
                        event.key == pygame.K_s
                    ):  # Save the grid to a file when 's' key is pressed
                        with open("grid.txt", "w") as file:
                            for row in grid:
                                file.write(" ".join(map(str, row)) + "\n")

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
                    grid[row][col] = current_tile

            elif erasing:
                if 0 <= col < GRID_WIDTH and 0 <= row < GRID_HEIGHT:
                    if grid[row][col] != 0:
                        if tile_y > wave.get_target_height():
                            wave.add_volume(-(TILE_SIZE**2 * math.pi))
                            print()
                    grid[row][col] = 0

            keys = pygame.key.get_pressed()

            player_velocity[1] += gravity

            if keys[pygame.K_LEFT]:
                direction = False
                if player_speed > 0:
                    player_speed /= 1.1
                player_speed -= player_acceleration
            elif keys[pygame.K_RIGHT]:
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
                player_speed += (
                    player_dash_speed if player_speed >= 0 else -player_dash_speed
                )
                dash_timer = dash_cooldown
            if dash_timer > 0:
                dash_timer -= 1
            if keys[pygame.K_UP] and not is_jumping and (is_on_ground or is_on_wall):
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
            update_weather(
                weather, raindrops, lightning_pos, clouds, leaves, wind, rain
            )
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
                            wave.splash(
                                index=wave.get_spring_index_for_x_pos(
                                    i.body.position.x
                                ),
                                vel=i.radius,
                            )
                            if VOLUME_RISE:
                                if i not in done:
                                    wave.add_volume(i.radius**2 * math.pi)
                                    done.append(i)
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
            pygame.draw.rect(
                screen, col, (player_x, player_y, player_size, player_size)
            )
            # pygame.draw.rect(screen, GREEN, ai)
            draw_grid()
            pygame.display.flip()
            clock.tick(60)

        pygame.quit()
        sys.exit()

        # Send data to the server
        message = input("Enter message to send: ")
        client_socket.sendall(message.encode())

        # Receive response from the server
        data = client_socket.recv(1024)
        print("Received from server:", data.decode())
    finally:
        client_socket.close()


if __name__ == "__main__":
    main()

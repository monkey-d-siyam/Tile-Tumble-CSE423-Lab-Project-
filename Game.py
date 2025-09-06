from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math, time, sys, random

# Camera-related variables
camera_pos = (0, 500, 500)
fovY = 60
GRID_LENGTH = 600

# Game constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
ASPECT = WINDOW_WIDTH / WINDOW_HEIGHT

# Game variables
gravity = -500.0
jump_strength = 200.0
max_jump_duration = 0.35
ball_radius = 10.0
ball_pos = [0.0, 0.0, 10.0]
ball_vel = [0.0, 0.0, 0.0]
jumping = False
jump_start_time = 0.0
score = 0
lives = 3
current_round = 1
max_rounds = 5
round_target_score = 4
game_over = False
game_won = False
game_paused = False
last_tile = None
time_on_tile = 0.0
max_tile_time = 3.0
show_timer = False
time_last = time.time()
game_start_time = time.time()
bounce_timer = 0.0
bounce_time_limit = 10.0
base_bounce_time = 10.0
show_bounce_timer = True
last_bounce_time = time.time()
move_keys = {"a": False, "d": False, "w": False, "s": False}
space_pressed = False
difficulty_timer = None
difficulty_mode = False
speed_multiplier = 1.0
base_speed = 200.0
difficulty_level = 1
obstacle_speed_multiplier = 1.0
camera_distance = 500.0
camera_angle = 0
camera_height = 500.0
wall_height = 80.0
grid_size_x = 20
grid_size_y = 15
tile_size = 80
half_size_x = grid_size_x * tile_size / 2
half_size_y = grid_size_y * tile_size / 2
obstacles = []
tree_obstacles = []
boundary_trees = []
projectiles = []
collectibles = []
special_collectibles = []
holes = set()
theme = "default"
shields = []
shield_active = False
shield_duration = 0.0
max_shield_duration = 10.0
zones = {'safe': [], 'normal': [], 'danger': []}
small_obstacle_trees = []

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def update_bounce_timer():
    global bounce_timer, bounce_time_limit, lives, game_over, ball_pos, ball_vel, shield_active, shield_duration, max_shield_duration
    bounce_time_limit = max(3.0, base_bounce_time - (current_round - 1))
    current_time = time.time()
    bounce_timer = current_time - last_bounce_time
    if bounce_timer >= bounce_time_limit:
        if shield_active:
            shield_active = False
            shield_duration = 0.0
            reset_bounce_timer()
        else:
            lives -= 1
            if lives <= 0:
                game_over = True
                return
            else:
                ball_pos[:] = find_safe_start_tile()
                ball_vel[:] = [0.0, 0.0, 0.0]
                shield_active = True
                shield_duration = 0.0
                max_shield_duration = 2.0
                reset_bounce_timer()

def reset_bounce_timer():
    global bounce_timer, last_bounce_time
    bounce_timer = 0.0
    last_bounce_time = time.time()

def initialize_zones():
    global zones
    zones = {'safe': [], 'normal': [], 'danger': []}
    for i in range(grid_size_x):
        for j in range(grid_size_y):
            if (i, j) not in holes:
                if (i + j) % 2 == 0:
                    zones['safe'].append((i, j))
                else:
                    if random.random() < 0.1:
                        zones['danger'].append((i, j))
                    else:
                        zones['normal'].append((i, j))

def generate_holes():
    global holes
    holes = set()
    hole_count = min(20 + current_round * 15, 80)
    while len(holes) < hole_count:
        i = random.randint(1, grid_size_x - 2)
        j = random.randint(1, grid_size_y - 2)
        holes.add((i, j))

def find_safe_tile():
    attempts = 0
    while attempts < 100:
        i = random.randint(0, grid_size_x - 1)
        j = random.randint(0, grid_size_y - 1)
        if (i, j) not in holes:
            x = i * tile_size - half_size_x + tile_size / 2
            y = j * tile_size - half_size_y + tile_size / 2
            return (x, y)
        attempts += 1
    return (0, 0)

def find_safe_start_tile():
    for i in range(grid_size_x):
        for j in range(grid_size_y):
            if (i, j) not in holes:
                if i == 0 and j == 0:
                    x = i * tile_size - half_size_x + tile_size / 2
                    y = j * tile_size - half_size_y + tile_size / 2
                    return [x, y, 10.0]
    return [0.0, 0.0, 10.0]

def generate_obstacles():
    global obstacles
    obstacles = []
    obstacle_count = 3 + current_round * 3
    for _ in range(obstacle_count):
        x, y = find_safe_tile()
        obstacles.append({
            'pos': [x + random.uniform(-30, 30), y + random.uniform(-30, 30), 30],
            'base_size': random.uniform(6 + current_round * 2, 18 + current_round * 3),
            'current_size': 0,
            'vel': random.uniform(30 + current_round * 25, 100 + current_round * 35) * random.choice([-1, 1]),
            'shrink_speed': random.uniform(0.2, 0.8 + current_round * 0.3),
            'min_size': random.uniform(2, 5),
            'float_height': random.uniform(15, 50),
            'float_speed': random.uniform(0.6 + current_round * 0.4, 2.0 + current_round * 0.6),
            'float_offset': random.random() * 6.28,
            'pulse': 0,
            'pattern': random.choice(['oscillate', 'circle', 'figure8', 'zigzag']),
            'pattern_time': 0.0,
            'original_pos': [x, y],
            'aggressiveness': 1.0 + current_round * 0.4
        })

def generate_tree_obstacles():
    global tree_obstacles
    tree_obstacles = []
    tree_count = min(current_round * 2, 10)
    if current_round <= 1:
        shooting_pattern = 'one_side'
    elif current_round <= 3:
        shooting_pattern = 'two_sides'
    else:
        shooting_pattern = 'all_sides'
    for _ in range(tree_count):
        x, y = find_safe_tile()
        tree_obstacles.append({
            'pos': [x, y, 0],
            'shooting_pattern': shooting_pattern,
            'last_shot_time': 0.0,
            'shoot_interval': max(3.5 - current_round * 0.4, 0.8),
            'projectile_speed': 80 + current_round * 30
        })

def generate_boundary_trees():
    global boundary_trees
    boundary_trees = []
    if current_round >= 5:
        spacing = tile_size * 2
        tree_positions = []
        for x in range(-int(half_size_x), int(half_size_x), spacing):
            tree_positions.extend([
                (x, half_size_y + 40, 0),
                (x, -half_size_y - 40, 0)
            ])
        for y in range(-int(half_size_y), int(half_size_y), spacing):
            tree_positions.extend([
                (half_size_x + 40, y, 0),
                (-half_size_x - 40, y, 0)
            ])
        for tx, ty, tz in tree_positions:
            boundary_trees.append({
                'pos': [tx, ty, tz],
                'shooting_pattern': 'all_sides',
                'last_shot_time': 0.0,
                'shoot_interval': 2.0,
                'projectile_speed': 120
            })

def generate_small_obstacle_trees():
    global small_obstacle_trees
    small_obstacle_trees = []
    count = 6 + current_round * 2
    for _ in range(count):
        x, y = find_safe_tile()
        small_obstacle_trees.append({
            'pos': [x, y, 0],
            'shooting_pattern': random.choice(['one_side', 'two_sides', 'all_sides']),
            'last_shot_time': 0.0,
            'shoot_interval': max(4.0 - current_round * 0.3, 1.0),
            'projectile_speed': 60 + current_round * 20
        })

def update_tree_obstacles(dt):
    global projectiles
    current_time = time.time()
    for tree in tree_obstacles:
        if current_time - tree['last_shot_time'] >= tree['shoot_interval']:
            tree['last_shot_time'] = current_time
            shoot_projectiles_from_tree(tree)
    if current_round >= 5:
        for tree in boundary_trees:
            if current_time - tree['last_shot_time'] >= tree['shoot_interval']:
                tree['last_shot_time'] = current_time
                shoot_projectiles_from_tree(tree)

def update_small_obstacle_trees(dt):
    global projectiles
    current_time = time.time()
    for tree in small_obstacle_trees:
        if current_time - tree['last_shot_time'] >= tree['shoot_interval']:
            tree['last_shot_time'] = current_time
            shoot_projectiles_from_tree(tree)

def shoot_projectiles_from_tree(tree):
    global projectiles
    dx = ball_pos[0] - tree['pos'][0]
    dy = ball_pos[1] - tree['pos'][1]
    distance = math.sqrt(dx**2 + dy**2)
    if distance > 0 and distance < 600:
        dx /= distance
        dy /= distance
        if tree['shooting_pattern'] == 'one_side':
            projectiles.append({
                'pos': [tree['pos'][0], tree['pos'][1], 25],
                'vel': [dx * tree['projectile_speed'], dy * tree['projectile_speed'], 0],
                'life_time': 0.0,
                'max_life': 5.0,
                'size': 4
            })
        elif tree['shooting_pattern'] == 'two_sides':
            for angle_offset in [-math.pi/4, math.pi/4]:
                new_dx = dx * math.cos(angle_offset) - dy * math.sin(angle_offset)
                new_dy = dx * math.sin(angle_offset) + dy * math.cos(angle_offset)
                projectiles.append({
                    'pos': [tree['pos'][0], tree['pos'][1], 25],
                    'vel': [new_dx * tree['projectile_speed'], new_dy * tree['projectile_speed'], 0],
                    'life_time': 0.0,
                    'max_life': 5.0,
                    'size': 4
                })
        elif tree['shooting_pattern'] == 'all_sides':
            for i in range(8):
                angle = i * math.pi / 4
                proj_dx = math.cos(angle)
                proj_dy = math.sin(angle)
                projectiles.append({
                    'pos': [tree['pos'][0], tree['pos'][1], 25],
                    'vel': [proj_dx * tree['projectile_speed'], proj_dy * tree['projectile_speed'], 0],
                    'life_time': 0.0,
                    'max_life': 5.0,
                    'size': 5 if current_round >= 5 else 4
                })

def update_projectiles(dt):
    global projectiles
    remaining_projectiles = []
    for proj in projectiles:
        proj['pos'][0] += proj['vel'][0] * dt
        proj['pos'][1] += proj['vel'][1] * dt
        proj['life_time'] += dt
        if (proj['life_time'] < proj['max_life'] and
            -half_size_x - 100 < proj['pos'][0] < half_size_x + 100 and
            -half_size_y - 100 < proj['pos'][1] < half_size_y + 100):
            remaining_projectiles.append(proj)
    projectiles[:] = remaining_projectiles

def draw_tree_obstacles():
    for tree in tree_obstacles:
        tx, ty = tree['pos'][:2]
        if tree['shooting_pattern'] == 'one_side':
            glColor3f(0.4, 0.2, 0.1)
        elif tree['shooting_pattern'] == 'two_sides':
            glColor3f(0.6, 0.3, 0.1)
        else:
            glColor3f(0.8, 0.2, 0.1)
        glPushMatrix()
        glTranslatef(tx, ty, 20)
        glScalef(8, 8, 40)
        glutSolidCube(1)
        glPopMatrix()
        if tree['shooting_pattern'] == 'all_sides':
            pulse = 0.5 + 0.5 * math.sin(time.time() * 3)
            glColor3f(pulse, 0.1, 0.1)
        elif tree['shooting_pattern'] == 'two_sides':
            glColor3f(0.6, 0.4, 0.1)
        else:
            glColor3f(0.0, 0.5, 0.0)
        glPushMatrix()
        glTranslatef(tx, ty, 50)
        glutSolidCone(20, 50, 12, 12)
        glPopMatrix()

def draw_small_obstacle_trees():
    for tree in small_obstacle_trees:
        tx, ty = tree['pos'][:2]
        glColor3f(0.5, 0.25, 0.1)
        glPushMatrix()
        glTranslatef(tx, ty, 10)
        glScalef(4, 4, 15)
        glutSolidCube(1)
        glPopMatrix()
        if tree['shooting_pattern'] == 'all_sides':
            pulse = 0.5 + 0.5 * math.sin(time.time() * 3)
            glColor3f(pulse, 0.1, 0.1)
        elif tree['shooting_pattern'] == 'two_sides':
            glColor3f(0.6, 0.4, 0.1)
        else:
            glColor3f(0.0, 0.5, 0.0)
        glPushMatrix()
        glTranslatef(tx, ty, 22)
        glutSolidCone(10, 20, 8, 8)
        glPopMatrix()

def draw_projectiles():
    for proj in projectiles:
        glPushMatrix()
        glTranslatef(proj['pos'][0], proj['pos'][1], proj['pos'][2])
        age_ratio = proj['life_time'] / proj['max_life']
        if current_round >= 5:
            glColor3f(1.0, 0.2 - age_ratio * 0.1, 0.1)
        else:
            glColor3f(0.8 + age_ratio * 0.2, 0.4 - age_ratio * 0.3, 0.1)
        glutSolidSphere(proj['size'], 8, 8)
        glPopMatrix()

def generate_collectibles():
    global collectibles, special_collectibles
    collectibles = []
    special_collectibles = []
    collectible_count = max(4, 12 - current_round * 2)
    for _ in range(collectible_count):
        x, y = find_safe_tile()
        collectibles.append({
            'type': random.choice(['cube', 'torus', 'pyramid']),
            'pos': [x, y, 15],
            'rotation': 0.0,
            'collected': False,
            'float_offset': random.random() * 6.28
        })
    special_count = 1 + current_round
    effects = ['speed_boost', 'slow_time', 'extra_life', 'shield', 'score_multiplier']
    for _ in range(special_count):
        x, y = find_safe_tile()
        special_collectibles.append({
            'pos': [x, y, 20],
            'effect': random.choice(effects),
            'collected': False,
            'glow': 0.0,
            'rotation': 0.0
        })

def generate_shields():
    global shields
    shields = []
    shield_count = max(1, 3 - current_round // 2)
    for _ in range(shield_count):
        x, y = find_safe_tile()
        shields.append({
            'pos': [x, y, 10],
            'collected': False,
            'rotation': 0.0
        })

def advance_round():
    global current_round, score, speed_multiplier, obstacle_speed_multiplier, max_tile_time, bounce_time_limit
    if current_round < max_rounds:
        current_round += 1
        new_bounce_limit = max(3.0, base_bounce_time - (current_round - 1))
        speed_multiplier += 0.15
        obstacle_speed_multiplier += 0.25
        max_tile_time = max(0.8, max_tile_time * 0.85)
        generate_holes()
        initialize_zones()
        generate_obstacles()
        generate_tree_obstacles()
        generate_boundary_trees()
        generate_collectibles()
        generate_shields()
        generate_small_obstacle_trees()
        score = 0
        reset_bounce_timer()

def update_round_progression():
    global score, current_round
    if score >= round_target_score and current_round < max_rounds:
        advance_round()

def reset_game(reset_score=True, reset_lives=True):
    global ball_pos, ball_vel, jumping, jump_start_time, score, lives, game_over, game_won
    global collectibles, special_collectibles, time_last, obstacles, last_tile, time_on_tile
    global show_timer, difficulty_timer, difficulty_mode, speed_multiplier, game_start_time
    global shield_active, shield_duration, difficulty_level, game_paused, tree_obstacles, projectiles
    global obstacle_speed_multiplier, max_shield_duration, current_round, boundary_trees
    global bounce_timer, bounce_time_limit, last_bounce_time, small_obstacle_trees
    ball_pos[:] = find_safe_start_tile()
    ball_vel[:] = [0.0, 0.0, 0.0]
    jumping = False
    jump_start_time = 0.0
    if reset_score:
        score = 0
        current_round = 1
        obstacle_speed_multiplier = 1.0
    if reset_lives:
        lives = 3
    game_over = False
    game_won = False
    game_paused = False
    time_last = time.time()
    game_start_time = time.time()
    last_tile = None
    time_on_tile = 0.0
    show_timer = False
    shield_active = False
    shield_duration = 0.0
    max_shield_duration = 10.0
    difficulty_timer = None
    difficulty_mode = False
    speed_multiplier = 1.0
    max_tile_time = 3.0
    bounce_timer = 0.0
    bounce_time_limit = base_bounce_time
    last_bounce_time = time.time()
    obstacles.clear()
    tree_obstacles.clear()
    boundary_trees.clear()
    projectiles.clear()
    collectibles.clear()
    special_collectibles.clear()
    shields.clear()
    small_obstacle_trees.clear()
    generate_holes()
    initialize_zones()
    generate_obstacles()
    generate_tree_obstacles()
    generate_boundary_trees()
    generate_collectibles()
    generate_shields()
    generate_small_obstacle_trees()

def setup_projection():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60.0, ASPECT, 1.0, 3000.0)
    glMatrixMode(GL_MODELVIEW)

def reshape(w, h):
    global WINDOW_WIDTH, WINDOW_HEIGHT, ASPECT
    WINDOW_WIDTH = w
    WINDOW_HEIGHT = h
    ASPECT = w / h if h > 0 else 1
    glViewport(0, 0, w, h)
    setup_projection()

def setup_scene():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)
    glLoadIdentity()
    angle_rad = math.radians(camera_angle)
    eye_x = ball_pos[0] - camera_distance * math.cos(angle_rad)
    eye_y = ball_pos[1] + camera_distance * math.sin(angle_rad)
    eye_z = ball_pos[2] + camera_height
    gluLookAt(eye_x, eye_y, eye_z,
              ball_pos[0], ball_pos[1], ball_pos[2],
              0.0, 0.0, 1.0)
    if theme == "default":
        if current_round >= 5:
            glClearColor(0.7, 0.3, 0.3, 1.0)
        else:
            glClearColor(0.5, 0.8, 1.0, 1.0)
    elif theme == "dark":
        if current_round >= 5:
            glClearColor(0.2, 0.1, 0.1, 1.0)
        else:
            glClearColor(0.1, 0.1, 0.2, 1.0)

def draw_floor():
    global theme
    if theme == "default":
        if current_round >= 5:
            safe_color = (0.9, 0.9, 0.9)
            normal_color = (0.4, 0.6, 0.4)
            danger_color = (1.0, 0.3, 0.3)
            hole_color = (0.1, 0.1, 0.1)
        else:
            safe_color = (1.0, 1.0, 1.0)
            normal_color = (0.302, 0.471, 0.388)
            danger_color = (0.8, 0.2, 0.2)
            hole_color = (0.0, 0.0, 0.0)
    elif theme == "dark":
        safe_color = (0.3, 0.3, 0.3)
        normal_color = (0.1, 0.2, 0.1)
        danger_color = (0.3, 0.1, 0.1)
        hole_color = (0.5, 0.0, 0.0)

    for i in range(grid_size_x):
        for j in range(grid_size_y):
            x = i * tile_size - half_size_x
            y = j * tile_size - half_size_y
            if (i, j) in holes:
                glColor3f(*hole_color)
            elif (i, j) in zones['danger']:
                glColor3f(*danger_color)
            elif (i, j) in zones['safe']:
                glColor3f(*safe_color)
            else:
                glColor3f(*normal_color)
            glBegin(GL_QUADS)
            glVertex3f(x, y, 0.0)
            glVertex3f(x + tile_size, y, 0.0)
            glVertex3f(x + tile_size, y + tile_size, 0.0)
            glVertex3f(x, y + tile_size, 0.0)
            glEnd()
            glColor3f(0.0, 0.0, 0.0)
            glLineWidth(1.0)
            glBegin(GL_LINE_LOOP)
            glVertex3f(x, y, 0.1)
            glVertex3f(x + tile_size, y, 0.1)
            glVertex3f(x + tile_size, y + tile_size, 0.1)
            glVertex3f(x, y + tile_size, 0.1)
            glEnd()

def draw_walls():
    glColor3f(0.2, 0.2, 0.8)
    wall_positions = [
        (-half_size_x, 0, -half_size_y, half_size_y, True),
        (half_size_x, 0, -half_size_y, half_size_y, True),
        (0, half_size_y, -half_size_x, half_size_x, False),
        (0, -half_size_y, -half_size_x, half_size_x, False)
    ]
    for wall in wall_positions:
        if wall[4]:
            x, _, y1, y2 = wall[:4]
            glBegin(GL_QUADS)
            glVertex3f(x, y1, 0)
            glVertex3f(x, y2, 0)
            glVertex3f(x, y2, wall_height)
            glVertex3f(x, y1, wall_height)
            glEnd()
        else:
            _, y, x1, x2 = wall[:4]
            glBegin(GL_QUADS)
            glVertex3f(x1, y, 0)
            glVertex3f(x2, y, 0)
            glVertex3f(x2, y, wall_height)
            glVertex3f(x1, y, wall_height)
            glEnd()

def draw_trees():
    if theme == "default":
        if current_round >= 5:
            trunk_color = (0.6, 0.1, 0.1)
            foliage_color = (0.8, 0.2, 0.2)
        else:
            trunk_color = (0.55, 0.27, 0.07)
            foliage_color = (0.0, 0.5, 0.0)
    elif theme == "dark":
        trunk_color = (0.3, 0.15, 0.05)
        foliage_color = (0.0, 0.3, 0.3)

    tree_positions = []
    spacing = tile_size * 2
    for x in range(-int(half_size_x), int(half_size_x), spacing):
        tree_positions.extend([
            (x, half_size_y + 40, 0),
            (x, -half_size_y - 40, 0)
        ])
    for y in range(-int(half_size_y), int(half_size_y), spacing):
        tree_positions.extend([
            (half_size_x + 40, y, 0),
            (-half_size_x - 40, y, 0)
        ])

    for tx, ty, tz in tree_positions:
        glColor3f(*trunk_color)
        glPushMatrix()
        glTranslatef(tx, ty, 15)
        glScalef(8, 8, 30)
        glutSolidCube(1)
        glPopMatrix()
        if current_round >= 5:
            pulse = 0.5 + 0.5 * math.sin(time.time() * 4)
            glColor3f(pulse, 0.1, 0.1)
        else:
            glColor3f(*foliage_color)
        glPushMatrix()
        glTranslatef(tx, ty, 45)
        glutSolidCone(20, 50, 12, 12)
        glPopMatrix()

def draw_collectibles():
    current_time = time.time()
    for c in collectibles:
        if not c['collected']:
            glPushMatrix()
            x, y, base_z = c['pos']
            float_z = base_z + 5 * math.sin(current_time * 2 + c['float_offset'])
            glTranslatef(x, y, float_z)
            c['rotation'] += 2.0
            glRotatef(c['rotation'], 0, 0, 1)
            if c['type'] == 'cube':
                glColor3f(1.0, 0.8, 0.0)
                glutSolidCube(15)
            elif c['type'] == 'torus':
                glColor3f(0.0, 1.0, 1.0)
                glutSolidTorus(3, 10, 12, 12)
            elif c['type'] == 'pyramid':
                glColor3f(1.0, 0.0, 1.0)
                glBegin(GL_QUADS)
                glVertex3f(-7, -7, 0)
                glVertex3f(7, -7, 0)
                glVertex3f(7, 7, 0)
                glVertex3f(-7, 7, 0)
                glEnd()
                glBegin(GL_TRIANGLES)
                glVertex3f(0, 0, 14); glVertex3f(-7, -7, 0); glVertex3f(7, -7, 0)
                glVertex3f(0, 0, 14); glVertex3f(7, 7, 0); glVertex3f(-7, 7, 0)
                glVertex3f(0, 0, 14); glVertex3f(7, -7, 0); glVertex3f(7, 7, 0)
                glVertex3f(0, 0, 14); glVertex3f(-7, 7, 0); glVertex3f(-7, -7, 0)
                glEnd()
            glPopMatrix()

def draw_special_collectibles():
    current_time = time.time()
    for sc in special_collectibles:
        if not sc['collected']:
            glPushMatrix()
            x, y, base_z = sc['pos']
            sc['glow'] += 0.1
            sc['rotation'] += 3.0
            glow_intensity = 0.5 + 0.5 * math.sin(sc['glow'])
            float_z = base_z + 8 * math.sin(current_time * 1.5)
            glTranslatef(x, y, float_z)
            glRotatef(sc['rotation'], 0, 0, 1)
            effect_colors = {
                'speed_boost': (0.0, 1.0, 0.0),
                'slow_time': (0.0, 0.0, 1.0),
                'extra_life': (1.0, 0.0, 0.0),
                'shield': (1.0, 1.0, 0.0),
                'score_multiplier': (1.0, 0.5, 0.0)
            }
            color = effect_colors.get(sc['effect'], (1.0, 1.0, 1.0))
            glColor3f(color[0] * glow_intensity, color[1] * glow_intensity, color[2] * glow_intensity)
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(0, 0, 0)
            for i in range(11):
                angle = i * 2 * math.pi / 10
                radius = 12 if i % 2 == 0 else 6
                glVertex3f(math.cos(angle) * radius, math.sin(angle) * radius, 0)
            glEnd()
            glColor3f(1.0, 1.0, 1.0)
            glBegin(GL_LINES)
            glVertex3f(0, 0, 8)
            glVertex3f(0, 0, 18)
            glVertex3f(6, 0, 13)
            glVertex3f(-6, 0, 13)
            glVertex3f(0, 6, 13)
            glVertex3f(0, -6, 13)
            glEnd()
            glPopMatrix()

def draw_obstacles():
    current_time = time.time()
    for o in obstacles:
        glPushMatrix()
        x, y, z = o['pos']
        glTranslatef(x, y, z)
        o['pulse'] += 0.1 * o['aggressiveness']
        pulse_factor = 0.5 + 0.5 * math.sin(o['pulse'])
        if o['current_size'] <= 0:
            o['current_size'] = o['base_size']
        size_ratio = (o['current_size'] - o['min_size']) / max(1, (o['base_size'] - o['min_size']))
        red_intensity = 0.7 + (1.0 - size_ratio) * 0.3 + pulse_factor * 0.2
        green_blue = 0.05 + size_ratio * 0.15
        glColor3f(red_intensity, green_blue, green_blue)
        glutSolidSphere(o['current_size'], 16, 16)
        if o['current_size'] < o['base_size'] * 0.6:
            glPushMatrix()
            glow_size = o['current_size'] * (1.2 + 0.4 * pulse_factor)
            glColor4f(1.0, 0.2, 0.2, 0.4 + 0.3 * pulse_factor)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glutWireSphere(glow_size, 12, 12)
            glDisable(GL_BLEND)
            glPopMatrix()
        glPopMatrix()

def draw_ball():
    glPushMatrix()
    glTranslatef(ball_pos[0], ball_pos[1], ball_pos[2])
    if shield_active:
        glow = 0.5 + 0.5 * math.sin(time.time() * 5)
        glColor3f(0.0, glow, 1.0)
    elif jumping:
        glColor3f(1.0, 1.0, 0.0)
    elif current_round >= 5:
        pulse = 0.5 + 0.5 * math.sin(time.time() * 2)
        glColor3f(1.0, pulse * 0.5, pulse * 0.5)
    else:
        glColor3f(1.0, 0.0, 0.0)
    glutSolidSphere(ball_radius, 32, 32)
    if shield_active:
        glColor4f(0.0, 0.8, 1.0, 0.3)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glutWireSphere(ball_radius + 5, 16, 16)
        glDisable(GL_BLEND)
    glPopMatrix()

def draw_shields():
    for shield in shields:
        if not shield['collected']:
            glPushMatrix()
            x, y, z = shield['pos']
            glTranslatef(x, y, z + 5 * math.sin(time.time() * 2))
            shield['rotation'] += 2.0
            glRotatef(shield['rotation'], 0, 0, 1)
            glColor3f(0.0, 1.0, 1.0)
            glutSolidCube(20)
            glColor3f(1.0, 1.0, 1.0)
            glBegin(GL_LINE_LOOP)
            for i in range(8):
                angle = i * math.pi / 4
                glVertex3f(math.cos(angle) * 8, math.sin(angle) * 8, 12)
            glEnd()
            glPopMatrix()

def draw_ui():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glDisable(GL_DEPTH_TEST)
    glColor3f(1, 1, 1)
    glRasterPos2f(10, WINDOW_HEIGHT - 25)
    if current_round >= 5:
        glColor3f(1, 0.3, 0.3)
    score_text = f"ROUND {current_round}/{max_rounds} | Score: {score}/{round_target_score} | Lives: {lives}"
    for ch in score_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    time_left = max(0, bounce_time_limit - bounce_timer)
    if time_left <= 3.0:
        pulse = 0.5 + 0.5 * math.sin(time.time() * 8)
        glColor3f(pulse, 0.2, 0.2)
    elif time_left <= 5.0:
        glColor3f(1.0, 0.6, 0.0)
    else:
        glColor3f(0.0, 1.0, 0.0)
    glRasterPos2f(10, WINDOW_HEIGHT - 50)
    bounce_text = f" BOUNCE TIMER: {time_left:.1f}s / {bounce_time_limit:.0f}s ⚡"
    for ch in bounce_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    elapsed_time = time.time() - game_start_time
    glColor3f(0.8, 0.8, 0.8)
    glRasterPos2f(10, WINDOW_HEIGHT - 75)
    timer_text = f"Time: {elapsed_time:.1f}s"
    for ch in timer_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(ch))
    if current_round >= 5:
        pulse = 0.5 + 0.5 * math.sin(time.time() * 6)
        glColor3f(pulse, 0.2, 0.2)
        glRasterPos2f(10, WINDOW_HEIGHT - 100)
        warning_text = " FINAL ROUND! ALL BOUNDARY TREES ARE ACTIVE!"
        for ch in warning_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    if show_timer:
        time_left_tile = max(0, max_tile_time - time_on_tile)
        glColor3f(1, 0.5, 0) if time_left_tile > 1 else glColor3f(1, 0, 0)
        glRasterPos2f(10, WINDOW_HEIGHT - 125)
        timer_warning = f"Move in: {time_left_tile:.1f}s"
        for ch in timer_warning:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    if shield_active:
        remaining_shield = max(0, max_shield_duration - shield_duration)
        glColor3f(0, 1, 1)
        glRasterPos2f(10, WINDOW_HEIGHT - 150)
        shield_text = f"Shield: {remaining_shield:.1f}s"
        for ch in shield_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    glColor3f(0.8, 0.8, 0.8)
    glRasterPos2f(WINDOW_WIDTH - 350, 25)
    controls = "WASD: Move | Space: Jump (MUST BOUNCE!) | T: Theme | P: Pause | R: Restart"
    for ch in controls:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(ch))
    if game_paused:
        glColor3f(1, 1, 0)
        glRasterPos2f(WINDOW_WIDTH // 2 - 100, WINDOW_HEIGHT // 2 + 20)
        pause_text = "GAME PAUSED"
        for ch in pause_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
            
        glRasterPos2f(WINDOW_WIDTH // 2 - 120, WINDOW_HEIGHT // 2 - 20)
        pause_instruction = "Press P to resume"
        for ch in pause_instruction:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    
    glEnable(GL_DEPTH_TEST)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_game_over():
    if game_over:
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glColor3f(1, 0, 0)
        glRasterPos2f(WINDOW_WIDTH // 2 - 180, WINDOW_HEIGHT // 2)
        game_over_text = f"GAME OVER! Reached Round {current_round} (Press R to Restart)"
        for ch in game_over_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
        glEnable(GL_DEPTH_TEST)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

def draw_win_message():
    if game_won:
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glColor3f(0, 1, 0)
        glRasterPos2f(WINDOW_WIDTH // 2 - 120, WINDOW_HEIGHT // 2)
        win_text = f"🏆 YOU SURVIVED ALL 5 ROUNDS! 🏆 (Press R to Restart)"
        for ch in win_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
        glEnable(GL_DEPTH_TEST)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

def update_obstacles(dt):
    for o in obstacles:
        o['pattern_time'] += dt * o['aggressiveness']
        if o['pattern'] == 'oscillate':
            o['pos'][1] += o['vel'] * dt * obstacle_speed_multiplier
            if o['pos'][1] > half_size_y - o['current_size'] or o['pos'][1] < -half_size_y + o['current_size']:
                o['vel'] *= -1.1
        elif o['pattern'] == 'circle':
            radius = 40 + current_round * 10
            radius_variation = 15 * math.sin(o['pattern_time'] * 0.5)
            total_radius = radius + radius_variation
            o['pos'][0] = o['original_pos'][0] + total_radius * math.cos(o['pattern_time'])
            o['pos'][1] = o['original_pos'][1] + total_radius * math.sin(o['pattern_time'])
        elif o['pattern'] == 'figure8':
            scale = 50 + current_round * 10
            o['pos'][0] = o['original_pos'][0] + scale * math.cos(o['pattern_time'])
            o['pos'][1] = o['original_pos'][1] + scale * math.sin(2 * o['pattern_time']) / 2
        elif o['pattern'] == 'zigzag':
            o['pos'][0] = o['original_pos'][0] + 50 * math.sin(o['pattern_time'] * 2)
            o['pos'][1] += o['vel'] * dt * obstacle_speed_multiplier
            if o['pos'][1] > half_size_y - o['current_size'] or o['pos'][1] < -half_size_y + o['current_size']:
                o['vel'] *= -1
        shrink_rate = o['shrink_speed'] * dt
        if current_round >= 3:
            shrink_rate *= 0.7
        o['current_size'] -= shrink_rate
        if o['current_size'] <= o['min_size']:
            o['current_size'] = o['base_size']
        float_intensity = 1.0 + current_round * 0.3
        o['pos'][2] = o['float_height'] + 15 * math.sin(time.time() * o['float_speed'] * float_intensity + o['float_offset'])

def apply_special_effect(effect):
    global speed_multiplier, lives, shield_active, shield_duration, max_tile_time, score
    if effect == 'speed_boost':
        speed_multiplier += 0.3
    elif effect == 'slow_time':
        for o in obstacles:
            o['vel'] *= 0.6
    elif effect == 'extra_life':
        lives += 1
    elif effect == 'shield':
        shield_active = True
        shield_duration = 0.0
    elif effect == 'score_multiplier':
        score += 2

def check_tile_effects():
    global max_tile_time, speed_multiplier
    i = int(math.floor((ball_pos[0] + half_size_x) / tile_size))
    j = int(math.floor((ball_pos[1] + half_size_y) / tile_size))
    current_tile = (i, j)
    base_time = max_tile_time
    if current_tile in zones['danger']:
        max_tile_time = max(0.4, base_time - current_round * 0.2)
    elif current_tile in zones['safe']:
        max_tile_time = base_time + 1.0
    else:
        max_tile_time = base_time

def update():
    global time_last, ball_pos, ball_vel, jumping, jump_start_time, score, lives
    global game_over, last_tile, time_on_tile, show_timer, game_won, speed_multiplier
    global shield_active, shield_duration, difficulty_timer, difficulty_mode, game_paused
    global max_shield_duration, obstacles, tree_obstacles, projectiles, collectibles
    global special_collectibles, shields, max_tile_time, current_round, boundary_trees
    global obstacle_speed_multiplier, bounce_timer, bounce_time_limit, last_bounce_time
    global small_obstacle_trees

    if game_paused:
        return

    now = time.time()
    dt = now - time_last
    time_last = now

    if game_over or game_won:
        return

    update_bounce_timer()
    if game_over:
        return

    if current_round > max_rounds or (current_round == max_rounds and score >= round_target_score):
        game_won = True
        return

    if shield_active:
        shield_duration += dt
        if shield_duration >= max_shield_duration:
            shield_active = False
            shield_duration = 0.0

    move_dir = [0, 0]
    if move_keys['w']: move_dir[0] += 1
    if move_keys['s']: move_dir[0] -= 1
    if move_keys['a']: move_dir[1] += 1
    if move_keys['d']: move_dir[1] -= 1

    if move_dir[0] and move_dir[1]:
        length = math.sqrt(move_dir[0]**2 + move_dir[1]**2)
        move_dir = [d / length for d in move_dir]

    ball_vel[0] = move_dir[0] * base_speed * speed_multiplier
    ball_vel[1] = move_dir[1] * base_speed * speed_multiplier

    on_ground = ball_pos[2] <= ball_radius + 1
    if space_pressed and on_ground and not jumping:
        jumping = True
        jump_start_time = now
        ball_vel[2] = jump_strength
        reset_bounce_timer()

    if jumping:
        if space_pressed and (now - jump_start_time) < max_jump_duration:
            ball_vel[2] = jump_strength
        else:
            jumping = False

    ball_vel[2] += gravity * dt
    for i in range(3):
        ball_pos[i] += ball_vel[i] * dt

    if ball_pos[2] < ball_radius:
        ball_pos[2] = ball_radius
        ball_vel[2] = 0
        jumping = False

    ball_pos[0] = max(-half_size_x + ball_radius, min(half_size_x - ball_radius, ball_pos[0]))
    ball_pos[1] = max(-half_size_y + ball_radius, min(half_size_y - ball_radius, ball_pos[1]))

    check_tile_effects()

    for o in obstacles:
        dx = ball_pos[0] - o['pos'][0]
        dy = ball_pos[1] - o['pos'][1]
        dz = ball_pos[2] - o['pos'][2]
        distance = math.sqrt(dx**2 + dy**2 + dz**2)
        if distance < ball_radius + o['current_size'] and on_ground:
            if shield_active:
                shield_active = False
                shield_duration = 0.0
            else:
                lives -= 1
                if lives <= 0:
                    game_over = True
                    return
                else:
                    ball_pos[:] = find_safe_start_tile()
                    ball_vel[:] = [0.0, 0.0, 0.0]
                    shield_active = True
                    max_shield_duration = 2.0
                    reset_bounce_timer()
            break

    update_tree_obstacles(dt)
    update_projectiles(dt)

    for proj in projectiles[:]:
        dx = ball_pos[0] - proj['pos'][0]
        dy = ball_pos[1] - proj['pos'][1]
        dz = ball_pos[2] - proj['pos'][2]
        distance = math.sqrt(dx**2 + dy**2 + dz**2)
        if distance < ball_radius + proj['size'] and not on_ground:
            if shield_active:
                shield_active = False
                shield_duration = 0.0
                projectiles.remove(proj)
            else:
                lives -= 1
                if lives <= 0:
                    game_over = True
                    return
                else:
                    ball_pos[:] = find_safe_start_tile()
                    ball_vel[:] = [0.0, 0.0, 0.0]
                    shield_active = True
                    shield_duration = 0.0
                    max_shield_duration = 2.0
                    reset_bounce_timer()
                projectiles.remove(proj)
            break

    for shield in shields:
        if not shield['collected']:
            dx = ball_pos[0] - shield['pos'][0]
            dy = ball_pos[1] - shield['pos'][1]
            dz = ball_pos[2] - shield['pos'][2]
            distance = math.sqrt(dx**2 + dy**2 + dz**2)
            if distance < ball_radius + 15:
                shield['collected'] = True
                shield_active = True
                shield_duration = 0.0
                max_shield_duration = 8.0

    i = int(math.floor((ball_pos[0] + half_size_x) / tile_size))
    j = int(math.floor((ball_pos[1] + half_size_y) / tile_size))
    current_tile = (i, j)

    if ball_pos[2] <= ball_radius + 1 and current_tile not in holes:
        if current_tile == last_tile:
            time_on_tile += dt
            show_timer = True
            if time_on_tile >= max_tile_time:
                lives -= 1
                time_on_tile = 0.0
                last_tile = None
                show_timer = False
                if lives <= 0:
                    game_over = True
                else:
                    ball_pos[:] = find_safe_start_tile()
                    ball_vel[:] = [0.0, 0.0, 0.0]
                    reset_bounce_timer()
        else:
            last_tile = current_tile
            time_on_tile = 0.0
            show_timer = True
    else:
        show_timer = False

    if current_tile in holes and ball_pos[2] <= ball_radius + 1:
        if shield_active:
            shield_active = False
            shield_duration = 0.0
        else:
            lives -= 1
            if lives <= 0:
                game_over = True
            else:
                ball_pos[:] = find_safe_start_tile()
                ball_vel[:] = [0.0, 0.0, 0.0]
                reset_bounce_timer()

    update_obstacles(dt)

    remaining_collectibles = []
    for c in collectibles:
        if not c['collected']:
            dx = ball_pos[0] - c['pos'][0]
            dy = ball_pos[1] - c['pos'][1]
            dz = ball_pos[2] - c['pos'][2]
            distance = math.sqrt(dx**2 + dy**2 + dz**2)
            if distance < ball_radius + 10:
                c['collected'] = True
                score += 1
                if len(collectibles) < max(2, 6 - current_round):
                    x, y = find_safe_tile()
                    collectibles.append({
                        'type': random.choice(['cube', 'torus', 'pyramid']),
                        'pos': [x, y, 15],
                        'rotation': 0.0,
                        'collected': False,
                        'float_offset': random.random() * 6.28
                    })
            else:
                remaining_collectibles.append(c)
    collectibles[:] = remaining_collectibles

    for sc in special_collectibles:
        if not sc['collected']:
            dx = ball_pos[0] - sc['pos'][0]
            dy = ball_pos[1] - sc['pos'][1]
            dz = ball_pos[2] - sc['pos'][2]
            distance = math.sqrt(dx**2 + dy**2 + dz**2)
            if distance < ball_radius + 12:
                sc['collected'] = True
                score += 1
                apply_special_effect(sc['effect'])

    update_round_progression()

def display():
    setup_scene()
    draw_floor()
    draw_walls()
    draw_trees()
    draw_tree_obstacles()
    draw_small_obstacle_trees()
    draw_projectiles()
    if not game_won:
        draw_collectibles()
        draw_special_collectibles()
    draw_shields()
    draw_obstacles()
    draw_ball()
    draw_ui()
    draw_game_over()
    draw_win_message()
    glutSwapBuffers()

def idle():
    """Idle function that runs continuously - fixed pause functionality"""
    if not game_paused:  # Only update if game is not paused
        update()
    glutPostRedisplay()

def keyboard(k, x, y):
    global space_pressed, theme, difficulty_timer, difficulty_mode, speed_multiplier, game_paused, time_last
    
    if k == b'\x1b':
        sys.exit()
    if k == b' ':
        if not game_paused:
            space_pressed = True
    if k in [b'a', b'd', b'w', b's']: 
        if not game_paused:
            move_keys[k.decode()] = True
    if k == b'r':   
        reset_game()
    if k == b't': 
        theme = "dark" if theme == "default" else "default"
    if k == b'p':
        game_paused = not game_paused
        if not game_paused:
            time_last = time.time()

def keyboard_up(k, x, y):
    global space_pressed
    
    if k == b' ':
        space_pressed = False
    if k in [b'a', b'd', b'w', b's']:
        move_keys[k.decode()] = False

def special_keys(key, x, y):
    global camera_angle, camera_height, camera_distance
    if key == GLUT_KEY_LEFT:
        camera_angle += 5
    elif key == GLUT_KEY_RIGHT:
        camera_angle -= 5
    elif key == GLUT_KEY_UP:
        camera_height += 20
    elif key == GLUT_KEY_DOWN:
        camera_height -= 20
    elif key == GLUT_KEY_PAGE_UP:
        camera_distance = max(200, camera_distance - 50)
    elif key == GLUT_KEY_PAGE_DOWN:
        camera_distance = min(1000, camera_distance + 50)
    camera_height = max(100, min(1000, camera_height))

def mouse(button, state, x, y):
    global camera_angle
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        camera_angle = 0
    elif button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        global camera_height, camera_distance
        camera_height = 500.0
        camera_distance = 500.0
        camera_angle = 0

def main():
    print(" === ENHANCED TILE TUMBLE - 5 ROUND CHALLENGE WITH BOUNCE TIMER ===")
    print("Controls:")
    print("  WASD - Move ball")
    print("  Space - Jump (hold for higher jump)")
    print("  Arrow Keys - Adjust camera")
    print("  T - Toggle theme")
    print("  P - Pause/unpause")
    print("  R - Restart game")
    print("  ESC - Exit")
    print("\n OBJECTIVE: Survive 5 increasingly difficult rounds!")
    print("Each round: Collect 4 points to advance")
    print(" BOUNCE TIMER: Must jump every few seconds or lose a life!")
    print("   - Round 1: 10 seconds")
    print("   - Round 2: 9 seconds")
    print("   - Round 3: 8 seconds")
    print("   - Round 4: 7 seconds")
    print("   - Round 5: 6 seconds")
    print("ROUND 5 SPECIAL: All boundary trees become active shooters!")
    print(" STRATEGY: Obstacles hurt when ON GROUND, Projectiles hurt when IN AIR!")
    print(" Win by completing all 5 rounds!\n")
    
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Enhanced Tile Tumble - 5 Round Challenge with Bounce Timer")
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)

    glutReshapeFunc(reshape)
    glutDisplayFunc(display)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboard)
    glutKeyboardUpFunc(keyboard_up)
    glutSpecialFunc(special_keys)
    glutMouseFunc(mouse)
    setup_projection()
    reset_game()
    
    print(" Game initialized! Round 1 begins!")
    print(" Collect 4 points to advance to Round 2!")
    print(" REMEMBER: Must jump every 10 seconds!")
    glutMainLoop()

if __name__ == '__main__':
    main()
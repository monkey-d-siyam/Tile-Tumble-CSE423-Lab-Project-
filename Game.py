from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18, GLUT_BITMAP_HELVETICA_12
from OpenGL.GLU import *
import math, time, sys, random
import ctypes

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
ASPECT = WINDOW_WIDTH / WINDOW_HEIGHT

# Physics constants
gravity = -500.0
jump_strength = 250.0
max_jump_duration = 0.35

# Ball properties
ball_radius = 10.0
ball_pos = [0.0, 0.0, 10.0]
ball_vel = [0.0, 0.0, 0.0]
jumping = False
jump_start_time = 0.0

# Game state
score = 0
lives = 3
game_over = False
game_won = False
game_paused = False
last_tile = None
time_on_tile = 0.0
max_tile_time = 3.0  # Reduced for better gameplay
show_timer = False
time_last = time.time()
game_start_time = time.time()

# Input handling
move_keys = {"a": False, "d": False, "w": False, "s": False}
space_pressed = False

# Difficulty and progression
difficulty_timer = None
difficulty_mode = False
speed_multiplier = 1.0
base_speed = 200.0
difficulty_level = 1

# Camera settings
camera_distance = 500.0
camera_angle = 0
camera_height = 500.0

# Grid and environment
wall_height = 80.0
grid_size_x = 20  # Increased grid size
grid_size_y = 15
tile_size = 80
half_size_x = grid_size_x * tile_size / 2
half_size_y = grid_size_y * tile_size / 2

# Game objects
obstacles = []
collectibles = []
special_collectibles = []
holes = set()
theme = "default"
shields = []
shield_active = False
shield_duration = 0.0
max_shield_duration = 10.0

# Zone system for checkered floor
zones = {
    'safe': [],    # White tiles - safe zone
    'normal': [],  # Green tiles - normal zone  
    'danger': []   # Special colored tiles - danger zone
}

def initialize_zones():
    """Initialize the zone system for checkered tiles"""
    global zones
    zones = {'safe': [], 'normal': [], 'danger': []}
    
    for i in range(grid_size_x):
        for j in range(grid_size_y):
            if (i, j) not in holes:
                if (i + j) % 2 == 0:  # White tiles
                    zones['safe'].append((i, j))
                else:  # Green tiles
                    if random.random() < 0.1:  # 10% chance for danger zones
                        zones['danger'].append((i, j))
                    else:
                        zones['normal'].append((i, j))

def generate_holes():
    """Generate random holes in the grid"""
    global holes
    holes = set()
    # Generate fewer holes initially, increase with difficulty
    hole_count = min(50 + difficulty_level * 10, 80)
    
    while len(holes) < hole_count:
        i = random.randint(1, grid_size_x - 2)  # Avoid edges
        j = random.randint(1, grid_size_y - 2)
        holes.add((i, j))

def find_safe_tile():
    """Find a random safe tile (not a hole)"""
    attempts = 0
    while attempts < 100:
        i = random.randint(0, grid_size_x - 1)
        j = random.randint(0, grid_size_y - 1)
        if (i, j) not in holes:
            x = i * tile_size - half_size_x + tile_size / 2
            y = j * tile_size - half_size_y + tile_size / 2
            return (x, y)
        attempts += 1
    return (0, 0)  # Fallback

def find_safe_start_tile():
    """Find a safe starting position for the ball"""
    # Start from center and work outward
    for radius in range(3):
        for i in range(grid_size_x // 2 - radius, grid_size_x // 2 + radius + 1):
            for j in range(grid_size_y // 2 - radius, grid_size_y // 2 + radius + 1):
                if 0 <= i < grid_size_x and 0 <= j < grid_size_y and (i, j) not in holes:
                    x = i * tile_size - half_size_x + tile_size / 2
                    y = j * tile_size - half_size_y + tile_size / 2
                    return [x, y, 10.0]
    return [0.0, 0.0, 10.0]

def generate_obstacles():
    """Generate dynamic obstacles with patterns"""
    global obstacles
    obstacles = []
    obstacle_count = 6 + difficulty_level * 2
    
    for _ in range(obstacle_count):
        x, y = find_safe_tile()
        obstacles.append({
            'pos': [x + random.uniform(-30, 30), y + random.uniform(-30, 30), 30],
            'base_size': random.uniform(12, 25),
            'current_size': 0,  # Will grow to base_size
            'vel': random.uniform(50, 150) * random.choice([-1, 1]),
            'shrink_speed': random.uniform(0.5, 1.5),
            'min_size': random.uniform(3, 8),
            'float_height': random.uniform(20, 60),
            'float_speed': random.uniform(1.0, 3.0),
            'float_offset': random.random() * 6.28,
            'pulse': 0,
            'pattern': random.choice(['oscillate', 'circle', 'figure8']),
            'pattern_time': 0.0,
            'original_pos': [x, y]
        })

def generate_collectibles():
    """Generate random collectibles and special collectibles"""
    global collectibles, special_collectibles
    collectibles = []
    special_collectibles = []
    
    # Regular collectibles
    collectible_count = 8 + difficulty_level
    for _ in range(collectible_count):
        x, y = find_safe_tile()
        collectibles.append({
            'type': random.choice(['cube', 'torus', 'pyramid']),
            'pos': [x, y, 15],
            'rotation': 0.0,
            'collected': False,
            'float_offset': random.random() * 6.28
        })
    
    # Special collectibles with effects
    special_count = 3 + difficulty_level // 2
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
    """Generate shield collectibles"""
    global shields
    shields = []
    shield_count = 2 + difficulty_level // 3
    
    for _ in range(shield_count):
        x, y = find_safe_tile()
        shields.append({
            'pos': [x, y, 10],
            'collected': False,
            'rotation': 0.0
        })

def reset_game(reset_score=True, reset_lives=True):
    """Reset game state with improved initialization"""
    global ball_pos, ball_vel, jumping, jump_start_time, score, lives, game_over, game_won
    global collectibles, special_collectibles, time_last, obstacles, last_tile, time_on_tile
    global show_timer, difficulty_timer, difficulty_mode, speed_multiplier, game_start_time
    global shield_active, shield_duration, difficulty_level, game_paused

    # Reset ball
    ball_pos[:] = find_safe_start_tile()
    ball_vel[:] = [0.0, 0.0, 0.0]
    jumping = False
    jump_start_time = 0.0

    # Reset game state
    if reset_score:
        score = 0
        difficulty_level = 1
        
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

    # Reset power-ups
    shield_active = False
    shield_duration = 0.0
    
    # Reset difficulty
    difficulty_timer = None
    difficulty_mode = False
    speed_multiplier = 1.0

    # Regenerate game world
    generate_holes()
    initialize_zones()
    generate_obstacles()
    generate_collectibles()
    generate_shields()

def setup_projection():
    """Setup 3D projection matrix"""
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60.0, ASPECT, 1.0, 3000.0)
    glMatrixMode(GL_MODELVIEW)

def reshape(w, h):
    """Handle window resizing"""
    global WINDOW_WIDTH, WINDOW_HEIGHT, ASPECT
    WINDOW_WIDTH = w
    WINDOW_HEIGHT = h
    ASPECT = w / h if h > 0 else 1
    glViewport(0, 0, w, h)
    setup_projection()

def setup_scene():
    """Setup the 3D scene with camera and lighting"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)
    glLoadIdentity()
    
    # Camera follows ball with smooth movement
    angle_rad = math.radians(camera_angle)
    eye_x = ball_pos[0] - camera_distance * math.cos(angle_rad)
    eye_y = ball_pos[1] + camera_distance * math.sin(angle_rad)
    eye_z = ball_pos[2] + camera_height
    
    gluLookAt(eye_x, eye_y, eye_z,
              ball_pos[0], ball_pos[1], ball_pos[2],
              0.0, 0.0, 1.0)
    
    # Set background color based on theme
    if theme == "default":
        glClearColor(0.5, 0.8, 1.0, 1.0)  # Sky blue
    elif theme == "dark":
        glClearColor(0.1, 0.1, 0.2, 1.0)  # Dark blue

def draw_floor():
    """Draw checkered tile floor with zones"""
    global theme
    
    # Define colors based on theme
    if theme == "default":
        safe_color = (1.0, 1.0, 1.0)      # White - safe zone
        normal_color = (0.302, 0.471, 0.388)  # Green - normal zone
        danger_color = (0.8, 0.2, 0.2)    # Red - danger zone
        hole_color = (0.0, 0.0, 0.0)      # Black - holes
    elif theme == "dark":
        safe_color = (0.3, 0.3, 0.3)      # Dark gray - safe zone
        normal_color = (0.1, 0.2, 0.1)    # Dark green - normal zone
        danger_color = (0.3, 0.1, 0.1)    # Dark red - danger zone
        hole_color = (0.5, 0.0, 0.0)      # Dark red - holes

    for i in range(grid_size_x):
        for j in range(grid_size_y):
            x = i * tile_size - half_size_x
            y = j * tile_size - half_size_y
            
            # Determine tile color and type
            if (i, j) in holes:
                glColor3f(*hole_color)
            elif (i, j) in zones['danger']:
                glColor3f(*danger_color)
            elif (i, j) in zones['safe']:
                glColor3f(*safe_color)
            else:  # normal zone
                glColor3f(*normal_color)
            
            # Draw tile with slight 3D effect
            glBegin(GL_QUADS)
            glVertex3f(x, y, 0.0)
            glVertex3f(x + tile_size, y, 0.0)
            glVertex3f(x + tile_size, y + tile_size, 0.0)
            glVertex3f(x, y + tile_size, 0.0)
            glEnd()
            
            # Add tile borders for better visibility
            glColor3f(0.0, 0.0, 0.0)
            glLineWidth(1.0)
            glBegin(GL_LINE_LOOP)
            glVertex3f(x, y, 0.1)
            glVertex3f(x + tile_size, y, 0.1)
            glVertex3f(x + tile_size, y + tile_size, 0.1)
            glVertex3f(x, y + tile_size, 0.1)
            glEnd()

def draw_walls():
    """Draw boundary walls and trees"""
    # Walls
    glColor3f(0.2, 0.2, 0.8)
    wall_positions = [
        (-half_size_x, 0, -half_size_y, half_size_y, True),   # Left wall
        (half_size_x, 0, -half_size_y, half_size_y, True),    # Right wall
        (0, half_size_y, -half_size_x, half_size_x, False),   # Top wall
        (0, -half_size_y, -half_size_x, half_size_x, False)   # Bottom wall
    ]
    
    for wall in wall_positions:
        if wall[4]:  # Vertical wall
            x, _, y1, y2 = wall[:4]
            glBegin(GL_QUADS)
            glVertex3f(x, y1, 0)
            glVertex3f(x, y2, 0)
            glVertex3f(x, y2, wall_height)
            glVertex3f(x, y1, wall_height)
            glEnd()
        else:  # Horizontal wall
            _, y, x1, x2 = wall[:4]
            glBegin(GL_QUADS)
            glVertex3f(x1, y, 0)
            glVertex3f(x2, y, 0)
            glVertex3f(x2, y, wall_height)
            glVertex3f(x1, y, wall_height)
            glEnd()

def draw_trees():
    """Draw decorative trees around the boundaries"""
    if theme == "default":
        trunk_color = (0.55, 0.27, 0.07)
        foliage_color = (0.0, 0.5, 0.0)
    elif theme == "dark":
        trunk_color = (0.3, 0.15, 0.05)
        foliage_color = (0.0, 0.3, 0.3)

    tree_positions = []
    spacing = tile_size * 2
    
    # Trees along boundaries
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
        # Draw trunk
        glColor3f(*trunk_color)
        glPushMatrix()
        glTranslatef(tx, ty, 15)
        glScalef(8, 8, 30)
        glutSolidCube(1)
        glPopMatrix()

        # Draw foliage
        glColor3f(*foliage_color)
        glPushMatrix()
        glTranslatef(tx, ty, 45)
        glutSolidCone(20, 50, 12, 12)
        glPopMatrix()

def draw_collectibles():
    """Draw regular collectibles with rotation animation"""
    current_time = time.time()
    
    for c in collectibles:
        if not c['collected']:
            glPushMatrix()
            x, y, base_z = c['pos']
            
            # Floating animation
            float_z = base_z + 5 * math.sin(current_time * 2 + c['float_offset'])
            glTranslatef(x, y, float_z)
            
            # Rotation animation
            c['rotation'] += 2.0
            glRotatef(c['rotation'], 0, 0, 1)
            
            # Set color based on type
            if c['type'] == 'cube':
                glColor3f(1.0, 0.8, 0.0)  # Gold
                glutSolidCube(15)
            elif c['type'] == 'torus':
                glColor3f(0.0, 1.0, 1.0)  # Cyan
                glutSolidTorus(3, 10, 12, 12)
            elif c['type'] == 'pyramid':
                glColor3f(1.0, 0.0, 1.0)  # Magenta
                # Draw pyramid
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
    """Draw special collectibles with effects"""
    current_time = time.time()
    
    for sc in special_collectibles:
        if not sc['collected']:
            glPushMatrix()
            x, y, base_z = sc['pos']
            
            # Enhanced floating and glowing animation
            sc['glow'] += 0.1
            sc['rotation'] += 3.0
            glow_intensity = 0.5 + 0.5 * math.sin(sc['glow'])
            float_z = base_z + 8 * math.sin(current_time * 1.5)
            
            glTranslatef(x, y, float_z)
            glRotatef(sc['rotation'], 0, 0, 1)
            
            # Color based on effect type
            effect_colors = {
                'speed_boost': (0.0, 1.0, 0.0),      # Green
                'slow_time': (0.0, 0.0, 1.0),        # Blue  
                'extra_life': (1.0, 0.0, 0.0),       # Red
                'shield': (1.0, 1.0, 0.0),           # Yellow
                'score_multiplier': (1.0, 0.5, 0.0)  # Orange
            }
            
            color = effect_colors.get(sc['effect'], (1.0, 1.0, 1.0))
            glColor3f(color[0] * glow_intensity, color[1] * glow_intensity, color[2] * glow_intensity)
            
            # Draw star shape
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(0, 0, 0)
            for i in range(11):
                angle = i * 2 * math.pi / 10
                radius = 12 if i % 2 == 0 else 6
                glVertex3f(math.cos(angle) * radius, math.sin(angle) * radius, 0)
            glEnd()
            
            # Draw effect indicator
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
    """Draw dynamic obstacles with patterns"""
    current_time = time.time()
    
    for o in obstacles:
        glPushMatrix()
        x, y, z = o['pos']
        glTranslatef(x, y, z)

        # Pulsing effect
        o['pulse'] += 0.1
        pulse_factor = 0.5 + 0.5 * math.sin(o['pulse'])

        # Color based on size (danger level)
        size_ratio = (o['current_size'] - o['min_size']) / (o['base_size'] - o['min_size'])
        red_intensity = 0.8 + (1.0 - size_ratio) * 0.2 * pulse_factor
        green_blue = 0.1 * size_ratio

        glColor3f(red_intensity, green_blue, green_blue)
        glutSolidSphere(o['current_size'], 16, 16)

        # Glow effect when small/dangerous
        if o['current_size'] < o['base_size'] * 0.7:
            glPushMatrix()
            glow_size = o['current_size'] * (1.0 + 0.3 * pulse_factor)
            glColor4f(1.0, 0.3, 0.3, 0.3 + 0.2 * pulse_factor)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glutWireSphere(glow_size, 12, 12)
            glDisable(GL_BLEND)
            glPopMatrix()

        glPopMatrix()

def draw_ball():
    """Draw the player ball with enhanced visuals"""
    glPushMatrix()
    glTranslatef(ball_pos[0], ball_pos[1], ball_pos[2])
    
    # Ball color changes based on state
    if shield_active:
        # Shield effect - glowing blue
        glow = 0.5 + 0.5 * math.sin(time.time() * 5)
        glColor3f(0.0, glow, 1.0)
    elif jumping:
        glColor3f(1.0, 1.0, 0.0)  # Yellow when jumping
    else:
        glColor3f(1.0, 0.0, 0.0)  # Red normally
    
    glutSolidSphere(ball_radius, 32, 32)
    
    # Draw shield effect
    if shield_active:
        glColor4f(0.0, 0.8, 1.0, 0.3)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glutWireSphere(ball_radius + 5, 16, 16)
        glDisable(GL_BLEND)
    
    glPopMatrix()

def draw_shields():
    """Draw shield collectibles"""
    for shield in shields:
        if not shield['collected']:
            glPushMatrix()
            x, y, z = shield['pos']
            glTranslatef(x, y, z + 5 * math.sin(time.time() * 2))
            
            shield['rotation'] += 2.0
            glRotatef(shield['rotation'], 0, 0, 1)
            
            glColor3f(0.0, 1.0, 1.0)  # Cyan
            glutSolidCube(20)
            
            # Draw shield symbol
            glColor3f(1.0, 1.0, 1.0)
            glBegin(GL_LINE_LOOP)
            for i in range(8):
                angle = i * math.pi / 4
                glVertex3f(math.cos(angle) * 8, math.sin(angle) * 8, 12)
            glEnd()
            
            glPopMatrix()

def draw_ui():
    """Draw comprehensive UI including score, lives, timer"""
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glDisable(GL_DEPTH_TEST)

    # Score and Lives
    glColor3f(1, 1, 1)
    glRasterPos2f(10, WINDOW_HEIGHT - 25)
    score_text = f"Score: {score} | Lives: {lives} | Level: {difficulty_level}"
    for ch in score_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    # Game timer
    elapsed_time = time.time() - game_start_time
    glRasterPos2f(10, WINDOW_HEIGHT - 50)
    timer_text = f"Time: {elapsed_time:.1f}s"
    for ch in timer_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(ch))

    # Tile timer warning
    if show_timer:
        time_left = max(0, max_tile_time - time_on_tile)
        glColor3f(1, 0.5, 0) if time_left > 1 else glColor3f(1, 0, 0)
        glRasterPos2f(10, WINDOW_HEIGHT - 75)
        timer_warning = f"Move in: {time_left:.1f}s"
        for ch in timer_warning:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    # Difficulty mode timer
    if difficulty_mode and difficulty_timer is not None:
        time_remaining = max(0, 40 - (time.time() - difficulty_timer))
        glColor3f(1, 0, 0)
        glRasterPos2f(10, WINDOW_HEIGHT - 100)
        diff_text = f"HARD MODE - Time Left: {time_remaining:.1f}s"
        for ch in diff_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    # Shield status
    if shield_active:
        remaining_shield = max(0, max_shield_duration - shield_duration)
        glColor3f(0, 1, 1)
        glRasterPos2f(10, WINDOW_HEIGHT - 125)
        shield_text = f"Shield: {remaining_shield:.1f}s"
        for ch in shield_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    # Controls help
    glColor3f(0.8, 0.8, 0.8)
    glRasterPos2f(WINDOW_WIDTH - 300, 25)
    controls = "WASD: Move | Space: Jump | T: Theme | X: Hard Mode | R: Restart"
    for ch in controls:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(ch))

    # Pause indicator
    if game_paused:
        glColor3f(1, 1, 0)
        glRasterPos2f(WINDOW_WIDTH // 2 - 50, WINDOW_HEIGHT // 2)
        pause_text = "PAUSED (P to resume)"
        for ch in pause_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    glEnable(GL_DEPTH_TEST)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_game_over():
    """Draw game over message"""
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
        glRasterPos2f(WINDOW_WIDTH // 2 - 150, WINDOW_HEIGHT // 2)
        game_over_text = f"GAME OVER! Final Score: {score} (Press R to Restart)"
        for ch in game_over_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
        
        glEnable(GL_DEPTH_TEST)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

def draw_win_message():
    """Draw win message"""
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
        glRasterPos2f(WINDOW_WIDTH // 2 - 100, WINDOW_HEIGHT // 2)
        win_text = f"YOU WIN! Score: {score} (Press R to Restart)"
        for ch in win_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
        
        glEnable(GL_DEPTH_TEST)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

def update_obstacles(dt):
    """Update dynamic obstacles with patterns"""
    for o in obstacles:
        # Update pattern movement
        o['pattern_time'] += dt
        
        if o['pattern'] == 'oscillate':
            # Simple back and forth movement
            o['pos'][1] += o['vel'] * dt
            if o['pos'][1] > half_size_y - o['current_size'] or o['pos'][1] < -half_size_y + o['current_size']:
                o['vel'] *= -1
                
        elif o['pattern'] == 'circle':
            # Circular movement around original position
            radius = 50
            o['pos'][0] = o['original_pos'][0] + radius * math.cos(o['pattern_time'])
            o['pos'][1] = o['original_pos'][1] + radius * math.sin(o['pattern_time'])
            
        elif o['pattern'] == 'figure8':
            # Figure-8 movement pattern
            scale = 60
            o['pos'][0] = o['original_pos'][0] + scale * math.cos(o['pattern_time'])
            o['pos'][1] = o['original_pos'][1] + scale * math.sin(2 * o['pattern_time']) / 2

        # Size pulsing effect
        o['current_size'] -= o['shrink_speed'] * dt
        if o['current_size'] <= o['min_size']:
            o['current_size'] = o['base_size']

        # Floating movement
        o['pos'][2] = o['float_height'] + 10 * math.sin(time.time() * o['float_speed'] + o['float_offset'])

def apply_special_effect(effect):
    """Apply special collectible effects"""
    global speed_multiplier, lives, shield_active, shield_duration, max_tile_time, score
    
    if effect == 'speed_boost':
        speed_multiplier += 0.3
        print("Speed boost activated!")
        
    elif effect == 'slow_time':
        # Temporarily slow down obstacles
        for o in obstacles:
            o['vel'] *= 0.5
        print("Time slowed!")
        
    elif effect == 'extra_life':
        lives += 1
        print("Extra life gained!")
        
    elif effect == 'shield':
        shield_active = True
        shield_duration = 0.0
        print("Shield activated!")
        
    elif effect == 'score_multiplier':
        score += 3  # Bonus points
        print("Score multiplier! +3 bonus points!")

def check_tile_effects():
    """Check for special tile zone effects"""
    global max_tile_time, speed_multiplier
    
    # Get current tile
    i = int(math.floor((ball_pos[0] + half_size_x) / tile_size))
    j = int(math.floor((ball_pos[1] + half_size_y) / tile_size))
    current_tile = (i, j)
    
    # Apply zone effects
    if current_tile in zones['danger']:
        # Danger zone - faster timer
        max_tile_time = 2.0
    elif current_tile in zones['safe']:
        # Safe zone - slower timer  
        max_tile_time = 4.0
    else:
        # Normal zone
        max_tile_time = 3.0

def update_difficulty():
    """Score-based difficulty scaling"""
    global difficulty_level, max_tile_time, speed_multiplier
    
    new_difficulty = 1 + score // 5  # Increase difficulty every 5 points
    
    if new_difficulty > difficulty_level:
        difficulty_level = new_difficulty
        print(f"Difficulty increased to level {difficulty_level}!")
        
        # Spawn more obstacles
        if len(obstacles) < 15:
            x, y = find_safe_tile()
            obstacles.append({
                'pos': [x + random.uniform(-30, 30), y + random.uniform(-30, 30), 30],
                'base_size': random.uniform(15, 30),
                'current_size': 0,
                'vel': random.uniform(80, 200) * random.choice([-1, 1]),
                'shrink_speed': random.uniform(1.0, 2.0),
                'min_size': random.uniform(3, 10),
                'float_height': random.uniform(20, 60),
                'float_speed': random.uniform(1.5, 4.0),
                'float_offset': random.random() * 6.28,
                'pulse': 0,
                'pattern': random.choice(['oscillate', 'circle', 'figure8']),
                'pattern_time': 0.0,
                'original_pos': [x, y]
            })

def update():
    """Main game update loop"""
    global time_last, ball_pos, ball_vel, jumping, jump_start_time, score, lives
    global game_over, last_tile, time_on_tile, show_timer, game_won, speed_multiplier
    global shield_active, shield_duration, difficulty_timer, difficulty_mode, game_paused

    if game_paused:
        return

    now = time.time()
    dt = now - time_last
    time_last = now

    # Check difficulty mode timer
    if difficulty_mode and difficulty_timer is not None:
        time_remaining = max(0, 40 - (now - difficulty_timer))
        if time_remaining <= 0:
            game_over = True
            print("Game Over! You ran out of time in difficulty mode.")
            return

    if game_over or game_won:
        return

    # Check win condition
    if score >= 15:  # Increased win condition
        game_won = True
        print("Congratulations! You achieved the target score and won!")
        return

    # Update shield duration
    if shield_active:
        shield_duration += dt
        if shield_duration >= max_shield_duration:
            shield_active = False
            shield_duration = 0.0
            print("Shield expired!")

    # Ball movement based on input
    move_dir = [0, 0]
    if move_keys['w']: move_dir[0] += 1
    if move_keys['s']: move_dir[0] -= 1
    if move_keys['a']: move_dir[1] += 1
    if move_keys['d']: move_dir[1] -= 1

    # Normalize diagonal movement
    if move_dir[0] and move_dir[1]:
        length = math.sqrt(move_dir[0]**2 + move_dir[1]**2)
        move_dir = [d / length for d in move_dir]

    # Apply movement
    ball_vel[0] = move_dir[0] * base_speed * speed_multiplier
    ball_vel[1] = move_dir[1] * base_speed * speed_multiplier

    # Jumping mechanics
    on_ground = ball_pos[2] <= ball_radius
    if space_pressed and on_ground and not jumping:
        jumping = True
        jump_start_time = now
        ball_vel[2] = jump_strength

    if jumping:
        if space_pressed and (now - jump_start_time) < max_jump_duration:
            ball_vel[2] = jump_strength
        else:
            jumping = False

    # Apply gravity and movement
    ball_vel[2] += gravity * dt
    for i in range(3):
        ball_pos[i] += ball_vel[i] * dt

    # Ground collision
    if ball_pos[2] < ball_radius:
        ball_pos[2] = ball_radius
        ball_vel[2] = 0
        jumping = False

    # Boundary collision
    ball_pos[0] = max(-half_size_x + ball_radius, min(half_size_x - ball_radius, ball_pos[0]))
    ball_pos[1] = max(-half_size_y + ball_radius, min(half_size_y - ball_radius, ball_pos[1]))

    # Check tile effects
    check_tile_effects()

    # Obstacle collision detection
    for o in obstacles:
        dx = ball_pos[0] - o['pos'][0]
        dy = ball_pos[1] - o['pos'][1]
        dz = ball_pos[2] - o['pos'][2]
        distance = math.sqrt(dx**2 + dy**2 + dz**2)

        if distance < ball_radius + o['current_size']:
            if shield_active:
                shield_active = False
                shield_duration = 0.0
                print("Shield protected you from obstacle!")
            else:
                lives -= 1
                print(f"Hit obstacle! Lives remaining: {lives}")
                if lives <= 0:
                    game_over = True
                    print("Game Over!")
                else:
                    # Reset to safe position
                    ball_pos[:] = find_safe_start_tile()
                    ball_vel[:] = [0.0, 0.0, 0.0]
            break

    # Shield collectible collision
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
                print("Shield collected and activated!")

    # Tile timer mechanic
    i = int(math.floor((ball_pos[0] + half_size_x) / tile_size))
    j = int(math.floor((ball_pos[1] + half_size_y) / tile_size))
    current_tile = (i, j)

    if ball_pos[2] <= ball_radius + 1 and current_tile not in holes:
        if current_tile == last_tile:
            time_on_tile += dt
            show_timer = True
            if time_on_tile >= max_tile_time:
                lives -= 1
                print(f"Stayed too long on tile! Lives remaining: {lives}")
                time_on_tile = 0.0
                last_tile = None
                show_timer = False
                if lives <= 0:
                    game_over = True
                else:
                    # Reset to safe position
                    ball_pos[:] = find_safe_start_tile()
                    ball_vel[:] = [0.0, 0.0, 0.0]
        else:
            last_tile = current_tile
            time_on_tile = 0.0
            show_timer = True
    else:
        show_timer = False

    # Hole collision
    if current_tile in holes and ball_pos[2] <= ball_radius + 1:
        lives -= 1
        print(f"Fell into hole! Lives remaining: {lives}")
        if lives <= 0:
            game_over = True
        else:
            # Reset to safe position
            ball_pos[:] = find_safe_start_tile()
            ball_vel[:] = [0.0, 0.0, 0.0]

    # Update obstacles
    update_obstacles(dt)

    # Regular collectible collision
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
                print(f"Collectible gathered! Score: {score}")
                # Spawn new collectible
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

    # Special collectible collision
    for sc in special_collectibles:
        if not sc['collected']:
            dx = ball_pos[0] - sc['pos'][0]
            dy = ball_pos[1] - sc['pos'][1]
            dz = ball_pos[2] - sc['pos'][2]
            distance = math.sqrt(dx**2 + dy**2 + dz**2)

            if distance < ball_radius + 12:
                sc['collected'] = True
                score += 2
                apply_special_effect(sc['effect'])
                print(f"Special collectible! Score: {score}")

    # Update difficulty scaling
    update_difficulty()

def display():
    """Main display function"""
    setup_scene()
    draw_floor()
    draw_walls()
    draw_trees()
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
    """Idle function for continuous updates"""
    update()
    glutPostRedisplay()

def keyboard(k, x, y):
    """Handle keyboard input"""
    global space_pressed, theme, difficulty_timer, difficulty_mode, speed_multiplier, game_paused
    
    if k == b'\x1b':  # Escape key
        sys.exit()
        
    if k == b' ':  # Space for jumping
        space_pressed = True
        
    if k in [b'a', b'd', b'w', b's']:  # Movement keys
        move_keys[k.decode()] = True
        
    if k == b'r':  # Restart game
        if game_over or game_won or difficulty_mode:
            reset_game()
            
    if k == b't':  # Toggle theme
        theme = "dark" if theme == "default" else "default"
        print(f"Theme changed to: {theme}")
        
    if k == b'x':  # Activate difficulty mode
        if not difficulty_mode:
            difficulty_mode = True
            difficulty_timer = time.time()
            speed_multiplier *= 1.5
            print("Difficulty mode activated! You have 40 seconds to finish!")
            
    if k == b'p':  # Pause/unpause
        game_paused = not game_paused
        if game_paused:
            print("Game paused")
        else:
            print("Game resumed")
            time_last = time.time()  # Reset timer to avoid large dt

def keyboard_up(k, x, y):
    """Handle key release"""
    global space_pressed
    
    if k == b' ':
        space_pressed = False
        
    if k in [b'a', b'd', b'w', b's']:
        move_keys[k.decode()] = False

def special_keys(key, x, y):
    """Handle special keys (arrow keys) for camera control"""
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
    """Handle mouse input"""
    global camera_angle
    
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        # Quick camera snap
        camera_angle = 0
        
    elif button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        # Reset camera to default position
        global camera_height, camera_distance
        camera_height = 500.0
        camera_distance = 500.0
        camera_angle = 0

def main():
    """Initialize and run the game"""
    print("=== TILE TUMBLE ===")
    print("Controls:")
    print("  WASD - Move ball")
    print("  Space - Jump (hold for higher jump)")
    print("  Arrow Keys - Adjust camera")
    print("  T - Toggle theme")
    print("  X - Activate difficulty mode")
    print("  P - Pause/unpause")
    print("  R - Restart game")
    print("  ESC - Exit")
    print("\nObjective: Collect items, avoid obstacles, reach 15 points to win!")
    print("Watch out for holes and don't stay on tiles too long!")
    
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Tile Tumble - 3D Ball Game")
    
    # Enable depth testing and other OpenGL features
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    
    # Set up lighting
    light_pos = [0.0, 0.0, 1000.0, 1.0]
    glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
    glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
    
    # Register callback functions
    glutReshapeFunc(reshape)
    glutDisplayFunc(display)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboard)
    glutKeyboardUpFunc(keyboard_up)
    glutSpecialFunc(special_keys)
    glutMouseFunc(mouse)
    
    # Initialize game
    setup_projection()
    reset_game()
    
    print("\nGame initialized! Have fun!")
    glutMainLoop()

if __name__ == '__main__':
    main()
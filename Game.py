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
current_round = 1
max_rounds = 5
round_target_score = 4  # Score needed to advance to next round
game_over = False
game_won = False
game_paused = False
last_tile = None
time_on_tile = 0.0
max_tile_time = 3.0
show_timer = False
time_last = time.time()
game_start_time = time.time()


# NEW: Bounce Timer System
bounce_timer = 0.0  # Time since last bounce/jump
bounce_time_limit = 10.0  # Time limit for bouncing (starts at 10 seconds)
base_bounce_time = 10.0  # Base time for level 1
show_bounce_timer = True  # Always show bounce timer
last_bounce_time = time.time()  # Track when last bounce occurred


# Input handling
move_keys = {"a": False, "d": False, "w": False, "s": False}
space_pressed = False


# Difficulty and progression
difficulty_timer = None
difficulty_mode = False
speed_multiplier = 1.0
base_speed = 200.0
difficulty_level = 1
obstacle_speed_multiplier = 1.0


# Camera settings
camera_distance = 500.0
camera_angle = 0
camera_height = 500.0


# Grid and environment
wall_height = 80.0
grid_size_x = 20
grid_size_y = 15
tile_size = 80
half_size_x = grid_size_x * tile_size / 2
half_size_y = grid_size_y * tile_size / 2


# Game objects
obstacles = []
tree_obstacles = []
boundary_trees = []  # NEW: Boundary trees for round 5
projectiles = []
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


def update_bounce_timer():
    """Update bounce timer system"""
    global bounce_timer, bounce_time_limit, lives, game_over, ball_pos, ball_vel, shield_active, shield_duration, max_shield_duration
    
    # Calculate bounce time limit based on current round (10, 9, 8, 7, 6 seconds)
    bounce_time_limit = max(3.0, base_bounce_time - (current_round - 1))
    
    # Update bounce timer
    current_time = time.time()
    bounce_timer = current_time - last_bounce_time
    
    # Check if bounce time limit exceeded
    if bounce_timer >= bounce_time_limit:
        if shield_active:
            # Shield protects from bounce timeout
            shield_active = False
            shield_duration = 0.0
            print("Shield protected you from bounce timeout!")
            reset_bounce_timer()
        else:
            lives -= 1
            print(f"BOUNCE TIMEOUT! You must jump every {bounce_time_limit:.0f} seconds! Lives remaining: {lives}")
            if lives <= 0:
                game_over = True
                print("Game Over! You failed to bounce in time!")
                return
            else:
                # Reset to safe position with brief shield
                ball_pos[:] = find_safe_start_tile()
                ball_vel[:] = [0.0, 0.0, 0.0]
                shield_active = True
                shield_duration = 0.0
                max_shield_duration = 2.0
                print("Respawned with temporary shield!")
                reset_bounce_timer()


def reset_bounce_timer():
    """Reset the bounce timer"""
    global bounce_timer, last_bounce_time
    bounce_timer = 0.0
    last_bounce_time = time.time()
    print(f"Bounce timer reset! Must bounce within {bounce_time_limit:.0f} seconds")


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
    # Generate more holes with higher rounds
    hole_count = min(20 + current_round * 15, 80)
    
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
    """Generate dynamic obstacles with round-based difficulty scaling"""
    global obstacles
    obstacles = []
    # More obstacles with higher rounds
    obstacle_count = 3 + current_round * 3
    
    for _ in range(obstacle_count):
        x, y = find_safe_tile()
        obstacles.append({
            'pos': [x + random.uniform(-30, 30), y + random.uniform(-30, 30), 30],
            'base_size': random.uniform(6 + current_round * 2, 18 + current_round * 3),
            'current_size': 0,  # Will grow to base_size
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
    """Generate tree obstacles with round-based shooting patterns"""
    global tree_obstacles
    tree_obstacles = []
    
    # Number of trees increases with rounds
    tree_count = min(current_round * 2, 10)
    
    # Determine shooting pattern based on round
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
            'shoot_interval': max(3.5 - current_round * 0.4, 0.8),  # Faster shooting at higher rounds
            'projectile_speed': 80 + current_round * 30
        })


def generate_boundary_trees():
    """Generate boundary trees that activate in round 5"""
    global boundary_trees
    boundary_trees = []
    
    # Only activate boundary trees in round 5
    if current_round >= 5:
        spacing = tile_size * 2
        tree_positions = []
        
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
        
        # Convert boundary tree positions to active shooters
        for tx, ty, tz in tree_positions:
            boundary_trees.append({
                'pos': [tx, ty, tz],
                'shooting_pattern': 'all_sides',  # Boundary trees shoot in all directions
                'last_shot_time': 0.0,
                'shoot_interval': 2.0,  # Very frequent shooting
                'projectile_speed': 120
            })


def update_tree_obstacles(dt):
    """Update tree obstacles and handle projectile shooting"""
    global projectiles
    current_time = time.time()
    
    # Update regular tree obstacles
    for tree in tree_obstacles:
        if current_time - tree['last_shot_time'] >= tree['shoot_interval']:
            tree['last_shot_time'] = current_time
            shoot_projectiles_from_tree(tree)
    
    # Update boundary trees (only in round 5)
    if current_round >= 5:
        for tree in boundary_trees:
            if current_time - tree['last_shot_time'] >= tree['shoot_interval']:
                tree['last_shot_time'] = current_time
                shoot_projectiles_from_tree(tree)


def shoot_projectiles_from_tree(tree):
    """Helper function to shoot projectiles from any tree"""
    global projectiles
    
    # Calculate direction to player
    dx = ball_pos[0] - tree['pos'][0]
    dy = ball_pos[1] - tree['pos'][1]
    distance = math.sqrt(dx**2 + dy**2)
    
    if distance > 0 and distance < 600:  # Shooting range
        dx /= distance
        dy /= distance
        
        if tree['shooting_pattern'] == 'one_side':
            # Shoot one projectile toward player
            projectiles.append({
                'pos': [tree['pos'][0], tree['pos'][1], 25],
                'vel': [dx * tree['projectile_speed'], dy * tree['projectile_speed'], 0],
                'life_time': 0.0,
                'max_life': 5.0,
                'size': 4
            })
            
        elif tree['shooting_pattern'] == 'two_sides':
            # Shoot from two directions
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
            # Shoot in 8 directions (all sides)
            for i in range(8):
                angle = i * math.pi / 4  # 45-degree intervals
                proj_dx = math.cos(angle)
                proj_dy = math.sin(angle)
                projectiles.append({
                    'pos': [tree['pos'][0], tree['pos'][1], 25],
                    'vel': [proj_dx * tree['projectile_speed'], proj_dy * tree['projectile_speed'], 0],
                    'life_time': 0.0,
                    'max_life': 5.0,
                    'size': 5 if current_round >= 5 else 4  # Larger projectiles in round 5
                })


def update_projectiles(dt):
    """Update tree projectiles"""
    global projectiles
    remaining_projectiles = []
    
    for proj in projectiles:
        # Update position
        proj['pos'][0] += proj['vel'][0] * dt
        proj['pos'][1] += proj['vel'][1] * dt
        proj['life_time'] += dt
        
        # Check if projectile is still valid
        if (proj['life_time'] < proj['max_life'] and
            -half_size_x - 100 < proj['pos'][0] < half_size_x + 100 and
            -half_size_y - 100 < proj['pos'][1] < half_size_y + 100):
            remaining_projectiles.append(proj)
    
    projectiles[:] = remaining_projectiles


def draw_tree_obstacles():
    """Draw tree obstacles with visual indicators for danger level"""
    for tree in tree_obstacles:
        tx, ty = tree['pos'][:2]
        
        # Draw trunk with color based on shooting pattern
        if tree['shooting_pattern'] == 'one_side':
            glColor3f(0.4, 0.2, 0.1)  # Brown
        elif tree['shooting_pattern'] == 'two_sides':
            glColor3f(0.6, 0.3, 0.1)  # Orange-brown
        else:  # all_sides
            glColor3f(0.8, 0.2, 0.1)  # Red-brown (most dangerous)
            
        glPushMatrix()
        glTranslatef(tx, ty, 20)
        glScalef(8, 8, 40)
        glutSolidCube(1)
        glPopMatrix()

        # Draw foliage with danger indicators
        if tree['shooting_pattern'] == 'all_sides':
            # Pulsing red for most dangerous
            pulse = 0.5 + 0.5 * math.sin(time.time() * 3)
            glColor3f(pulse, 0.1, 0.1)
        elif tree['shooting_pattern'] == 'two_sides':
            glColor3f(0.6, 0.4, 0.1)  # Orange
        else:
            glColor3f(0.0, 0.5, 0.0)  # Green
            
        glPushMatrix()
        glTranslatef(tx, ty, 50)
        glutSolidCone(20, 50, 12, 12)
        glPopMatrix()


def draw_projectiles():
    """Draw tree projectiles"""
    for proj in projectiles:
        glPushMatrix()
        glTranslatef(proj['pos'][0], proj['pos'][1], proj['pos'][2])
        
        # Color changes based on age and round
        age_ratio = proj['life_time'] / proj['max_life']
        if current_round >= 5:
            # More dangerous looking projectiles in round 5
            glColor3f(1.0, 0.2 - age_ratio * 0.1, 0.1)
        else:
            glColor3f(0.8 + age_ratio * 0.2, 0.4 - age_ratio * 0.3, 0.1)
        
        glutSolidSphere(proj['size'], 8, 8)
        glPopMatrix()


def generate_collectibles():
    """Generate random collectibles and special collectibles"""
    global collectibles, special_collectibles
    collectibles = []
    special_collectibles = []
    
    # Regular collectibles - fewer at higher rounds to increase challenge
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
    
    # Special collectibles with effects
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
    """Generate shield collectibles"""
    global shields
    shields = []
    shield_count = max(1, 3 - current_round // 2)  # Fewer shields at higher rounds
    
    for _ in range(shield_count):
        x, y = find_safe_tile()
        shields.append({
            'pos': [x, y, 10],
            'collected': False,
            'rotation': 0.0
        })


def advance_round():
    """Advance to the next round"""
    global current_round, score, speed_multiplier, obstacle_speed_multiplier, max_tile_time, bounce_time_limit
    
    if current_round < max_rounds:
        current_round += 1
        print(f"\n🎯 === ROUND {current_round} BEGINS! ===")
        
        # Update bounce time limit for new round
        new_bounce_limit = max(3.0, base_bounce_time - (current_round - 1))
        print(f"⏰ NEW BOUNCE TIMER: Must jump every {new_bounce_limit:.0f} seconds!")
        
        if current_round == 2:
            print("⚠️ Round 2: Trees shoot from TWO directions!")
        elif current_round == 3:
            print("⚠️ Round 3: More obstacles and faster movement!")
        elif current_round == 4:
            print("⚠️ Round 4: Trees shoot from ALL SIDES!")
        elif current_round == 5:
            print("🔥 FINAL ROUND 5: BOUNDARY TREES ACTIVATE!")
            print("🔥 All wall trees now fire projectiles!")
            print(f"⏰ BOUNCE TIMER: Only {new_bounce_limit:.0f} seconds between jumps!")
        
        # Progressive difficulty increases
        speed_multiplier += 0.15
        obstacle_speed_multiplier += 0.25
        max_tile_time = max(0.8, max_tile_time * 0.85)
        
        # Regenerate world for new round
        generate_holes()
        initialize_zones()
        generate_obstacles()
        generate_tree_obstacles()
        generate_boundary_trees()
        generate_collectibles()
        generate_shields()
        
        # Reset score for new round and bounce timer
        score = 0
        reset_bounce_timer()
        
        print(f"Round {current_round} initialized!")
        print(f"Target score: {round_target_score} points to advance")
        if current_round == 5:
            print("Win condition: Survive and collect 4 points!")


def update_round_progression():
    """Check if player should advance to next round"""
    global score, current_round
    
    if score >= round_target_score and current_round < max_rounds:
        advance_round()


def reset_game(reset_score=True, reset_lives=True):
    """Reset game state with improved initialization"""
    global ball_pos, ball_vel, jumping, jump_start_time, score, lives, game_over, game_won
    global collectibles, special_collectibles, time_last, obstacles, last_tile, time_on_tile
    global show_timer, difficulty_timer, difficulty_mode, speed_multiplier, game_start_time
    global shield_active, shield_duration, difficulty_level, game_paused, tree_obstacles, projectiles
    global obstacle_speed_multiplier, max_shield_duration, current_round, boundary_trees
    global bounce_timer, bounce_time_limit, last_bounce_time

    # Reset ball
    ball_pos[:] = find_safe_start_tile()
    ball_vel[:] = [0.0, 0.0, 0.0]
    jumping = False
    jump_start_time = 0.0

    # Reset game state
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

    # Reset power-ups
    shield_active = False
    shield_duration = 0.0
    max_shield_duration = 10.0
    
    # Reset difficulty
    difficulty_timer = None
    difficulty_mode = False
    speed_multiplier = 1.0
    max_tile_time = 3.0

    # Reset bounce timer
    bounce_timer = 0.0
    bounce_time_limit = base_bounce_time
    last_bounce_time = time.time()

    # Clear all game objects
    obstacles.clear()
    tree_obstacles.clear()
    boundary_trees.clear()
    projectiles.clear()
    collectibles.clear()
    special_collectibles.clear()
    shields.clear()

    # Regenerate game world
    generate_holes()
    initialize_zones()
    generate_obstacles()
    generate_tree_obstacles()
    generate_boundary_trees()
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
    
    # Set background color based on theme and round
    if theme == "default":
        if current_round >= 5:
            glClearColor(0.7, 0.3, 0.3, 1.0)  # Reddish for final round
        else:
            glClearColor(0.5, 0.8, 1.0, 1.0)  # Sky blue
    elif theme == "dark":
        if current_round >= 5:
            glClearColor(0.2, 0.1, 0.1, 1.0)  # Dark red
        else:
            glClearColor(0.1, 0.1, 0.2, 1.0)  # Dark blue


def draw_floor():
    """Draw checkered tile floor with zones"""
    global theme
    
    # Define colors based on theme and round
    if theme == "default":
        if current_round >= 5:
            safe_color = (0.9, 0.9, 0.9)      # Light gray - safe zone
            normal_color = (0.4, 0.6, 0.4)    # Dark green - normal zone
            danger_color = (1.0, 0.3, 0.3)    # Bright red - danger zone
            hole_color = (0.1, 0.1, 0.1)      # Dark - holes
        else:
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
    """Draw boundary walls"""
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
    """Draw decorative trees around the boundaries - ACTIVE IN ROUND 5"""
    if theme == "default":
        if current_round >= 5:
            trunk_color = (0.6, 0.1, 0.1)  # Dark red trunk for active trees
            foliage_color = (0.8, 0.2, 0.2)  # Red foliage for danger
        else:
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

        # Draw foliage with pulsing effect in round 5
        if current_round >= 5:
            pulse = 0.5 + 0.5 * math.sin(time.time() * 4)
            glColor3f(pulse, 0.1, 0.1)  # Pulsing red
        else:
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
    """Draw dynamic obstacles with enhanced visuals"""
    current_time = time.time()
    
    for o in obstacles:
        glPushMatrix()
        x, y, z = o['pos']
        glTranslatef(x, y, z)

        # Enhanced pulsing effect based on aggressiveness
        o['pulse'] += 0.1 * o['aggressiveness']
        pulse_factor = 0.5 + 0.5 * math.sin(o['pulse'])

        # Color based on size and danger level
        if o['current_size'] <= 0:
            o['current_size'] = o['base_size']
            
        size_ratio = (o['current_size'] - o['min_size']) / max(1, (o['base_size'] - o['min_size']))
        red_intensity = 0.7 + (1.0 - size_ratio) * 0.3 + pulse_factor * 0.2
        green_blue = 0.05 + size_ratio * 0.15

        glColor3f(red_intensity, green_blue, green_blue)
        glutSolidSphere(o['current_size'], 16, 16)

        # Enhanced glow effect for dangerous obstacles
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
    """Draw the player ball with enhanced visuals"""
    glPushMatrix()
    glTranslatef(ball_pos[0], ball_pos[1], ball_pos[2])
    
    # Ball color changes based on state and round
    if shield_active:
        # Shield effect - glowing blue
        glow = 0.5 + 0.5 * math.sin(time.time() * 5)
        glColor3f(0.0, glow, 1.0)
    elif jumping:
        glColor3f(1.0, 1.0, 0.0)  # Yellow when jumping
    elif current_round >= 5:
        # Special color for final round
        pulse = 0.5 + 0.5 * math.sin(time.time() * 2)
        glColor3f(1.0, pulse * 0.5, pulse * 0.5)  # Pulsing red-pink
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
    """Draw comprehensive UI including score, lives, timer, ROUND, and BOUNCE TIMER"""
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glDisable(GL_DEPTH_TEST)

    # Score, Lives, and ROUND
    glColor3f(1, 1, 1)
    glRasterPos2f(10, WINDOW_HEIGHT - 25)
    if current_round >= 5:
        glColor3f(1, 0.3, 0.3)  # Red text for final round
    score_text = f"ROUND {current_round}/{max_rounds} | Score: {score}/{round_target_score} | Lives: {lives}"
    for ch in score_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    # NEW: BOUNCE TIMER - Most Important Display
    time_left = max(0, bounce_time_limit - bounce_timer)
    if time_left <= 3.0:
        # Critical - Red and pulsing
        pulse = 0.5 + 0.5 * math.sin(time.time() * 8)
        glColor3f(pulse, 0.2, 0.2)
    elif time_left <= 5.0:
        # Warning - Orange
        glColor3f(1.0, 0.6, 0.0)
    else:
        # Safe - Green
        glColor3f(0.0, 1.0, 0.0)
    
    glRasterPos2f(10, WINDOW_HEIGHT - 50)
    bounce_text = f"⚡ BOUNCE TIMER: {time_left:.1f}s / {bounce_time_limit:.0f}s ⚡"
    for ch in bounce_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    # Game timer
    elapsed_time = time.time() - game_start_time
    glColor3f(0.8, 0.8, 0.8)
    glRasterPos2f(10, WINDOW_HEIGHT - 75)
    timer_text = f"Time: {elapsed_time:.1f}s"
    for ch in timer_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(ch))

    # Round 5 warning
    if current_round >= 5:
        pulse = 0.5 + 0.5 * math.sin(time.time() * 6)
        glColor3f(pulse, 0.2, 0.2)
        glRasterPos2f(10, WINDOW_HEIGHT - 100)
        warning_text = "⚠️ FINAL ROUND! ALL BOUNDARY TREES ARE ACTIVE!"
        for ch in warning_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    # Tile timer warning
    if show_timer:
        time_left_tile = max(0, max_tile_time - time_on_tile)
        glColor3f(1, 0.5, 0) if time_left_tile > 1 else glColor3f(1, 0, 0)
        glRasterPos2f(10, WINDOW_HEIGHT - 125)
        timer_warning = f"Move in: {time_left_tile:.1f}s"
        for ch in timer_warning:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    # Shield status
    if shield_active:
        remaining_shield = max(0, max_shield_duration - shield_duration)
        glColor3f(0, 1, 1)
        glRasterPos2f(10, WINDOW_HEIGHT - 150)
        shield_text = f"Shield: {remaining_shield:.1f}s"
        for ch in shield_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    # Controls help
    glColor3f(0.8, 0.8, 0.8)
    glRasterPos2f(WINDOW_WIDTH - 350, 25)
    controls = "WASD: Move | Space: Jump (MUST BOUNCE!) | T: Theme | P: Pause | R: Restart"
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
    """Update dynamic obstacles with enhanced patterns and round-based difficulty scaling"""
    for o in obstacles:
        # Update pattern movement with aggressiveness factor
        o['pattern_time'] += dt * o['aggressiveness']
        
        if o['pattern'] == 'oscillate':
            # Enhanced oscillation with speed variations
            o['pos'][1] += o['vel'] * dt * obstacle_speed_multiplier
            if o['pos'][1] > half_size_y - o['current_size'] or o['pos'][1] < -half_size_y + o['current_size']:
                o['vel'] *= -1.1  # Slight speed increase on bounce
                
        elif o['pattern'] == 'circle':
            # Circular movement with varying radius
            radius = 40 + current_round * 10
            radius_variation = 15 * math.sin(o['pattern_time'] * 0.5)
            total_radius = radius + radius_variation
            o['pos'][0] = o['original_pos'][0] + total_radius * math.cos(o['pattern_time'])
            o['pos'][1] = o['original_pos'][1] + total_radius * math.sin(o['pattern_time'])
            
        elif o['pattern'] == 'figure8':
            # Enhanced figure-8 with round scaling
            scale = 50 + current_round * 10
            o['pos'][0] = o['original_pos'][0] + scale * math.cos(o['pattern_time'])
            o['pos'][1] = o['original_pos'][1] + scale * math.sin(2 * o['pattern_time']) / 2
            
        elif o['pattern'] == 'zigzag':
            # New zigzag pattern
            o['pos'][0] = o['original_pos'][0] + 50 * math.sin(o['pattern_time'] * 2)
            o['pos'][1] += o['vel'] * dt * obstacle_speed_multiplier
            if o['pos'][1] > half_size_y - o['current_size'] or o['pos'][1] < -half_size_y + o['current_size']:
                o['vel'] *= -1

        # Enhanced size pulsing
        shrink_rate = o['shrink_speed'] * dt
        if current_round >= 3:
            shrink_rate *= 0.7  # 30% slower shrinking = more dangerous
        
        o['current_size'] -= shrink_rate
        if o['current_size'] <= o['min_size']:
            o['current_size'] = o['base_size']

        # Enhanced floating movement
        float_intensity = 1.0 + current_round * 0.3
        o['pos'][2] = o['float_height'] + 15 * math.sin(time.time() * o['float_speed'] * float_intensity + o['float_offset'])


def apply_special_effect(effect):
    """Apply special collectible effects"""
    global speed_multiplier, lives, shield_active, shield_duration, max_tile_time, score
    
    if effect == 'speed_boost':
        speed_multiplier += 0.3
        print("Speed boost activated!")
        
    elif effect == 'slow_time':
        # Temporarily slow down obstacles
        for o in obstacles:
            o['vel'] *= 0.6
        print("Time slowed!")
        
    elif effect == 'extra_life':
        lives += 1
        print("Extra life gained!")
        
    elif effect == 'shield':
        shield_active = True
        shield_duration = 0.0
        print("Shield activated!")
        
    elif effect == 'score_multiplier':
        score += 2  # Bonus points
        print("Score multiplier! +2 bonus points!")


def check_tile_effects():
    """Check for special tile zone effects"""
    global max_tile_time, speed_multiplier
    
    # Get current tile
    i = int(math.floor((ball_pos[0] + half_size_x) / tile_size))
    j = int(math.floor((ball_pos[1] + half_size_y) / tile_size))
    current_tile = (i, j)
    
    # Apply zone effects with round scaling
    base_time = max_tile_time
    if current_tile in zones['danger']:
        # Danger zone - faster timer
        max_tile_time = max(0.4, base_time - current_round * 0.2)
    elif current_tile in zones['safe']:
        # Safe zone - slower timer  
        max_tile_time = base_time + 1.0
    else:
        # Normal zone
        max_tile_time = base_time


def update():
    """Main game update loop with enhanced collision detection, round progression, and BOUNCE TIMER"""
    # ALL global variables that are modified in this function
    global time_last, ball_pos, ball_vel, jumping, jump_start_time, score, lives
    global game_over, last_tile, time_on_tile, show_timer, game_won, speed_multiplier
    global shield_active, shield_duration, difficulty_timer, difficulty_mode, game_paused
    global max_shield_duration, obstacles, tree_obstacles, projectiles, collectibles
    global special_collectibles, shields, max_tile_time, current_round, boundary_trees
    global obstacle_speed_multiplier, bounce_timer, bounce_time_limit, last_bounce_time

    if game_paused:
        return

    now = time.time()
    dt = now - time_last
    time_last = now

    if game_over or game_won:
        return

    # NEW: Update Bounce Timer System - CRITICAL
    update_bounce_timer()
    if game_over:  # Check if bounce timer caused game over
        return

    # Check win condition (completing all 5 rounds)
    if current_round > max_rounds or (current_round == max_rounds and score >= round_target_score):
        game_won = True
        print("🎉 CONGRATULATIONS! You survived all 5 rounds!")
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

    # Jumping mechanics with BOUNCE TIMER RESET
    on_ground = ball_pos[2] <= ball_radius + 1  # Small tolerance for ground detection
    if space_pressed and on_ground and not jumping:
        jumping = True
        jump_start_time = now
        ball_vel[2] = jump_strength
        # RESET BOUNCE TIMER WHEN JUMPING
        reset_bounce_timer()

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

    # ENHANCED Obstacle collision detection - ONLY WHEN ON GROUND
    for o in obstacles:
        dx = ball_pos[0] - o['pos'][0]
        dy = ball_pos[1] - o['pos'][1]
        dz = ball_pos[2] - o['pos'][2]
        distance = math.sqrt(dx**2 + dy**2 + dz**2)

        # Only check obstacle collision when ball is on ground
        if distance < ball_radius + o['current_size'] and on_ground:
            if shield_active:
                shield_active = False
                shield_duration = 0.0
                print("Shield protected you from DEADLY obstacle!")
            else:
                # INSTANT LIFE LOSS - No mercy!
                lives -= 1
                print(f"OBSTACLE COLLISION! Lives remaining: {lives}")
                if lives <= 0:
                    game_over = True
                    print("Game Over! Destroyed by obstacle!")
                    return
                else:
                    # Reset to safe position with brief invincibility
                    ball_pos[:] = find_safe_start_tile()
                    ball_vel[:] = [0.0, 0.0, 0.0]
                    shield_active = True  # Brief protection after respawn
                    shield_duration = 0.0
                    max_shield_duration = 2.0  # Very short protection period in higher rounds
                    reset_bounce_timer()  # Reset bounce timer on respawn
                    print("Respawned with temporary shield!")
            break

    # Update tree obstacles and projectiles
    update_tree_obstacles(dt)
    update_projectiles(dt)

    # ENHANCED Projectile collision detection - ONLY WHEN IN AIR
    for proj in projectiles[:]:  # Use slice copy to avoid modification during iteration
        dx = ball_pos[0] - proj['pos'][0]
        dy = ball_pos[1] - proj['pos'][1]
        dz = ball_pos[2] - proj['pos'][2]
        distance = math.sqrt(dx**2 + dy**2 + dz**2)

        # Only check projectile collision when ball is in air (not on ground)
        if distance < ball_radius + proj['size'] and not on_ground:
            if shield_active:
                shield_active = False
                shield_duration = 0.0
                print("Shield blocked DEADLY projectile!")
                # Remove the projectile
                projectiles.remove(proj)
            else:
                lives -= 1
                print(f"PROJECTILE HIT! Lives remaining: {lives}")
                if lives <= 0:
                    game_over = True
                    print("Game Over! Shot down by projectile!")
                    return
                else:
                    ball_pos[:] = find_safe_start_tile()
                    ball_vel[:] = [0.0, 0.0, 0.0]
                    shield_active = True
                    shield_duration = 0.0
                    max_shield_duration = 2.0
                    reset_bounce_timer()  # Reset bounce timer on respawn
                    print("Respawned with temporary shield!")
                # Remove the projectile
                projectiles.remove(proj)
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
                max_shield_duration = 8.0  # Reduced shield time in later rounds
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
                    reset_bounce_timer()
        else:
            last_tile = current_tile
            time_on_tile = 0.0
            show_timer = True
    else:
        show_timer = False

    # Hole collision
    if current_tile in holes and ball_pos[2] <= ball_radius + 1:
        if shield_active:
            shield_active = False
            shield_duration = 0.0
            print("Shield saved you from the hole!")
        else:
            lives -= 1
            print(f"Fell into hole! Lives remaining: {lives}")
            if lives <= 0:
                game_over = True
            else:
                # Reset to safe position
                ball_pos[:] = find_safe_start_tile()
                ball_vel[:] = [0.0, 0.0, 0.0]
                reset_bounce_timer()

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
                print(f"Collectible gathered! Score: {score}/{round_target_score}")
                # Spawn new collectible in fewer quantities at higher rounds
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

    # Special collectible collision
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
                print(f"Special collectible! Score: {score}/{round_target_score}")

    # Update round progression
    update_round_progression()


def display():
    """Main display function"""
    setup_scene()
    draw_floor()
    draw_walls()
    draw_trees()
    draw_tree_obstacles()
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
        reset_game()
            
    if k == b't':  # Toggle theme
        theme = "dark" if theme == "default" else "default"
        print(f"Theme changed to: {theme}")
            
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
    print("🎮 === ENHANCED TILE TUMBLE - 5 ROUND CHALLENGE WITH BOUNCE TIMER ===")
    print("Controls:")
    print("  WASD - Move ball")
    print("  Space - Jump (hold for higher jump)")
    print("  Arrow Keys - Adjust camera")
    print("  T - Toggle theme")
    print("  P - Pause/unpause")
    print("  R - Restart game")
    print("  ESC - Exit")
    print("\n🎯 OBJECTIVE: Survive 5 increasingly difficult rounds!")
    print("📊 Each round: Collect 4 points to advance")
    print("⚡ BOUNCE TIMER: Must jump every few seconds or lose a life!")
    print("   - Round 1: 10 seconds")
    print("   - Round 2: 9 seconds")
    print("   - Round 3: 8 seconds")
    print("   - Round 4: 7 seconds")
    print("   - Round 5: 6 seconds")
    print("⚠️ ROUND 5 SPECIAL: All boundary trees become active shooters!")
    print("💡 STRATEGY: Obstacles hurt when ON GROUND, Projectiles hurt when IN AIR!")
    print("🏆 Win by completing all 5 rounds!\n")
    
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Enhanced Tile Tumble - 5 Round Challenge with Bounce Timer")
    
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
    
    print("🚀 Game initialized! Round 1 begins!")
    print("🎯 Collect 4 points to advance to Round 2!")
    print("⚡ REMEMBER: Must jump every 10 seconds!")
    glutMainLoop()


if __name__ == '__main__':
    main()
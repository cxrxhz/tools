import pygame
import math
import random

# ---------------------- 基本参数配置 ----------------------
# 屏幕尺寸
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# 视野设置：FOV（视野角度）及其相关参数
FOV = math.pi / 3  # 60度视野角
HALF_FOV = FOV / 2
NUM_RAYS = SCREEN_WIDTH  # 每个屏幕列投射一条射线
DELTA_ANGLE = FOV / NUM_RAYS  # 每条射线间的角度差
# 用于计算墙面高度的投影平面距离
DISTANCE_PROJ_PLANE = SCREEN_WIDTH / (2 * math.tan(HALF_FOV))

# 最大投射距离，防止无限延伸
MAX_DEPTH = 30

# ---------------------- 迷宫生成相关参数 ----------------------
# 生成迷宫时，网格尺寸建议使用奇数（这样每个迷宫墙间会有通路）
MAZE_WIDTH = 21  # 横向格数
MAZE_HEIGHT = 21  # 纵向格数


# 在迷宫的坐标体系中，每个格子的大小就认为是1

def generate_maze(w, h):
    """
    利用递归回溯算法生成一个随机迷宫。
    生成时先创建所有格子为墙（用1表示），再从 (1,1) 开始挖通路（用0表示）。
    挖通路时每次步长为2，同时删去两格之间的墙壁。
    """
    # 初始化全墙迷宫
    maze = [[1 for _ in range(w)] for _ in range(h)]

    def carve(x, y):
        maze[y][x] = 0  # 将当前位置打通
        # 四个随机顺序的方向，步长为2
        directions = [(2, 0), (-2, 0), (0, 2), (0, -2)]
        random.shuffle(directions)
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 < nx < w - 1 and 0 < ny < h - 1:
                if maze[ny][nx] == 1:
                    # 同时打通路径与中间墙
                    maze[y + dy // 2][x + dx // 2] = 0
                    carve(nx, ny)

    carve(1, 1)
    return maze


# 生成迷宫
maze = generate_maze(MAZE_WIDTH, MAZE_HEIGHT)

# ---------------------- 玩家相关初始数据 ----------------------
# 玩家在迷宫中的位置（浮点数，方便计算连续运动）
player_x = 1.5
player_y = 1.5
player_angle = 0  # 初始朝向（弧度制，0 表示向右）

# ---------------------- Pygame 初始化 ----------------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("3D 迷宫 - 第一人称射线投射演示")
clock = pygame.time.Clock()


# ---------------------- 射线投射函数 ----------------------
def cast_ray(px, py, ray_angle):
    """
    利用 DDA 算法，从玩家位置向给定角度投射一条射线，
    返回该射线与墙体的“垂直距离”（经过鱼眼校正前）以及命中的边类型（用于简单阴影效果）。
    """
    # 射线方向向量
    ray_dir_x = math.cos(ray_angle)
    ray_dir_y = math.sin(ray_angle)

    # 玩家当前所在格子
    map_x = int(px)
    map_y = int(py)

    # 计算每格在 x、y 方向上的投射“距离增量”
    delta_dist_x = abs(1 / ray_dir_x) if ray_dir_x != 0 else float('inf')
    delta_dist_y = abs(1 / ray_dir_y) if ray_dir_y != 0 else float('inf')

    # 根据射线方向确定步进方向和初始边界距离
    if ray_dir_x < 0:
        step_x = -1
        side_dist_x = (px - map_x) * delta_dist_x
    else:
        step_x = 1
        side_dist_x = (map_x + 1.0 - px) * delta_dist_x

    if ray_dir_y < 0:
        step_y = -1
        side_dist_y = (py - map_y) * delta_dist_y
    else:
        step_y = 1
        side_dist_y = (map_y + 1.0 - py) * delta_dist_y

    # DDA 循环：沿射线方向不断走格子，直到撞上墙
    hit = False
    side = None  # 0：撞击的是竖直方向的墙; 1：撞击的是水平方向的墙
    while not hit and 0 <= map_x < MAZE_WIDTH and 0 <= map_y < MAZE_HEIGHT:
        if side_dist_x < side_dist_y:
            side_dist_x += delta_dist_x
            map_x += step_x
            side = 0
        else:
            side_dist_y += delta_dist_y
            map_y += step_y
            side = 1
        # 若该格子的值为 1 则视为墙
        if maze[map_y][map_x] == 1:
            hit = True

    # 根据撞击边计算射线距离
    if side == 0:
        perp_dist = (map_x - px + (1 - step_x) / 2) / ray_dir_x
    else:
        perp_dist = (map_y - py + (1 - step_y) / 2) / ray_dir_y

    return perp_dist, side


# ---------------------- 主循环 ----------------------
running = True
while running:
    # 处理退出事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 处理键盘输入：前进、后退、旋转
    keys = pygame.key.get_pressed()
    move_speed = 0.05  # 移动步长
    rot_speed = 0.03  # 旋转步长（弧度）
    # 前进（向当前朝向移动）
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        new_x = player_x + math.cos(player_angle) * move_speed
        new_y = player_y + math.sin(player_angle) * move_speed
        # 如果新位置不撞墙则允许移动（记得索引顺序：[y][x]）
        if maze[int(new_y)][int(new_x)] == 0:
            player_x = new_x
            player_y = new_y
    # 后退
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        new_x = player_x - math.cos(player_angle) * move_speed
        new_y = player_y - math.sin(player_angle) * move_speed
        if maze[int(new_y)][int(new_x)] == 0:
            player_x = new_x
            player_y = new_y
    # 左转
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        player_angle -= rot_speed
    # 右转
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        player_angle += rot_speed

    # ---------------------- 渲染 3D 视图 ----------------------
    # 先用纯色填充整个屏幕
    screen.fill((0, 0, 0))
    # 绘制天花板（上半部分）与地板（下半部分）
    pygame.draw.rect(screen, (100, 100, 100), (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT // 2))
    pygame.draw.rect(screen, (50, 50, 50), (0, SCREEN_HEIGHT // 2, SCREEN_WIDTH, SCREEN_HEIGHT // 2))

    # 对屏幕每一列进行射线投射计算
    for col in range(SCREEN_WIDTH):
        # 当前射线角 = 玩家朝向 - FOV/2 + 每列对应的增量
        ray_angle = player_angle - HALF_FOV + (col / SCREEN_WIDTH) * FOV
        perp_dist, side = cast_ray(player_x, player_y, ray_angle)
        if perp_dist == 0:
            perp_dist = 0.0001  # 避免除零

        # 根据距离计算墙面高度（距离越近，墙面越高）
        wall_height = int(SCREEN_HEIGHT / perp_dist)
        # 计算在屏幕上的绘制起始 y 坐标（让墙面垂直居中）
        start_y = SCREEN_HEIGHT // 2 - wall_height // 2
        # 简单的色调处理：根据撞击的是水平墙还是竖直墙，颜色深浅不同，营造阴影效果
        shade = 255 if side == 1 else 200
        wall_color = (shade, shade, shade)
        # 绘制当前列的墙面（一条竖直线）
        pygame.draw.rect(screen, wall_color, (col, start_y, 1, wall_height))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()

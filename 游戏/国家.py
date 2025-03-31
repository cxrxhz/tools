# -*- coding: utf-8 -*-
"""
【配置参数说明】
config_dict 中定义了所有关键参数和系数：
    ECON_GROWTH_RATE: 每个控制格子每帧带来的经济增长倍率（乘以国家控制格数）
    MILITARY_RECOVERY_DIVISOR: 军力恢复 = (经济 × 激进系数) / 此值
    RECOVERY_ECON_COST_RATE: 补充军力所消耗经济的比例（按恢复量计算）
    MAINTENANCE_ECON_COST_RATE: 持续维护成本，每帧按军力值扣除经济（防止军力过高）
    BATTLE_LOSS_ATTACKER / BATTLE_LOSS_DEFENDER: 跨国战斗中输方军力损耗系数
    CAPITAL_OCCUPATION_ECON_LOSS: 首都被占领时，对经济的损失比例（例如0.10表示损失10%）
    CAPITAL_OCCUPATION_CD: 首都被占领经济损失的冷却步数
    STATUS_UPDATE_INTERVAL: 每多少步更新一次状态栏快照
    CAPITAL_RECALC_INTERVAL: 固定间隔步数（不包括首都被占领）重新计算首都
    INSTANT_CAPITAL_RECALC: 当首都被占领时是否立即重新计算首都（True为是）
"""
config_dict = {
    "ECON_GROWTH_RATE": 0.005,  # 每个控制单元带来的经济增长
    "MILITARY_RECOVERY_DIVISOR": 500.0,  # 军力恢复除数（恢复 = (经济×激进)/该值）
    "RECOVERY_ECON_COST_RATE": 0.002,  # 补充军力的同时，每帧消耗经济 = 恢复量×该值
    "MAINTENANCE_ECON_COST_RATE": 0.0002,  # 持续维护成本：每帧按军力值扣除经济 = 军力×该值
    "BATTLE_LOSS_ATTACKER": 0.03,  # 跨国战斗失败时攻击方军力损耗率
    "BATTLE_LOSS_DEFENDER": 0.07,  # 跨国战斗失败时防守方军力损耗率
    "CAPITAL_OCCUPATION_ECON_LOSS": 0.10,  # 首都被占领时经济损失比例
    "CAPITAL_OCCUPATION_CD": 1000,  # 首都被占领经济损失冷却步数
    "STATUS_UPDATE_INTERVAL": 100,  # 状态栏快照更新间隔步数
    "CAPITAL_RECALC_INTERVAL": 3000,  # 固定间隔步数重新计算首都
    "INSTANT_CAPITAL_RECALC": True  # 首都被占领后立即重新计算首都
}

import random
import pygame
import sys
import math

# =================================
# 1. 全局参数设定（使用配置参数）
# =================================
ROWS = 30  # 网格行数
COLS = 30  # 网格列数
CELL_SIZE = 20  # 每个小单元的像素大小
GRID_WIDTH = COLS * CELL_SIZE
GRID_HEIGHT = ROWS * CELL_SIZE

LOG_PANEL_WIDTH = 400  # 侧边日志栏宽度
WINDOW_WIDTH = GRID_WIDTH + LOG_PANEL_WIDTH
WINDOW_HEIGHT = GRID_HEIGHT

BLOCK_SIZE = 2  # 每 BLOCK_SIZE×BLOCK_SIZE 个小单元构成一个大格子（用于地形）
TERRAIN_ROWS = ROWS // BLOCK_SIZE
TERRAIN_COLS = COLS // BLOCK_SIZE

NUM_COUNTRIES = 8
country_ids = [chr(65 + i) for i in range(NUM_COUNTRIES)]  # "A"~"H"
country_colors = {
    "A": (255, 0, 0),  # 红
    "B": (0, 0, 255),  # 蓝
    "C": (0, 255, 0),  # 绿
    "D": (255, 165, 0),  # 橙
    "E": (128, 0, 128),  # 紫
    "F": (255, 255, 0),  # 黄
    "G": (0, 255, 255),  # 青
    "H": (255, 0, 255)  # 品红
}

terrain_emojis = ["⛰️", "🌳", "🌾", "🏜️"]
terrain_bonus = {"⛰️": 1.2, "🌳": 1.1, "🌾": 1.0, "🏜️": 0.9}

logs = []  # 记录重大事件日志
step_counter = 0  # 模拟步计数器

LOG_BG_COLOR = (240, 240, 240)
TEXT_COLOR = (0, 0, 0)

# 用于首都被占领经济损失的冷却（1000步内不重复触发）
capital_cooldown = {cid: -config_dict["CAPITAL_OCCUPATION_CD"] for cid in country_ids}
# 基准版图面积（理想情况下每国控制格数）
baseline_territory = (ROWS * COLS) / NUM_COUNTRIES  # 约112.5

# 状态栏快照更新控制
last_status_update = 0
status_snapshot = {}
log_snapshot = {}


# =================================
# 2. 新增函数：get_neighbors 和 are_connected
# =================================
def get_neighbors(i, j, rows, cols):
    """返回(i,j)位置的上下左右邻居（符合边界条件）"""
    neighbors = []
    if i > 0:
        neighbors.append((i - 1, j))
    if i < rows - 1:
        neighbors.append((i + 1, j))
    if j > 0:
        neighbors.append((i, j - 1))
    if j < cols - 1:
        neighbors.append((i, j + 1))
    return neighbors


def are_connected(i, j, ni, nj):
    """
    使用深度优先搜索(DFS)判断(i,j)与(ni,nj)是否连通，
    条件是两者属于同一国家（相同国家ID）。
    """
    visited = set()
    stack = [(i, j)]
    while stack:
        x, y = stack.pop()
        if (x, y) == (ni, nj):
            return True
        if (x, y) in visited:
            continue
        visited.add((x, y))
        for nx, ny in get_neighbors(x, y, ROWS, COLS):
            if grid[nx][ny] == grid[i][j] and (nx, ny) not in visited:
                stack.append((nx, ny))
    return False


# =================================
# 3. PyGame 初始化与字体设置
# =================================
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("国家战争模拟 - 随机地图 + 颜色版")
clock = pygame.time.Clock()

try:
    main_font = pygame.font.SysFont("Microsoft YaHei", 18)
except Exception:
    main_font = pygame.font.SysFont("SimHei", 18)
button_font = pygame.font.SysFont("Microsoft YaHei", 24)
try:
    emoji_font = pygame.font.SysFont("Segoe UI Emoji", 18)
except Exception:
    emoji_font = main_font

button_width = 100
button_height = 40
pause_button_rect = pygame.Rect(GRID_WIDTH + 20, WINDOW_HEIGHT - 100, button_width, button_height)
quit_button_rect = pygame.Rect(GRID_WIDTH + 20, WINDOW_HEIGHT - 50, button_width, button_height)
paused = False


# =================================
# 4. 定义国家类与初始属性设置
# =================================
class Country:
    def __init__(self, name, military, economy, aggressiveness):
        self.name = name  # 国家标识，如 "A", "B", ...
        self.military = military  # 初始军力
        self.economy = economy  # 初始经济实力
        self.aggressiveness = aggressiveness  # 激进系数，影响作战能力

    def __str__(self):
        return f"国家 {self.name}: 军力 {self.military:.1f}, 经 {self.economy:.1f}, 激 {self.aggressiveness:.2f}"


Countries = {}
for cid in country_ids:
    military = random.randint(100, 200)
    economy = random.randint(80, 150)
    aggressiveness = round(random.uniform(0.5, 0.9), 2)
    Countries[cid] = Country(cid, military, economy, aggressiveness)

# =================================
# 5. 随机生成初始地图（以Voronoi分区确保同国区域连通）
# =================================
seed_positions = {}
for cid in country_ids:
    seed_positions[cid] = (random.randint(0, ROWS - 1), random.randint(0, COLS - 1))

grid = []
for i in range(ROWS):
    row = []
    for j in range(COLS):
        best = None
        best_dist = float('inf')
        for cid, pos in seed_positions.items():
            di = i - pos[0]
            dj = j - pos[1]
            d = di * di + dj * dj
            if d < best_dist:
                best_dist = d
                best = cid
        row.append(best)
    grid.append(row)


# =================================
# 6. 随机生成地形网格（每个大格子BLOCK_SIZE×BLOCK_SIZE），并平滑处理
# =================================
def generate_terrain_grid():
    terrain_grid = [[random.choice(terrain_emojis) for j in range(TERRAIN_COLS)] for i in range(TERRAIN_ROWS)]
    for _ in range(3):
        new_grid = [row[:] for row in terrain_grid]
        for i in range(TERRAIN_ROWS):
            for j in range(TERRAIN_COLS):
                neighbor_counts = {}
                for ni, nj in get_neighbors(i, j, TERRAIN_ROWS, TERRAIN_COLS):
                    t = terrain_grid[ni][nj]
                    neighbor_counts[t] = neighbor_counts.get(t, 0) + 1
                neighbor_counts[terrain_grid[i][j]] = neighbor_counts.get(terrain_grid[i][j], 0) + 1
                new_grid[i][j] = max(neighbor_counts, key=neighbor_counts.get)
        terrain_grid = new_grid
    return terrain_grid


terrain_grid = generate_terrain_grid()


def get_terrain_bonus(i, j):
    block_i = i // BLOCK_SIZE
    block_j = j // BLOCK_SIZE
    terrain = terrain_grid[block_i][block_j]
    return terrain_bonus.get(terrain, 1.0)


# =================================
# 7. 计算区域大小（判断孤立区域）
# =================================
def get_region_size(i, j):
    target = grid[i][j]
    visited = set()
    stack = [(i, j)]
    size = 0
    while stack:
        x, y = stack.pop()
        if (x, y) in visited:
            continue
        visited.add((x, y))
        size += 1
        for nx, ny in get_neighbors(x, y, ROWS, COLS):
            if grid[nx][ny] == target and (nx, ny) not in visited:
                stack.append((nx, ny))
    return size


# =================================
# 8. 计算各国首都位置（不包括灭亡国家）
# =================================
def recalc_capitals():
    # 对于每个国家，找出所有连通区域，若该国控制格数为0则忽略，
    # 否则选择最大区域的平均坐标作为首都
    capitals = {}
    visited = [[False] * COLS for _ in range(ROWS)]
    regions_by_country = {cid: [] for cid in country_ids}

    def dfs(i, j, cid):
        stack = [(i, j)]
        region = []
        while stack:
            x, y = stack.pop()
            if visited[x][y]:
                continue
            visited[x][y] = True
            if grid[x][y] != cid:
                continue
            region.append((x, y))
            for nx, ny in get_neighbors(x, y, ROWS, COLS):
                if not visited[nx][ny]:
                    stack.append((nx, ny))
        return region

    for i in range(ROWS):
        for j in range(COLS):
            if not visited[i][j]:
                cid = grid[i][j]
                region = dfs(i, j, cid)
                if region:
                    regions_by_country[cid].append(region)
    for cid, regions in regions_by_country.items():
        # 如果一个国家灭亡，则不计算首都
        total = sum(len(r) for r in regions)
        if total == 0:
            continue
        largest = max(regions, key=lambda r: len(r))
        avg_i = sum(x for x, y in largest) / len(largest)
        avg_j = sum(y for x, y in largest) / len(largest)
        capitals[cid] = (int(round(avg_i)), int(round(avg_j)))
    return capitals


capitals = recalc_capitals()
next_capital_update = config_dict["CAPITAL_RECALC_INTERVAL"]


# =================================
# 9. 辅助函数：计算距离因素
# =================================
def get_distance_factor(i, j, capital_coord):
    if not capital_coord:
        return 1.0
    d = abs(i - capital_coord[0]) + abs(j - capital_coord[1])
    return max(0.8, 1 - 0.005 * d)


# =================================
# 10. 修改战斗模拟函数
# =================================
def simulate_battle():
    global step_counter
    i = random.randint(0, ROWS - 1)
    j = random.randint(0, COLS - 1)
    nbs = get_neighbors(i, j, ROWS, COLS)
    if not nbs:
        return
    ni, nj = random.choice(nbs)
    # 如果同国，则检查是否连通
    if grid[i][j] == grid[ni][nj]:
        if are_connected(i, j, ni, nj):
            return  # 连通则不发生战斗
        else:
            # 同国但不连通，进行整合战斗，获得20%加成
            region_size_a = get_region_size(i, j)
            region_size_b = get_region_size(ni, nj)
            p = (region_size_a * 1.2) / (region_size_a * 1.2 + region_size_b) if (
                                                                                             region_size_a + region_size_b) > 0 else 0.5
            if random.random() < p:
                grid[ni][nj] = grid[i][j]
                logs.append(f"国家 {grid[i][j]} 孤立整合成功 ({region_size_a} vs {region_size_b})")
            else:
                grid[i][j] = grid[ni][nj]
                logs.append(f"国家 {grid[ni][nj]} 孤立整合成功 ({region_size_b} vs {region_size_a})")
            return

    # 跨国战斗：随机决定进攻方
    if random.random() < 0.5:
        attacker_cell = (i, j)
        defender_cell = (ni, nj)
    else:
        attacker_cell = (ni, nj)
        defender_cell = (i, j)
    ai, aj = attacker_cell
    di, dj = defender_cell
    attacker_id = grid[ai][aj]
    defender_id = grid[di][dj]
    attacker = Countries[attacker_id]
    defender = Countries[defender_id]

    attacker_effective = attacker.military * (1 + 0.1 * attacker.aggressiveness) * random.uniform(0.9, 1.1)
    defender_effective = defender.military * random.uniform(0.9, 1.1) * get_terrain_bonus(di, dj)

    factor_att = get_distance_factor(ai, aj, capitals.get(attacker_id))
    factor_def = get_distance_factor(di, dj, capitals.get(defender_id))
    attacker_effective *= factor_att
    defender_effective *= factor_def

    region_size = get_region_size(di, dj)
    if region_size <= 1:
        defender_effective *= 0.4
    elif region_size < 9:
        factor = 0.4 + (region_size - 1) * ((1.0 - 0.4) / 8)
        defender_effective *= factor

    win_prob = attacker_effective / (attacker_effective + defender_effective)
    if random.random() < win_prob:
        grid[di][dj] = attacker_id
        attacker_loss = config_dict["BATTLE_LOSS_ATTACKER"] * attacker.military
        defender_loss = config_dict["BATTLE_LOSS_DEFENDER"] * defender.military
        attacker.military = max(attacker.military - attacker_loss, 1)
        defender.military = max(defender.military - defender_loss, 1)
    else:
        grid[ai][aj] = defender_id
        attacker_loss = config_dict["BATTLE_LOSS_DEFENDER"] * attacker.military
        defender_loss = config_dict["BATTLE_LOSS_ATTACKER"] * defender.military
        attacker.military = max(attacker.military - attacker_loss, 1)
        defender.military = max(defender.military - defender_loss, 1)
    step_counter += 1


# =================================
# 11. 更新恢复函数：更新军力恢复、经济增长与 aggressiveness 调整
# 同时补充军力会消耗经济，且根据军力的大小持续减少经济
# =================================
def update_recovery_and_aggressiveness():
    territory_count = {cid: 0 for cid in country_ids}
    for i in range(ROWS):
        for j in range(COLS):
            territory_count[grid[i][j]] += 1
    for cid in country_ids:
        # 如果国家灭亡则跳过
        if territory_count[cid] == 0:
            continue
        # 经济增长：每帧增长 = 每格增长 * 控制单元数
        growth = config_dict["ECON_GROWTH_RATE"] * territory_count[cid]
        Countries[cid].economy += growth
        # 军力恢复：恢复 = (经济×激进) / 指定除数
        recovery = (Countries[cid].economy * Countries[cid].aggressiveness) / config_dict["MILITARY_RECOVERY_DIVISOR"]
        Countries[cid].military += recovery
        # 补充军力会消耗经济：按恢复量乘以补充成本率
        econ_cost = recovery * config_dict["RECOVERY_ECON_COST_RATE"]
        Countries[cid].economy = max(Countries[cid].economy - econ_cost, 0)
        # 持续根据军力规模消耗经济（维护成本）
        maintenance_cost = Countries[cid].military * config_dict["MAINTENANCE_ECON_COST_RATE"]
        Countries[cid].economy = max(Countries[cid].economy - maintenance_cost, 0)
        # 调整 aggressiveness：若控制面积大于基准，则激进降低；反之则提高
        current = territory_count[cid]
        if current > baseline_territory:
            Countries[cid].aggressiveness = max(0.5, Countries[cid].aggressiveness - 0.0005 * (
                        (current - baseline_territory) / baseline_territory))
        elif current < baseline_territory:
            Countries[cid].aggressiveness = min(1.2, Countries[cid].aggressiveness + 0.0005 * (
                        (baseline_territory - current) / baseline_territory))


# =================================
# 12. 绘制函数：绘制国家区域、地形及首都标记
# 灭亡的国家（控制单元为0）不在状态栏显示，且其首都标记也不绘制
# =================================
def draw_grid():
    for i in range(ROWS):
        for j in range(COLS):
            cid = grid[i][j]
            rect = pygame.Rect(j * CELL_SIZE, i * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, country_colors[cid], rect)


def draw_terrain():
    for bi in range(TERRAIN_ROWS):
        for bj in range(TERRAIN_COLS):
            terrain = terrain_grid[bi][bj]
            text = emoji_font.render(terrain, True, (100, 100, 100))
            block_x = bj * BLOCK_SIZE * CELL_SIZE
            block_y = bi * BLOCK_SIZE * CELL_SIZE
            block_width = BLOCK_SIZE * CELL_SIZE
            block_height = BLOCK_SIZE * CELL_SIZE
            text_rect = text.get_rect(center=(block_x + block_width / 2, block_y + block_height / 2))
            screen.blit(text, text_rect)


def draw_capitals():
    for cid, pos in capitals.items():
        # 如果该国灭亡，则跳过首都标记
        territory = sum(row.count(cid) for row in grid)
        if territory == 0:
            continue
        x, y = pos
        center_x = int((y + 0.5) * CELL_SIZE)
        center_y = int((x + 0.5) * CELL_SIZE)
        r = CELL_SIZE // 2 - 2
        points = []
        for i in range(5):
            angle = math.radians(72 * i - 90)
            x_point = center_x + r * math.cos(angle)
            y_point = center_y + r * math.sin(angle)
            points.append((x_point, y_point))
        pygame.draw.polygon(screen, (0, 0, 0), points)
        inner_points = []
        inner_r = r * 0.6
        for i in range(5):
            angle = math.radians(72 * i - 90 + 36)
            x_point = center_x + inner_r * math.cos(angle)
            y_point = center_y + inner_r * math.sin(angle)
            inner_points.append((x_point, y_point))
        pygame.draw.polygon(screen, country_colors[cid], inner_points)


def draw_log_panel():
    # 绘制状态栏：显示每个国家的状态（仅显示仍在存续的国家）以及最新的日志快照
    log_panel_rect = pygame.Rect(GRID_WIDTH, 0, LOG_PANEL_WIDTH, WINDOW_HEIGHT)
    pygame.draw.rect(screen, LOG_BG_COLOR, log_panel_rect)
    y = 10
    territory_count = {cid: 0 for cid in country_ids}
    for i in range(ROWS):
        for j in range(COLS):
            territory_count[grid[i][j]] += 1
    for cid in country_ids:
        if territory_count[cid] == 0:
            continue  # 灭亡的国家不显示
        text = status_snapshot.get(cid,
                                   f"国 {cid}: 军 {Countries[cid].military:.1f}, 经 {Countries[cid].economy:.1f}, 激 {Countries[cid].aggressiveness:.2f}, 控 {territory_count[cid]}")
        color_rect = pygame.Rect(GRID_WIDTH + 10, y, 20, 20)
        pygame.draw.rect(screen, country_colors[cid], color_rect)
        text_render = main_font.render(text, True, TEXT_COLOR)
        screen.blit(text_render, (GRID_WIDTH + 40, y))
        y += 25
    y_offset = y + 10
    if log_snapshot:
        for line in log_snapshot:
            log_text = main_font.render(line, True, TEXT_COLOR)
            screen.blit(log_text, (GRID_WIDTH + 10, y_offset))
            y_offset += 20
    else:
        displayed_logs = logs[-10:]
        for line in displayed_logs:
            log_text = main_font.render(line, True, TEXT_COLOR)
            screen.blit(log_text, (GRID_WIDTH + 10, y_offset))
            y_offset += 20
    pygame.draw.rect(screen, (180, 180, 180), pause_button_rect)
    pygame.draw.rect(screen, (180, 180, 180), quit_button_rect)
    pause_text = button_font.render("暂停" if not paused else "继续", True, (0, 0, 0))
    quit_text = button_font.render("结束", True, (0, 0, 0))
    pause_rect = pause_text.get_rect(center=pause_button_rect.center)
    quit_rect = quit_text.get_rect(center=quit_button_rect.center)
    screen.blit(pause_text, pause_rect)
    screen.blit(quit_text, quit_rect)


# =================================
# 13. 主循环：更新、暂停及状态栏快照更新
# =================================
extinct_flags = {cid: False for cid in country_ids}
last_status_update = 0
status_snapshot = {}
log_snapshot = {}

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            if pause_button_rect.collidepoint(pos):
                paused = not paused
            if quit_button_rect.collidepoint(pos):
                running = False

    if not paused:
        for _ in range(10):
            simulate_battle()
        update_recovery_and_aggressiveness()

        territory_count = {cid: 0 for cid in country_ids}
        for i in range(ROWS):
            for j in range(COLS):
                territory_count[grid[i][j]] += 1  # 统计每个国家的控制单元数

        # 每100步更新状态栏与日志快照
        if step_counter - last_status_update >= config_dict["STATUS_UPDATE_INTERVAL"]:
            last_status_update = step_counter
            territory_count = {cid: 0 for cid in country_ids}
            for i in range(ROWS):
                for j in range(COLS):
                    territory_count[grid[i][j]] += 1
            status_snapshot = {}
            for cid in country_ids:
                if territory_count[cid] == 0:
                    continue
                status_snapshot[
                    cid] = f"国 {cid}: 军 {Countries[cid].military:.1f}, 经 {Countries[cid].economy:.1f}, 激 {Countries[cid].aggressiveness:.2f}, 控 {territory_count[cid]}"
            log_snapshot = logs[-10:]

        # 检查各国首都是否被占领（即首都所在单元不属于该国），若是且冷却期已过，则经济损失10%，更新冷却，并立即重新计算首都
    if not paused:
        current_step = step_counter
        capitals_changed = False
        for cid in country_ids:
            if cid not in territory_count or territory_count[cid] == 0:
                continue
            if cid in capitals:
                ci, cj = capitals[cid]
                if grid[ci][cj] != cid and current_step - capital_cooldown[cid] >= config_dict["CAPITAL_OCCUPATION_CD"]:
                    Countries[cid].economy *= (1 - config_dict["CAPITAL_OCCUPATION_ECON_LOSS"])
                    logs.append(f"国家 {cid} 首都被占, 经受损")
                    capital_cooldown[cid] = current_step
                    capitals_changed = True
        if capitals_changed:
            capitals = recalc_capitals()  # 立即重新计算首都
            # 同时更新定时更新的计时器，避免和后面的定时更新冲突
            next_capital_update = step_counter + config_dict["CAPITAL_RECALC_INTERVAL"]

    # 每3000步重新计算首都位置（非暂停状态下）
    if step_counter >= next_capital_update and not paused:
        capitals = recalc_capitals()
        next_capital_update += config_dict["CAPITAL_RECALC_INTERVAL"]



    screen.fill((255, 255, 255), rect=pygame.Rect(0, 0, GRID_WIDTH, GRID_HEIGHT))
    draw_grid()
    draw_terrain()
    # 绘制首都标记，只对未灭亡国家显示
    draw_capitals()
    draw_log_panel()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()

territory_count = {cid: 0 for cid in country_ids}
for i in range(ROWS):
    for j in range(COLS):
        territory_count[grid[i][j]] += 1

print("=== 最终各国状态 ===")
for cid in country_ids:
    if territory_count[cid] == 0:
        continue
    print(Countries[cid])
    print(f"控制单元数: {territory_count[cid]}")

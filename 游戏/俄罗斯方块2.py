import pygame
import random

# 初始化Pygame
pygame.init()

# 定义屏幕大小和方块大小
SCREEN_WIDTH = 600  # 增加宽度以容纳下一个方块预览
SCREEN_HEIGHT = 800
BLOCK_SIZE = 40
COLUMN = 10
ROW = 20

# 定义颜色
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
COLORS = [
    (0, 255, 0),     # S形状，绿色
    (255, 0, 0),     # Z形状，红色
    (0, 255, 255),   # I形状，青色
    (255, 255, 0),   # O形状，黄色
    (0, 0, 255),     # J形状，蓝色
    (255, 165, 0),   # L形状，橙色
    (128, 0, 128)    # T形状，紫色
]

# 定义七种俄罗斯方块形状及其旋转状态
S_SHAPE = [
    [[0, 1, 1],
     [1, 1, 0]],
    [[1, 0],
     [1, 1],
     [0, 1]]
]

Z_SHAPE = [
    [[1, 1, 0],
     [0, 1, 1]],
    [[0, 1],
     [1, 1],
     [1, 0]]
]

I_SHAPE = [
    [[1, 1, 1, 1]],
    [[1],
     [1],
     [1],
     [1]]
]

O_SHAPE = [
    [[1, 1],
     [1, 1]]
]

J_SHAPE = [
    [[1, 0, 0],
     [1, 1, 1]],
    [[1, 1],
     [1, 0],
     [1, 0]],
    [[1, 1, 1],
     [0, 0, 1]],
    [[0, 1],
     [0, 1],
     [1, 1]]
]

L_SHAPE = [
    [[0, 0, 1],
     [1, 1, 1]],
    [[1, 0],
     [1, 0],
     [1, 1]],
    [[1, 1, 1],
     [1, 0, 0]],
    [[1, 1],
     [0, 1],
     [0, 1]]
]

T_SHAPE = [
    [[0, 1, 0],
     [1, 1, 1]],
    [[1, 0],
     [1, 1],
     [1, 0]],
    [[1, 1, 1],
     [0, 1, 0]],
    [[0, 1],
     [1, 1],
     [0, 1]]
]

SHAPES = [S_SHAPE, Z_SHAPE, I_SHAPE, O_SHAPE, J_SHAPE, L_SHAPE, T_SHAPE]

# 定义方块类
class Block:
    def __init__(self, x, y, shape):
        self.x = x  # 方块的列位置
        self.y = y  # 方块的行位置
        self.shape = shape  # 旋转状态列表
        self.color = COLORS[SHAPES.index(shape)]
        self.rotation = 0  # 初始旋转状态

    def image(self):
        return self.shape[self.rotation % len(self.shape)]

    def rotate(self):
        self.rotation = (self.rotation + 1) % len(self.shape)

# 创建网格
def create_grid(locked_positions={}):
    grid = [[BLACK for _ in range(COLUMN)] for _ in range(ROW)]
    for i in range(ROW):
        for j in range(COLUMN):
            if (j, i) in locked_positions:
                grid[i][j] = locked_positions[(j, i)]
    return grid

# 检测是否有效位置
def valid_space(shape, grid):
    accepted_positions = [[(j, i) for j in range(COLUMN) if grid[i][j] == BLACK] for i in range(ROW)]
    accepted_positions = [j for sub in accepted_positions for j in sub]
    formatted = convert_shape_format(shape)
    for pos in formatted:
        if pos not in accepted_positions:
            if pos[1] > -1:
                return False
    return True

# 检测是否失败
def check_lost(positions):
    for pos in positions:
        x, y = pos
        if y < 1:
            return True
    return False

# 生成新方块
def get_shape():
    return Block(COLUMN // 2 - 2, 0, random.choice(SHAPES))

# 将形状格式化为坐标
def convert_shape_format(shape):
    positions = []
    format = shape.image()
    for i, line in enumerate(format):
        for j, column in enumerate(line):
            if column != 0:
                positions.append((shape.x + j, shape.y + i))
    return positions

# 消除满行
def clear_rows(grid, locked):
    increment = 0
    for i in range(ROW - 1, -1, -1):
        row = grid[i]
        if BLACK not in row:
            increment += 1
            index = i
            for j in range(COLUMN):
                try:
                    del locked[(j, i)]
                except:
                    continue
    if increment > 0:
        for key in sorted(list(locked), key=lambda x: x[1])[::-1]:
            x, y = key
            if y < index:
                new_key = (x, y + increment)
                locked[new_key] = locked.pop(key)
        # 根据消除的行数增加得分
        scores = {1: 100, 2: 300, 3: 600, 4: 1000}
        return scores.get(increment, 0)
    return 0

# 绘制文本
def draw_text_middle(surface, text, size, color):
    font = pygame.font.SysFont('SimHei', size, bold=True)
    lines = text.split('\n')
    total_height = len(lines) * (font.get_height() + 5)
    for i, line in enumerate(lines):
        label = font.render(line, True, color)
        surface.blit(label, (SCREEN_WIDTH / 2 - label.get_width() / 2,
                             SCREEN_HEIGHT / 2 - total_height / 2 + i * (font.get_height() + 5)))

# 绘制网格线
def draw_grid(surface):
    for i in range(ROW):
        pygame.draw.line(surface, GRAY, (0, i * BLOCK_SIZE), (COLUMN * BLOCK_SIZE, i * BLOCK_SIZE))
    for j in range(COLUMN):
        pygame.draw.line(surface, GRAY, (j * BLOCK_SIZE, 0), (j * BLOCK_SIZE, ROW * BLOCK_SIZE))

# 绘制窗口和分数
def draw_window(surface, grid, score=0, next_piece=None):
    surface.fill(BLACK)
    # 绘制网格方块
    for i in range(ROW):
        for j in range(COLUMN):
            pygame.draw.rect(surface, grid[i][j],
                             (j * BLOCK_SIZE, i * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 0)
    # 绘制网格线
    draw_grid(surface)
    # 显示得分
    font = pygame.font.SysFont('SimHei', 30)
    label = font.render(f'分数：{score}', True, (255, 255, 255))
    surface.blit(label, (COLUMN * BLOCK_SIZE + 20, 10))
    # 绘制“下一个方块”预览
    if next_piece:
        font = pygame.font.SysFont('SimHei', 25)
        label = font.render('下一个方块：', True, (255, 255, 255))
        start_x = COLUMN * BLOCK_SIZE + 20
        start_y = 150
        surface.blit(label, (start_x, start_y - 30))
        format = next_piece.shape[0]
        for i, line in enumerate(format):
            for j, column in enumerate(line):
                if column != 0:
                    pygame.draw.rect(surface, next_piece.color,
                                     (start_x + j * BLOCK_SIZE, start_y + i * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 0)

# 主游戏函数
def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('俄罗斯方块')
    clock = pygame.time.Clock()
    locked_positions = {}
    grid = create_grid(locked_positions)

    change_piece = False
    run = True
    current_piece = get_shape()
    next_piece = get_shape()
    fall_time = 0
    default_fall_speed = 0.8  # 默认下落速度
    fall_speed = default_fall_speed
    level_time = 0
    score = 0

    while run:
        grid = create_grid(locked_positions)
        fall_time += clock.get_rawtime()
        level_time += clock.get_rawtime()
        clock.tick()

        # 方块下落控制
        if fall_time / 1000 > fall_speed:
            fall_time = 0
            current_piece.y += 1
            if not valid_space(current_piece, grid) and current_piece.y > 0:
                current_piece.y -= 1
                change_piece = True

        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.display.quit()
                quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    current_piece.x -= 1
                    if not valid_space(current_piece, grid):
                        current_piece.x += 1
                elif event.key == pygame.K_RIGHT:
                    current_piece.x += 1
                    if not valid_space(current_piece, grid):
                        current_piece.x -= 1
                elif event.key == pygame.K_DOWN:
                    current_piece.y += 1
                    if not valid_space(current_piece, grid):
                        current_piece.y -= 1
                elif event.key == pygame.K_UP:
                    current_piece.rotate()
                    if not valid_space(current_piece, grid):
                        current_piece.rotation = (current_piece.rotation - 1) % len(current_piece.shape)

        # 检测按键状态，加速下落
        keys = pygame.key.get_pressed()
        if keys[pygame.K_DOWN]:
            fall_speed = 0.05  # 加快下落速度
        else:
            fall_speed = default_fall_speed  # 恢复默认速度

        shape_pos = convert_shape_format(current_piece)

        # 绘制当前方块到网格中
        for i in range(len(shape_pos)):
            x, y = shape_pos[i]
            if y > -1:
                grid[y][x] = current_piece.color

        # 方块落地后锁定并生成新方块
        if change_piece:
            for pos in shape_pos:
                locked_positions[(pos[0], pos[1])] = current_piece.color
            current_piece = next_piece
            next_piece = get_shape()
            change_piece = False
            row_score = clear_rows(grid, locked_positions)
            score += row_score  # 根据消除的行数增加得分

        # 绘制游戏窗口
        draw_window(screen, grid, score, next_piece)
        pygame.display.update()

        # 检查游戏是否结束
        if check_lost(locked_positions):
            draw_text_middle(screen, f"游戏结束\n总分：{score}", 50, (255, 255, 255))
            pygame.display.update()
            pygame.time.delay(3000)
            run = False

if __name__ == '__main__':
    main()

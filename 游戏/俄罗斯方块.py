import pygame
import random

# 初始化 Pygame
pygame.init()

# 游戏窗口尺寸
WINDOW_WIDTH = 500
WINDOW_HEIGHT = 600

# 颜色定义
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
ORANGE = (255, 165, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
PURPLE = (128, 0, 128)
RED = (255, 0, 0)

# 游戏区域尺寸
GRID_WIDTH = 10
GRID_HEIGHT = 20
CELL_SIZE = 30

# 方块形状定义
SHAPES = [
    [[1, 5, 9, 13], [4, 5, 6, 7]],  # I
    [[4, 5, 9, 10], [2, 6, 5, 9]],  # Z
    [[6, 7, 9, 10], [1, 5, 6, 10]],  # S
    [[1, 2, 5, 9], [0, 4, 5, 6], [1, 5, 9, 8], [4, 5, 6, 10]],  # L
    [[1, 2, 6, 10], [5, 6, 7, 9], [2, 6, 10, 11], [3, 5, 6, 7]],  # J
    [[1, 4, 5, 6], [1, 4, 5, 9], [4, 5, 6, 9], [1, 5, 6, 9]],  # T
    [[1, 2, 5, 6]],  # O
]

COLORS = [CYAN, BLUE, ORANGE, YELLOW, GREEN, PURPLE, RED]


class Tetris:
    def __init__(self):
        self.window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("俄罗斯方块")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 24, bold=True)

        self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.score = 0
        self.level = 1
        self.current_piece = self.new_piece()
        self.next_piece = self.new_piece()
        self.game_over = False

    def new_piece(self):
        shape_type = random.randint(0, len(SHAPES) - 1)
        return {
            'shape': SHAPES[shape_type],
            'color': COLORS[shape_type],
            'x': GRID_WIDTH // 2 - 2,
            'y': 0,
            'rotation': 0
        }

    def check_collision(self, piece, dx=0, dy=0):
        shape = piece['shape'][piece['rotation']]
        for i in range(4):
            x = piece['x'] + (shape[i] % 4) + dx
            y = piece['y'] + (shape[i] // 4) + dy
            if x < 0 or x >= GRID_WIDTH or y >= GRID_HEIGHT:
                return True
            if y >= 0 and self.grid[y][x]:
                return True
        return False

    def lock_piece(self, piece):
        shape = piece['shape'][piece['rotation']]
        for i in range(4):
            x = piece['x'] + (shape[i] % 4)
            y = piece['y'] + (shape[i] // 4)
            if y >= 0:
                self.grid[y][x] = piece['color']

        lines = self.clear_lines()
        self.update_score(lines)
        self.current_piece = self.next_piece
        self.next_piece = self.new_piece()

        if self.check_collision(self.current_piece):
            self.game_over = True

    def clear_lines(self):
        lines = 0
        for y in range(GRID_HEIGHT):
            if all(self.grid[y]):
                del self.grid[y]
                self.grid.insert(0, [0] * GRID_WIDTH)
                lines += 1
        return lines

    def update_score(self, lines):
        score_values = {0: 0, 1: 40, 2: 100, 3: 300, 4: 1200}
        self.score += score_values[lines] * self.level
        if self.score // 1000 >= self.level:
            self.level += 1

    def move(self, dx):
        if not self.game_over:
            if not self.check_collision(self.current_piece, dx=dx):
                self.current_piece['x'] += dx

    def rotate(self):
        if not self.game_over:
            new_rotation = (self.current_piece['rotation'] + 1) % len(self.current_piece['shape'])
            old_rotation = self.current_piece['rotation']
            self.current_piece['rotation'] = new_rotation
            if self.check_collision(self.current_piece):
                self.current_piece['rotation'] = old_rotation

    def drop(self):
        if not self.game_over:
            while not self.check_collision(self.current_piece, dy=1):
                self.current_piece['y'] += 1
            self.lock_piece(self.current_piece)

    def draw_grid(self):
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                color = self.grid[y][x]
                if color:
                    pygame.draw.rect(self.window, color,
                                     (x * CELL_SIZE + 1, y * CELL_SIZE + 1, CELL_SIZE - 2, CELL_SIZE - 2))

    def draw_piece(self, piece, offset_x=0, offset_y=0):
        shape = piece['shape'][piece['rotation']]
        for i in range(4):
            x = piece['x'] + (shape[i] % 4)
            y = piece['y'] + (shape[i] // 4)
            pygame.draw.rect(self.window, piece['color'],
                             ((x + offset_x) * CELL_SIZE + 1, (y + offset_y) * CELL_SIZE + 1, CELL_SIZE - 2,
                              CELL_SIZE - 2))

    def draw_sidebar(self):
        # 绘制下一个方块
        self.window.blit(self.font.render("Next:", True, WHITE), (320, 30))
        self.draw_piece(self.next_piece, offset_x=GRID_WIDTH + 1, offset_y=2)

        # 绘制分数和等级
        self.window.blit(self.font.render(f"Score: {self.score}", True, WHITE), (320, 200))
        self.window.blit(self.font.render(f"Level: {self.level}", True, WHITE), (320, 250))

        if self.game_over:
            self.window.blit(self.font.render("GAME OVER!", True, RED), (320, 400))

    def run(self):
        fall_time = 0
        fall_speed = 1000  # 初始下落速度

        while True:
            self.window.fill(BLACK)

            # 处理事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        self.move(-1)
                    elif event.key == pygame.K_RIGHT:
                        self.move(1)
                    elif event.key == pygame.K_UP:
                        self.rotate()
                    elif event.key == pygame.K_DOWN:
                        self.move(0, 1)
                    elif event.key == pygame.K_SPACE:
                        self.drop()

            # 自动下落
            delta_time = self.clock.get_rawtime()
            fall_time += delta_time
            if fall_time >= fall_speed:
                if not self.check_collision(self.current_piece, dy=1):
                    self.current_piece['y'] += 1
                else:
                    self.lock_piece(self.current_piece)
                fall_time = 0

            # 更新游戏速度
            fall_speed = max(50, 1000 - (self.level - 1) * 100)

            # 绘制游戏元素
            self.draw_grid()
            self.draw_piece(self.current_piece)
            self.draw_sidebar()

            pygame.display.flip()
            self.clock.tick(60)


if __name__ == "__main__":
    game = Tetris()
    game.run()
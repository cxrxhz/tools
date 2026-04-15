import pygame
import random
import sys

# 初始化 Pygame
pygame.init()

# ==================== 常量定义 ====================

# 窗口尺寸
WINDOW_WIDTH = 640
WINDOW_HEIGHT = 480

# 网格参数
CELL_SIZE = 20
GRID_COLS = WINDOW_WIDTH // CELL_SIZE   # 32 列
GRID_ROWS = WINDOW_HEIGHT // CELL_SIZE  # 24 行

# 颜色定义
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DARK_GRAY = (30, 30, 30)
GRID_COLOR = (40, 40, 40)
RED = (220, 50, 50)
FOOD_COLOR_1 = (255, 80, 80)
FOOD_COLOR_2 = (255, 160, 160)
SNAKE_HEAD = (100, 255, 100)
SNAKE_TAIL = (0, 100, 0)
SCORE_COLOR = (200, 200, 200)
OVERLAY_COLOR = (0, 0, 0, 180)

# 方向
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

# 游戏参数
INITIAL_LENGTH = 3
INITIAL_FPS = 8
MAX_FPS = 20
SCORE_PER_FOOD = 10
LEVEL_UP_SCORE = 50


# ==================== Snake 类 ====================

class Snake:
    def __init__(self):
        self.reset()

    def reset(self):
        """重置蛇到初始状态"""
        center_x = GRID_COLS // 2
        center_y = GRID_ROWS // 2
        self.body = [(center_x - i, center_y) for i in range(INITIAL_LENGTH)]
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.grow = False

    @property
    def head(self):
        return self.body[0]

    def set_direction(self, new_dir):
        """设置方向（防止直接反向）"""
        opposite = (-self.direction[0], -self.direction[1])
        if new_dir != opposite:
            self.next_direction = new_dir

    def move(self):
        """移动蛇"""
        self.direction = self.next_direction
        hx, hy = self.head
        dx, dy = self.direction
        new_head = (hx + dx, hy + dy)
        self.body.insert(0, new_head)
        if not self.grow:
            self.body.pop()
        else:
            self.grow = False

    def check_collision(self):
        """检测是否撞墙或撞自身"""
        hx, hy = self.head
        # 撞墙
        if hx < 0 or hx >= GRID_COLS or hy < 0 or hy >= GRID_ROWS:
            return True
        # 撞自身
        if self.head in self.body[1:]:
            return True
        return False

    def draw(self, surface):
        """绘制渐变色蛇身"""
        length = len(self.body)
        for i, (x, y) in enumerate(self.body):
            # 从头到尾渐变：SNAKE_HEAD → SNAKE_TAIL
            if length > 1:
                t = i / (length - 1)
            else:
                t = 0
            r = int(SNAKE_HEAD[0] + (SNAKE_TAIL[0] - SNAKE_HEAD[0]) * t)
            g = int(SNAKE_HEAD[1] + (SNAKE_TAIL[1] - SNAKE_HEAD[1]) * t)
            b = int(SNAKE_HEAD[2] + (SNAKE_TAIL[2] - SNAKE_HEAD[2]) * t)
            color = (r, g, b)

            rect = pygame.Rect(x * CELL_SIZE + 1, y * CELL_SIZE + 1,
                               CELL_SIZE - 2, CELL_SIZE - 2)
            pygame.draw.rect(surface, color, rect, border_radius=4)

            # 蛇头绘制眼睛
            if i == 0:
                self._draw_eyes(surface, x, y)

    def _draw_eyes(self, surface, x, y):
        """在蛇头上绘制眼睛"""
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2
        dx, dy = self.direction

        # 眼睛偏移
        if dx == 0:  # 上或下
            eye1 = (cx - 4, cy + dy * 2)
            eye2 = (cx + 4, cy + dy * 2)
        else:  # 左或右
            eye1 = (cx + dx * 2, cy - 4)
            eye2 = (cx + dx * 2, cy + 4)

        pygame.draw.circle(surface, WHITE, eye1, 3)
        pygame.draw.circle(surface, WHITE, eye2, 3)
        pygame.draw.circle(surface, BLACK, eye1, 1)
        pygame.draw.circle(surface, BLACK, eye2, 1)


# ==================== Food 类 ====================

class Food:
    def __init__(self):
        self.position = (0, 0)
        self.pulse_timer = 0

    def spawn(self, snake_body):
        """在蛇身以外的随机位置生成食物"""
        while True:
            pos = (random.randint(0, GRID_COLS - 1), random.randint(0, GRID_ROWS - 1))
            if pos not in snake_body:
                self.position = pos
                self.pulse_timer = 0
                break

    def draw(self, surface):
        """绘制带脉冲动画的食物"""
        self.pulse_timer += 1
        # 脉冲效果：大小在 0.7~1.0 之间波动
        import math
        pulse = 0.85 + 0.15 * math.sin(self.pulse_timer * 0.15)
        size = int((CELL_SIZE - 2) * pulse)
        offset = (CELL_SIZE - size) // 2

        x, y = self.position
        # 颜色脉冲
        t = 0.5 + 0.5 * math.sin(self.pulse_timer * 0.1)
        r = int(FOOD_COLOR_1[0] + (FOOD_COLOR_2[0] - FOOD_COLOR_1[0]) * t)
        g = int(FOOD_COLOR_1[1] + (FOOD_COLOR_2[1] - FOOD_COLOR_1[1]) * t)
        b = int(FOOD_COLOR_1[2] + (FOOD_COLOR_2[2] - FOOD_COLOR_1[2]) * t)

        rect = pygame.Rect(x * CELL_SIZE + offset, y * CELL_SIZE + offset, size, size)
        pygame.draw.rect(surface, (r, g, b), rect, border_radius=6)


# ==================== Game 类 ====================

class Game:
    def __init__(self):
        self.window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("贪吃蛇")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont('SimHei', 48, bold=True)
        self.font_medium = pygame.font.SysFont('SimHei', 24)
        self.font_small = pygame.font.SysFont('SimHei', 18)

        self.snake = Snake()
        self.food = Food()
        self.score = 0
        self.level = 1
        self.game_over = False
        self.food.spawn(self.snake.body)

    def reset(self):
        """重置游戏"""
        self.snake.reset()
        self.score = 0
        self.level = 1
        self.game_over = False
        self.food.spawn(self.snake.body)

    def handle_events(self):
        """处理键盘事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if self.game_over:
                    if event.key == pygame.K_SPACE:
                        self.reset()
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                else:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.snake.set_direction(UP)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.snake.set_direction(DOWN)
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        self.snake.set_direction(LEFT)
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        self.snake.set_direction(RIGHT)
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

    def update(self):
        """更新游戏状态"""
        if self.game_over:
            return

        self.snake.move()

        # 检测碰撞
        if self.snake.check_collision():
            self.game_over = True
            return

        # 检测吃食物
        if self.snake.head == self.food.position:
            self.snake.grow = True
            self.score += SCORE_PER_FOOD
            self.level = self.score // LEVEL_UP_SCORE + 1
            self.food.spawn(self.snake.body)

    def draw_grid(self):
        """绘制网格背景"""
        self.window.fill(DARK_GRAY)
        for x in range(0, WINDOW_WIDTH, CELL_SIZE):
            pygame.draw.line(self.window, GRID_COLOR, (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, CELL_SIZE):
            pygame.draw.line(self.window, GRID_COLOR, (0, y), (WINDOW_WIDTH, y))

    def draw_hud(self):
        """绘制分数和等级"""
        score_text = self.font_small.render(f"分数: {self.score}", True, SCORE_COLOR)
        level_text = self.font_small.render(f"等级: {self.level}", True, SCORE_COLOR)
        length_text = self.font_small.render(f"长度: {len(self.snake.body)}", True, SCORE_COLOR)

        # 半透明背景条
        hud_surface = pygame.Surface((WINDOW_WIDTH, 28), pygame.SRCALPHA)
        hud_surface.fill((0, 0, 0, 120))
        self.window.blit(hud_surface, (0, 0))

        self.window.blit(score_text, (10, 4))
        self.window.blit(level_text, (WINDOW_WIDTH // 2 - 40, 4))
        self.window.blit(length_text, (WINDOW_WIDTH - 100, 4))

    def draw_game_over(self):
        """绘制游戏结束画面"""
        # 半透明遮罩
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill(OVERLAY_COLOR)
        self.window.blit(overlay, (0, 0))

        # 游戏结束文字
        title = self.font_large.render("游戏结束", True, RED)
        score = self.font_medium.render(f"最终分数: {self.score}", True, WHITE)
        hint = self.font_small.render("按 空格键 重新开始  |  按 ESC 退出", True, SCORE_COLOR)

        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40))
        score_rect = score.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 10))
        hint_rect = hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 50))

        self.window.blit(title, title_rect)
        self.window.blit(score, score_rect)
        self.window.blit(hint, hint_rect)

    def get_fps(self):
        """根据等级计算帧率"""
        return min(INITIAL_FPS + (self.level - 1) * 2, MAX_FPS)

    def run(self):
        """游戏主循环"""
        while True:
            self.handle_events()
            self.update()

            # 绘制
            self.draw_grid()
            self.food.draw(self.window)
            self.snake.draw(self.window)
            self.draw_hud()

            if self.game_over:
                self.draw_game_over()

            pygame.display.flip()
            self.clock.tick(self.get_fps())


# ==================== 程序入口 ====================

if __name__ == "__main__":
    game = Game()
    game.run()

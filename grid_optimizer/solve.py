"""
方格设备摆放优化器 - 最终版
==============================
问题：在10x11的方格中摆放设备和人物：
  - 每个设备必须与至少一个人相邻（上下左右，斜着不算）
  - 人必须有路径能走过去（所有非设备格子必须连通）
  - 目标：最大化设备数量

方法：
  阶段1: 构造模式 + 贪心填充 + 迭代局部搜索 (快速找到好解)
  阶段2: 用好解作为CP-SAT求解器的初始提示 (尝试证明最优性)
"""

import sys
import random
import time as _time
from collections import deque


def install_pkg(package):
    import importlib
    try:
        return importlib.import_module(package)
    except ImportError:
        print(f"  Installing {package}...")
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', package])
        return importlib.import_module(package)


ROWS = 10
COLS = 11

def get_neighbors(r, c):
    result = []
    if r > 0: result.append((r-1, c))
    if r < ROWS-1: result.append((r+1, c))
    if c > 0: result.append((r, c-1))
    if c < COLS-1: result.append((r, c+1))
    return result

NEIGHBORS = {}
for _r in range(ROWS):
    for _c in range(COLS):
        NEIGHBORS[(_r, _c)] = get_neighbors(_r, _c)


def is_valid(grid):
    start = None
    total_empty = 0
    for r in range(ROWS):
        for c in range(COLS):
            if grid[r][c] == 1:
                ok = False
                for nr, nc in NEIGHBORS[(r, c)]:
                    if grid[nr][nc] == 0:
                        ok = True
                        break
                if not ok:
                    return False
            else:
                total_empty += 1
                if start is None:
                    start = (r, c)
    if total_empty <= 1:
        return True
    seen = [[False]*COLS for _ in range(ROWS)]
    seen[start[0]][start[1]] = True
    q = deque([start])
    visited = 0
    while q:
        cr, cc = q.popleft()
        visited += 1
        for nr, nc in NEIGHBORS[(cr, cc)]:
            if not seen[nr][nc] and grid[nr][nc] == 0:
                seen[nr][nc] = True
                q.append((nr, nc))
    return visited == total_empty


def count_eq(grid):
    return sum(grid[r][c] for r in range(ROWS) for c in range(COLS))


def greedy_fill(grid):
    changed = True
    while changed:
        changed = False
        cells = [(r, c) for r in range(ROWS) for c in range(COLS) if grid[r][c] == 0]
        random.shuffle(cells)
        for r, c in cells:
            grid[r][c] = 1
            if is_valid(grid):
                changed = True
            else:
                grid[r][c] = 0
    return grid


def multi_greedy(grid, trials=20):
    best = count_eq(grid)
    best_grid = [row[:] for row in grid]
    for _ in range(trials):
        g = [row[:] for row in grid]
        g = greedy_fill(g)
        eq = count_eq(g)
        if eq > best:
            best = eq
            best_grid = [row[:] for row in g]
    return best_grid, best


def perturb_and_refill(grid, num_remove=5):
    g = [row[:] for row in grid]
    eq_cells = [(r, c) for r in range(ROWS) for c in range(COLS) if g[r][c] == 1]
    if len(eq_cells) < num_remove:
        return g
    for r, c in random.sample(eq_cells, num_remove):
        g[r][c] = 0
    return greedy_fill(g)


def iterated_local_search(grid, iterations=300, remove_range=(2, 12)):
    best = count_eq(grid)
    best_grid = [row[:] for row in grid]
    for _ in range(iterations):
        g = perturb_and_refill(best_grid, random.randint(*remove_range))
        eq = count_eq(g)
        if eq >= best:
            best = eq
            best_grid = [row[:] for row in g]
    return best_grid, best


def print_grid(grid, title=""):
    eq = count_eq(grid)
    valid = is_valid(grid)
    non_eq = ROWS * COLS - eq
    people = sum(1 for r in range(ROWS) for c in range(COLS)
                 if grid[r][c] == 0 and any(grid[nr][nc] == 1 for nr, nc in NEIGHBORS[(r, c)]))

    if title:
        print(f"\n  === {title} ===")
    print(f"  设备: {eq}/{ROWS*COLS} ({eq/(ROWS*COLS):.0%})  "
          f"有效: {'YES' if valid else 'NO'}  人: {people}  路径: {non_eq - people}")
    print()
    print("     " + " ".join(f"{c:2d}" for c in range(COLS)))
    print("    +" + "---" * COLS + "+")
    for r in range(ROWS):
        s = f" {r:2d} |"
        for c in range(COLS):
            if grid[r][c] == 1:
                s += " E "
            else:
                adj = any(grid[nr][nc] == 1 for nr, nc in NEIGHBORS[(r, c)])
                s += " P " if adj else " . "
        s += "|"
        print(s)
    print("    +" + "---" * COLS + "+")
    return eq


# ============================================================
# 阶段1: 启发式求解
# ============================================================

def heuristic_solve():
    """用多种模式+贪心+ILS找到好解"""
    print("  [阶段1] 启发式求解")
    print("  " + "-" * 50)

    patterns = []

    # 模式族: 2行设备 + 1行通道, 不同偏移和通道列
    for offset in range(3):
        for path_col in [0, COLS//2, COLS-1]:
            grid = [[0] * COLS for _ in range(ROWS)]
            for r in range(ROWS):
                if (r - offset) % 3 < 2:
                    for c in range(COLS):
                        grid[r][c] = 1
                    grid[r][path_col] = 0
            if is_valid(grid):
                patterns.append(grid)

    # 棋盘模式
    for parity in [0, 1]:
        grid = [[0] * COLS for _ in range(ROWS)]
        for r in range(ROWS):
            for c in range(COLS):
                if (r + c) % 2 == parity:
                    grid[r][c] = 1
        if is_valid(grid):
            patterns.append(grid)

    # 隔行模式 + 竖直通道
    for path_col in [0, COLS//2, COLS-1]:
        grid = [[0] * COLS for _ in range(ROWS)]
        for r in range(ROWS):
            if r % 2 == 1:
                for c in range(COLS):
                    grid[r][c] = 1
                grid[r][path_col] = 0
        if is_valid(grid):
            patterns.append(grid)

    # 全1, 不同通道行间距 + 竖直通道
    for spacing in [3, 4]:
        for start_row in range(spacing):
            for path_col in [0, COLS//2, COLS-1]:
                grid = [[1] * COLS for _ in range(ROWS)]
                for r in range(ROWS):
                    grid[r][path_col] = 0
                for r in range(start_row, ROWS, spacing):
                    for c in range(COLS):
                        grid[r][c] = 0
                # 修复无邻居设备
                for _ in range(5):
                    for r in range(ROWS):
                        for c in range(COLS):
                            if grid[r][c] == 1:
                                if not any(grid[nr][nc] == 0 for nr, nc in NEIGHBORS[(r, c)]):
                                    grid[r][c] = 0
                if is_valid(grid):
                    patterns.append(grid)

    print(f"  生成 {len(patterns)} 个基础模式")

    # 多次贪心填充
    best_grid = None
    best_score = 0
    results = []

    for i, grid in enumerate(patterns):
        g, eq = multi_greedy(grid, trials=15)
        results.append((eq, [row[:] for row in g]))
        if eq > best_score:
            best_score = eq
            best_grid = [row[:] for row in g]

    results.sort(key=lambda x: -x[0])
    print(f"  贪心最优: {best_score}")

    # ILS深度搜索前几名
    for i in range(min(5, len(results))):
        eq, grid = results[i]
        g, eq2 = iterated_local_search(grid, iterations=500, remove_range=(2, 10))
        if eq2 > best_score:
            best_score = eq2
            best_grid = [row[:] for row in g]
            print(f"  ILS改善: {eq} -> {eq2}")

    # 深度搜索最优解
    for trial in range(20):
        g, eq = iterated_local_search(best_grid, iterations=300, remove_range=(3, 15))
        if eq > best_score:
            best_score = eq
            best_grid = [row[:] for row in g]
            print(f"  深度搜索改善: {eq}")

    print(f"  启发式最优: {best_score}")
    return best_grid, best_score


# ============================================================
# 阶段2: CP-SAT 精确求解（带初始提示）
# ============================================================

def cpsat_solve(hint_grid=None, time_limit=300):
    """CP-SAT精确求解，可选初始提示"""
    install_pkg('ortools')
    from ortools.sat.python import cp_model

    print(f"\n  [阶段2] CP-SAT 精确求解 (限时{time_limit}秒)")
    print("  " + "-" * 50)

    model = cp_model.CpModel()
    N = ROWS * COLS

    e = {}
    ne = {}
    for r in range(ROWS):
        for c in range(COLS):
            e[r, c] = model.NewBoolVar(f'e_{r}_{c}')
            ne[r, c] = model.NewBoolVar(f'ne_{r}_{c}')
            model.Add(e[r, c] + ne[r, c] == 1)

    model.Maximize(sum(e[r, c] for r in range(ROWS) for c in range(COLS)))

    # 约束1: 每个设备至少有一个非设备邻居
    for r in range(ROWS):
        for c in range(COLS):
            nbrs = NEIGHBORS[(r, c)]
            model.Add(e[r, c] <= sum(ne[nr, nc] for nr, nc in nbrs))

    # 约束2: 连通性（网络流）
    model.Add(e[0, 0] == 0)

    f = {}
    for r in range(ROWS):
        for c in range(COLS):
            for nr, nc in NEIGHBORS[(r, c)]:
                f[r, c, nr, nc] = model.NewIntVar(0, N, f'f_{r}_{c}_{nr}_{nc}')

    for r in range(ROWS):
        for c in range(COLS):
            if r == 0 and c == 0:
                continue
            nbrs = NEIGHBORS[(r, c)]
            inflow = sum(f[nr, nc, r, c] for nr, nc in nbrs)
            outflow = sum(f[r, c, nr, nc] for nr, nc in nbrs)
            model.Add(inflow - outflow >= 1).OnlyEnforceIf(ne[r, c])
            model.Add(inflow == 0).OnlyEnforceIf(e[r, c])
            model.Add(outflow == 0).OnlyEnforceIf(e[r, c])

    for r in range(ROWS):
        for c in range(COLS):
            for nr, nc in NEIGHBORS[(r, c)]:
                model.Add(f[r, c, nr, nc] == 0).OnlyEnforceIf(e[r, c])
                model.Add(f[r, c, nr, nc] == 0).OnlyEnforceIf(e[nr, nc])

    # 提供初始解提示
    if hint_grid:
        for r in range(ROWS):
            for c in range(COLS):
                model.AddHint(e[r, c], hint_grid[r][c])
        print(f"  提供了启发式解作为初始提示 (设备={count_eq(hint_grid)})")

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = 8
    solver.parameters.log_search_progress = False

    print(f"  求解中...")
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        grid = [[solver.Value(e[r, c]) for c in range(COLS)] for r in range(ROWS)]
        eq = count_eq(grid)
        status_str = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
        bound = int(solver.BestObjectiveBound())
        print(f"  状态: {status_str}")
        print(f"  设备: {eq}, 上界: {bound}")
        if status == cp_model.OPTIMAL:
            print(f"  >>> 已证明最优! <<<")
        else:
            print(f"  最优解在 [{eq}, {bound}] 之间")
        return grid, eq, bound, status_str
    else:
        print(f"  求解失败")
        return None, 0, 0, "FAILED"


# ============================================================
# 主函数
# ============================================================

def main():
    print()
    print("=" * 60)
    print("  10x11 方格设备摆放优化器")
    print("=" * 60)
    print(f"  格子: {ROWS} x {COLS} = {ROWS*COLS}")
    print(f"  约束:")
    print(f"    1. 每个设备必须与至少一个人相邻(上下左右)")
    print(f"    2. 所有非设备格必须连通(人能走过去)")
    print(f"  目标: 最大化设备数量")
    print("=" * 60)
    print()

    t0 = _time.time()

    # 阶段1: 启发式
    heuristic_grid, heuristic_score = heuristic_solve()

    # 阶段2: CP-SAT (带提示)
    cpsat_grid, cpsat_score, bound, status = cpsat_solve(
        hint_grid=heuristic_grid, time_limit=300
    )

    elapsed = _time.time() - t0

    # 最终结果
    if cpsat_grid and cpsat_score >= heuristic_score:
        final_grid = cpsat_grid
        final_score = cpsat_score
        method = f"CP-SAT ({status})"
    else:
        final_grid = heuristic_grid
        final_score = heuristic_score
        method = "启发式"

    print(f"\n{'=' * 60}")
    print(f"  最终结果 (方法: {method})")
    print(f"{'=' * 60}")
    print_grid(final_grid)

    if status == "FEASIBLE":
        print(f"\n  注: CP-SAT上界={bound}, 最优解在[{final_score}, {bound}]之间")
    elif status == "OPTIMAL":
        print(f"\n  已证明 {final_score} 是最优解!")

    print(f"\n  原始数据 (1=设备, 0=非设备):")
    for r in range(ROWS):
        print(f"    {final_grid[r]}")

    print(f"\n  总耗时: {elapsed:.1f}秒")
    print()


if __name__ == '__main__':
    main()

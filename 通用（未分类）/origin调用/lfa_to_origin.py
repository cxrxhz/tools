"""
从 Cr2Te3 LFA 4.22 数据中批量提取热扩散率，
通过 originpro 包将数据导入 Origin 并绘制点线图。
"""
import originpro as op
import sys
import os
import csv
import time

if hasattr(op, 'excepthook'):
    sys.excepthook = op.excepthook

# ============ 配置区 ============
DATA_DIR = r"F:\OneDrive - 草莓甜品屋\实验数据\Cr2Te3\LFA\4.22"
SAVE_NAME = "Cr2Te3_LFA_4.22.opju"
# ================================


def extract_lfa(file_path):
    """从单个 LFA CSV 提取 Material、Mean Diffusivity、Std_Dev"""
    material = None
    mean_diff = None
    std_dev = None
    encodings = ['gbk', 'utf-8-sig', 'utf-16']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row:
                        continue
                    if row[0].startswith('#Material'):
                        material = row[1].strip()
                    if row[0].startswith('#Mean'):
                        mean_diff = float(row[3])
                    if row[0].startswith('#Std_Dev'):
                        std_dev = float(row[3])
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    return material, mean_diff, std_dev


def collect_all(data_dir):
    """遍历目录，按编号排序提取所有样品数据"""
    results = []
    for fname in os.listdir(data_dir):
        if not fname.endswith('.csv'):
            continue
        parts = fname.split()
        if not parts:
            continue
        try:
            sample_num = int(parts[0])
        except ValueError:
            continue
        fpath = os.path.join(data_dir, fname)
        material, mean_diff, std_dev = extract_lfa(fpath)
        if mean_diff is not None:
            results.append((sample_num, material, mean_diff, std_dev))
    results.sort(key=lambda x: x[0])
    return results


def main():
    # ---- 第一步：提取数据 ----
    print("正在从 CSV 中提取热扩散率...")
    results = collect_all(DATA_DIR)
    if not results:
        print("未找到有效数据，请检查路径。")
        return

    print(f"成功提取 {len(results)} 个样品数据：")
    for num, mat, diff, std in results:
        print(f"  编号 {num} | {mat} | α = {diff:.3f} ± {std:.3f} mm²/s")

    # 准备列数据
    sample_nums = [r[0] for r in results]
    labels = [r[1] for r in results]        # 如 "1 - B1"
    diffusivities = [r[2] for r in results]
    std_devs = [r[3] for r in results]

    # ---- 第二步：启动 Origin 并写入数据 ----
    print("\n正在启动 Origin...")
    op.set_show(True)

    try:
        # 新建工作簿（from_list 会自动扩展列数）
        wks = op.new_sheet('w', lname='Cr2Te3 LFA 4.22')

        # 写入数据，from_list 自动创建列
        wks.from_list(0, sample_nums, 'Sample Number')
        wks.from_list(1, diffusivities, 'Diffusivity')
        wks.from_list(2, std_devs, 'Std Dev')

        print("-> 数据已写入工作簿")

        # ---- 第三步：绘制点线图 ----
        graph = op.new_graph(template='scatter')
        layer = graph[0]

        # 添加数据到图层（Y列=col1 热扩散率，X列=col0 编号）
        plot = layer.add_plot(wks, 1, 0)
        layer.rescale()

        print("-> 点线图绘制完成")

        # ---- 第四步：保存 ----
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        save_path = os.path.join(desktop, SAVE_NAME)
        op.save(save_path)
        print(f"\n文件已保存至: {save_path}")

        time.sleep(3)

    except Exception as e:
        print(f"Origin 操作出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if op and op.oext:
            op.exit()
        print("Origin 已安全关闭。")


if __name__ == '__main__':
    main()

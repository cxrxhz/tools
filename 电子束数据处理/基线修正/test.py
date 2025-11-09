#!/usr/bin/env python3
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter, find_peaks
import tkinter as tk
from tkinter import filedialog
import matplotlib as mpl

# ---------------------- 可配置参数 ----------------------
# 数据预处理与信号平滑参数
SMOOTHING_WINDOW = 31  # Savitzky–Golay 滤波窗口长度（必须为奇数）
POLYORDER = 3  # 多项式阶数

# 波谷检测参数（用于分段）
VALLEY_PROMINENCE = 0.5  # 检测波谷时要求的最低显著性
VALLEY_DISTANCE = None  # 可设置采样点数的最小距离

# 基线扣除：回到原先版本，采用每个周期的最小值作为基线
# 振幅计算：周期内最大值减去最小值
# ----------------------------------------------------------

# 设置 Matplotlib 中文字体（可选）和避免负号显示问题
mpl.rcParams['font.sans-serif'] = ['SimHei']  # 如 Windows 上可使用 "SimHei" 或 "Microsoft YaHei"
mpl.rcParams['axes.unicode_minus'] = False


def load_data(filename):
    """
    逐行读取数据文件，跳过无法转换为数值的行（例如含说明文字的行）。
    每行取前4个数字，其中：
      第一列为 x，
      第二列为 y1，
      第四列为 y2。
    返回 x, y1, y2（均为 numpy 数组）。
    """
    valid_lines = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            try:
                float(parts[0])
            except ValueError:
                continue
            if len(parts) < 4:
                continue
            try:
                # 取前4个数字
                numbers = [float(x) for x in parts[:4]]
                valid_lines.append(numbers)
            except ValueError:
                continue

    if len(valid_lines) == 0:
        raise ValueError(f"{filename} 中没有有效数据行。")
    data = np.array(valid_lines)
    x = data[:, 0]
    y1 = data[:, 1]
    y2 = data[:, 3]
    return x, y1, y2


def segment_by_valleys(x, y, smoothing_window=SMOOTHING_WINDOW, polyorder=POLYORDER,
                       valley_prominence=VALLEY_PROMINENCE, valley_distance=VALLEY_DISTANCE):
    """
    采用 Savitzky–Golay 滤波对信号进行平滑后，
    对平滑后信号取负值，并调用 find_peaks 检测局部峰值，
    从而检测出原始信号中的局部最小值（波谷）。
    若未检测到波谷，则整条信号视为1段。
    为确保边界完整，若首尾未检测到则加入第一个点及最后一个点。

    返回一个分段列表，每个分段为字典，包含分段索引（indices），
    以及分段的 x 和 y 数据。
    """
    y_smooth = savgol_filter(y, window_length=smoothing_window, polyorder=polyorder)
    valley_indices, _ = find_peaks(-y_smooth, prominence=valley_prominence, distance=valley_distance)
    if len(valley_indices) == 0:
        return [{"indices": np.arange(len(y)), "x": x, "y": y}]
    if valley_indices[0] != 0:
        valley_indices = np.r_[0, valley_indices]
    if valley_indices[-1] != len(y) - 1:
        valley_indices = np.r_[valley_indices, len(y) - 1]
    segments = []
    for i in range(len(valley_indices) - 1):
        idx = np.arange(valley_indices[i], valley_indices[i + 1] + 1)
        segments.append({
            "indices": idx,
            "x": x[idx],
            "y": y[idx]
        })
    return segments


def correct_segment_by_valley(y_seg):
    """
    对单个波周期进行基线扣除（原始版本）：
      - 定义基线为该周期数据的最小值；
      - 扣除基线后，该周期的振幅计算为：max(y_seg) - min(y_seg)。
    返回扣除基线后的信号、计算得到的基线及振幅。
    """
    baseline = np.min(y_seg)  # 原始版本使用最小值
    y_corr = y_seg - baseline
    amplitude = np.max(y_seg) - baseline
    return y_corr, baseline, amplitude


def baseline_correction_by_valleys(x, y, smoothing_window=SMOOTHING_WINDOW, polyorder=POLYORDER):
    """
    先调用 segment_by_valleys 将信号分为完整的波周期，
    然后对每个周期调用 correct_segment_by_valley 进行基线扣除，
    得到扣除基线后的信号、各周期的基线及振幅（变化量）。

    返回：
      - y_corrected：扣除基线后的完整信号（与 x 长度一致）
      - segments：分段信息列表
      - baselines：每段计算得到的基线列表
      - amplitudes：每段计算得到的振幅变化量列表
    """
    segments = segment_by_valleys(x, y, smoothing_window, polyorder, VALLEY_PROMINENCE, VALLEY_DISTANCE)
    y_corrected = np.empty_like(y)
    baselines = []
    amplitudes = []
    for seg in segments:
        idx = seg["indices"]
        y_seg = seg["y"]
        y_corr, baseline, amplitude = correct_segment_by_valley(y_seg)
        y_corrected[idx] = y_corr
        baselines.append(baseline)
        amplitudes.append(amplitude)
    return y_corrected, segments, baselines, amplitudes


def get_valid_files(folder_path):
    """
    遍历指定文件夹中的所有文件，返回符合以下条件的文件完整路径列表：
      - 后缀为 ".txt"（忽略大小写），
      - 或无后缀，
      - 或后缀（不计点）的长度超过 5 个字符。
    """
    valid_files = []
    for filename in os.listdir(folder_path):
        full_path = os.path.join(folder_path, filename)
        if os.path.isfile(full_path):
            root, ext = os.path.splitext(filename)
            if ext.lower() == ".txt" or ext == "" or (len(ext) - 1 > 5):
                valid_files.append(full_path)
    return valid_files


def main():
    # 弹出文件夹选择对话框（隐藏 Tk 主窗口）
    root = tk.Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory(title="请选择包含数据文件的文件夹")
    if not folder_path:
        print("未选择文件夹，程序退出。")
        return

    files = get_valid_files(folder_path)
    if not files:
        print("在选择的文件夹中没有找到符合条件的文件！")
        return

    for file_path in files:
        print(f"正在处理：{file_path}")
        try:
            x, y1, y2 = load_data(file_path)
        except Exception as e:
            print(f"读取文件 {file_path} 时出错: {e}")
            continue

        # 针对 y1 和 y2 信号，采用波谷分段后基线扣除（使用最小值作为基线）
        y1_corr, segs1, bases1, amps1 = baseline_correction_by_valleys(x, y1)
        y2_corr, segs2, bases2, amps2 = baseline_correction_by_valleys(x, y2)

        print(f"文件 {os.path.basename(file_path)}:")
        print("  y1 每个波的振幅变化量：")
        for i, amp in enumerate(amps1):
            print(f"    波 {i + 1}: {amp:.4f}")
        print("  y2 每个波的振幅变化量：")
        for i, amp in enumerate(amps2):
            print(f"    波 {i + 1}: {amp:.4f}")

        # 绘制图形，展示原始信号与扣除基线后的信号，并标出检测到的波谷位置
        plt.figure(figsize=(12, 10))
        plt.subplot(2, 1, 1)
        plt.plot(x, y1, label="原始 y1", alpha=0.5)
        plt.plot(x, y1_corr, label="扣除基线后 y1", linewidth=2)
        # 绘制每个分段的起止边界
        for seg in segs1:
            plt.axvline(x=seg["x"][0], color="gray", linestyle="--", alpha=0.5)
            plt.axvline(x=seg["x"][-1], color="gray", linestyle="--", alpha=0.5)
        plt.xlabel("x")
        plt.ylabel("y1")
        plt.title(f"{os.path.basename(file_path)} - y1 扣除基线")
        plt.legend()

        plt.subplot(2, 1, 2)
        plt.plot(x, y2, label="原始 y2", alpha=0.5)
        plt.plot(x, y2_corr, label="扣除基线后 y2", linewidth=2)
        for seg in segs2:
            plt.axvline(x=seg["x"][0], color="gray", linestyle="--", alpha=0.5)
            plt.axvline(x=seg["x"][-1], color="gray", linestyle="--", alpha=0.5)
        plt.xlabel("x")
        plt.ylabel("y2")
        plt.title(f"{os.path.basename(file_path)} - y2 扣除基线")
        plt.legend()

        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    main()

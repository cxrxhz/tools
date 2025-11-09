#!/usr/bin/env python3
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter, find_peaks
import tkinter as tk
from tkinter import filedialog
import matplotlib as mpl

# ---------------------- 可配置参数 ----------------------
SMOOTHING_WINDOW = 21  # Savitzky–Golay 滤波窗口长度（必须为奇数）
POLYORDER = 3  # 多项式阶数
VALLEY_PROMINENCE = 0.5  # 波谷显著性阈值
VALLEY_DISTANCE = None  # 波谷最小间隔采样点数
MIN_PEAK_LENGTH = 50  # 输出波峰的最小数据点数阈值
# ----------------------------------------------------------

mpl.rcParams['font.sans-serif'] = ['SimHei']
mpl.rcParams['axes.unicode_minus'] = False


def load_data(filename):
    """
    逐行读取数据文件，跳过无法转换为数值的行（例如包含说明文字的行）。
    每行取前4个数字，其中：
      - 第一列为 x，
      - 第二列为 y1，
      - 第四列为 y2。
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
    对信号采用 Savitzky–Golay 平滑后，通过查找波谷将信号分段。
    利用平滑后的信号找到候选波谷，再根据左右波峰判断有效性，
    返回分段列表，每段为字典，包含 "indices"、"x" 与 "y" 数据。
    """
    y_smooth = savgol_filter(y, window_length=smoothing_window, polyorder=polyorder)
    candidate_valleys = find_peaks(-y_smooth, distance=valley_distance)[0]
    candidate_peaks = find_peaks(y_smooth)[0]
    candidate_peaks.sort()

    valid_valleys = []
    for v in candidate_valleys:
        pos = np.searchsorted(candidate_peaks, v)
        left_peak = candidate_peaks[pos - 1] if pos > 0 else None
        right_peak = candidate_peaks[pos] if pos < len(candidate_peaks) else None
        refs = []
        if left_peak is not None:
            refs.append(y_smooth[left_peak])
        if right_peak is not None:
            refs.append(y_smooth[right_peak])
        if not refs:
            continue
        ref_value = min(refs)
        if ref_value <= 0:
            continue
        if (ref_value - y_smooth[v]) / ref_value >= valley_prominence:
            valid_valleys.append(v)
    valid_valleys = np.array(valid_valleys)
    # 若没有检测到有效波谷，则整个信号视为一段
    if len(valid_valleys) == 0:
        valley_indices = np.arange(len(y))
    else:
        if valid_valleys[0] != 0:
            valid_valleys = np.r_[0, valid_valleys]
        if valid_valleys[-1] != len(y) - 1:
            valid_valleys = np.r_[valid_valleys, len(y) - 1]
        valley_indices = valid_valleys

    segments = []
    for i in range(len(valley_indices) - 1):
        idx = np.arange(valley_indices[i], valley_indices[i + 1] + 1)
        segments.append({
            "indices": idx,
            "x": x[idx],
            "y": y[idx]
        })
    return segments


def linear_correct_segment(x_seg, y_seg):
    """
    对单个波（从一个波谷到下一个波谷）的数据，采用两端点构造线性基线，
    然后扣除该基线进行修正，使得左右端点均归零，消除线性外界干扰。
    """
    if len(x_seg) < 2:
        return y_seg  # 若数据太少则直接返回
    baseline = y_seg[0] + (y_seg[-1] - y_seg[0]) * (x_seg - x_seg[0]) / (x_seg[-1] - x_seg[0])
    return y_seg - baseline


def linear_baseline_correction(x, y):
    """
    先调用 segment_by_valleys 将信号分割成各波段，
    对每个波段调用 linear_correct_segment 进行线性基线修正，
    得到修正后的完整信号，并返回各段信息以便后续波峰提取。
    """
    segments = segment_by_valleys(x, y)
    y_corr = np.empty_like(y)
    for seg in segments:
        idx = seg["indices"]
        x_seg = seg["x"]
        y_seg = seg["y"]
        y_corr[idx] = linear_correct_segment(x_seg, y_seg)
    return y_corr, segments


def get_accepted_peaks(segments, x, y1_corr, min_length=MIN_PEAK_LENGTH):
    """
    根据分段信息从 y1_corr 中提取波峰数据，
    删除每个波段的首尾（假定为波谷），
    仅输出长度大于等于 min_length 的峰。
    返回一个列表，每个字典包含：
         "peak_no": 波峰编号，
         "x": 此波峰中点所在的 x 坐标，
         "y": 此波峰中点所在的 y1_corr 坐标，
         "indices": 该波峰的所有数据点索引。
    """
    accepted_peaks = []
    peak_no = 0
    for seg in segments:
        idx = seg["indices"]
        if len(idx) <= 2:
            continue
        # 去除左右波谷
        peak_idx = idx[1:-1]
        if len(peak_idx) < min_length:
            continue
        peak_no += 1
        mid_index = peak_idx[len(peak_idx) // 2]
        accepted_peaks.append({
            "peak_no": peak_no,
            "x": x[mid_index],
            "y": y1_corr[mid_index],
            "indices": peak_idx  # 保存该波峰的全部数据点索引
        })
    return accepted_peaks


def save_graph(original_path, x, y1, y2, y1_corr, y2_corr, accepted_peaks=None):
    """
    在原数据目录下建立 graph 文件夹，
    保存一张图像（展示修正前和修正后 y1 与 y2 曲线），
    在图像上标注每个输出峰的编号（基于 y1_corr 的中点位置），
    同时保存修正后的数据到文本文件中，表头格式修改为：
         第一行：列名称（Time, y1_corr, y2_corr）
         第二行：单位（s, Ω, Ω）
    图像文件命名为：<原文件名>_compare.png，
    数据文件命名为：<原文件名>_corrected.txt。
    """
    file_dir = os.path.dirname(original_path)
    output_folder = os.path.join(file_dir, "graph")
    os.makedirs(output_folder, exist_ok=True)
    base_name = os.path.basename(original_path)

    plt.figure(figsize=(12, 10))
    ax1 = plt.subplot(2, 1, 1)
    plt.plot(x, y1, label="原始 y1", alpha=0.5)
    plt.plot(x, y1_corr, label="修正后 y1", linewidth=2)
    plt.xlabel("Time(s)")
    plt.ylabel("y1")
    plt.legend()

    # 在第一子图上标注输出峰编号
    if accepted_peaks is not None:
        for peak in accepted_peaks:
            ann_x = peak["x"]
            ann_y = peak["y"]
            peak_no = peak["peak_no"]
            ax1.text(ann_x, ann_y + 0.2, f"{peak_no}", color="red", fontsize=12, fontweight="bold")

    ax2 = plt.subplot(2, 1, 2)
    plt.plot(x, y2, label="原始 y2", alpha=0.5)
    plt.plot(x, y2_corr, label="修正后 y2", linewidth=2)
    plt.xlabel("Time(s)")
    plt.ylabel("y2")
    plt.legend()

    plt.suptitle(base_name)
    plt.tight_layout()
    image_path = os.path.join(output_folder, base_name + "_compare.png")
    plt.savefig(image_path)
    plt.close()

    # 输出修正后的数据，表头增加第二行表示单位
    data_path = os.path.join(output_folder, base_name + "_corrected.txt")
    processed_data = np.column_stack((x, y1_corr, y2_corr))
    header = "Time\ty1_corr\ty2_corr\ns\tΩ\tΩ"
    np.savetxt(data_path, processed_data, delimiter="\t", header=header, comments="")
    print(f"已保存图像至: {image_path}")
    print(f"已保存修正数据至: {data_path}")


def extract_peaks(original_path, x, y1_corr, y2_corr, accepted_peaks):
    """
    在原数据目录下建立 result 文件夹，
    针对每个输出的波峰（accepted_peaks），将该波峰的全部数据（去除首尾波谷）保存到单独文件中，
    文件命名格式为：<原文件全名>-<波峰编号>.txt，
    保存内容为：Time, y1_corr, y2_corr，其中表头第二行为单位。
    """
    file_dir = os.path.dirname(original_path)
    result_folder = os.path.join(file_dir, "result")
    os.makedirs(result_folder, exist_ok=True)
    base_name = os.path.basename(original_path)

    for peak in accepted_peaks:
        peak_no = peak["peak_no"]
        indices = peak["indices"]
        peak_data = np.column_stack((x[indices], y1_corr[indices], y2_corr[indices]))
        header = "Time\ty1_corr\ty2_corr\ns\tΩ\tΩ"
        peak_file = os.path.join(result_folder, f"{base_name}-{peak_no}.txt")
        np.savetxt(peak_file, peak_data, delimiter="\t", header=header, comments="")
        print(f"已保存波峰数据至: {peak_file}")


def main():
    root = tk.Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory(title="请选择包含数据文件的文件夹")
    if not folder_path:
        print("未选择文件夹，程序退出。")
        return

    # 不再过滤后缀，尝试处理所有文件
    files = [os.path.join(folder_path, fname) for fname in os.listdir(folder_path)
             if os.path.isfile(os.path.join(folder_path, fname))]
    if not files:
        print("在选择的文件夹中没有找到文件！")
        return

    for file_path in files:
        print(f"正在处理：{file_path}")
        try:
            x, y1, y2 = load_data(file_path)
        except Exception as e:
            print(f"读取文件 {file_path} 时出错，跳过该文件。错误信息：{e}")
            continue

        try:
            y1_corr, segments_y1 = linear_baseline_correction(x, y1)
            y2_corr, segments_y2 = linear_baseline_correction(x, y2)
        except Exception as e:
            print(f"处理文件 {file_path} 时出错（基线修正），跳过该文件。错误信息：{e}")
            continue

        try:
            # 提取满足长度要求的输出峰（基于 y1 分段，通常 y1 与 y2 同步采样）
            accepted_peaks = get_accepted_peaks(segments_y1, x, y1_corr, min_length=MIN_PEAK_LENGTH)
            # 保存比较图像和修正后的数据，在图像中标注每个输出峰的编号
            save_graph(file_path, x, y1, y2, y1_corr, y2_corr, accepted_peaks)
            # 保存波峰数据到 result 文件夹
            extract_peaks(file_path, x, y1_corr, y2_corr, accepted_peaks)
        except Exception as e:
            print(f"保存结果时出错（文件 {file_path}），跳过保存过程。错误信息：{e}")
            continue


if __name__ == "__main__":
    main()

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
SMOOTHING_WINDOW = 31    # Savitzky–Golay 滤波窗口长度（必须为奇数）
POLYORDER = 3            # 多项式阶数

# 波谷检测参数（用于分段）
# VALLEY_PROMINENCE 表示百分比阈值，
# 如设置成 0.5 表示候选波谷相对于其左右局部峰值中较小者下降至少 50% 才认为显著
VALLEY_PROMINENCE = 0.5
VALLEY_DISTANCE = None    # 可设置采样点数的最小距离
# ----------------------------------------------------------

# 设置 Matplotlib 中文字体和避免负号显示问题
mpl.rcParams['font.sans-serif'] = ['SimHei']
mpl.rcParams['axes.unicode_minus'] = False


def load_data(filename):
    """
    逐行读取数据文件，跳过无法转换为数值的行（例如含说明文字的行）。
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
    对信号采用平滑处理后，在负信号中寻找候选波谷，通过显著性筛选分段。
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
        rel_drop = (ref_value - y_smooth[v]) / ref_value
        if rel_drop >= valley_prominence:
            valid_valleys.append(v)
    valid_valleys = np.array(valid_valleys)
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


def correct_segment_by_valley(y_seg):
    """
    分段两步扣除基线后，返回最终数据、基线信息和振幅：
      1. 第一阶段：以该段最小值作为原始基线扣除，使该段最低归 0。
      2. 第二阶段：在第一次扣除结果中，筛选出所有小于 0.1 的数值，
         计算中位数作为二次基线扣除，使波谷部分归 0。
    """
    original_baseline = np.min(y_seg)
    y_corr_stage1 = y_seg - original_baseline
    candidates = y_corr_stage1[y_corr_stage1 < 0.1]
    secondary_baseline = np.median(candidates) if len(candidates) > 0 else 0
    y_corr_final = y_corr_stage1 - secondary_baseline
    amplitude = np.max(y_corr_final) - np.min(y_corr_final)
    return y_corr_final, (original_baseline, secondary_baseline), amplitude


def baseline_correction_by_valleys(x, y, smoothing_window=SMOOTHING_WINDOW, polyorder=POLYORDER):
    """
    先调用 segment_by_valleys 将信号分割成各个波周期，
    然后对每个分段调用 correct_segment_by_valley 进行两步基线扣除，
    得到最终扣除后的完整信号、各周期分段信息、基线信息及振幅变化量。
    返回：
      - y_corrected：扣除基线后的完整信号（与 x 长度一致）
      - segments：分段信息列表
      - baselines：各周期 (原始基线, 二次基线) 列表
      - amplitudes：各周期振幅变化量列表
    """
    segments = segment_by_valleys(x, y, smoothing_window, polyorder, VALLEY_PROMINENCE, VALLEY_DISTANCE)
    y_corrected = np.empty_like(y)
    baselines = []
    amplitudes = []
    for seg in segments:
        idx = seg["indices"]
        y_seg = seg["y"]
        y_corr, bl_tuple, amp = correct_segment_by_valley(y_seg)
        y_corrected[idx] = y_corr
        baselines.append(bl_tuple)
        amplitudes.append(amp)
    return y_corrected, segments, baselines, amplitudes


def get_valid_files(folder_path):
    """
    遍历指定文件夹中的所有文件，返回满足以下条件的文件完整路径列表：
      - 后缀为 ".txt"（忽略大小写）或无后缀，或后缀（不计点）的长度超过 5 个字符。
    """
    valid_files = []
    for filename in os.listdir(folder_path):
        full_path = os.path.join(folder_path, filename)
        if os.path.isfile(full_path):
            root, ext = os.path.splitext(filename)
            if ext.lower() == ".txt" or ext == "" or (len(ext) - 1 > 5):
                valid_files.append(full_path)
    return valid_files


def annotate_plot(ax, segments, amplitudes, threshold=0.2):
    """
    在图中标注振幅和重新编号后的波段编号。
    先筛选出振幅大于或等于 threshold 的波段，然后依次重新编号并标注。
    """
    # 筛选
    filtered = [(seg, amp) for seg, amp in zip(segments, amplitudes) if amp >= threshold]
    for j, (seg, amp) in enumerate(filtered):
        new_idx = j + 1
        mid_x = seg["x"][len(seg["x"]) // 2]
        max_y = np.max(seg["y"])
        ax.text(mid_x, max_y + 0.2, f"{new_idx}: {amp:.2f}", color="red")


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

        # 针对 y1 和 y2 信号，进行分段和两步基线扣除
        y1_corr, segs1, bases1, amps1 = baseline_correction_by_valleys(x, y1)
        y2_corr, segs2, bases2, amps2 = baseline_correction_by_valleys(x, y2)

        print(f"文件 {os.path.basename(file_path)}:")
        print("  y1 每个波的振幅变化量：")
        for i, amp in enumerate(amps1):
            print(f"    波 {i + 1}: {amp:.4f}")
        print("  y2 每个波的振幅变化量：")
        for i, amp in enumerate(amps2):
            print(f"    波 {i + 1}: {amp:.4f}")

        # 在原文件所在目录下建立“基线修正”文件夹
        file_dir = os.path.dirname(file_path)
        output_folder = os.path.join(file_dir, "基线修正")
        os.makedirs(output_folder, exist_ok=True)

        original_name = os.path.basename(file_path)
        base_name = original_name[:-4] if original_name.lower().endswith(".txt") else original_name

        # 保存处理后的数据文件（Time(s), dR1(Ω), dR2(Ω)）
        data_output_path = os.path.join(output_folder, base_name + ".txt")
        processed_data = np.column_stack((x, y1_corr, y2_corr))
        header = "Time(s)\tdR1(Ω)\tdR2(Ω)"
        np.savetxt(data_output_path, processed_data, delimiter="\t", header=header, comments="")
        print(f"已保存处理数据至: {data_output_path}")

        # 生成 dR-fit 数据 —— 筛选振幅 >= 0.2 的波段，并重新编号
        dR1_filtered = [(j + 1, amp) for j, amp in enumerate(amp for amp in amps1 if amp >= 0.2)]
        dR2_filtered = [(j + 1, amp) for j, amp in enumerate(amp for amp in amps2 if amp >= 0.2)]
        dR_fit_path = os.path.join(output_folder, f"{base_name}-dR-fit.txt")
        with open(dR_fit_path, "w", encoding="utf-8") as f:
            f.write("X1\tdR1(Ω)\tX2\tdR2(Ω)\n")
            max_len = max(len(dR1_filtered), len(dR2_filtered))
            for i in range(max_len):
                # 如果某一列没有数据，写入空字符串
                x1_val, dr1_val = dR1_filtered[i] if i < len(dR1_filtered) else ("", "")
                x2_val, dr2_val = dR2_filtered[i] if i < len(dR2_filtered) else ("", "")
                f.write(f"{x1_val}\t{dr1_val}\t{x2_val}\t{dr2_val}\n")
        print(f"已保存 dR-fit 文件至: {dR_fit_path}")

        # 绘制图形（带标注版本）
        plt.figure(figsize=(12, 10))
        # y1 部分
        ax1 = plt.subplot(2, 1, 1)
        plt.plot(x, y1, label="原始 y1", alpha=0.5)
        plt.plot(x, y1_corr, label="扣除基线后 y1", linewidth=2)
        for seg in segs1:
            plt.axvline(x=seg["x"][0], color="gray", linestyle="--", alpha=0.5)
            plt.axvline(x=seg["x"][-1], color="gray", linestyle="--", alpha=0.5)
        annotate_plot(ax1, segs1, amps1, threshold=0.2)
        plt.xlabel("x")
        plt.ylabel("y1")
        plt.title(f"{os.path.basename(file_path)} - y1 扣除基线（带标注）")
        plt.legend()

        ax2 = plt.subplot(2, 1, 2)
        plt.plot(x, y2, label="原始 y2", alpha=0.5)
        plt.plot(x, y2_corr, label="扣除基线后 y2", linewidth=2)
        for seg in segs2:
            plt.axvline(x=seg["x"][0], color="gray", linestyle="--", alpha=0.5)
            plt.axvline(x=seg["x"][-1], color="gray", linestyle="--", alpha=0.5)
        annotate_plot(ax2, segs2, amps2, threshold=0.2)
        plt.xlabel("x")
        plt.ylabel("y2")
        plt.title(f"{os.path.basename(file_path)} - y2 扣除基线（带标注）")
        plt.legend()
        plt.tight_layout()

        image_output_path_annot = os.path.join(output_folder, base_name + "-annotated.png")
        plt.savefig(image_output_path_annot)
        print(f"已保存带标注图形至: {image_output_path_annot}")
        plt.close()

        # 绘制图形（无标注版本）
        plt.figure(figsize=(12, 10))
        plt.subplot(2, 1, 1)
        plt.plot(x, y1, label="原始 y1", alpha=0.5)
        plt.plot(x, y1_corr, label="扣除基线后 y1", linewidth=2)
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
        image_output_path_no_annot = os.path.join(output_folder, base_name + "-no-annotation.png")
        plt.savefig(image_output_path_no_annot)
        print(f"已保存无标注图形至: {image_output_path_no_annot}")
        plt.close()


if __name__ == "__main__":
    main()

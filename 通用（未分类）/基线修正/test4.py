#!/usr/bin/env python3
import os
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog
import matplotlib as mpl

# ---------------------- 可配置参数 ----------------------
PEAK_THRESHOLD = 1.0         # 波峰阈值：第一次基线修正后，数值 ≥ 此值为波峰状态
MIN_PEAK_LENGTH = 5          # 连续满足波峰条件的采样点最少个数
VALLEY_THRESHOLD = 1.0       # 波谷阈值：扩展边界时，当数据小于此值视为波谷区域
AMPLITUDE_THRESHOLD = 0.2    # 振幅低于此值的波峰不参与后续编号与记录
STABILITY_TOLERANCE = 0.1    # 稳定性容限：在波峰区域中允许的最大波动值，用于判断平稳子区段
# ----------------------------------------------------------

mpl.rcParams["font.sans-serif"] = ["SimHei"]
mpl.rcParams["axes.unicode_minus"] = False


def load_data(filename):
    """
    逐行读取数据文件，跳过非数值行。
    每行取前4个数字，其中第一列为 x，第二列为 y1，第四列为 y2。
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


def segment_by_wave_peaks(x, y, peak_threshold=PEAK_THRESHOLD,
                           min_length=MIN_PEAK_LENGTH, valley_threshold=VALLEY_THRESHOLD):
    """
    1. 进行第一次基线修正：y_stage1 = y - min(y)
    2. 扫描 y_stage1，当检测到连续 ≥ min_length 个数据点且其值 ≥ peak_threshold 时，
       认为这是波峰候选区域。记录该区域的起始与结束点。
    3. 为确保包含两侧波谷，向左右扩展区域，扩展条件为数据 < valley_threshold。
    4. 在生成的分段字典中增加键 "crest_indices"，表示在扩展后的分段中，真正满足连续 ≥ peak_threshold 的那部分数据的相对索引。
    返回：
      segments：列表，每个元素为字典，包含 "indices"（扩展后整体区间全局索引）、"x"、"y"（对应基线修正后数据）、
                "crest_indices"（波峰部分在本分段内的相对索引）。
      y_stage1：第一次基线修正后的信号。
      global_base：全局最小值。
    """
    global_base = np.min(y)
    y_stage1 = y - global_base
    segments = []
    i = 0
    N = len(y_stage1)
    while i < N:
        if y_stage1[i] >= peak_threshold:
            start_peak = i
            # 连续满足的区域
            while i < N and y_stage1[i] >= peak_threshold:
                i += 1
            end_peak = i - 1
            if end_peak - start_peak + 1 >= min_length:
                # 向左扩展
                left = start_peak
                while left > 0 and y_stage1[left - 1] < valley_threshold:
                    left -= 1
                # 向右扩展
                right = end_peak
                while right < N - 1 and y_stage1[right + 1] < valley_threshold:
                    right += 1
                indices = np.arange(left, right + 1)
                # 计算波峰区域在扩展后区间中对应的相对索引
                crest_start = start_peak - left
                crest_end = end_peak - left
                crest_indices = np.arange(crest_start, crest_end + 1)
                segments.append({
                    "indices": indices,
                    "x": x[left:right + 1],
                    "y": y_stage1[left:right + 1],
                    "crest_indices": crest_indices
                })
        else:
            i += 1
    return segments, y_stage1, global_base


def find_largest_stable_subsegment(arr, tolerance):
    """
    在数组 arr（波峰区域数据）中寻找最长稳定连续子区段，
    定义稳定为该子区段内最大值与最小值之差不超过 tolerance。
    返回该子区段数组；若找不到，则返回 None。
    """
    best_start = 0
    best_end = -1
    best_length = 0
    n = len(arr)
    for i in range(n):
        current_min = arr[i]
        current_max = arr[i]
        for j in range(i, n):
            current_min = min(current_min, arr[j])
            current_max = max(current_max, arr[j])
            if current_max - current_min > tolerance:
                break
            if (j - i + 1) > best_length:
                best_length = j - i + 1
                best_start = i
                best_end = j
    if best_length == 0:
        return None
    return arr[best_start:best_end+1]


def correct_segment_by_peaks(seg, valley_threshold=VALLEY_THRESHOLD,
                               stability_tolerance=STABILITY_TOLERANCE):
    """
    对单个分段执行二次基线扣除：
      1. 从分段信号 seg["y"] 中提取两侧连续低于 valley_threshold 的数据（即波谷部分），
         合并后计算中位数作为二次基线。
      2. 扣除该二次基线得到修正信号。
      3. 在修正后的信号中，仅取波峰区域数据（利用 seg["crest_indices"] 提取），
         在该区域中寻找最长稳定子区段（即波动范围在 tolerance 内的最长连续子序列）。
         若找到，则以该子区段数据的平均值作为振幅；否则以整个波峰区域数据平均值作为振幅。
    返回：
      corrected：二次扣除后的分段信号（数组）。
      valley_median：二次基线值。
      amplitude：该分段波峰区域的振幅值（稳定子区段平均值或整个区域平均值）。
    """
    y_seg = seg["y"]
    # 提取左右波谷数据
    left_vals = []
    i = 0
    while i < len(y_seg) and y_seg[i] < valley_threshold:
        left_vals.append(y_seg[i])
        i += 1
    right_vals = []
    i = len(y_seg) - 1
    while i >= 0 and y_seg[i] < valley_threshold:
        right_vals.append(y_seg[i])
        i -= 1
    valley_data = left_vals + right_vals
    if len(valley_data) > 0:
        valley_median = np.median(valley_data)
    else:
        valley_median = 0
    corrected = y_seg - valley_median
    # 取波峰区域数据
    crest_values = corrected[seg["crest_indices"]]
    stable_region = find_largest_stable_subsegment(crest_values, stability_tolerance)
    if stable_region is not None and len(stable_region) > 0:
        amplitude = np.mean(stable_region)
    else:
        amplitude = np.mean(crest_values)
    return corrected, valley_median, amplitude


def process_channel(x, y, peak_threshold=PEAK_THRESHOLD,
                    min_length=MIN_PEAK_LENGTH, valley_threshold=VALLEY_THRESHOLD,
                    stability_tolerance=STABILITY_TOLERANCE):
    """
    对单个信号通道进行处理：
      1. 调用 segment_by_wave_peaks 得到第一次基线修正后的信号 y_stage1、分段列表及全局最小值。
      2. 对每个分段调用 correct_segment_by_peaks，得到二次扣除后的结果，
         并更新对应区域，记录每个波峰区域的振幅（基于最大稳定子区段平均值）。
    返回：
      y_corrected：整个信号的更新结果（基于第一次基线修正经过二次扣除）。
      segments：分段列表。
      amplitudes：各分段振幅值。
      global_base：全局最小值。
    """
    segments, y_stage1, global_base = segment_by_wave_peaks(x, y, peak_threshold, min_length, valley_threshold)
    y_corrected = np.copy(y_stage1)
    amplitudes = []
    for seg in segments:
        corrected, valley_median, amp = correct_segment_by_peaks(seg, valley_threshold, stability_tolerance)
        amplitudes.append(amp)
        y_corrected[seg["indices"]] = corrected
    return y_corrected, segments, amplitudes, global_base


def get_valid_files(folder_path):
    """
    遍历指定文件夹中的文件，返回满足条件（后缀为 ".txt" 或无后缀，或后缀长度超过 5 个字符）的完整路径列表。
    """
    valid_files = []
    for filename in os.listdir(folder_path):
        full_path = os.path.join(folder_path, filename)
        if os.path.isfile(full_path):
            root, ext = os.path.splitext(filename)
            if ext.lower() == ".txt" or ext == "" or (len(ext) - 1 > 5):
                valid_files.append(full_path)
    return valid_files


def annotate_plot(ax, segments, amplitudes, threshold=AMPLITUDE_THRESHOLD):
    """
    在图中标注满足振幅 ≥ threshold 的波峰区域：
      对于每个符合条件的分段，
      用红色水平线绘制波峰区域（即 seg["crest_indices"] 对应的 x 区间）的边界，
      水平线的 y 值即为计算出的振幅值，同时在水平线中点标注 "编号: 振幅"（例如 "1: 3.45"）。
    """
    filtered = [(seg, amp) for seg, amp in zip(segments, amplitudes) if amp >= threshold]
    for j, (seg, amp) in enumerate(filtered):
        new_idx = j + 1
        # 取波峰区域在该分段内的 x 坐标
        crest_indices = seg["crest_indices"]
        crest_left_x = seg["x"][crest_indices[0]]
        crest_right_x = seg["x"][crest_indices[-1]]
        # 在波峰区域上绘制红色水平线
        ax.hlines(y=amp, xmin=crest_left_x, xmax=crest_right_x, color="red", linestyles="-", linewidth=2)
        # 标注文本放置在水平线中点上方
        mid_x = (crest_left_x + crest_right_x) / 2
        ax.text(mid_x, amp + 0.2, f"{new_idx}: {amp:.2f}", color="red", ha="center")


def main():
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

        # 分别处理 y1 与 y2
        y1_corr, segs1, amps1, base1 = process_channel(x, y1)
        y2_corr, segs2, amps2, base2 = process_channel(x, y2)

        print(f"文件 {os.path.basename(file_path)}:")
        print("  y1 每个波的振幅（取最大平稳子区段平均）:")
        for i, amp in enumerate(amps1):
            print(f"    波 {i+1}: {amp:.4f}")
        print("  y2 每个波的振幅（取最大平稳子区段平均）:")
        for i, amp in enumerate(amps2):
            print(f"    波 {i+1}: {amp:.4f}")

        file_dir = os.path.dirname(file_path)
        # “基线修正”文件夹保存处理后数据和无标注图像
        output_folder = os.path.join(file_dir, "基线修正")
        os.makedirs(output_folder, exist_ok=True)
        # “dR-fit”文件夹保存 dR-fit 文件和带标注图（与基线修正同级）
        dR_fit_folder = os.path.join(file_dir, "dR-fit")
        os.makedirs(dR_fit_folder, exist_ok=True)

        original_name = os.path.basename(file_path)
        base_name = original_name[:-4] if original_name.lower().endswith(".txt") else original_name

        # 保存处理后的数据文件
        data_output_path = os.path.join(output_folder, base_name + ".txt")
        processed_data = np.column_stack((x, y1_corr, y2_corr))
        header = "Time(s)\tdR1(Ω)\tdR2(Ω)"
        np.savetxt(data_output_path, processed_data, delimiter="\t", header=header, comments="")
        print(f"已保存处理数据至: {data_output_path}")

        # 生成 dR-fit 文件 —— 对振幅 ≥ AMPLITUDE_THRESHOLD 的波峰重新编号
        dR1_filtered = [(j + 1, amp) for j, amp in enumerate(amp for amp in amps1 if amp >= AMPLITUDE_THRESHOLD)]
        dR2_filtered = [(j + 1, amp) for j, amp in enumerate(amp for amp in amps2 if amp >= AMPLITUDE_THRESHOLD)]
        dR_fit_path = os.path.join(dR_fit_folder, f"{base_name}-dR-fit.txt")
        with open(dR_fit_path, "w", encoding="utf-8") as f:
            f.write("X1\tdR1(Ω)\tX2\tdR2(Ω)\n")
            max_len = max(len(dR1_filtered), len(dR2_filtered))
            for i in range(max_len):
                x1_val, dr1_val = dR1_filtered[i] if i < len(dR1_filtered) else ("", "")
                x2_val, dr2_val = dR2_filtered[i] if i < len(dR2_filtered) else ("", "")
                f.write(f"{x1_val}\t{dr1_val}\t{x2_val}\t{dr2_val}\n")
        print(f"已保存 dR-fit 文件至: {dR_fit_path}")

        # 绘制带标注图（保存到 dR-fit 文件夹）
        plt.figure(figsize=(12, 10))
        # y1 部分
        ax1 = plt.subplot(2, 1, 1)
        plt.plot(x, y1, label="原始 y1", alpha=0.5)
        plt.plot(x, y1_corr, label="扣除基线后 y1", linewidth=2)
        for seg in segs1:
            plt.axvline(x=seg["x"][0], color="gray", linestyle="--", alpha=0.5)
            plt.axvline(x=seg["x"][-1], color="gray", linestyle="--", alpha=0.5)
        annotate_plot(ax1, segs1, amps1)
        plt.xlabel("x")
        plt.ylabel("y1")
        plt.title(f"{os.path.basename(file_path)} - y1 扣除基线（带标注）")
        plt.legend()
        # y2 部分
        ax2 = plt.subplot(2, 1, 2)
        plt.plot(x, y2, label="原始 y2", alpha=0.5)
        plt.plot(x, y2_corr, label="扣除基线后 y2", linewidth=2)
        for seg in segs2:
            plt.axvline(x=seg["x"][0], color="gray", linestyle="--", alpha=0.5)
            plt.axvline(x=seg["x"][-1], color="gray", linestyle="--", alpha=0.5)
        annotate_plot(ax2, segs2, amps2)
        plt.xlabel("x")
        plt.ylabel("y2")
        plt.title(f"{os.path.basename(file_path)} - y2 扣除基线（带标注）")
        plt.legend()
        plt.tight_layout()
        image_output_path_annot = os.path.join(dR_fit_folder, base_name + "-annotated.png")
        plt.savefig(image_output_path_annot)
        print(f"已保存带标注图形至: {image_output_path_annot}")
        plt.close()

        # 绘制无标注图（保存至“基线修正”文件夹）
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

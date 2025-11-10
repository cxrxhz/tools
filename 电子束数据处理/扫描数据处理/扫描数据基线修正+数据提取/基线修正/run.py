#!/usr/bin/env python3
import os
import numpy as np
import tkinter as tk
from tkinter import filedialog
import matplotlib as mpl

mpl.rcParams['font.sans-serif'] = ['SimHei']  # 使用 SimHei 显示中文
mpl.rcParams['axes.unicode_minus'] = False    # 正常显示负号


# ---------------------- 可配置参数 ----------------------
SMOOTHING_WINDOW = 21  # Savitzky–Golay 滤波窗口长度（必须为奇数）
POLYORDER = 3  # 多项式阶数
VALLEY_PROMINENCE = 0.2  # 波谷显著性阈值
VALLEY_DISTANCE = None  # 波谷最小间隔采样点数
MIN_PEAK_LENGTH = 50  # 输出波峰的最小数据点数阈值


# ----------------------------------------------------------

def load_data(filename):
    """
    逐行读取数据文件，跳过无法转换为数值的行（例如含说明文字的行）。
    每行取前 4 个数字，其中：
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
    返回的 segments 是个列表，每个元素为字典，包含 "indices"、"x" 与 "y" 数据。
    """
    from scipy.signal import savgol_filter, find_peaks
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
    对单个波段数据（从一个波谷到下一个波谷）进行两步基线扣除：

    第一步：粗略归零 —— 直接以该段的最小值作为基线扣除，
           使得该段信号的最低点归零。

    第二步：线性修正 —— 利用粗略归零后信号的首尾两点构造直线基线，
           再从粗略归零后的信号中扣除该直线，保证该段两端均归零。

    参数：
       x_seg: 该波段内对应的 x 值（numpy 数组）。
       y_seg: 该波段内的原始 y 值（numpy 数组）。

    返回：
       扣除了基线后的信号（numpy 数组）。
    """
    # 第一步：粗略归零，扣除该波段最小值
    rough = y_seg - np.min(y_seg)

    # 如果数据点不足，直接返回粗略归零结果
    if len(x_seg) < 2:
        return rough

    # 第二步：线性修正——利用粗略归零后的首尾数据构造直线基线
    baseline = rough[0] + (rough[-1] - rough[0]) * (x_seg - x_seg[0]) / (x_seg[-1] - x_seg[0])
    corrected = rough - baseline
    return corrected


def linear_baseline_correction(x, y):
    """
    对信号进行分段，每个段内采用线性基线修正，返回修正后的完整信号和各段信息。
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
    根据分段信息提取波峰数据：
      - 对每个分段先去掉首尾（假定为波谷），
      - 若剩余数据点数不少于 min_length，则视为有效波峰，
      - 返回的列表中每个元素为字典，包含波峰编号、该波峰中点的 x、y 值及该波峰数据点索引。
    """
    accepted_peaks = []
    peak_no = 0
    for seg in segments:
        idx = seg["indices"]
        if len(idx) <= 2:
            continue
        # 删除分段首尾（波谷）后的数据点
        peak_idx = idx[1:-1]
        if len(peak_idx) < min_length:
            continue
        peak_no += 1
        mid_index = peak_idx[len(peak_idx) // 2]
        accepted_peaks.append({
            "peak_no": peak_no,
            "x": x[mid_index],
            "y": y1_corr[mid_index],
            "indices": peak_idx
        })
    return accepted_peaks


def save_graph(file_path, x, y1, y2, y1_corr, y2_corr, accepted_peaks):
    """
    绘制图像并保存：
      - 上图显示 y1（原始与修正后），并在修正后曲线上标注输出峰编号；
      - 下图显示 y2（原始与修正后）。
    同时保存修正后的数据。
    输出到与每个数据文件同级的 “graph” 文件夹，图像命名为 [原文件名]_compare.png，
    修正数据命名为 [原文件名]_corrected.txt。
    """
    import matplotlib.pyplot as plt
    file_dir = os.path.dirname(file_path)
    output_folder = os.path.join(file_dir, "graph")
    os.makedirs(output_folder, exist_ok=True)
    base_name = os.path.basename(file_path)

    plt.figure(figsize=(12, 10))
    ax1 = plt.subplot(2, 1, 1)
    plt.plot(x, y1, label="原始 y1", alpha=0.5)
    plt.plot(x, y1_corr, label="修正后 y1", linewidth=2)
    plt.xlabel("Time(s)")
    plt.ylabel("y1")
    plt.legend()
    if accepted_peaks:
        for peak in accepted_peaks:
            ax1.text(peak["x"], peak["y"] + 0.2, f"{peak['peak_no']}",
                     color="red", fontsize=12, fontweight="bold")
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

    # 保存修正后的数据，列为 Time, y1_corr, y2_corr，单位分别为 s, Ω, Ω
    data_path = os.path.join(output_folder, base_name + "_corrected.txt")
    processed_data = np.column_stack((x, y1_corr, y2_corr))
    header = "Time\ty1_corr\ty2_corr\ns\tΩ\tΩ"
    np.savetxt(data_path, processed_data, delimiter="\t", header=header, comments="")
    print("已保存图像至:", image_path)
    print("已保存修正数据至:", data_path)


def extract_peaks(file_path, x, y1_corr, y2_corr, accepted_peaks):
    """
    保存每个有效波峰数据到单独的文本文件。
    输出文件命名规则： [原文件名（含扩展名）]-[波峰编号].txt
    文件内容包含列： Time, y1_corr, y2_corr（单位：s, Ω, Ω）
    输出到与数据文件同级的 “result” 文件夹中。
    """
    file_dir = os.path.dirname(file_path)
    result_folder = os.path.join(file_dir, "result")
    os.makedirs(result_folder, exist_ok=True)

    # **保留原始文件名的扩展名**
    base_name = os.path.basename(file_path)  # 直接获取完整文件名（含扩展名）

    for peak in accepted_peaks:
        peak_no = peak["peak_no"]
        indices = peak["indices"]
        peak_data = np.column_stack((x[indices], y1_corr[indices], y2_corr[indices]))
        header = "Time\ty1_corr\ty2_corr\ns\tΩ\tΩ"

        # **修改输出文件命名格式：保留扩展名**
        peak_file = os.path.join(result_folder, f"{base_name}-{peak_no}.txt")

        np.savetxt(peak_file, peak_data, delimiter="\t", header=header, comments="")
        print("已保存波峰数据至:", peak_file)


def main():
    root = tk.Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory(title="请选择包含数据文件的文件夹")
    if not folder_path:
        print("未选择文件夹，程序退出。")
        return

    # 获取该文件夹下所有文件（不区分后缀）
    files = [os.path.join(folder_path, fname) for fname in os.listdir(folder_path)
             if os.path.isfile(os.path.join(folder_path, fname))]
    if not files:
        print("在选择的文件夹中没有找到文件！")
        return

    for file_path in files:
        print("正在处理：", file_path)
        try:
            x, y1, y2 = load_data(file_path)
        except Exception as e:
            print("读取文件", file_path, "时出错，跳过。错误信息:", e)
            continue

        try:
            y1_corr, segments_y1 = linear_baseline_correction(x, y1)
            y2_corr, segments_y2 = linear_baseline_correction(x, y2)
        except Exception as e:
            print("处理文件", file_path, "时出错（基线修正），跳过。错误信息:", e)
            continue

        try:
            accepted_peaks = get_accepted_peaks(segments_y1, x, y1_corr, min_length=MIN_PEAK_LENGTH)
            save_graph(file_path, x, y1, y2, y1_corr, y2_corr, accepted_peaks)
            extract_peaks(file_path, x, y1_corr, y2_corr, accepted_peaks)
        except Exception as e:
            print("保存结果时出错（文件", file_path, "），跳过。错误信息:", e)
            continue

    # 在所有文件处理完成后，单独输出一行标记供总控程序读取
    final_result_folder = os.path.join(folder_path, "result")
    print("RESULT_FOLDER:" + final_result_folder, flush=True)


if __name__ == "__main__":
    main()

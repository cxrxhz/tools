#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
说明：
  此脚本专为单份数据文件的临时处理设计，运行时弹出窗口选择文件。
  处理流程如下：

    1. 读取文件中所有数值数据行（每行至少含有5个数字），全部数据均参与处理。
    2. 手动指定平稳区域：弹出对话框输入一个或多个平稳区段，
       以第一列的 x 值为依据，格式示例："4-10 100-200" 表示 x 值在 4～10 与 100～200 的数据均为平稳区域。
    3. 对各平稳区域，舍弃该区域前后20%数据（若数据太少则全部采用），
       合并各区域后的中间部分，用于计算 dR1（第2列）和 dR2（第4列）的均值作为基值。
    4. 对所有数据计算新的 dR1 与 dR2（原值减去基值），并计算比值（dR1/dR2 与 dR2/dR1）。
    5. 输出两个文件（存放于原文件所在目录的 diff 文件夹中）：
         - “*原文件名*-origindiff”：输出所有数据行（保留原始 x 值）；
         - “*原文件名*-data”：过滤掉平稳区域的数据，再过滤相对变化率低于 0.0003 的行，
           对剩余数据重新赋予等距 x 坐标（范围 0～用户输入的扫描长度，单位 µm）。
"""

import os
import tkinter as tk
from tkinter import filedialog, simpledialog
import numpy as np

def parse_stable_intervals(user_input):
    """
    解析用户输入的平稳区段字符串，例如 "4-10 100-200"
    返回一个列表，每个元素为 (lower, upper) 的元组（浮点数）。
    """
    intervals = []
    tokens = user_input.strip().split()
    for token in tokens:
        try:
            parts = token.split('-')
            if len(parts) != 2:
                continue
            lower = float(parts[0])
            upper = float(parts[1])
            if lower > upper:
                lower, upper = upper, lower
            intervals.append((lower, upper))
        except ValueError:
            continue
    return intervals

def in_any_stable_interval(x_val, intervals):
    """
    判断 x_val 是否落在给定的一组区间内
    """
    for (lower, upper) in intervals:
        if lower <= x_val <= upper:
            return True
    return False

def process_file(filepath, rel_threshold=0.0003, scan_length=0.0):
    # ---------------------------- 读取数据 --------------------------------
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    data_list = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        try:
            nums = [float(item) for item in parts]
            if len(nums) >= 5:
                data_list.append(nums[:5])
        except ValueError:
            continue

    if len(data_list) < 1:
        print(f"文件 {filepath} 中没有足够数据，无法处理。")
        return

    data = np.array(data_list)
    n_rows = data.shape[0]
    print(f"共读取 {n_rows} 行数据。")

    # ---------------- 用户指定平稳区域 -------------------------
    root = tk.Tk()
    root.withdraw()
    prompt_msg = (f"当前文件 {os.path.basename(filepath)} 中共有 {n_rows} 行数据。\n"
                  "请以空格分隔输入一个或多个平稳区段，\n"
                  "格式： '起始-结束'（以第一列 x 值为索引），例如：\n"
                  "    4-10 100-200\n"
                  "表示 x 值在 4～10 和 100～200 的数据为平稳区域。")
    user_input = simpledialog.askstring("选择平稳区域", prompt_msg)
    if user_input is None or user_input.strip() == "":
        print("未输入平稳区域，文件处理取消。")
        return

    stable_intervals = parse_stable_intervals(user_input)
    if not stable_intervals:
        print("未解析到有效平稳区段，文件处理取消。")
        return

    print(f"已选择平稳区段：{stable_intervals}")

    # ---------------- 提取平稳区段数据（用于基值计算） ------------------
    stable_segments = []
    for (lower, upper) in stable_intervals:
        mask = (data[:, 0] >= lower) & (data[:, 0] <= upper)
        seg = data[mask]
        if seg.shape[0] > 0:
            stable_segments.append(seg)
        else:
            print(f"警告：区段 {lower}-{upper} 内未找到数据。")
    if not stable_segments:
        print("所选平稳区段内无数据，文件处理取消。")
        return

    # 对每个平稳区段舍弃前后20%，用于计算基值
    mid_stable_list = []
    for seg in stable_segments:
        n_seg = seg.shape[0]
        start_idx = int(n_seg * 0.2)
        end_idx = int(n_seg * 0.8)
        if end_idx <= start_idx:
            mid_seg = seg
        else:
            mid_seg = seg[start_idx:end_idx]
        mid_stable_list.append(mid_seg)
    all_mid_stable = np.concatenate(mid_stable_list, axis=0)
    baseline_dR1 = np.mean(all_mid_stable[:, 1])
    baseline_dR2 = np.mean(all_mid_stable[:, 3])
    print(f"基值计算结果：baseline_dR1 = {baseline_dR1:.6g}，baseline_dR2 = {baseline_dR2:.6g}")

    # ------------------- 计算新变化量及比值 -------------------------------
    delta_dR1 = data[:, 1] - baseline_dR1
    delta_dR2 = data[:, 3] - baseline_dR2

    ratio_dR1_dR2 = np.empty(n_rows)
    ratio_dR2_dR1 = np.empty(n_rows)
    for i in range(n_rows):
        if abs(delta_dR2[i]) > 1e-12:
            ratio_dR1_dR2[i] = delta_dR1[i] / delta_dR2[i]
        else:
            ratio_dR1_dR2[i] = np.nan
        if abs(delta_dR1[i]) > 1e-12:
            ratio_dR2_dR1[i] = delta_dR2[i] / delta_dR1[i]
        else:
            ratio_dR2_dR1[i] = np.nan

    # 构造新数据，第一列仍为原始的 x 值
    new_data = np.column_stack((data[:, 0], delta_dR1, data[:, 2], delta_dR2, data[:, 4],
                                ratio_dR1_dR2, ratio_dR2_dR1))

    # ---------------- 输出 1：“origindiff” 文件 --------------------------
    header_names_origin = ["times", "dR1", "φ1", "dR2", "φ1", "dR1/dR2", "dR2/dR1"]
    header_units_origin = ["none", "Ω", "°", "Ω", "°", "none", "none"]
    header_line1_origin = " ".join(header_names_origin)
    header_line2_origin = " ".join(header_units_origin)

    out_lines_orig = [header_line1_origin, header_line2_origin]
    for row in new_data:
        formatted = " ".join(f"{val:.6g}" if not np.isnan(val) else "nan" for val in row)
        out_lines_orig.append(formatted)
    output_orig = "\n".join(out_lines_orig)

    file_dir = os.path.dirname(filepath)
    diff_dir = os.path.join(file_dir, "diff")
    if not os.path.exists(diff_dir):
        os.makedirs(diff_dir)
    base_name = os.path.basename(filepath)
    outname_orig = f"{base_name}-origindiff"
    outpath_orig = os.path.join(diff_dir, outname_orig)
    with open(outpath_orig, "w", encoding="utf-8") as f_out:
        f_out.write(output_orig)
    print(f"已生成：{outpath_orig}")

    # ---------------- 输出 2：“data” 文件 --------------------------
    # 过滤掉位于任意平稳区段内的行
    candidate_rows = [row for row in new_data if not in_any_stable_interval(row[0], stable_intervals)]
    candidate_rows = np.array(candidate_rows) if candidate_rows else np.empty((0, new_data.shape[1]))
    print(f"非平稳区域候选数据行数: {candidate_rows.shape[0]}")

    # 针对候选数据，过滤掉相对于基值变化率不足 rel_threshold 的行
    filtered_rows = []
    for row in candidate_rows:
        if abs(baseline_dR1) > 1e-12:
            r1 = abs(row[1]) / abs(baseline_dR1)
        else:
            r1 = abs(row[1])
        if abs(baseline_dR2) > 1e-12:
            r2 = abs(row[3]) / abs(baseline_dR2)
        else:
            r2 = abs(row[3])
        if r1 < rel_threshold and r2 < rel_threshold:
            continue
        else:
            filtered_rows.append(row)
    print(f"过滤后有效数据行数: {len(filtered_rows)}")
    if filtered_rows:
        filtered_rows = np.array(filtered_rows)
        n_filtered = filtered_rows.shape[0]
        # 重新赋予 x 坐标为等距数列，从 0 到 scan_length
        new_x = np.linspace(0, scan_length, n_filtered)
        filtered_rows[:, 0] = new_x
    else:
        print("过滤后无有效数据行。")

    header_names_data = ["L", "dR1", "φ1", "dR2", "φ1", "dR1/dR2", "dR2/dR1"]
    header_units_data = ["µm", "Ω", "°", "Ω", "°", "none", "none"]
    header_line1_data = " ".join(header_names_data)
    header_line2_data = " ".join(header_units_data)

    out_lines_data = [header_line1_data, header_line2_data]
    if filtered_rows.size > 0:
        for row in filtered_rows:
            formatted = " ".join(f"{val:.6g}" if not np.isnan(val) else "nan" for val in row)
            out_lines_data.append(formatted)
    output_data = "\n".join(out_lines_data)

    outname_data = f"{base_name}-data"
    outpath_data = os.path.join(diff_dir, outname_data)
    with open(outpath_data, "w", encoding="utf-8") as f_out:
        f_out.write(output_data)
    print(f"已生成：{outpath_data}")

def main():
    # 选择文件对话框
    root = tk.Tk()
    root.withdraw()
    filepath = filedialog.askopenfilename(title="请选择数据文件")
    if not filepath:
        print("未选择文件，程序退出。")
        return

    scan_length = simpledialog.askfloat("扫描长度", "请输入扫描长度（单位 µm）:")
    if scan_length is None:
        print("未输入扫描长度，程序退出。")
        return

    process_file(filepath, rel_threshold=0.0003, scan_length=scan_length)

if __name__ == "__main__":
    main()

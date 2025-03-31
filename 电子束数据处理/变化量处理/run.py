#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
说明：
  本脚本会弹出对话框选择一个目录，目录中应含有多个数据文件（无后缀或后缀超过5字符的文件）。

  对每个文件的处理步骤如下：
    1. 读取文件中所有数值数据行（每行至少含有5个数字），并舍弃前 5 行数据。
    2. 从剩余数据开始，依次比较相邻两行中 dR1（第2列）与 dR2（第4列）的相对变化率，
       当两者均不超过 0.0003 时认为处于平稳区域，否则平稳区域结束。记下平稳区域的结束行索引（包含）。
    3. 在识别到的平稳区域中，舍弃前后20%的数据行（仅用于基值计算），对中间部分分别计算 dR1 与 dR2 的平均值，作为基值。
    4. 对整个数据（舍弃前5行后的所有数据）计算新 dR1 与 dR2（各自 = 原值 – 基值），并计算比值（dR1/dR2 和 dR2/dR1）。
    5. 生成两个输出文件（均保存在源文件所在目录下的 diff 文件夹内）：
         - “*原文件名*-origindiff”：输出所有数据行，表头由两行组成：
               第一行：times  dR1   φ1   dR2   φ1   dR1/dR2   dR2/dR1
               第二行：none   Ω   °   Ω   °   none       none
         - “*原文件名*-data”：先【舍弃平稳区域的所有行】，然后过滤掉剩余数据中相对于基值变化率不足 0.0003 的行（即同时
           dR1 与 dR2 的相对变化率均不足 0.0003 的行）。剩余数据将重新编号 x（即第一列），赋值为等距间隔，
           从 0 开始到用户输入的扫描长度（单位 µm）。表头第一列改为 "x"，单位为 µm，其余列同 origindiff。

  文件过滤规则：
    - 如果文件扩展名存在且字符数（不含点）不超过 5，则视为常规后缀文件，不处理；
      只有无后缀或后缀字符数超过5的文件才处理。
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, simpledialog
import numpy as np

# 重新配置标准输出编码为 utf-8，以避免打印时编码错误
sys.stdout.reconfigure(encoding="utf-8")

def process_file(filepath, skip_lines=5, rel_threshold=0.0003, scan_length=0.0):
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
            # 只解析至少5个数字的行
            nums = [float(p) for p in parts]
            if len(nums) >= 5:
                data_list.append(nums[:5])
        except ValueError:
            continue

    if len(data_list) <= skip_lines:
        print(f"文件 {filepath} 中数据行不足 {skip_lines+1} 行，无法处理。")
        return

    # 舍弃开头的 skip_lines 行数据（只针对成功解析的数值数据行）
    data = np.array(data_list[skip_lines:])
    n_rows = data.shape[0]
    # 数据各列解释（0-indexed）：0 - times, 1 - dR1, 2 - φ1, 3 - dR2, 4 - φ1

    # --------------------- 识别平稳区域 ----------------------------------
    stable_end_index = 0  # 稳定区域最后一行的索引（包含）
    for i in range(1, n_rows):
        prev_dR1 = data[i-1, 1]
        cur_dR1  = data[i, 1]
        if abs(prev_dR1) > 1e-12:
            rel_change_dR1 = abs(cur_dR1 - prev_dR1) / abs(prev_dR1)
        else:
            rel_change_dR1 = abs(cur_dR1 - prev_dR1)

        prev_dR2 = data[i-1, 3]
        cur_dR2  = data[i, 3]
        if abs(prev_dR2) > 1e-12:
            rel_change_dR2 = abs(cur_dR2 - prev_dR2) / abs(prev_dR2)
        else:
            rel_change_dR2 = abs(cur_dR2 - prev_dR2)

        if rel_change_dR1 <= rel_threshold and rel_change_dR2 <= rel_threshold:
            stable_end_index = i
        else:
            break

    if stable_end_index < 1:
        print(f"文件 {filepath} 未能识别出足够的平稳区域。")
        return

    # --------------------- 基值计算 --------------------------------------
    stable_data = data[:stable_end_index+1, :]
    n_stable = stable_data.shape[0]
    start_idx = int(n_stable * 0.1)
    end_idx   = int(n_stable * 0.9)
    if end_idx <= start_idx:
        mid_stable = stable_data
    else:
        mid_stable = stable_data[start_idx:end_idx, :]

    baseline_dR1 = np.mean(mid_stable[:, 1])
    baseline_dR2 = np.mean(mid_stable[:, 3])

    # ------------------- 计算变化量及比值 -------------------------------
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

    new_data = np.column_stack((
        data[:, 0],
        delta_dR1,
        data[:, 2],
        delta_dR2,
        data[:, 4],
        ratio_dR1_dR2,
        ratio_dR2_dR1
    ))

    # ------------------ 输出 1：“origindiff” 文件 --------------------------
    # 表头（两行）：对于 origindiff 文件，第一列名称保持 "times"
    header_names_origin = ["times", "dR1", "φ1", "dR2", "φ1", "dR1/dR2", "dR2/dR1"]
    # 对于没有单位的项，设置为 "none"
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

    # ------------------ 输出 2：“data” 文件 --------------------------
    # 先舍弃平稳区域（即索引 0 ~ stable_end_index 的行），
    # 然后过滤掉剩余数据中相对于基值变化率不足 rel_threshold 的数据行
    candidate_data = new_data[stable_end_index+1:]
    filtered_rows = []
    for row in candidate_data:
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

    if filtered_rows:
        filtered_rows = np.array(filtered_rows)
        n_filtered = filtered_rows.shape[0]
        new_x = np.linspace(0, scan_length, n_filtered)
        filtered_rows[:, 0] = new_x
    else:
        print(f"文件 {filepath} 过滤后无有效数据行。")

    # 对 data 文件的表头，其中第一列名称改为 "x"，单位为 "µm"
    header_names_data = ["L", "dR1", "φ1", "dR2", "φ1", "dR1/dR2", "dR2/dR1"]
    header_units_data = ["µm", "Ω", "°", "Ω", "°", "none", "none"]
    header_line1_data = " ".join(header_names_data)
    header_line2_data = " ".join(header_units_data)

    out_lines_data = [header_line1_data, header_line2_data]
    if filtered_rows is not None and len(filtered_rows) > 0:
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
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(title="请选择包含数据文件的目录")
    if not folder:
        print("未选择目录，程序退出。")
        return

    scan_length = simpledialog.askfloat("扫描长度", "请输入扫描长度（单位 µm）:")
    if scan_length is None:
        print("未输入扫描长度，程序退出。")
        return

    for filename in os.listdir(folder):
        full_path = os.path.join(folder, filename)
        if os.path.isfile(full_path):
            base, ext = os.path.splitext(filename)
            if ext != "" and len(ext[1:]) <= 5:
                continue
            try:
                process_file(full_path, skip_lines=5, rel_threshold=0.0003, scan_length=scan_length)
            except Exception as e:
                print(f"处理 {full_path} 时发生错误：{e}")

if __name__ == "__main__":
    main()

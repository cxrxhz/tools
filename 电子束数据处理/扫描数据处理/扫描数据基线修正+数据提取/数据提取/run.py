#!/usr/bin/env python3
import os
import sys
import shutil
import numpy as np
import tkinter as tk
import matplotlib.pyplot as plt
from tkinter import filedialog, messagebox

# ---------------------- 可配置参数 ----------------------
PEAK_THRESHOLD = 0.2  # 截止阈值，凡是 |y1| 或 |y2| 小于此值的行均舍弃
# ----------------------------------------------------------

# 自定义对话框，用于输入扫描长度、单位、α0 和 Gb
class ScanAlphaDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("参数设置")
        self.resizable(False, False)
        self.result = None

        tk.Label(self, text="扫描长度:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.length_entry = tk.Entry(self)
        self.length_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self, text="单位:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.unit_var = tk.StringVar(value="μm")
        units = ["m", "cm", "mm", "μm", "nm"]
        self.unit_option = tk.OptionMenu(self, self.unit_var, *units)
        self.unit_option.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(self, text="α0:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.alpha0_entry = tk.Entry(self)
        self.alpha0_entry.grid(row=2, column=1, padx=5, pady=5)

        tk.Label(self, text="Gb:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.gb_entry = tk.Entry(self)
        self.gb_entry.grid(row=3, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="OK", width=8, command=self.on_ok).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", width=8, command=self.on_cancel).pack(side="left", padx=5)

        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.grab_set()
        self.wait_window()

    def on_ok(self):
        try:
            length = float(self.length_entry.get())
            alpha0 = float(self.alpha0_entry.get())
            gb = float(self.gb_entry.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字！")
            return
        self.result = (length, self.unit_var.get(), alpha0, gb)
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

def process_result_files(result_folder):
    """
    ① 弹出对话框输入扫描长度、单位、α0 和 Gb；
    ② 读取 result 文件夹内的所有 .txt 文件（假定文件中的列顺序为：Time, y1_corr, y2_corr）；
    ③ 针对每个文件：
         - 先过滤：仅保留 |y1| 和 |y2| 均大于或等于阈值的行；
         - 以过滤后的数据为准，重新计算扫描时间 T_adj = T_filtered - T_filtered[0]
           以及 L（0 到输入扫描长度均匀分布，行数等于过滤后的数据行数）；
         - 计算其余列：αi1 = y1/y2, αi2 = y2/y1, Ri1 和 Ri2；
         - 保存处理后数据到 result-processed 文件夹中（文件名为 [原文件名]_processed.txt）；
         - 生成一张图，显示原始文件中 y1 和 y2 的数据，并用红色散点标记被过滤掉的点，保存为 [原文件名]_filtered.png；
    ④ 处理所有文件后，计算所有文件中过滤后数据的最大行数；
         如果某文件行数低于最大行数的 80%（阈值），则将其数据文件和图像移动（归档）到 result-processed 目录下的 “归档” 子文件夹中。
    """
    root = tk.Tk()
    root.withdraw()
    dialog = ScanAlphaDialog(root)
    if dialog.result is None:
        print("未输入参数，程序退出。")
        return
    scan_length, chosen_unit, alpha0, gb = dialog.result

    parent_folder = os.path.dirname(os.path.abspath(result_folder))
    processed_folder = os.path.join(parent_folder, "result-processed")
    os.makedirs(processed_folder, exist_ok=True)
    archive_folder = os.path.join(processed_folder, "归档")
    os.makedirs(archive_folder, exist_ok=True)

    files = [os.path.join(result_folder, f) for f in os.listdir(result_folder)
             if os.path.isfile(os.path.join(result_folder, f)) and f.lower().endswith(".txt")]
    if not files:
        print("在 result 文件夹中不存在任何 .txt 文件！")
        return

    header = ("L\tTime\ty1_corr\ty2_corr\tαi1\tαi2\tα0\tGb\tRi1\tRi2\n" +
              f"{chosen_unit}\ts\tΩ\tΩ\t-\t-\t-\t-\tK/W\tK/W")

    # 保存每个文件处理信息（文件名、行数、数据文件路径、图像路径）
    processed_info = []

    for file_path in files:
        print(f"正在处理文件：{file_path}")
        try:
            data = np.loadtxt(file_path, skiprows=2, delimiter="\t")
        except Exception as e:
            print(f"读取文件 {file_path} 时出错：{e}")
            continue

        if data.ndim == 1:
            data = data[np.newaxis, :]
        # 提取原始数据
        T_orig_full = data[:, 0]
        y1_full = data[:, 1]
        y2_full = data[:, 2]

        # 先过滤：仅保留 |y1| 与 |y2| 均大于或等于阈值的行
        valid_mask = (np.abs(y1_full) >= PEAK_THRESHOLD) & (np.abs(y2_full) >= PEAK_THRESHOLD)
        if not np.any(valid_mask):
            print(f"警告：文件 {file_path} 所有数据均低于阈值 {PEAK_THRESHOLD}，保留全部数据")
            valid_mask = np.full_like(y1_full, True, dtype=bool)

        # 保存原始数据用于绘图
        T_for_plot = T_orig_full.copy()
        y1_for_plot = y1_full.copy()
        y2_for_plot = y2_full.copy()

        # 基于过滤后的数据重新计算扫描时间和扫描长度
        T_orig = T_orig_full[valid_mask]
        y1_filtered = y1_full[valid_mask]
        y2_filtered = y2_full[valid_mask]
        num_valid = len(T_orig)
        T_adj = T_orig - T_orig[0]
        L = np.linspace(0, scan_length, num_valid)

        # 计算其它列
        alpha_i1 = y1_filtered / y2_filtered
        alpha_i2 = y2_filtered / y1_filtered
        alpha0_col = np.full((num_valid, 1), alpha0)
        gb_col = np.full((num_valid, 1), gb)
        Ri1 = (1 / gb) * (alpha0 - alpha_i1) / (1 + alpha_i1)
        Ri2 = (1 / gb) * (alpha0 - alpha_i2) / (1 + alpha_i2)
        Ri1 = Ri1.reshape(-1, 1)
        Ri2 = Ri2.reshape(-1, 1)

        new_data = np.column_stack((L, T_adj, y1_filtered, y2_filtered,
                                     alpha_i1, alpha_i2, alpha0_col, gb_col, Ri1, Ri2))

        base_name = os.path.basename(file_path)
        out_file = os.path.join(processed_folder, f"{base_name}_processed.txt")
        try:
            np.savetxt(out_file, new_data, delimiter="\t", header=header, comments="")
            print("已保存处理数据至:", out_file)
        except Exception as e:
            print("保存文件时出错:", e)
            continue

        # 生成图像：显示原始数据及被舍弃的数据（红色散点）
        plt.figure(figsize=(10, 6))
        plt.plot(T_for_plot, y1_for_plot, label="原始 y1", color="blue", alpha=0.5)
        plt.plot(T_for_plot, y2_for_plot, label="原始 y2", color="green", alpha=0.5)
        plt.scatter(T_for_plot[~valid_mask], y1_for_plot[~valid_mask],
                    color="red", label="舍弃的 y1", alpha=0.7)
        plt.scatter(T_for_plot[~valid_mask], y2_for_plot[~valid_mask],
                    color="red", label="舍弃的 y2", alpha=0.7)
        plt.xlabel("Time (s)")
        plt.ylabel("Signal (Ω)")
        plt.legend()
        plt.title(f"数据筛选 - {base_name}")
        filtered_img = os.path.join(processed_folder, f"{base_name}_filtered.png")
        plt.savefig(filtered_img)
        plt.close()
        print("已生成筛选图像至:", filtered_img)

        # 记录处理信息
        processed_info.append({
            "base_name": base_name,
            "rows": num_valid,
            "data_file": out_file,
            "img_file": filtered_img
        })

    # 归档处理：以过滤后数据行数为准，计算所有文件中的最大行数
    if processed_info:
        max_rows = max(info["rows"] for info in processed_info)
        archive_threshold = 0.7 * max_rows
        print(f"最大数据行数为 {max_rows}，归档阈值为 {archive_threshold:.0f} 行")
        # 对行数低于归档阈值的文件进行归档，将其移动到 processed_folder/归档
        for info in processed_info:
            if info["rows"] < archive_threshold:
                # 移动数据文件
                dest_data = os.path.join(archive_folder, os.path.basename(info["data_file"]))
                try:
                    shutil.move(info["data_file"], dest_data)
                    print(f"归档数据文件 {os.path.basename(info['data_file'])}")
                except Exception as e:
                    print("归档数据文件时出错:", e)
                # 移动图像文件
                dest_img = os.path.join(archive_folder, os.path.basename(info["img_file"]))
                try:
                    shutil.move(info["img_file"], dest_img)
                    print(f"归档图像文件 {os.path.basename(info['img_file'])}")
                except Exception as e:
                    print("归档图像文件时出错:", e)
    else:
        print("没有处理任何文件。")

    print("所有文件处理完成。")

def main():
    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        result_folder = sys.argv[1]
    else:
        root = tk.Tk()
        root.withdraw()
        result_folder = filedialog.askdirectory(title="请选择包含结果文件的文件夹 (result目录)")
        if not result_folder:
            print("未选择文件夹，程序退出。")
            return
    print("使用的 result 文件夹为：", result_folder)
    process_result_files(result_folder)

if __name__ == "__main__":
    main()

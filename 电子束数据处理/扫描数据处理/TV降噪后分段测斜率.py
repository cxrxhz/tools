#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置部分：所有可以调整的参数都在此处定义，便于统一管理
--------------------------------------------------

【文件读取相关】
SKIP_HEADER_LINES                跳过的表头行数（默认 1 行，可根据实际情况修改）
DEFAULT_FILE_ENCODING            如果不希望自动检测编码，也可以指定（例如："gbk"），设为 None 时自动检测

【TV 去噪相关】
TV_DENOISE_WEIGHT                TV 去噪参数 weight，值越大平滑效果越强

【变点检测相关】
CHANGE_POINT_PENALTY             变点检测惩罚项，值越大检测到的变点越少
CHANGE_POINT_MIN_SIZE            变点检测中每个分段的最小长度，避免产生太短的分段
CHANGE_POINT_MODEL               变点检测所用模型，当 rpt.LinearRegression() 不可用时，使用该字符串（通常设为 "linear"）

【RANSAC 回归相关】
RANSAC_RESIDUAL_THRESHOLD_MULTIPLIER   RANSAC 残差阈值乘数，实际阈值为该值乘以 y 值的标准差

【Matplotlib 显示设置】
MATPLOTLIB_FONT                  用于图形显示中文的字体名称（确保系统安装了该字体）


你可以根据数据情况修改下面各项配置。
--------------------------------------------------
"""

# 文件读取配置
SKIP_HEADER_LINES = 1
DEFAULT_FILE_ENCODING = None  # 设置为 None 时自动检测文件编码

# TV 去噪配置
TV_DENOISE_WEIGHT = 100

# 变点检测配置
CHANGE_POINT_PENALTY = 0.2
CHANGE_POINT_MIN_SIZE = 5
CHANGE_POINT_MODEL = "linear"  # 当 rpt.LinearRegression() 无法使用时采用该模型

# RANSAC 回归配置
RANSAC_RESIDUAL_THRESHOLD_MULTIPLIER = 2

# Matplotlib显示配置
MATPLOTLIB_FONT = "SimHei"

# --------------------------------------------------
# 以下代码不需要修改
# --------------------------------------------------

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from skimage.restoration import denoise_tv_chambolle
import ruptures as rpt
from sklearn.linear_model import RANSACRegressor
import tkinter as tk
from tkinter import filedialog, simpledialog
import chardet

# 设置 Matplotlib 用于显示中文和正确显示负号
plt.rcParams['font.sans-serif'] = [MATPLOTLIB_FONT]
plt.rcParams['axes.unicode_minus'] = False


def detect_encoding(file_path, num_bytes=10000):
    """
    检测文件编码，读取前 num_bytes 个字节进行检测。
    如果 DEFAULT_FILE_ENCODING 不为 None，则直接使用该编码。
    """
    if DEFAULT_FILE_ENCODING is not None:
        print("使用指定的文件编码:", DEFAULT_FILE_ENCODING)
        return DEFAULT_FILE_ENCODING

    with open(file_path, 'rb') as f:
        rawdata = f.read(num_bytes)
    result = chardet.detect(rawdata)
    encoding = result['encoding']
    print("检测到的文件编码:", encoding)
    return encoding


def load_data():
    """
    弹出文件对话框选择数据文件，并读取数据。
    针对 TXT 文件默认使用空白字符（空格、制表符）作为分隔符。
    如果数据列数不足2，则提示错误退出。

    返回:
        t: 数据的第一列（时间/索引）
        y: 数据的第二列（测量值）
    """
    # 初始化 Tkinter（隐藏主窗口）
    root = tk.Tk()
    root.withdraw()

    # 弹出文件选择对话框（支持 TXT 与 CSV 文件）
    file_path = filedialog.askopenfilename(
        title="请选择数据文件",
        filetypes=[("TXT Files", "*.txt"), ("CSV Files", "*.csv"), ("All Files", "*.*")]
    )
    if not file_path:
        print("未选择任何文件，程序退出")
        exit()

    # 使用配置中指定的跳过行数
    header_lines = SKIP_HEADER_LINES

    # 检测文件编码
    encoding = detect_encoding(file_path)

    # 根据文件后缀选择读取方式
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".txt":
            # TXT 文件使用空白字符作为分隔符
            df = pd.read_csv(file_path, skiprows=header_lines, encoding=encoding, sep=r'\s+')
        else:
            # CSV 文件使用默认的逗号分隔
            df = pd.read_csv(file_path, skiprows=header_lines, encoding=encoding)
    except Exception as e:
        print("读取文件出错，请检查文件格式。")
        print(e)
        exit()

    print("初次读取后的数据列:", df.columns.tolist())

    # 如果列数不足2，则再尝试一次用空白字符作为分隔符
    if df.shape[1] < 2:
        print("检测到的数据列数不足2，尝试使用空格作为分隔符重新读取...")
        try:
            df = pd.read_csv(file_path, skiprows=header_lines, encoding=encoding, sep=r'\s+')
            print("重新读取后的数据列:", df.columns.tolist())
        except Exception as e:
            print("通过空格分隔读取数据失败，请检查数据文件格式。")
            print(e)
            exit()

    if df.shape[1] < 2:
        print("读取的数据仍不足两列，请检查数据文件是否正确。")
        exit()

    # 假设第一列为 t，第二列为 y
    t = df.iloc[:, 0].values
    y = df.iloc[:, 1].values

    return t, y


def main():
    # 1. 读取数据
    t, y = load_data()

    # 2. 对数据进行 TV 去噪，保留趋势及断点信息
    denoised = denoise_tv_chambolle(y, weight=TV_DENOISE_WEIGHT)

    # 显示原始数据与 TV 去噪后的结果
    plt.figure(figsize=(10, 4))
    plt.plot(t, y, label="原始数据", alpha=0.5)
    plt.plot(t, denoised, label="TV 去噪", linewidth=2)
    plt.xlabel("t")
    plt.ylabel("y")
    plt.title("原始数据 vs TV 去噪结果")
    plt.legend()
    plt.show()

    # 3. 变点检测：利用 ruptures 检测数据中的趋势变化点
    denoised_reshaped = denoised.reshape(-1, 1)
    try:
        # 首先试用 rpt.LinearRegression 模型
        model = rpt.LinearRegression().fit(denoised_reshaped)
        algo = rpt.Pelt(model=model, min_size=CHANGE_POINT_MIN_SIZE).fit(denoised_reshaped)
    except Exception as e:
        print("使用 rpt.LinearRegression 出错，尝试使用 model='{}'".format(CHANGE_POINT_MODEL))
        algo = rpt.Pelt(model=CHANGE_POINT_MODEL, min_size=CHANGE_POINT_MIN_SIZE).fit(denoised_reshaped)

    change_points = algo.predict(pen=CHANGE_POINT_PENALTY)
    if change_points and change_points[-1] == len(y):
        change_points = change_points[:-1]

    print("检测到的变点位置（索引）：", change_points)

    # 绘制变点检测结果
    plt.figure(figsize=(10, 4))
    plt.plot(t, denoised, label="TV 去噪")
    for cp in change_points:
        x_val = t[cp] if cp < len(t) else t[-1]
        plt.axvline(x=x_val, color='r', linestyle='--')
    plt.xlabel("t")
    plt.ylabel("y")
    plt.title("变点检测结果")
    plt.legend()
    plt.show()

    # 4. 分段鲁棒回归：对每个区段使用 RANSAC 拟合直线，排除无效数据影响
    slopes = []
    segment_centers = []
    starts = [0] + change_points
    ends = change_points + [len(y)]

    for start, end in zip(starts, ends):
        X = np.arange(start, end).reshape(-1, 1)
        segment = y[start:end]

        residual_threshold = np.std(y) * RANSAC_RESIDUAL_THRESHOLD_MULTIPLIER
        ransac = RANSACRegressor(residual_threshold=residual_threshold).fit(X, segment)
        slope = ransac.estimator_.coef_[0]
        slopes.append(slope)
        segment_centers.append(np.mean(t[start:end]))

    # 输出每个区段的斜率
    for i, s in enumerate(slopes):
        print("区段 {} 的斜率: {:.4f}".format(i + 1, s))

    # 绘制区段斜率估计结果
    plt.figure(figsize=(10, 4))
    plt.plot(segment_centers, slopes, 'bo-', label="区段斜率")
    plt.xlabel("t (区段中心)")
    plt.ylabel("斜率")
    plt.title("各区段斜率估计")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    main()

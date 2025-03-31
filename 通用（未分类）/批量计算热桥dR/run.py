import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from tkinter import Tk, filedialog

# Function to process each file
def process_file(file_path):
    I2, R1, R2 = [], [], []
    with open(file_path, 'r') as file:
        lines = file.readlines()[2:]  # 跳过前两行
        for line in lines:
            columns = line.split()
            if len(columns) >= 5:
                I2.append(float(columns[1]))
                R1.append(float(columns[2]))
                R2.append(float(columns[4]))
    return np.array(I2), np.array(R1), np.array(R2)

# Function to plot and fit data
def plot_and_fit(x, y, xlabel, ylabel, title):
    slope, intercept, r_value, p_value, std_err = linregress(x, y)
    plt.figure()
    plt.plot(x, y, 'o', label='原始数据')
    plt.plot(x, intercept + slope * x, 'r', label='拟合直线')
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.show()
    return slope

# Function to select root directory
def select_directory():
    root = Tk()
    root.withdraw()  # 隐藏主窗口
    directory = filedialog.askdirectory(title='选择包含数据文件夹的根目录')
    root.destroy()
    return directory

# Select the root directory containing the data folders
root_directory = select_directory()
if not root_directory:
    print('未选择任何目录，程序退出。')
    exit()

# Initialize lists to store overall results
overall_temperatures = []
overall_dR1_values = []
overall_dR2_values = []

# Traverse each subdirectory in the root directory
for subdir in os.listdir(root_directory):
    subdir_path = os.path.join(root_directory, subdir)
    if os.path.isdir(subdir_path):
        # Initialize lists to store results for this datasetD
        temperatures = []
        dR1_values = []
        dR2_values = []
        # Process each file in the subdirectory
        for file_name in os.listdir(subdir_path):
            if file_name.endswith('.txt'):
                try:
                    temperature = int(file_name.split('K')[0])
                except ValueError:
                    # 跳过不包含温度信息的文件
                    continue

                file_path = os.path.join(subdir_path, file_name)
                I2, R1, R2 = process_file(file_path)

                if len(I2) == 0:
                    print(f'文件 {file_name} 中的数据不足，已跳过。')
                    continue

                # Perform linear fit and calculate dy for R1 and R2
                slope_R1 = plot_and_fit(I2, R1, 'I2', 'R1', f'{file_name} 的线性拟合 (R1)')
                slope_R2 = plot_and_fit(I2, R2, 'I2', 'R2', f'{file_name} 的线性拟合 (R2)')

                # Calculate dy (slope * dx)
                dx = max(I2) - min(I2)
                print(f'文件: {file_name}, 斜率 R1: {slope_R1}, 斜率 R2: {slope_R2}, dx: {dx}')
                dR1 = slope_R1 * dx
                dR2 = slope_R2 * dx

                # Store results
                temperatures.append(temperature)
                dR1_values.append(dR1)
                dR2_values.append(dR2)

        if temperatures:
            # Sort results by temperature
            sorted_results = sorted(zip(temperatures, dR1_values, dR2_values))

            # Output temperature and dR1/dR2 values to a txt file in the subdirectory
            output_file = os.path.join(subdir_path, 'temperature_dR1_dR2_sorted.txt')
            with open(output_file, 'w') as f:
                f.write('Temperature(K)\tdR1\tdR2\n')
                for temp, dR1, dR2 in sorted_results:
                    f.write(f'{temp}\t{dR1}\t{dR2}\n')

            print(f'数据集 {subdir} 的结果已保存到 {output_file}')

            # Store overall results
            overall_temperatures.extend(temperatures)
            overall_dR1_values.extend(dR1_values)
            overall_dR2_values.extend(dR2_values)
        else:
            print(f'数据集 {subdir} 中没有有效的数据文件。')

# Optionally, you can output the overall results to a file
if overall_temperatures:
    overall_output_file = os.path.join(root_directory, 'overall_temperature_dR1_dR2_sorted.txt')
    sorted_overall_results = sorted(zip(overall_temperatures, overall_dR1_values, overall_dR2_values))
    with open(overall_output_file, 'w') as f:
        f.write('Temperature(K)\tdR1\tdR2\n')
        for temp, dR1, dR2 in sorted_overall_results:
            f.write(f'{temp}\t{dR1}\t{dR2}\n')

    print(f'所有数据集的总结果已保存到 {overall_output_file}')
else:
    print('没有处理任何数据，未生成总结果文件。')


import csv
import os
import tkinter as tk
from tkinter import filedialog, messagebox


def extract_material_and_diffusivity(file_name):
    """
    从给定的 CSV 文件中提取 #Material 和 #Mean #Diffusivity/(mm^2/s) 信息。

    参数:
    file_name (str): CSV 文件的路径。

    返回:
    tuple: 包含 material 和 mean_diffusivity 的元组。
    """
    material = None
    mean_diffusivity = None

    # 定义尝试使用的编码列表
    encodings = ['gbk', 'utf-8-sig', 'utf-16']
    for encoding in encodings:
        try:
            with open(file_name, 'r', encoding=encoding) as file:
                reader = csv.reader(file)
                for row in reader:
                    # 查找以 #Material 开头的行并提取信息
                    if row and row[0].startswith('#Material'):
                        material = row[1]
                    # 查找以 #Mean 开头且包含 Diffusivity 信息的行并提取数据
                    if row and row[0].startswith('#Mean'):
                        mean_diffusivity = row[3]  # 确保提取的列正确
            # 成功读取后退出循环
            break
        except UnicodeDecodeError:
            # 如果当前编码读取失败，则尝试下一个编码
            continue

    return material, mean_diffusivity


def process_files(directory):
    """
    处理指定目录中的所有 CSV 文件，提取每个文件中的 #Material 和 #Mean #Diffusivity/(mm^2/s) 信息，
    并按照文件名前缀（例如 "1-2"）进行排序。

    参数:
    directory (str): 包含 CSV 文件的目录路径。

    返回:
    list: 包含每个文件的文件名前缀、material 和 mean_diffusivity 的列表。
    """
    results = []
    # 遍历目录中的所有文件
    for file_name in os.listdir(directory):
        if file_name.endswith('.csv'):
            # 假定文件名开头部分为 "数字-数字"，例如 "1-2"
            parts = file_name.split()
            if not parts:
                continue
            file_prefix = parts[0]  # 比如 "1-2"
            if '-' not in file_prefix:
                continue
            subparts = file_prefix.split('-')
            if len(subparts) != 2:
                continue
            try:
                num1 = int(subparts[0])
                num2 = int(subparts[1])
            except ValueError:
                continue

            file_path = os.path.join(directory, file_name)
            material, mean_diffusivity = extract_material_and_diffusivity(file_path)
            # 保存排序依据和所需的字段
            results.append(((num1, num2), file_prefix, material, mean_diffusivity))

    # 依据提取的数字元组进行排序
    results.sort(key=lambda x: x[0])
    # 返回需要输出的内容
    return [(prefix, material, mean_diffusivity) for (_, prefix, material, mean_diffusivity) in results]


def save_results_to_csv(results, output_file):
    """
    将提取的结果保存到 CSV 文件中。

    参数:
    results (list): 包含每个文件的文件名前缀、material 和 mean_diffusivity 的列表。
    output_file (str): 输出 CSV 文件的路径。
    """
    with open(output_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['File Number', 'Material', 'Mean Diffusivity (mm^2/s)'])
        writer.writerows(results)


def main():
    # 初始化 Tkinter 并隐藏主窗口
    root = tk.Tk()
    root.withdraw()

    # 弹出目录选择窗口
    directory = filedialog.askdirectory(title="请选择包含 CSV 文件的文件夹")
    if not directory:
        messagebox.showinfo("提示", "未选择任何目录，程序退出。")
        return

    results = process_files(directory)

    # 将结果保存至所选目录下的 extracted_results.csv
    output_file = os.path.join(directory, 'extracted_results.csv')
    save_results_to_csv(results, output_file)

    messagebox.showinfo("完成", f"提取的结果已保存到\n{output_file}")


if __name__ == "__main__":
    main()

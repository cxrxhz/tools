import csv
import os


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

    # 使用 gbk 编码打开 CSV 文件进行读取
    with open(file_name, 'r', encoding='gbk') as file:
        reader = csv.reader(file)
        for row in reader:
            # 查找以 #Material 开头的行并提取信息
            if row and row[0].startswith('#Material'):
                material = row[1]
            # 查找以 #Mean 开头且包含 #Diffusivity/(mm^2/s) 的行并提取信息
            if row and row[0].startswith('#Mean'):
                mean_diffusivity = row[3]  # 确保提取正确的列

    return material, mean_diffusivity


def process_files(file_paths):
    """
    处理指定路径中的所有 CSV 文件，提取每个文件中的 #Material 和 #Mean #Diffusivity/(mm^2/s) 信息。

    参数:
    file_paths (list): 包含 CSV 文件路径的列表。

    返回:
    list: 包含每个文件的文件名对应的数字、material 和 mean_diffusivity 的列表。
    """
    results = []
    # 遍历所有文件路径
    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        try:
            file_number = int(file_name.split()[0])  # 提取文件名开头的数字
            material, mean_diffusivity = extract_material_and_diffusivity(file_path)
            results.append((file_number, material, mean_diffusivity))
        except ValueError:
            # 忽略非数字开头的文件名
            continue

    # 按照文件名对应的数字排序
    results.sort(key=lambda x: x[0])

    return results


def save_results_to_csv(results, output_file):
    """
    将提取的结果保存到一个 CSV 文件中。

    参数:
    results (list): 包含每个文件的文件名对应的数字、material 和 mean_diffusivity 的列表。
    output_file (str): 输出 CSV 文件的路径。
    """
    with open(output_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['File Number', 'Material', 'Mean Diffusivity (mm^2/s)'])
        writer.writerows(results)


# 主程序
if __name__ == "__main__":
    file_paths = []

    print("请输入包含 CSV 文件的文件路径（按下 ESC 键结束输入）:")

    while True:
        try:
            file_path = input("文件路径: ")
            if file_path.lower() == 'esc':
                break
            if os.path.isfile(file_path):
                file_paths.append(file_path)
            else:
                print("无效的文件路径，请重新输入。")
        except KeyboardInterrupt:
            break

    results = process_files(file_paths)

    # 保存结果到一个新的 CSV 文件中
    output_file = 'extracted_results.csv'
    save_results_to_csv(results, output_file)

    print(f"提取的结果已保存到 {output_file}")

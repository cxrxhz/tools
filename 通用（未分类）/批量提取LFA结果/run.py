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


def process_files(directory):
    """
    处理指定目录中的所有 CSV 文件，提取每个文件中的 #Material 和 #Mean #Diffusivity/(mm^2/s) 信息。

    参数:
    directory (str): 包含 CSV 文件的目录路径。

    返回:
    list: 包含每个文件的文件名对应的数字、material 和 mean_diffusivity 的列表。
    """
    results = []
    # 遍历目录中的所有文件
    for file_name in os.listdir(directory):
        if file_name.endswith('.csv'):
            try:
                file_number = int(file_name.split()[0])  # 提取文件名开头的数字
                file_path = os.path.join(directory, file_name)
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
    directory = input("请输入包含 CSV 文件的文件夹路径: ")  # 提示用户输入文件夹路径
    results = process_files(directory)

    # 保存结果到一个新的 CSV 文件中
    output_file = os.path.join(directory, 'extracted_results.csv')
    save_results_to_csv(results, output_file)

    print(f"提取的结果已保存到 {output_file}")

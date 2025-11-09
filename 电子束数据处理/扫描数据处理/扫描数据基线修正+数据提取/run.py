import subprocess
import os


def get_result_folder(folder1):
    print("正在运行第一个程序：", os.path.join(folder1, "run.py"))
    try:
        result = subprocess.run(["python", "run.py"], cwd=folder1,
                                  check=True, capture_output=True, text=True, encoding="utf-8")
        if result.stdout is None:
            print("错误：未能获取输出")
            return None
        output_lines = result.stdout.splitlines()
        for line in output_lines:
            if line.startswith("RESULT_FOLDER:"):
                result_folder = line.replace("RESULT_FOLDER:", "").strip()
                print("检测到 result 文件夹路径:", result_folder)
                return result_folder
    except subprocess.CalledProcessError as e:
        print("第一个程序运行出错：", e)
        return None
    return None



def main():
    folder1 = os.path.abspath("基线修正")
    folder2 = os.path.abspath("数据提取")

    # 获取第一个程序的 result 文件夹路径
    result_folder = get_result_folder(folder1)
    if not result_folder or not os.path.exists(result_folder):
        print("找不到第一个程序的结果文件夹:", result_folder)
        return

    # 运行第二个程序，并传入 result 文件夹路径
    print("正在运行第二个程序：", os.path.join(folder2, "run.py"))
    try:
        subprocess.run(["python", "run.py", result_folder], cwd=folder2, check=True)
    except subprocess.CalledProcessError as e:
        print("第二个程序运行出错：", e)
        return

    print("所有程序运行完毕。")


if __name__ == "__main__":
    main()

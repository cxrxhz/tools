import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image


def convert_pngs_in_folder(folder, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)]):
    converted = 0
    # （仅转换当前目录下的文件，如需要递归可使用 os.walk）
    for file in os.listdir(folder):
        if file.lower().endswith('.png'):
            png_path = os.path.join(folder, file)
            ico_path = os.path.splitext(png_path)[0] + '.ico'
            try:
                with Image.open(png_path) as img:
                    img.save(ico_path, format='ICO', sizes=sizes)
                converted += 1
            except Exception as e:
                print(f"转换 {png_path} 失败: {e}")
    return converted


def main():
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    folder = filedialog.askdirectory(title="请选择包含 PNG 文件的文件夹")
    if not folder:
        messagebox.showinfo("提示", "未选择文件夹，程序退出。")
        return

    # 设置图标，如果需要使用自定义图标，请将路径替换为你的文件路径
    try:
        icon = tk.PhotoImage(file="path/to/your_icon.png")
        root.iconphoto(True, icon)
    except Exception as e:
        print(f"设置图标失败: {e}")

    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)]
    count = convert_pngs_in_folder(folder, sizes=sizes)
    messagebox.showinfo("转换完成", f"成功转换 {count} 个 PNG 文件为 ICO 格式。")


if __name__ == "__main__":
    main()

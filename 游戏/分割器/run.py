
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
try:
    import tkinterdnd2 as tkdnd
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

def split_text_file(input_file, output_folder=None, target_size=70000, tolerance=1000):
    """
    按指定字数分割文本，并确保分割点位于 [Wait] ... 换行符之后。
    
    :param input_file: 输入文件名
    :param target_size: 目标分块大小 (默认 70000)
    :param tolerance: 搜索分割点的容差范围 (默认 +/- 1000)
    """
    

    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 找不到文件 '{input_file}'")
        return

    # 设置输出文件夹
    if output_folder is None:
        output_folder = os.path.dirname(input_file)


    # 读取文件内容
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"读取文件出错: {e}")
        return

    total_length = len(content)
    print(f"文件总字数: {total_length}")
    
    start_index = 0
    part_num = 1
    
    # 核心分割逻辑
    while start_index < total_length:
        # 如果剩余内容少于目标大小+容差，直接作为最后一块保存

        if total_length - start_index <= target_size + tolerance:
            end_index = total_length
            save_chunk(content[start_index:end_index], input_file, part_num, output_folder)
            break
            
        # 设定理想的切割中心点
        ideal_split_point = start_index + target_size
        
        # 设定搜索窗口 [min_point, max_point]
        min_point = max(start_index, ideal_split_point - tolerance)
        max_point = min(total_length, ideal_split_point + tolerance)
        
        # 截取搜索窗口内的文本
        search_window = content[min_point:max_point]
        
        # 使用正则寻找 [Wait] 及其后的整行内容
        # 匹配模式： [Wait] 开头，后面跟任意字符，直到遇到换行符
        matches = list(re.finditer(r'\[Wait\].*?\n', search_window))
        
        cut_point = -1
        
        if matches:
            # 策略：优先选择最接近 ideal_split_point 的那个 [Wait]
            # 或者选择窗口内最后一个 [Wait] 以最大化利用空间
            # 这里我们选择窗口内最后一个匹配项，尽量让块大一点
            last_match = matches[-1]
            
            # last_match.end() 是相对于 search_window 的结束位置
            # 必须加上 min_point 才能得到全局位置
            cut_point = min_point + last_match.end()
            
            print(f"分块 {part_num}: 在位置 {cut_point} 找到完美分割点 (距离目标偏差: {cut_point - ideal_split_point})")
        
        else:
            # 备用方案：如果在 +/- 1000 字内没找到 [Wait]
            # 为了安全，我们向前（往回）搜索直到找到最近的一个 [Wait]
            # 这样虽然会导致这一块变短，但保证了语境完整
            print(f"分块 {part_num}: 警告 - 窗口内未找到 [Wait]，正在向前回溯搜索...")
            
            # 截取从当前起点到 min_point 的内容进行回溯
            fallback_window = content[start_index:min_point]
            fallback_matches = list(re.finditer(r'\[Wait\].*?\n', fallback_window))
            
            if fallback_matches:
                last_match = fallback_matches[-1]
                cut_point = start_index + last_match.end()
                print(f"分块 {part_num}: 在回溯位置 {cut_point} 找到分割点")
            else:
                # 实在找不到（比如开头几万字都没有Wait），只能强制硬切
                print(f"分块 {part_num}: 错误 - 范围内无 [Wait] 标记，执行强制硬切。")
                cut_point = ideal_split_point

        # 保存当前块

        save_chunk(content[start_index:cut_point], input_file, part_num, output_folder)
        
        # 更新起点，准备下一轮
        start_index = cut_point
        part_num += 1

def save_chunk(text, original_filename, part_num, output_folder):
    """保存分块文件"""
    # 生成新文件名，例如：history_part_01.txt
    base_name = os.path.splitext(os.path.basename(original_filename))[0]
    new_filename = f"{base_name}_part_{part_num:02d}.txt"
    out_path = os.path.join(output_folder, new_filename)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"--> 已保存: {out_path} (字数: {len(text)})")


# ================= GUI界面 =================
def run_gui():
    # If tkinterdnd2 is available, create the special root that supports drag-and-drop
    if DND_AVAILABLE:
        root = tkdnd.TkinterDnD.Tk()
    else:
        root = tk.Tk()
    root.title("互动故事分割器")
    root.geometry("500x250")

    input_file_var = tk.StringVar()
    output_folder_var = tk.StringVar()

    def select_input_file():
        file_path = filedialog.askopenfilename(title="选择输入文件", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if file_path:
            input_file_var.set(file_path)
            # 默认输出文件夹为输入文件所在目录
            output_folder_var.set(os.path.dirname(file_path))

    def select_output_folder():
        folder = filedialog.askdirectory(title="选择输出文件夹")
        if folder:
            output_folder_var.set(folder)

    def on_drop(event):
        # 兼容tkinterdnd2的拖拽
        file_path = event.data.strip('{}')
        if os.path.isfile(file_path):
            input_file_var.set(file_path)
            output_folder_var.set(os.path.dirname(file_path))

    def run_split():
        in_file = input_file_var.get()
        out_folder = output_folder_var.get()
        if not in_file or not os.path.isfile(in_file):
            messagebox.showerror("错误", "请选择有效的输入文件！")
            return
        if not out_folder or not os.path.isdir(out_folder):
            messagebox.showerror("错误", "请选择有效的输出文件夹！")
            return
        try:
            split_text_file(in_file, out_folder)
            messagebox.showinfo("完成", "分割完成！")
        except Exception as e:
            messagebox.showerror("出错", str(e))

    # 输入文件选择
    tk.Label(root, text="输入文件:").pack(anchor='w', padx=10, pady=(20, 0))
    input_frame = tk.Frame(root)
    input_frame.pack(fill='x', padx=10)
    input_entry = tk.Entry(input_frame, textvariable=input_file_var, width=50)
    input_entry.pack(side='left', fill='x', expand=True)
    tk.Button(input_frame, text="选择", command=select_input_file).pack(side='left', padx=5)

    # 拖拽支持
    if DND_AVAILABLE:
        try:
            input_entry.drop_target_register(tkdnd.DND_FILES)
            input_entry.dnd_bind('<<Drop>>', on_drop)
        except Exception:
            tk.Label(root, text="(拖拽不可用：注册失败)").pack(anchor='w', padx=20, pady=(0, 5))
    else:
        tk.Label(root, text="(可通过拖拽文件到上方输入框；如需启用，请安装 tkinterdnd2)").pack(anchor='w', padx=20, pady=(0, 5))

    # 输出文件夹选择
    tk.Label(root, text="输出文件夹:").pack(anchor='w', padx=10, pady=(10, 0))
    output_frame = tk.Frame(root)
    output_frame.pack(fill='x', padx=10)
    output_entry = tk.Entry(output_frame, textvariable=output_folder_var, width=50)
    output_entry.pack(side='left', fill='x', expand=True)
    tk.Button(output_frame, text="选择", command=select_output_folder).pack(side='left', padx=5)

    # 开始按钮
    tk.Button(root, text="开始分割", command=run_split, height=2, width=20, bg="#4CAF50", fg="white").pack(pady=20)

    root.mainloop()


if __name__ == "__main__":
    run_gui()
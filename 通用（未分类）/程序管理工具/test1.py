import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class ProgramManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("程序管理器")
        self.geometry("600x400")
        self.iconbitmap(r"E:\pythonProject\图标库\a-018-smartphone.ico")  # 设置程序窗口图标
        self.library_dir = None  # 选取的库文件夹路径

        # 上方按钮区域
        btn_frame = tk.Frame(self)
        btn_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        select_btn = tk.Button(btn_frame, text="选择库文件夹", command=self.select_library)
        select_btn.pack(side=tk.LEFT, padx=5)

        refresh_btn = tk.Button(btn_frame, text="刷新", command=self.refresh_tree)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        self.path_label = tk.Label(btn_frame, text="未选择目录")
        self.path_label.pack(side=tk.LEFT, padx=10)

        # 树状结构显示区域
        self.tree = ttk.Treeview(self)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ysb = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)

        self.node_paths = {}  # 保存 tree 节点与实际路径的映射

        # 绑定双击事件：双击含 run.py 的节点会启动程序，
        # 对于中间容器节点则实现展开/收缩操作
        self.tree.bind("<Double-1>", self.on_item_double_click)

        # 尝试加载上一次选择的库文件夹（保存在 last_library.txt 中）
        self.load_last_library()

    def load_last_library(self):
        config_file = os.path.join(os.path.dirname(__file__), "last_library.txt")
        if os.path.isfile(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    path = f.read().strip()
                if path and os.path.isdir(path):
                    self.library_dir = path
                    self.path_label.config(text=self.library_dir)
                    self.refresh_tree()
            except Exception as e:
                print("加载上次库文件夹失败:", e)

    def save_last_library(self, path):
        config_file = os.path.join(os.path.dirname(__file__), "last_library.txt")
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                f.write(path)
        except Exception as e:
            print("保存库文件夹失败:", e)

    def select_library(self):
        selected_dir = filedialog.askdirectory(title="选择库文件夹")
        if selected_dir:
            self.library_dir = selected_dir
            self.path_label.config(text=self.library_dir)
            self.save_last_library(selected_dir)
            self.refresh_tree()

    def refresh_tree(self):
        if not self.library_dir:
            messagebox.showwarning("未选择目录", "请先选择一个库文件夹！")
            return

        # 清空树控件
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.node_paths.clear()

        try:
            entries = os.listdir(self.library_dir)
        except Exception as e:
            messagebox.showerror("错误", f"无法读取目录: {e}")
            return

        # 只显示库文件夹下包含程序的子目录，不显示库文件夹本身
        subdirs = sorted([d for d in entries if os.path.isdir(os.path.join(self.library_dir, d))])
        for sub in subdirs:
            full_path = os.path.join(self.library_dir, sub)
            # 只有当文件夹自身或其子目录中包含 run.py 时才显示
            if self.has_program(full_path):
                self.build_tree(parent="", path=full_path)

    def has_program(self, directory):
        """
        判断当前目录或任一子目录中是否存在 run.py 文件
        """
        if os.path.isfile(os.path.join(directory, "run.py")):
            return True
        try:
            for entry in os.listdir(directory):
                sub_path = os.path.join(directory, entry)
                if os.path.isdir(sub_path) and self.has_program(sub_path):
                    return True
        except Exception as e:
            print(f"检查目录 {directory} 时出错: {e}")
        return False

    def build_tree(self, parent, path):
        """
        对于当前目录：
        - 如果该目录包含 run.py，则认为是“程序”文件夹，显示为叶子节点；
        - 否则继续递归地查找并显示其包含 run.py 的子目录。
        """
        if not self.has_program(path):
            return

        basename = os.path.basename(path) or path
        is_program = os.path.isfile(os.path.join(path, "run.py"))
        node_text = basename + (" [Run]" if is_program else "")
        node_id = self.tree.insert(parent, "end", text=node_text, open=True)
        self.node_paths[node_id] = path

        # 如果目录本身已是程序，则不展开子目录
        if is_program:
            return

        try:
            entries = os.listdir(path)
        except Exception as e:
            print(f"无法读取 {path} : {e}")
            return

        subdirs = sorted([d for d in entries if os.path.isdir(os.path.join(path, d))])
        for sub in subdirs:
            sub_path = os.path.join(path, sub)
            if self.has_program(sub_path):
                self.build_tree(node_id, sub_path)

    def on_item_double_click(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        path = self.node_paths.get(item_id)
        if not path:
            return
        run_file = os.path.join(path, "run.py")
        if os.path.isfile(run_file):
            self.run_program(path)
        else:
            # 对于非程序节点，双击时展开或收缩树节点
            if self.tree.item(item_id, "open"):
                self.tree.item(item_id, open=False)
            else:
                self.tree.item(item_id, open=True)

    def run_program(self, directory):
        """
        使用当前 Python 解释器启动目录下的 run.py 程序，
        如有需要，可修改为调用其他启动命令或 bat 脚本
        """
        run_path = os.path.join(directory, "run.py")
        if not os.path.isfile(run_path):
            messagebox.showerror("错误", f"{directory} 中未找到 run.py")
            return

        try:
            subprocess.Popen([sys.executable, run_path], cwd=directory)
            print(f"启动程序: {run_path}")
        except Exception as e:
            messagebox.showerror("启动失败", f"启动程序时出错: {e}")


if __name__ == "__main__":
    app = ProgramManager()
    app.mainloop()

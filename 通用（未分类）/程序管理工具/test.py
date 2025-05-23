import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

ICON_SIZE = (16, 16)  # 图标缩放至 16x16 像素


class ProgramManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("程序管理器")
        self.geometry("600x400")
        # 设置主窗口图标
        self.iconbitmap(r"E:\pythonProject\图标库\a-018-smartphone.ico")

        # 加载并缩放自定义图标
        try:
            img_closed = Image.open(r"E:\pythonProject\图标库\a-010-letter-closed.ico").convert("RGBA")
            img_open = Image.open(r"E:\pythonProject\图标库\a-010-letter.ico").convert("RGBA")
            img_program = Image.open(r"E:\pythonProject\图标库\a-033-website.ico").convert("RGBA")

            img_closed = img_closed.resize(ICON_SIZE, Image.LANCZOS)
            img_open = img_open.resize(ICON_SIZE, Image.LANCZOS)
            img_program = img_program.resize(ICON_SIZE, Image.LANCZOS)

            self.closedIndicator = ImageTk.PhotoImage(img_closed)
            self.openIndicator = ImageTk.PhotoImage(img_open)
            self.programIndicator = ImageTk.PhotoImage(img_program)
        except Exception as e:
            messagebox.showerror("图标加载错误", f"加载自定义图标失败: {e}")
            self.closedIndicator = None
            self.openIndicator = None
            self.programIndicator = None

        # 设置 Treeview 样式：移除默认的 indicator，仅保留 image 和 text
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.layout("Treeview.Item", [
            ('Treeitem.padding', {
                'sticky': 'nswe',
                'children': [
                    ('Treeitem.image', {'side': 'left', 'sticky': ''}),
                    ('Treeitem.text', {'side': 'left', 'sticky': ''}),
                ]
            })
        ])

        # 上方按钮区域
        btn_frame = tk.Frame(self)
        btn_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        select_btn = tk.Button(btn_frame, text="选择库文件夹", command=self.select_library)
        select_btn.pack(side=tk.LEFT, padx=5)
        refresh_btn = tk.Button(btn_frame, text="刷新", command=self.refresh_tree)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        self.path_label = tk.Label(btn_frame, text="未选择目录")
        self.path_label.pack(side=tk.LEFT, padx=10)

        # Treeview 区域
        self.tree = ttk.Treeview(self)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        ysb = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)

        self.node_paths = {}  # 记录每个节点对应的目录路径

        # 绑定事件：单击展开/折叠，双击启动程序
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<<TreeviewOpen>>", self.on_tree_open)
        self.tree.bind("<<TreeviewClose>>", self.on_tree_close)
        self.tree.bind("<Double-1>", self.on_item_double_click)

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
        if not hasattr(self, "library_dir") or not self.library_dir:
            messagebox.showwarning("未选择目录", "请先选择一个库文件夹！")
            return
        # 清空当前树
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.node_paths.clear()
        try:
            entries = os.listdir(self.library_dir)
        except Exception as e:
            messagebox.showerror("错误", f"无法读取目录: {e}")
            return
        subdirs = sorted([d for d in entries if os.path.isdir(os.path.join(self.library_dir, d))])
        for sub in subdirs:
            full_path = os.path.join(self.library_dir, sub)
            if self.has_program(full_path):
                self.build_tree(parent="", path=full_path)

    def has_program(self, directory):
        """递归检查目录或子目录中是否存在 run.py"""
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
        """构造树形结构，移除 `[Run]` 标记，并设置自定义程序图标"""
        if not self.has_program(path):
            return
        basename = os.path.basename(path) or path
        is_program = os.path.isfile(os.path.join(path, "run.py"))
        node_text = basename  # 移除 `[Run]`
        # 设定适当的图标
        image = self.programIndicator if is_program else self.openIndicator
        node_id = self.tree.insert(parent, "end", text=node_text, open=True, image=image)
        self.node_paths[node_id] = path
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

    def on_tree_click(self, event):
        """单击时，切换容器节点的展开/折叠状态并更新图标"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        if self.tree.get_children(item):
            current = self.tree.item(item, "open")
            new_state = not current
            self.tree.item(item, open=new_state)
            self.tree.item(item, image=self.openIndicator if new_state else self.closedIndicator)
            return "break"

    def on_tree_open(self, event):
        """展开时更新图标"""
        item = self.tree.focus()
        if item and self.tree.get_children(item):
            self.tree.item(item, image=self.openIndicator)

    def on_tree_close(self, event):
        """折叠时更新图标"""
        item = self.tree.focus()
        if item and self.tree.get_children(item):
            self.tree.item(item, image=self.closedIndicator)

    def on_item_double_click(self, event):
        """双击启动程序"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        path = self.node_paths.get(item)
        if not path:
            return
        run_file = os.path.join(path, "run.py")
        if os.path.isfile(run_file):
            self.run_program(path)

    def run_program(self, directory):
        """运行程序"""
        run_path = os.path.join(directory, "run.py")
        subprocess.Popen([sys.executable, run_path], cwd=directory)


if __name__ == "__main__":
    app = ProgramManager()
    app.mainloop()

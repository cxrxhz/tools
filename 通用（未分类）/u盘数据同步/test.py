import os
import shutil
import json
import filecmp
import tkinter as tk
from tkinter import filedialog, messagebox

CONFIG_FILE = "config.json"


def load_config():
    """加载配置文件，如果存在则返回配置字典，否则返回空字典。"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置失败: {e}")
    return {}


def save_config(config):
    """保存配置到配置文件。"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"保存配置失败: {e}")


def files_are_identical(file1, file2):
    """
    判断两个文件是否完全相同：
    先通过文件大小判断，若相同再利用 filecmp.cmp 进行逐字节比较。
    """
    try:
        if os.path.getsize(file1) != os.path.getsize(file2):
            return False
        return filecmp.cmp(file1, file2, shallow=False)
    except Exception as e:
        print(f"比较文件 {file1} 与 {file2} 时出错: {e}")
        return False


def prompt_user_dialog(parent, file_name, src_file, dest_file):
    """
    当目标文件存在且内容不一致时，弹出对话框询问用户如何处理冲突：
    - 覆盖 (o)
    - 跳过 (s)
    - 重命名 (r)
    """
    dialog = tk.Toplevel(parent)
    dialog.title("文件冲突")

    # 自适应显示提示信息
    msg = f"目标文件已存在：\n{dest_file}\n\n来源文件：\n{src_file}\n\n请选择操作："
    label = tk.Label(dialog, text=msg, justify=tk.LEFT)
    label.pack(padx=10, pady=10)

    result = tk.StringVar()

    def choose(option):
        result.set(option)
        dialog.destroy()

    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=10)

    btn_overwrite = tk.Button(btn_frame, text="覆盖", command=lambda: choose("o"))
    btn_overwrite.pack(side=tk.LEFT, padx=5)
    btn_skip = tk.Button(btn_frame, text="跳过", command=lambda: choose("s"))
    btn_skip.pack(side=tk.LEFT, padx=5)
    btn_rename = tk.Button(btn_frame, text="重命名", command=lambda: choose("r"))
    btn_rename.pack(side=tk.LEFT, padx=5)

    dialog.grab_set()  # 锁定父窗口
    parent.wait_window(dialog)  # 等待对话框关闭后继续
    return result.get()


class SyncApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("文件同步工具")
        self.geometry("700x300")

        # 从配置文件加载数据库路径和 U盘路径
        self.config_data = load_config()
        self.repo_root = self.config_data.get("repo_root", "")
        self.usb_root = self.config_data.get("usb_root", "")
        self.create_widgets()

    def create_widgets(self):
        # 数据库（目标）路径选择
        lbl_repo = tk.Label(self, text="数据库路径:")
        lbl_repo.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.entry_repo = tk.Entry(self, width=50)
        self.entry_repo.grid(row=0, column=1, padx=10, pady=10)
        self.entry_repo.insert(0, self.repo_root)
        btn_browse_repo = tk.Button(self, text="浏览", command=self.select_repo)
        btn_browse_repo.grid(row=0, column=2, padx=10, pady=10)

        # U盘（源）路径选择
        lbl_usb = tk.Label(self, text="U盘路径:")
        lbl_usb.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.entry_usb = tk.Entry(self, width=50)
        self.entry_usb.grid(row=1, column=1, padx=10, pady=10)
        self.entry_usb.insert(0, self.usb_root)
        btn_browse_usb = tk.Button(self, text="浏览", command=self.select_usb)
        btn_browse_usb.grid(row=1, column=2, padx=10, pady=10)

        # 开始同步按钮
        btn_sync = tk.Button(self, text="开始同步", command=self.start_sync)
        btn_sync.grid(row=2, column=1, padx=10, pady=20)

        # 状态信息标签
        self.status_label = tk.Label(self, text="等待操作...", fg="blue")
        self.status_label.grid(row=3, column=1, pady=10)

    def select_repo(self):
        """选择数据库路径，并更新配置。"""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.repo_root = folder_selected
            self.entry_repo.delete(0, tk.END)
            self.entry_repo.insert(0, folder_selected)
            self.config_data["repo_root"] = folder_selected
            save_config(self.config_data)
            self.status_label.config(text="数据库路径已更新")

    def select_usb(self):
        """选择 U盘路径，并更新配置。"""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.usb_root = folder_selected
            self.entry_usb.delete(0, tk.END)
            self.entry_usb.insert(0, folder_selected)
            self.config_data["usb_root"] = folder_selected
            save_config(self.config_data)
            self.status_label.config(text="U盘路径已更新")

    def start_sync(self):
        """
        开始同步：
        将源目录【U盘路径\SEM\SiNW】中的所有文件夹和文件，
        按原有结构复制到目标【数据库路径\SiNW\SEM】中，
        如果重复则按条件处理【跳过、覆盖、重命名】。
        """
        if not self.repo_root:
            messagebox.showwarning("警告", "请先选择数据库路径")
            return
        if not self.usb_root:
            messagebox.showwarning("警告", "请先选择U盘路径")
            return

        self.status_label.config(text="同步进行中...")

        # 构造源和目标目录（注意：根据需求固定了子目录）
        source_dir = os.path.join(self.usb_root, "SEM", "SiNW")
        dest_dir = os.path.join(self.repo_root, "SiNW", "SEM")

        if not os.path.exists(source_dir):
            messagebox.showerror("错误", f"源目录不存在：{source_dir}")
            self.status_label.config(text="同步失败")
            return

        os.makedirs(dest_dir, exist_ok=True)
        self.sync_directories(source_dir, dest_dir)
        self.status_label.config(text="同步完成")

    def sync_directories(self, source_dir, dest_dir):
        """
        遍历源目录中所有文件和文件夹，
        将文件复制到目标目录中，且保持相对路径结构不变。
        """
        for root, dirs, files in os.walk(source_dir):
            rel_path = os.path.relpath(root, source_dir)
            target_dir = os.path.join(dest_dir, rel_path)
            os.makedirs(target_dir, exist_ok=True)
            for file in files:
                source_file = os.path.join(root, file)
                dest_file = os.path.join(target_dir, file)
                if not os.path.exists(dest_file):
                    print(f"复制文件：{source_file} -> {dest_file}")
                    shutil.copy2(source_file, dest_file)
                else:
                    if files_are_identical(source_file, dest_file):
                        print(f"文件一致，跳过：{source_file}")
                    else:
                        action = prompt_user_dialog(self, file, source_file, dest_file)
                        if action == "o":
                            print(f"覆盖文件：{dest_file}")
                            shutil.copy2(source_file, dest_file)
                        elif action == "s":
                            print("跳过文件：", source_file)
                        elif action == "r":
                            base, ext = os.path.splitext(file)
                            count = 1
                            new_name = f"{base} - copy{count}{ext}"
                            new_dest_file = os.path.join(target_dir, new_name)
                            while os.path.exists(new_dest_file):
                                count += 1
                                new_name = f"{base} - copy{count}{ext}"
                                new_dest_file = os.path.join(target_dir, new_name)
                            print(f"重命名复制：{source_file} -> {new_dest_file}")
                            shutil.copy2(source_file, new_dest_file)


if __name__ == "__main__":
    app = SyncApp()
    app.mainloop()

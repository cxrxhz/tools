import os
import shutil
import json
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# 全局配置文件和同步记录文件
CONFIG_FILE = "config.json"
HISTORY_FILE = "sync_history.json"


###########################
# 同步记录相关辅助函数
###########################
def load_sync_history():
    """加载历史同步记录，返回列表"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("加载同步记录失败:", e)
    return []


def save_sync_history(history):
    """保存同步记录列表到文件"""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("保存同步记录失败:", e)


def record_event(session_record, sample, instrument, rel_path, file_name, dest_file, action):
    """
    根据文件的相对路径将事件记录到本次同步记录中。
    以 rel_path 的第一层目录（若为"."则归为"root"）作为分组。
    """
    group = "root" if rel_path == "." else rel_path.split(os.sep)[0]
    session_record.setdefault(sample, {}).setdefault(instrument, {}).setdefault(group, [])
    session_record[sample][instrument][group].append({
        "file": file_name,
        "dest": dest_file,
        "action": action
    })


###########################
# 配置文件辅助函数
###########################
def load_config():
    """加载配置文件（JSON格式），如果存在则返回配置字典，否则返回空字典。"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("加载配置失败:", e)
    return {}


def save_config(config):
    """保存配置字典到配置文件。"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("保存配置失败:", e)


###########################
# 文件操作辅助函数
###########################
def get_file_stat(file_path):
    """获取文件的状态（大小、修改时间等）"""
    try:
        return os.stat(file_path)
    except Exception as e:
        print(f"获取 {file_path} 状态时出错: {e}")
        return None


def get_file_hash(file_path, chunk_size=8192):
    """
    计算文件的 SHA256 哈希值，逐块读取数据，避免一次性加载大文件到内存。
    """
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        print(f"计算哈希出错: {file_path}, 错误: {e}")
        return None


def files_identical(source_file, dest_file, executor, chunk_size=8192):
    """
    判断两个文件是否相同：
      1. 并行调用 get_file_stat() 获取两个文件的大小和修改时间。
      2. 如果大小不同，返回 False；如果大小相同且修改时间（取整）一致，则认为相同。
      3. 若修改时间不同，则并行计算两个文件的哈希值对比。
    """
    future_source_stat = executor.submit(get_file_stat, source_file)
    future_dest_stat = executor.submit(get_file_stat, dest_file)
    stat_source = future_source_stat.result()
    stat_dest = future_dest_stat.result()
    if stat_source is None or stat_dest is None:
        return False
    if stat_source.st_size != stat_dest.st_size:
        return False
    if int(stat_source.st_mtime) == int(stat_dest.st_mtime):
        return True
    future_source_hash = executor.submit(get_file_hash, source_file, chunk_size)
    future_dest_hash = executor.submit(get_file_hash, dest_file, chunk_size)
    hash_source = future_source_hash.result()
    hash_dest = future_dest_hash.result()
    if hash_source is None or hash_dest is None:
        return False
    return hash_source == hash_dest


def copy_file_task(source, dest):
    """复制文件，保留元数据，并打印日志"""
    try:
        shutil.copy2(source, dest)
        print(f"Copied:\n  {source}\n  -> {dest}")
    except Exception as e:
        print(f"Error copying {source} -> {dest}: {e}")


def prompt_user_dialog(parent, file_name, src_file, dest_file):
    """
    当目标文件存在且内容不同时，弹出对话框供选择：覆盖 (o)、跳过 (s) 或重命名 (r)
    """
    dialog = tk.Toplevel(parent)
    dialog.title("文件冲突")

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

    dialog.grab_set()
    parent.wait_window(dialog)
    return result.get()


def sync_directories(source_dir, dest_dir, parent_window, executor, session_record, sample, instrument):
    """
    遍历 source_dir 中的所有文件和子文件夹，
    将文件复制到 dest_dir（保持相对目录结构），并记录复制事件到 session_record 中。
    """
    for root, dirs, files in os.walk(source_dir):
        rel_path = os.path.relpath(root, source_dir)
        target_dir = os.path.join(dest_dir, rel_path)
        try:
            os.makedirs(target_dir, exist_ok=True)
        except Exception as e:
            print(f"无法创建目录 {target_dir}: {e}")
            continue

        for file in files:
            source_file = os.path.join(root, file)
            dest_file = os.path.join(target_dir, file)
            if not os.path.exists(dest_file):
                print(f"Scheduling copy:\n  {source_file} -> {dest_file}")
                executor.submit(copy_file_task, source_file, dest_file)
                record_event(session_record, sample, instrument, rel_path, file, dest_file, "新复制")
            else:
                if files_identical(source_file, dest_file, executor):
                    print(f"文件一致，跳过:\n  {source_file}")
                else:
                    action = prompt_user_dialog(parent_window, file, source_file, dest_file)
                    if action == "o":
                        print(f"Scheduling overwrite:\n  {source_file} -> {dest_file}")
                        executor.submit(copy_file_task, source_file, dest_file)
                        record_event(session_record, sample, instrument, rel_path, file, dest_file, "覆盖")
                    elif action == "s":
                        print(f"跳过文件:\n  {source_file}")
                    elif action == "r":
                        base, ext = os.path.splitext(file)
                        count = 1
                        new_name = f"{base} - copy{count}{ext}"
                        new_dest_file = os.path.join(target_dir, new_name)
                        while os.path.exists(new_dest_file):
                            count += 1
                            new_name = f"{base} - copy{count}{ext}"
                            new_dest_file = os.path.join(target_dir, new_name)
                        print(f"Scheduling rename copy:\n  {source_file} -> {new_dest_file}")
                        executor.submit(copy_file_task, source_file, new_dest_file)
                        record_event(session_record, sample, instrument, rel_path, new_name, new_dest_file,
                                     "重命名复制")


############################################
# 主界面及同步工具类定义
############################################
class SyncApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("文件同步工具")
        self.geometry("900x500")
        self.config_data = load_config()
        self.repo_root = self.config_data.get("repo_root", "")
        self.usb_root = self.config_data.get("usb_root", "")
        self.create_widgets()

    def create_widgets(self):
        # 数据库（目标）路径组件
        lbl_repo = tk.Label(self, text="数据库路径:")
        lbl_repo.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.entry_repo = tk.Entry(self, width=60)
        self.entry_repo.grid(row=0, column=1, padx=10, pady=10)
        self.entry_repo.insert(0, self.repo_root)
        btn_browse_repo = tk.Button(self, text="浏览", command=self.select_repo)
        btn_browse_repo.grid(row=0, column=2, padx=10, pady=10)

        # U盘（源）路径组件
        lbl_usb = tk.Label(self, text="U盘路径:")
        lbl_usb.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.entry_usb = tk.Entry(self, width=60)
        self.entry_usb.grid(row=1, column=1, padx=10, pady=10)
        self.entry_usb.insert(0, self.usb_root)
        btn_browse_usb = tk.Button(self, text="浏览", command=self.select_usb)
        btn_browse_usb.grid(row=1, column=2, padx=10, pady=10)

        # 开始同步按钮
        btn_sync = tk.Button(self, text="开始同步", command=self.start_sync)
        btn_sync.grid(row=2, column=1, padx=10, pady=20)

        # 查看同步记录按钮
        btn_view_history = tk.Button(self, text="查看同步记录", command=self.show_sync_history)
        btn_view_history.grid(row=2, column=2, padx=10, pady=20)

        self.status_label = tk.Label(self, text="等待操作...", fg="blue")
        self.status_label.grid(row=3, column=1, pady=10)

    def select_repo(self):
        folder = filedialog.askdirectory()
        if folder:
            self.repo_root = folder
            self.entry_repo.delete(0, tk.END)
            self.entry_repo.insert(0, folder)
            self.config_data["repo_root"] = folder
            save_config(self.config_data)
            self.status_label.config(text="数据库路径已更新")

    def select_usb(self):
        folder = filedialog.askdirectory()
        if folder:
            self.usb_root = folder
            self.entry_usb.delete(0, tk.END)
            self.entry_usb.insert(0, folder)
            self.config_data["usb_root"] = folder
            save_config(self.config_data)
            self.status_label.config(text="U盘路径已更新")

    def start_sync(self):
        """
        同步逻辑：
          1. 仅处理数据库中已有的样品文件夹（不会自动创建新的样品文件夹）。
          2. 遍历 U盘根目录下各仪器文件夹（例如 SEM、CIA 等），再遍历其样品文件夹，
             如果该样品存在于数据库中，则目标路径为：数据库路径 / [样品] / [仪器]；
             若目标仪器文件夹不存在，则自动创建；
             然后利用线程池异步复制 USB 中所有文件（保留原有目录结构）。
          3. 对于每个复制任务，根据文件在相对目录中的第一层作为“批次”记录下来。
          4. 如果 USB 中的样品不在数据库中则跳过。
          5. 比较时先判断大小及修改时间，不一致时并发计算哈希值进行最终判断。
        """
        if not self.repo_root:
            messagebox.showwarning("警告", "请先选择数据库路径")
            return
        if not self.usb_root:
            messagebox.showwarning("警告", "请先选择U盘路径")
            return

        self.status_label.config(text="同步进行中...")

        db_samples = [name for name in os.listdir(self.repo_root)
                      if os.path.isdir(os.path.join(self.repo_root, name))]
        db_samples_set = set(db_samples)
        if not db_samples_set:
            messagebox.showwarning("警告", "数据库路径下未找到任何样品文件夹，无法同步数据。")
            self.status_label.config(text="同步终止")
            return

        current_sync_record = {}

        with ThreadPoolExecutor(max_workers=8) as executor:
            for instrument in os.listdir(self.usb_root):
                instrument_path = os.path.join(self.usb_root, instrument)
                if not os.path.isdir(instrument_path):
                    continue
                try:
                    samples_in_instrument = os.listdir(instrument_path)
                except PermissionError:
                    print(f"权限不足，无法访问目录：{instrument_path}，跳过。")
                    continue
                print(f"处理仪器文件夹: {instrument}")
                for sample in samples_in_instrument:
                    sample_usb_folder = os.path.join(instrument_path, sample)
                    if not os.path.isdir(sample_usb_folder):
                        continue
                    if sample not in db_samples_set:
                        print(f"跳过 USB 中不在数据库中的样品: {sample} 在 {instrument_path}")
                        continue
                    dest_sample_folder = os.path.join(self.repo_root, sample)
                    dest_instrument_folder = os.path.join(dest_sample_folder, instrument)
                    if not os.path.exists(dest_instrument_folder):
                        print(f"目标仪器文件夹不存在，自动创建：{dest_instrument_folder}")
                        os.makedirs(dest_instrument_folder, exist_ok=True)
                    print(f"同步：USB [{sample_usb_folder}] -> 数据库 [{dest_instrument_folder}]")
                    sync_directories(sample_usb_folder, dest_instrument_folder, self, executor, current_sync_record,
                                     sample, instrument)

        self.status_label.config(text="同步完成")
        if current_sync_record:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            session_entry = {"timestamp": timestamp, "records": current_sync_record}
            history = load_sync_history()
            history.append(session_entry)
            save_sync_history(history)
            print("同步记录已更新。")

    def show_sync_history(self):
        """打开新窗口显示同步记录，采用折叠菜单形式（默认全部展开，最新记录在上）"""
        history = load_sync_history()
        if not history:
            messagebox.showinfo("同步记录", "没有同步记录。")
            return

        # 对历史记录按时间降序排序（时间格式为"YYYY-MM-DD HH:MM:SS"，字符串排序可直接按时间排序）
        sorted_history = sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)

        hist_window = tk.Toplevel(self)
        hist_window.title("同步记录")
        hist_window.geometry("800x600")

        tree = ttk.Treeview(hist_window)
        tree.pack(fill=tk.BOTH, expand=True)

        # 设置Treeview列
        tree["columns"] = ("action", "dest")
        tree.column("#0", width=300, anchor="w")
        tree.column("action", width=80, anchor="center")
        tree.column("dest", anchor="w")
        tree.heading("#0", text="名称")
        tree.heading("action", text="操作")
        tree.heading("dest", text="文件路径")

        def on_double_click(event):
            item_id = tree.focus()
            values = tree.item(item_id, "values")
            # 如果第三列有内容，则认为是文件记录；打开目标文件
            if values and values[1]:
                file_path = values[1]
                try:
                    os.startfile(file_path)
                except Exception as e:
                    messagebox.showerror("错误", f"无法打开文件: {file_path}\n错误: {e}")

        tree.bind("<Double-1>", on_double_click)

        # 构建树形结构：同步时间 → 样品 → 仪器 → 批次 → 文件；
        # 注意所有节点的open参数都设为True，默认展开所有节点。
        for session in sorted_history:
            ts = session.get("timestamp", "未知时间")
            session_node = tree.insert("", "end", text=ts, open=True)
            records = session.get("records", {})
            for sample, inst_dict in records.items():
                sample_node = tree.insert(session_node, "end", text=sample, open=True)
                for instrument, group_dict in inst_dict.items():
                    inst_node = tree.insert(sample_node, "end", text=instrument, open=True)
                    for group, files in group_dict.items():
                        group_node = tree.insert(inst_node, "end", text=group, open=True)
                        for file_event in files:
                            file_name = file_event.get("file", "")
                            action = file_event.get("action", "")
                            dest = file_event.get("dest", "")
                            tree.insert(group_node, "end", text=file_name, values=(action, dest))

        # 增加垂直滚动条
        vsb = ttk.Scrollbar(hist_window, orient="vertical", command=tree.yview)
        vsb.pack(side='right', fill='y')
        tree.configure(yscrollcommand=vsb.set)


if __name__ == "__main__":
    app = SyncApp()
    app.mainloop()

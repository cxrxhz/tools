import os
import shutil
import json
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from PIL import Image, ImageTk

CONFIG_FILE = "config.json"
HISTORY_FILE = "sync_history.json"
IGNORE_FILE = "ignore_samples.json"
ICON_SIZE = (16, 16)  # 图标大小


############################################
# 同步记录相关辅助函数（历史记录）
############################################
def load_sync_history():
    """加载历史同步记录，返回记录列表"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("加载同步记录失败:", e)
    return []


def save_sync_history(history):
    """将同步记录列表保存到 HISTORY_FILE 中"""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("保存同步记录失败:", e)


def record_event(session_record, sample, instrument, rel_path, file_name, dest_file, action):
    """
    将复制事件记录到本次同步记录中。
    根据文件相对路径的第一层（若为"."，则归为"root"）作为“批次”
    """
    group = "root" if rel_path == "." else rel_path.split(os.sep)[0]
    session_record.setdefault(sample, {}).setdefault(instrument, {}).setdefault(group, [])
    session_record[sample][instrument][group].append({
        "file": file_name,
        "dest": dest_file,
        "action": action
    })


#############################################
# 配置文件辅助函数
#############################################
def load_config():
    """加载配置文件（JSON），存在则返回配置字典，否则返回空字典"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("加载配置失败:", e)
    return {}


def save_config(config):
    """保存配置字典到配置文件"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("保存配置失败:", e)


#############################################
# 忽略列表管理（新样品忽略）
#############################################
def load_ignore_list():
    """加载忽略列表，返回列表，每项格式为 "instrument::sample" """
    if os.path.exists(IGNORE_FILE):
        try:
            with open(IGNORE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("加载忽略列表失败:", e)
    return []


def save_ignore_list(ignore_list):
    """保存忽略列表到文件"""
    try:
        with open(IGNORE_FILE, "w", encoding="utf-8") as f:
            json.dump(ignore_list, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("保存忽略列表失败:", e)


#############################################
# 文件操作辅助函数
#############################################
def get_file_stat(file_path):
    """获取文件的状态（大小、修改时间等）"""
    try:
        return os.stat(file_path)
    except Exception as e:
        print(f"获取 {file_path} 状态时出错: {e}")
        return None


def get_file_hash(file_path, chunk_size=8192):
    """
    计算文件的 SHA256 哈希值，通过分块读取降低内存占用
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
    判断两个文件是否一致：
      1. 并行获取两者的 os.stat（大小、修改时间）
      2. 若大小不同返回 False，若大小相同且取整修改时间相同则认为一致；
      3. 否则并行计算 SHA256 哈希后比较。
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
    """复制文件（保留元数据），并输出复制日志"""
    try:
        shutil.copy2(source, dest)
        print(f"Copied:\n  {source}\n  -> {dest}")
    except Exception as e:
        print(f"Error copying {source} -> {dest}: {e}")


def prompt_user_dialog(parent, file_name, src_file, dest_file):
    """
    当目标文件存在且内容不一致时，弹出对话框供用户选择【覆盖】、【跳过】或【重命名】操作。
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
    遍历 source_dir 下所有文件及子目录，
    将文件复制到目标目录 dest_dir（保持目录结构），
    并记录实际进行的操作（新复制、覆盖、重命名复制）。
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


################################################
# 主界面及应用程序类定义
################################################
class SyncApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("文件同步工具")
        self.geometry("900x500")
        self.config_data = load_config()
        self.repo_root = self.config_data.get("repo_root", "")
        self.usb_root = self.config_data.get("usb_root", "")

        # 加载自定义图标（替换 Treeview 默认展开／折叠指示器）
        try:
            img_closed = Image.open(r"E:\pythonProject\图标库\a-010-letter-closed.ico").convert("RGBA")
            img_open = Image.open(r"E:\pythonProject\图标库\a-010-letter.ico").convert("RGBA")
            if hasattr(img_closed, "n_frames") and img_closed.n_frames > 1:
                img_closed.seek(0)
            if hasattr(img_open, "n_frames") and img_open.n_frames > 1:
                img_open.seek(0)
            img_closed = img_closed.resize(ICON_SIZE, Image.LANCZOS)
            img_open = img_open.resize(ICON_SIZE, Image.LANCZOS)
            self.closedIndicator = ImageTk.PhotoImage(img_closed)
            self.openIndicator = ImageTk.PhotoImage(img_open)
        except Exception as e:
            messagebox.showerror("图标加载错误", f"加载图标失败: {e}")
            self.closedIndicator = None
            self.openIndicator = None

        self.new_samples_window = None  # 保存新样品窗口引用
        self.create_widgets()

    def create_widgets(self):
        lbl_repo = tk.Label(self, text="数据库路径:")
        lbl_repo.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.entry_repo = tk.Entry(self, width=60)
        self.entry_repo.grid(row=0, column=1, padx=10, pady=10)
        self.entry_repo.insert(0, self.repo_root)
        btn_browse_repo = tk.Button(self, text="浏览", command=self.select_repo)
        btn_browse_repo.grid(row=0, column=2, padx=10, pady=10)

        lbl_usb = tk.Label(self, text="U盘路径:")
        lbl_usb.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.entry_usb = tk.Entry(self, width=60)
        self.entry_usb.grid(row=1, column=1, padx=10, pady=10)
        self.entry_usb.insert(0, self.usb_root)
        btn_browse_usb = tk.Button(self, text="浏览", command=self.select_usb)
        btn_browse_usb.grid(row=1, column=2, padx=10, pady=10)

        btn_sync = tk.Button(self, text="开始同步", command=self.start_sync)
        btn_sync.grid(row=2, column=1, padx=10, pady=20)

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
        同步流程：
         1. 扫描数据库根目录下已有的样品（不新建样品）。
         2. 根据每个样品文件夹下的子文件夹确定有效仪器集合（db_instruments_set）。
         3. 遍历 USB 根目录，只有名称在 db_instruments_set 内的文件夹才被当作仪器文件夹处理。
         4. 对于每个 USB 仪器文件夹，内部子目录为样品：
             - 如果样品存在于数据库中，则同步数据到 “样品/仪器” 目录；
             - 如果样品不存在，则记录为新样品供后续处理。
         5. 清理忽略列表：如果忽略记录中对应的 USB 文件夹已不存在，则从忽略列表中删除记录。
         6. 同步过程采用多线程处理，并记录实际复制操作到同步历史中。
        """
        if not self.repo_root:
            messagebox.showwarning("警告", "请先选择数据库路径")
            return
        if not self.usb_root:
            messagebox.showwarning("警告", "请先选择U盘路径")
            return

        self.status_label.config(text="同步进行中...")

        # 获取数据库中已有样品名称（不新建样品）
        db_samples = [name for name in os.listdir(self.repo_root)
                      if os.path.isdir(os.path.join(self.repo_root, name))]
        db_samples_set = set(db_samples)

        # 根据数据库中每个样品文件夹的子文件夹确定有效仪器名称集合
        db_instruments_set = set()
        for sample in db_samples:
            sample_path = os.path.join(self.repo_root, sample)
            try:
                for item in os.listdir(sample_path):
                    if os.path.isdir(os.path.join(sample_path, item)):
                        db_instruments_set.add(item)
            except Exception as e:
                print(f"读取 {sample_path} 内子目录时出错: {e}")

        # 先清理忽略列表：保留当前 USB 上仍存在的 “instrument::sample” 记录
        usb_ignore_keys = set()
        if os.path.isdir(self.usb_root):
            for instrument in os.listdir(self.usb_root):
                instrument_path = os.path.join(self.usb_root, instrument)
                if not os.path.isdir(instrument_path):
                    continue
                if instrument not in db_instruments_set:
                    continue
                try:
                    for sample in os.listdir(instrument_path):
                        sample_path = os.path.join(instrument_path, sample)
                        if os.path.isdir(sample_path):
                            usb_ignore_keys.add(f"{instrument}::{sample}")
                except Exception as e:
                    print(f"读取 {instrument_path} 内部时出错: {e}")
        ignore_list = load_ignore_list()
        new_ignore_list = [key for key in ignore_list if key in usb_ignore_keys]
        if set(ignore_list) != set(new_ignore_list):
            save_ignore_list(new_ignore_list)
            ignore_list = new_ignore_list

        new_samples = []  # 用于保存新样品记录
        current_sync_record = {}

        with ThreadPoolExecutor(max_workers=8) as executor:
            # 遍历 USB 根目录，筛选名称在 db_instruments_set 内的文件夹作为仪器文件夹
            for instrument in os.listdir(self.usb_root):
                instrument_path = os.path.join(self.usb_root, instrument)
                if not os.path.isdir(instrument_path):
                    continue
                if instrument not in db_instruments_set:
                    print(f"USB 文件夹 {instrument} 不在有效仪器列表中，忽略。")
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
                    if sample in db_samples_set:
                        # 样品存在于数据库中：同步数据
                        dest_sample_folder = os.path.join(self.repo_root, sample)
                        dest_instrument_folder = os.path.join(dest_sample_folder, instrument)
                        if not os.path.exists(dest_instrument_folder):
                            print(f"目标仪器文件夹不存在，自动创建：{dest_instrument_folder}")
                            os.makedirs(dest_instrument_folder, exist_ok=True)
                        print(f"同步：USB [{sample_usb_folder}] -> 数据库 [{dest_instrument_folder}]")
                        sync_directories(sample_usb_folder, dest_instrument_folder, self, executor, current_sync_record,
                                         sample, instrument)
                    else:
                        # 新样品：记录以供后续处理
                        key = f"{instrument}::{sample}"
                        if key in ignore_list:
                            print(f"新样品 {sample} 来自 {instrument} 已在忽略列表中，跳过。")
                        else:
                            print(f"发现新样品：{sample} 来自 {instrument}")
                            new_samples.append({
                                "instrument": instrument,
                                "sample": sample,
                                "usb_path": sample_usb_folder
                            })

        self.status_label.config(text="同步完成")
        if current_sync_record:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            session_entry = {"timestamp": timestamp, "records": current_sync_record}
            history = load_sync_history()
            history.append(session_entry)
            save_sync_history(history)
            print("同步记录已更新。")
        if new_samples:
            self.show_new_samples_window(new_samples)

    def show_new_samples_window(self, new_samples):
        """
        弹出新样品处理窗口，显示新发现的样品列表，并提供以下操作：
          1. 删除 USB 中该新样品文件夹
          2. 在数据库中新创建对应的新样品文件夹（连同仪器目录），并同步其内容
          3. 忽略：记录该新样品（格式 "instrument::sample"）到忽略文件，下次自动跳过
        """
        if self.new_samples_window is not None and self.new_samples_window.winfo_exists():
            self.new_samples_window.deiconify()
            self.new_samples_window.lift()
            return

        top = tk.Toplevel(self)
        top.title("新样品处理")
        top.geometry("600x400")
        self.new_samples_window = top

        def on_close():
            self.new_samples_window = None
            top.destroy()

        top.protocol("WM_DELETE_WINDOW", on_close)

        frame = tk.Frame(top)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("仪器", "样品", "USB路径")
        tree = ttk.Treeview(frame, columns=cols, show='headings')
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor="w")
        tree.pack(fill=tk.BOTH, expand=True)

        for item in new_samples:
            tree.insert("", "end", values=(item["instrument"], item["sample"], item["usb_path"]))

        btn_frame = tk.Frame(top)
        btn_frame.pack(pady=10)

        def delete_selected():
            selected = tree.selection()
            for item in selected:
                values = tree.item(item, "values")
                if not values:
                    continue
                instrument, sample, usb_path = values
                try:
                    shutil.rmtree(usb_path)
                    messagebox.showinfo("删除", f"已删除 USB 中 {sample} 来自 {instrument} 的文件夹")
                    tree.delete(item)
                except Exception as e:
                    messagebox.showerror("错误", f"删除失败：{e}")

        def create_selected():
            selected = tree.selection()
            for item in selected:
                values = tree.item(item, "values")
                if not values:
                    continue
                instrument, sample, usb_path = values
                dest_sample_folder = os.path.join(self.repo_root, sample)
                if not os.path.exists(dest_sample_folder):
                    try:
                        os.makedirs(dest_sample_folder)
                    except Exception as e:
                        messagebox.showerror("错误", f"无法创建样品文件夹 {sample}：{e}")
                        continue
                dest_instrument_folder = os.path.join(dest_sample_folder, instrument)
                if not os.path.exists(dest_instrument_folder):
                    try:
                        os.makedirs(dest_instrument_folder)
                    except Exception as e:
                        messagebox.showerror("错误", f"无法创建仪器文件夹 {instrument}：{e}")
                        continue
                with ThreadPoolExecutor(max_workers=4) as executor:
                    sync_directories(usb_path, dest_instrument_folder, self, executor, {}, sample, instrument)
                messagebox.showinfo("新样品", f"已在数据库中新建 {sample} 下的 {instrument} 文件夹，并同步数据")
                tree.delete(item)

        def ignore_selected():
            selected = tree.selection()
            ignore_list = load_ignore_list()
            for item in selected:
                values = tree.item(item, "values")
                if not values:
                    continue
                instrument, sample, _ = values
                key = f"{instrument}::{sample}"
                if key not in ignore_list:
                    ignore_list.append(key)
            save_ignore_list(ignore_list)
            messagebox.showinfo("忽略", "已忽略所选新样品，以后自动跳过")
            for item in selected:
                tree.delete(item)

        btn_delete = tk.Button(btn_frame, text="删除 USB 文件夹", command=delete_selected)
        btn_delete.pack(side=tk.LEFT, padx=5)
        btn_create = tk.Button(btn_frame, text="在数据库中新建样品", command=create_selected)
        btn_create.pack(side=tk.LEFT, padx=5)
        btn_ignore = tk.Button(btn_frame, text="忽略", command=ignore_selected)
        btn_ignore.pack(side=tk.LEFT, padx=5)

        top.transient(self)
        top.grab_set()
        self.wait_window(top)

    def show_sync_history(self):
        history = load_sync_history()
        if not history:
            messagebox.showinfo("同步记录", "没有同步记录。")
            return

        sorted_history = sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.layout("Custom.Treeview.Item", [
            ('Treeitem.padding', {
                'sticky': 'nswe',
                'children': [
                    ('Treeitem.image', {'side': 'left', 'sticky': ''}),
                    ('Treeitem.text', {'side': 'left', 'sticky': ''})
                ]
            })
        ])
        style.configure("Custom.Treeview", highlightthickness=0, bd=0, font=('TkDefaultFont', 10))

        hist_window = tk.Toplevel(self)
        hist_window.title("同步记录")
        hist_window.geometry("800x600")

        tree = ttk.Treeview(hist_window, style="Custom.Treeview")
        tree.pack(fill=tk.BOTH, expand=True)

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
            if values and values[1]:
                file_path = values[1]
                try:
                    os.startfile(file_path)
                except Exception as e:
                    messagebox.showerror("错误", f"无法打开文件: {file_path}\n错误: {e}")

        tree.bind("<Double-1>", on_double_click)

        def on_single_click(event):
            item_id = tree.identify_row(event.y)
            if item_id and tree.get_children(item_id):
                current_state = tree.item(item_id, "open")
                tree.item(item_id, open=not current_state)
                if not current_state:
                    tree.item(item_id, image=self.openIndicator)
                else:
                    tree.item(item_id, image=self.closedIndicator)

        tree.bind("<Button-1>", on_single_click)

        for session in sorted_history:
            ts = session.get("timestamp", "未知时间")
            session_node = tree.insert("", "end", text=ts, image=self.openIndicator, open=True)
            records = session.get("records", {})
            for sample, inst_dict in records.items():
                sample_node = tree.insert(session_node, "end", text=sample, image=self.openIndicator, open=True)
                for instrument, group_dict in inst_dict.items():
                    inst_node = tree.insert(sample_node, "end", text=instrument, image=self.openIndicator, open=True)
                    for group, files in group_dict.items():
                        group_node = tree.insert(inst_node, "end", text=group, image=self.openIndicator, open=True)
                        for file_event in files:
                            file_name = file_event.get("file", "")
                            action = file_event.get("action", "")
                            dest = file_event.get("dest", "")
                            tree.insert(group_node, "end", text=file_name, values=(action, dest))
        vsb = ttk.Scrollbar(hist_window, orient="vertical", command=tree.yview)
        vsb.pack(side='right', fill='y')
        tree.configure(yscrollcommand=vsb.set)


if __name__ == "__main__":
    app = SyncApp()
    app.mainloop()

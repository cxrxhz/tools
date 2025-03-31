import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import sys
import platform
import json
from pathlib import Path


class PyInstallerGUI:
    def __init__(self, master):
        self.master = master
        master.title("EXE打包工具 v2.0 (支持依赖项)")
        master.geometry("800x600")

        # 初始化路径配置
        self.pathsep = ";" if platform.system() == "Windows" else ":"
        self.dependency_map = self.load_dependency_map()

        # 创建界面
        self.create_widgets()

    def load_dependency_map(self):
        """加载依赖项数据库"""
        with open("dependency_map.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="选择Python脚本")
        file_frame.pack(fill=tk.X, pady=5)

        self.script_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.script_path, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="浏览...", command=self.select_script).pack(side=tk.LEFT)

        # 参数配置区域
        config_frame = ttk.LabelFrame(main_frame, text="打包参数设置")
        config_frame.pack(fill=tk.X, pady=5)

        # 单文件选项
        self.onefile = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="打包为单个文件(--onefile)",
                        variable=self.onefile).pack(anchor=tk.W)

        # 控制台窗口选项
        self.noconsole = tk.BooleanVar()
        ttk.Checkbutton(config_frame, text="隐藏控制台窗口(--noconsole)",
                        variable=self.noconsole).pack(anchor=tk.W)

        # 图标选择
        icon_frame = ttk.Frame(config_frame)
        icon_frame.pack(fill=tk.X, pady=2)
        self.icon_path = tk.StringVar()
        ttk.Entry(icon_frame, textvariable=self.icon_path, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(icon_frame, text="选择图标...", command=self.select_icon).pack(side=tk.LEFT)

        # 附加数据文件夹
        data_frame = ttk.Frame(config_frame)
        data_frame.pack(fill=tk.X, pady=2)
        self.add_data = tk.StringVar()
        ttk.Entry(data_frame, textvariable=self.add_data, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(data_frame, text="添加文件夹...", command=self.add_data_folder).pack(side=tk.LEFT)

        # 隐藏导入模块
        self.hidden_imports = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.hidden_imports,
                  width=50).pack(fill=tk.X, pady=5)
        ttk.Label(config_frame, text="隐藏导入模块(--hidden-import)，多个用逗号分隔").pack(anchor=tk.W)

        # 输出名称
        name_frame = ttk.Frame(config_frame)
        name_frame.pack(fill=tk.X, pady=2)
        ttk.Label(name_frame, text="输出名称:").pack(side=tk.LEFT)
        self.name = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.name, width=30).pack(side=tk.LEFT, padx=5)

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        self.start_btn = ttk.Button(btn_frame, text="开始打包", command=self.start_build)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="退出", command=self.master.quit).pack(side=tk.RIGHT)

        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="打包日志")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log = tk.Text(log_frame, wrap=tk.WORD)
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)

        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def select_script(self):
        """选择Python脚本"""
        path = filedialog.askopenfilename(
            title="选择要打包的Python脚本",
            filetypes=[("Python文件", "*.py"), ("所有文件", "*.*")]
        )
        if path:
            self.script_path.set(path)
            # 自动设置默认输出名称
            base = os.path.basename(path).split('.')[0]
            self.name.set(base)

    def select_icon(self):
        """选择图标文件"""
        path = filedialog.askopenfilename(
            title="选择程序图标",
            filetypes=[("图标文件", "*.ico"), ("所有文件", "*.*")]
        )
        if path:
            self.icon_path.set(path)

    def add_data_folder(self):
        """添加数据文件夹"""
        path = filedialog.askdirectory(title="选择附加数据文件夹")
        if path:
            # 格式：源路径[分隔符]目标路径
            target = os.path.basename(path)
            self.add_data.set(f"{path}{self.pathsep}{target}")

    def scan_dependencies(self, script_path):
        """核心改进：扫描并识别依赖项"""
        required = []
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read().lower()
            for lib in self.dependency_map:
                if f"import {lib}" in content or f"from {lib}" in content:
                    required.append(lib)
        return required

    def start_build(self):
        """完整的打包启动逻辑（含自动依赖处理）"""
        if not self.script_path.get():
            messagebox.showerror("错误", "请先选择要打包的Python脚本！")
            return

        # 构建基础命令
        cmd = ["pyinstaller", "--onefile"]

        # 添加基本参数
        if self.noconsole.get():
            cmd.append("--noconsole")
        if self.name.get():
            cmd.extend(["--name", self.name.get()])
        if self.icon_path.get():
            cmd.extend(["--icon", f'"{self.icon_path.get()}"'])

        # 自动扫描依赖项
        try:
            dependencies = self.scan_dependencies(self.script_path.get())
            self.log.insert(tk.END, f"检测到依赖项: {', '.join(dependencies)}\n")
        except Exception as e:
            messagebox.showerror("扫描错误", f"依赖扫描失败: {str(e)}")
            return

        # 添加依赖项参数
        for lib in dependencies:
            if lib in self.dependency_map:
                for item in self.dependency_map[lib]["files"]:
                    # 平台过滤
                    if platform.system().lower() not in item["platform"]:
                        continue

                    # 构建源路径和目标路径
                    src_path = Path(sys.base_prefix) / item["source"]
                    dest_path = item["dest"]

                    if not src_path.exists():
                        self.log.insert(tk.END, f"⚠️ 警告: 未找到依赖文件 {src_path}\n")
                        continue

                    # 添加打包参数
                    cmd.extend([
                        "--add-data",
                        f"{src_path.resolve()}{self.pathsep}{dest_path}"
                    ])
                    self.log.insert(tk.END, f"添加依赖: {src_path} → {dest_path}\n")

        # 添加用户定义的其他参数
        if self.add_data.get():
            for data in self.add_data.get().split(self.pathsep):
                cmd.extend(["--add-data", data])
                self.log.insert(tk.END, f"添加用户数据: {data}\n")

        # 添加隐藏导入
        if hidden_imports := self.hidden_imports.get():
            for imp in hidden_imports.split(','):
                cmd.extend(["--hidden-import", imp.strip()])
                self.log.insert(tk.END, f"添加隐藏导入: {imp.strip()}\n")

        # 添加目标脚本
        cmd.append(f'"{self.script_path.get()}"')

        # 禁用按钮防止重复点击
        self.start_btn.config(state=tk.DISABLED, text="打包中...")

        # 在后台线程执行打包
        threading.Thread(target=self.run_pyinstaller, args=(cmd,)).start()

    def run_pyinstaller(self, cmd):
        """执行PyInstaller命令"""
        try:
            # 将命令列表转换为字符串（处理空格）
            cmd_str = " ".join(cmd)
            self.log.insert(tk.END, f"执行命令: {cmd_str}\n")

            # 创建子进程
            proc = subprocess.Popen(
                cmd_str,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True,
                encoding="utf-8",  # 指定编码为UTF-8
                errors="replace"  # 替换无法解码的字符
            )

            # 实时输出日志
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    self.log.insert(tk.END, line)
                    self.log.see(tk.END)  # 自动滚动到底部

            # 检查返回码
            return_code = proc.poll()
            if return_code == 0:
                self.log.insert(tk.END, "\n打包成功完成！\n")
            else:
                self.log.insert(tk.END, f"\n打包失败，错误码: {return_code}\n")

        except Exception as e:
            self.log.insert(tk.END, f"发生错误: {str(e)}\n")

        finally:
            # 恢复按钮状态
            self.start_btn.config(state=tk.NORMAL, text="开始打包")
            self.log.insert(tk.END, "操作完成。\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = PyInstallerGUI(root)
    root.mainloop()
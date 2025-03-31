import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinterdnd2 import TkinterDnD, DND_FILES
import subprocess
import os


class PandocConverterGUI(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pandoc 全能文档转换工具")
        self.geometry("800x600")

        # 扩展名映射字典（新增关键部分）
        self.extension_map = {
            "latex": "tex",
            "context": "tex",
            "markdown": "md",
            "html5": "html",
            "xhtml5": "xhtml",
            "jats": "xml",
            "tei": "xml",
            "docbook5": "xml",
            "epub3": "epub",
            "epub": "epub",
            "asciidoc": "adoc",
            "mediawiki": "mediawiki",
            "textile": "textile"
        }

        # 更新后的格式分类（显示名称包含扩展提示）
        self.output_categories = {
            "办公文档": [
                ("Word 文档 (.docx)", "docx"),
                ("OpenDocument (.odt)", "odt"),
                ("富文本格式 (.rtf)", "rtf")
            ],
            "电子书": [
                ("EPUB 3 (.epub)", "epub3"),
                ("EPUB 2 (.epub)", "epub"),
                ("Kindle Mobi (.azw3)", "azw3")
            ],
            "排版格式": [
                ("PDF (需要 LaTeX)", "pdf"),
                ("LaTeX 文档 (.tex)", "latex"),
                ("ConTeXt (.tex)", "context")
            ],
            "网页格式": [
                ("HTML5 (.html)", "html5"),
                ("XHTML5 (.xhtml)", "xhtml5"),
                ("Markdown (.md)", "markdown")
            ],
            "学术格式": [
                ("JATS XML (.xml)", "jats"),
                ("TEI Simple (.xml)", "tei"),
                ("DocBook 5 (.xml)", "docbook5")
            ],
            "其他格式": [
                ("AsciiDoc (.adoc)", "asciidoc"),
                ("MediaWiki (.mediawiki)", "mediawiki"),
                ("Textile (.textile)", "textile")
            ]
        }

        self.create_widgets()

    def create_widgets(self):
        # 标签页容器
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # 文件转换标签页
        self.file_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.file_tab, text="文件转换")
        self.create_file_tab()

        # 代码转换标签页
        self.code_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.code_tab, text="代码转换")
        self.create_code_tab()

        # 状态栏
        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var).pack(side="bottom", fill="x")

    def create_file_tab(self):
        # 文件拖拽区域
        self.drop_label = ttk.Label(
            self.file_tab,
            text="拖拽文件到此区域 或 点击选择文件",
            relief="groove",
            padding=20
        )
        self.drop_label.pack(pady=20, fill="x", padx=20)
        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind("<<Drop>>", self.on_file_drop)

        # 格式选择框架
        format_frame = ttk.LabelFrame(self.file_tab, text="选择输出格式")
        format_frame.pack(pady=10, fill="x", padx=20)

        # 分类选择
        self.category_var = tk.StringVar()
        self.category_combobox = ttk.Combobox(
            format_frame,
            textvariable=self.category_var,
            values=list(self.output_categories.keys()),
            state="readonly",
            width=15
        )
        self.category_combobox.pack(side="left", padx=5)
        self.category_combobox.bind("<<ComboboxSelected>>", self.update_format_list)

        # 格式选择（带搜索）
        self.format_var = tk.StringVar()
        self.format_combobox = ttk.Combobox(
            format_frame,
            textvariable=self.format_var,
            state="readonly",
            width=40
        )
        self.format_combobox.pack(side="left", padx=5)

        # 转换按钮
        ttk.Button(
            self.file_tab,
            text="转换文件",
            command=self.convert_file
        ).pack(pady=10)

        # 设置文件转换默认选项
        self.category_var.set("办公文档")  # 默认分类
        self.update_format_list()  # 强制更新格式列表
        self.format_var.set("Word 文档 (.docx)")  # 默认格式

    # def create_code_tab(self):
    #     # 代码输入框
    #     self.code_input = scrolledtext.ScrolledText(
    #         self.code_tab,
    #         wrap=tk.WORD,
    #         height=20
    #     )
    #     self.code_input.pack(expand=True, fill="both", padx=10, pady=5)
    #
    #     # 代码转换格式选择
    #     code_format_frame = ttk.Frame(self.code_tab)
    #     code_format_frame.pack(pady=10)
    #
    #     ttk.Label(code_format_frame, text="输出格式:").pack(side="left")
    #     self.code_format_var = tk.StringVar()
    #     code_format_combobox = ttk.Combobox(
    #         code_format_frame,
    #         textvariable=self.code_format_var,
    #         values=[fmt[1] for category in self.output_categories.values() for fmt in category],
    #         state="readonly",
    #         width=20
    #     )
    #     code_format_combobox.pack(side="left", padx=5)
    #     code_format_combobox.set("docx")
    #
    #     # 转换按钮
    #     ttk.Button(
    #         self.code_tab,
    #         text="转换代码",
    #         command=self.convert_code
    #     ).pack()

    def on_file_drop(self, event):
        """处理文件拖拽事件"""
        file_path = event.data.strip().split()[0]
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]  # 移除转义花括号
        self.input_file = file_path
        self.drop_label.config(text=f"已选择文件：\n{os.path.basename(file_path)}")

    def update_format_list(self, event=None):
        """更新格式列表"""
        category = self.category_var.get()
        formats = self.output_categories.get(category, [])
        self.format_combobox["values"] = [fmt[0] for fmt in formats]
        if formats:
            self.format_combobox.current(0)

    def convert_file(self):
        if not hasattr(self, 'input_file'):
            messagebox.showerror("错误", "请先选择输入文件！")
            return

        selected_format = next(
            (fmt[1] for category in self.output_categories.values()
             for fmt in category if fmt[0] == self.format_var.get()),
            None
        )
        if not selected_format:
            messagebox.showerror("错误", "请选择有效的输出格式！")
            return

        # 获取正确扩展名（关键修复）
        ext = self.extension_map.get(selected_format, selected_format)

        # 生成带正确扩展名的输出路径
        output_dir = os.path.dirname(self.input_file)
        base_name = os.path.splitext(os.path.basename(self.input_file))[0]
        output_file = os.path.join(output_dir, f"{base_name}_converted.{ext}")

        # 构建命令（新增PDF引擎检查）
        cmd = ["pandoc", self.input_file, "-o", output_file]
        if selected_format == "pdf":
            if not self.check_latex():
                messagebox.showerror("错误", "请先安装LaTeX环境（如MiKTeX或TeX Live）")
                return
            cmd += ["--pdf-engine=xelatex"]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            self.status_var.set(f"转换成功！保存至：\n{output_file}")
            messagebox.showinfo("成功", f"文件已保存为：{os.path.basename(output_file)}")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() or "未知错误"
            self.status_var.set(f"转换失败：{error_msg}")
            messagebox.showerror("错误", f"Pandoc错误：\n{error_msg}")

    def _show_success(self, path):
        self.convert_btn.config(state="normal")
        messagebox.showinfo("成功", f"文件已保存为：{os.path.basename(path)}")

    def _show_error(self, msg):
        self.convert_btn.config(state="normal")
        messagebox.showerror("错误", msg)

    def check_latex(self):
        try:
            subprocess.run(["xelatex", "--version"],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def create_code_tab(self):
        """代码转换标签页布局"""
        # 输入格式框架
        input_frame = ttk.Frame(self.code_tab)
        input_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(input_frame, text="输入格式:").pack(side="left")
        self.input_format_var = tk.StringVar(value="latex")
        ttk.Combobox(
            input_frame,
            textvariable=self.input_format_var,
            values=["markdown", "html", "latex", "rst", "textile"],
            state="readonly",
            width=15
        ).pack(side="left", padx=5)

        # 输出格式框架
        output_frame = ttk.Frame(self.code_tab)
        output_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(output_frame, text="输出格式:").pack(side="left")
        self.code_format_var = tk.StringVar()
        code_format_combobox = ttk.Combobox(
            output_frame,
            textvariable=self.code_format_var,
            values=[fmt[1] for category in self.output_categories.values() for fmt in category],
            state="readonly",
            width=20
        )
        code_format_combobox.pack(side="left", padx=5)
        code_format_combobox.set("docx")

        # 代码输入框
        self.code_input = scrolledtext.ScrolledText(
            self.code_tab,
            wrap=tk.WORD,
            height=20
        )
        self.code_input.pack(expand=True, fill="both", padx=10, pady=5)

        # 转换按钮
        ttk.Button(
            self.code_tab,
            text="开始转换",
            command=self.convert_code
        ).pack(pady=10)

    # 修复后的代码转换方法
    def convert_code(self):
        """完整的代码转换逻辑"""
        # 获取输入内容
        code = self.code_input.get("1.0", tk.END).strip()
        if not code:
            messagebox.showerror("错误", "输入内容不能为空！")
            return

        # 获取格式参数
        input_format = self.input_format_var.get()
        output_format = self.code_format_var.get()
        if not output_format:
            messagebox.showerror("错误", "请选择输出格式！")
            return

        # 获取正确扩展名
        ext = self.extension_map.get(output_format, output_format)

        # 弹出保存对话框
        output_path = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            filetypes=[(f"{output_format.upper()}文件", f"*.{ext}")]
        )
        if not output_path:
            return

        # 编码处理（自动检测UTF-8/GBK）
        try:
            encoded_code = code.encode("utf-8")
        except UnicodeEncodeError:
            try:
                encoded_code = code.encode("gbk", errors="ignore")
            except Exception as e:
                messagebox.showerror("编码错误", f"无法处理文本编码: {str(e)}")
                return

        # 构建Pandoc命令
        cmd = ["pandoc", "-f", input_format, "-t", output_format, "-o", output_path]
        if output_format == "pdf":
            cmd += ["--pdf-engine=xelatex"]  # PDF需要LaTeX支持

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # 带超时控制的通信
            try:
                stdout, stderr = process.communicate(
                    input=encoded_code,
                    timeout=30  # 设置30秒超时
                )
            except subprocess.TimeoutExpired:
                process.kill()
                messagebox.showerror("错误", "转换超时，已终止进程！")
                return

            # 处理转换结果
            if process.returncode == 0:
                self.status_var.set(f"✅ 转换成功: {os.path.basename(output_path)}")
                messagebox.showinfo("成功", f"文件已保存至:\n{output_path}")
            else:
                error_msg = stderr.decode("utf-8", errors="ignore") if stderr else "未知错误"
                self.status_var.set(f"❌ 转换失败: {error_msg[:50]}...")
                messagebox.showerror("Pandoc错误", f"详细错误信息:\n{error_msg}")

        except FileNotFoundError:
            messagebox.showerror("错误", "未找到Pandoc，请确认已正确安装！")
        except Exception as e:
            messagebox.showerror("系统错误", f"发生意外错误:\n{str(e)}")


if __name__ == "__main__":
    app = PandocConverterGUI()
    app.mainloop()
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Pandoc 全能文档转换工具（单文件版本）
优化点：
  • 配置、转换逻辑与 UI 结构在单文件中分区实现，保证代码可读性
  • Pandoc 调用封装在独立的类中，便于扩展或单元测试
  • 修复了“点击选择文件”无反应的问题，现在点击区域将弹出文件选择对话框
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinterdnd2 import TkinterDnD, DND_FILES
import subprocess
import os

# ------------------------------------------------------------
# 配置数据区：扩展名映射与输出格式分类
# ------------------------------------------------------------
EXTENSION_MAP = {
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

OUTPUT_CATEGORIES = {
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

# ------------------------------------------------------------
# Pandoc 转换器：封装所有 Pandoc 调用逻辑
# ------------------------------------------------------------
class PandocConverter:
    def __init__(self, extension_map):
        self.extension_map = extension_map

    def build_output_path(self, input_file, selected_format):
        ext = self.extension_map.get(selected_format, selected_format)
        output_dir = os.path.dirname(input_file)
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        return os.path.join(output_dir, f"{base_name}_converted.{ext}")

    def convert_file(self, input_file, selected_format):
        output_file = self.build_output_path(input_file, selected_format)
        cmd = ["pandoc", input_file, "-o", output_file]
        if selected_format == "pdf":
            if not self.check_latex():
                raise EnvironmentError("请先安装LaTeX环境（如MiKTeX或TeX Live）")
            cmd += ["--pdf-engine=xelatex"]
        result = subprocess.run(cmd, check=True, capture_output=True)
        return output_file, result

    def convert_code(self, code, input_format, output_format, output_path):
        cmd = ["pandoc", "-f", input_format, "-t", output_format, "-o", output_path]
        if output_format == "pdf":
            cmd += ["--pdf-engine=xelatex"]
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(input=code.encode("utf-8"), timeout=30)
        return process.returncode, stdout, stderr

    def check_latex(self):
        try:
            subprocess.run(["xelatex", "--version"],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

# ------------------------------------------------------------
# 文件转换标签页：支持拖拽文件、点击选择文件及格式选择
# ------------------------------------------------------------
class FileConversionTab(ttk.Frame):
    def __init__(self, parent, output_categories, drop_callback, convert_callback):
        super().__init__(parent)
        self.output_categories = output_categories
        self.drop_callback = drop_callback
        self.convert_callback = convert_callback
        self.create_widgets()

    def create_widgets(self):
        self.drop_label = ttk.Label(
            self,
            text="拖拽文件到此区域 或 点击选择文件",
            relief="groove",
            padding=20
        )
        self.drop_label.pack(pady=20, fill="x", padx=20)
        # 注册拖拽目标
        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind("<<Drop>>", self.drop_callback)
        # 绑定鼠标点击事件
        self.drop_label.bind("<Button-1>", self.on_click_choose_file)

        format_frame = ttk.LabelFrame(self, text="选择输出格式")
        format_frame.pack(pady=10, fill="x", padx=20)

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

        self.format_var = tk.StringVar()
        self.format_combobox = ttk.Combobox(
            format_frame,
            textvariable=self.format_var,
            state="readonly",
            width=40
        )
        self.format_combobox.pack(side="left", padx=5)

        ttk.Button(self, text="转换文件", command=self.convert_callback).pack(pady=10)
        # 默认选择分类 “办公文档”
        self.category_var.set("办公文档")
        self.update_format_list()

    def update_format_list(self, event=None):
        category = self.category_var.get()
        formats = self.output_categories.get(category, [])
        self.format_combobox["values"] = [fmt[0] for fmt in formats]
        if formats:
            self.format_combobox.current(0)

    def on_click_choose_file(self, event):
        """
        点击标签时，弹出文件选择对话框，选择文件后调用 drop_callback 模拟拖拽事件
        """
        file_path = filedialog.askopenfilename()
        if file_path:
            # 构造一个简单的模拟事件，其 data 属性存放所选文件的路径
            class DummyEvent:
                pass
            dummy_event = DummyEvent()
            dummy_event.data = file_path
            self.drop_callback(dummy_event)

# ------------------------------------------------------------
# 代码转换标签页：代码输入、格式选择及输出路径选择
# ------------------------------------------------------------
class CodeConversionTab(ttk.Frame):
    def __init__(self, parent, output_categories, convert_callback):
        super().__init__(parent)
        self.output_categories = output_categories
        self.convert_callback = convert_callback
        self.create_widgets()

    def create_widgets(self):
        # 输入格式选择
        input_frame = ttk.Frame(self)
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

        # 输出格式选择
        output_frame = ttk.Frame(self)
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

        # 代码输入区域
        self.code_input = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=20)
        self.code_input.pack(expand=True, fill="both", padx=10, pady=5)

        ttk.Button(self, text="开始转换", command=self.convert_callback).pack(pady=10)

# ------------------------------------------------------------
# 主窗口：组合文件转换与代码转换标签页并调用转换逻辑
# ------------------------------------------------------------
class PandocConverterGUI(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pandoc 全能文档转换工具")
        self.geometry("800x600")
        self.converter = PandocConverter(EXTENSION_MAP)
        self.input_file = None  # 存储用户选择的文件路径
        self.create_widgets()

    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # 文件转换标签页
        self.file_tab = FileConversionTab(self.notebook, OUTPUT_CATEGORIES, self.on_file_drop, self.convert_file)
        self.notebook.add(self.file_tab, text="文件转换")
        # 代码转换标签页
        self.code_tab = CodeConversionTab(self.notebook, OUTPUT_CATEGORIES, self.convert_code)
        self.notebook.add(self.code_tab, text="代码转换")

        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var).pack(side="bottom", fill="x")

    def on_file_drop(self, event):
        file_path = event.data.strip().split()[0]
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]
        self.input_file = file_path
        self.file_tab.drop_label.config(text=f"已选择文件：\n{os.path.basename(file_path)}")

    def convert_file(self):
        if not self.input_file:
            messagebox.showerror("错误", "请先选择输入文件！")
            return

        # 根据下拉框中用户选择的格式寻找对应的格式码
        selected_format = None
        for category in OUTPUT_CATEGORIES.values():
            for fmt in category:
                if fmt[0] == self.file_tab.format_var.get():
                    selected_format = fmt[1]
                    break
            if selected_format:
                break

        if not selected_format:
            messagebox.showerror("错误", "请选择有效的输出格式！")
            return

        try:
            output_file, _ = self.converter.convert_file(self.input_file, selected_format)
            self.status_var.set(f"转换成功！保存至：\n{output_file}")
            messagebox.showinfo("成功", f"文件已保存为：{os.path.basename(output_file)}")
        except EnvironmentError as e:
            messagebox.showerror("错误", str(e))
        except Exception as e:
            messagebox.showerror("错误", f"转换失败：{str(e)}")

    def convert_code(self):
        code = self.code_tab.code_input.get("1.0", tk.END).strip()
        if not code:
            messagebox.showerror("错误", "输入内容不能为空！")
            return

        input_format = self.code_tab.input_format_var.get()
        output_format = self.code_tab.code_format_var.get()
        if not output_format:
            messagebox.showerror("错误", "请选择输出格式！")
            return

        # 根据映射获取正确文件后缀
        ext = EXTENSION_MAP.get(output_format, output_format)
        output_path = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            filetypes=[(f"{output_format.upper()}文件", f"*.{ext}")]
        )
        if not output_path:
            return

        try:
            # 编码处理，优先使用 UTF-8
            encoded_code = code.encode("utf-8")
        except UnicodeEncodeError:
            try:
                encoded_code = code.encode("gbk", errors="ignore")
            except Exception as e:
                messagebox.showerror("编码错误", f"无法处理文本编码: {str(e)}")
                return

        try:
            ret, stdout, stderr = self.converter.convert_code(code, input_format, output_format, output_path)
            if ret == 0:
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

# ------------------------------------------------------------
# 程序入口
# ------------------------------------------------------------
if __name__ == "__main__":
    app = PandocConverterGUI()
    app.mainloop()

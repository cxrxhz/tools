#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import sympy as sp
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
import json, os
import numpy as np

RESERVED_VARS = {"x", "y"}  # 保留符号，永远不当作参数
GLOBAL_PARAMS_PATH = os.path.join(os.path.dirname(__file__), "global_params.json")

def load_global_params():
    try:
        with open(GLOBAL_PARAMS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_global_params(params_dict):
    try:
        with open(GLOBAL_PARAMS_PATH, "w", encoding="utf-8") as f:
            json.dump(params_dict, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("保存全局参数失败：", e)

def update_global_param(name, value):
    params = load_global_params()
    params[name] = value
    save_global_params(params)

class ModelPlotterApp:
    def add_model(self):
        formula = simpledialog.askstring("输入公式", "请输入公式 (例如 y = km*(...含 x ...))")
        if not formula:
            return
        rhs = formula.split("=", 1)[-1].strip()
    def remove_model(self, idx):
        if 0 <= idx < len(self.models):
            del self.models[idx]
            self.render_multi_param_area()
    def __init__(self, master, mode="single"):
        # 设置matplotlib字体为支持中文
        try:
            matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
            matplotlib.rcParams['axes.unicode_minus'] = False
        except Exception:
            pass
        self.master = master
        self.master.title("模型绘图器")
        self.mode = mode
        self.config_dir = "configs"
        os.makedirs(self.config_dir, exist_ok=True)
        self.models = []      # [{formula, expr, params}]
        self.exp_data = None  # 实验数据
        self.build_ui()

    def build_ui(self):
        # 主frame，左右分栏
        main_frame = tk.Frame(self.master)
        main_frame.pack(fill="both", expand=True)

        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill="y", padx=8, pady=8)
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=8, pady=8)

        # 左侧：参数、按钮
        if self.mode == "single":
            tk.Label(left_frame, text="输入公式:").pack(anchor="w")
            self.formula_entry = tk.Entry(left_frame, width=32)
            self.formula_entry.pack(anchor="w")
            tk.Button(left_frame, text="解析公式", command=self.parse_formula).pack(anchor="w", pady=(2,8))
        else:
            tk.Button(left_frame, text="添加新模型", command=self.add_model).pack(anchor="w")
            tk.Button(left_frame, text="加载已有模型", command=self.load_model).pack(anchor="w")
            tk.Button(left_frame, text="加载实验数据", command=self.load_exp_data).pack(anchor="w")
            tk.Button(left_frame, text="保存项目", command=self.save_project).pack(anchor="w", pady=5)
            tk.Button(left_frame, text="读取项目", command=self.load_project).pack(anchor="w", pady=5)

        tk.Button(left_frame, text="保存模型", command=self.save_models).pack(anchor="w", pady=5)

        # 参数输入区（带滚动条）
        params_outer = tk.Frame(left_frame)
        params_outer.pack(fill="both", expand=True, pady=5)
        canvas = tk.Canvas(params_outer, borderwidth=0, highlightthickness=0)
        vscroll = tk.Scrollbar(params_outer, orient="vertical", command=canvas.yview)
        self.params_frame = tk.Frame(canvas)
        self.params_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.params_frame, anchor="nw")
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")
        # 鼠标滚轮支持
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.params_frame.bind_all("<MouseWheel>", _on_mousewheel)

        # x 范围
        range_frame = tk.Frame(left_frame)
        range_frame.pack(fill="x", pady=(8,0))
        self.xmin = tk.DoubleVar(value=0.0)
        self.xmax = tk.DoubleVar(value=0.12)
        tk.Label(range_frame, text="x最小:").pack(side=tk.LEFT)
        tk.Entry(range_frame, textvariable=self.xmin, width=10).pack(side=tk.LEFT, padx=5)
        tk.Label(range_frame, text="x最大:").pack(side=tk.LEFT)
        tk.Entry(range_frame, textvariable=self.xmax, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(range_frame, text="更新图像", command=self.update_plot).pack(side=tk.LEFT, padx=10)

        # 右侧：绘图区
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
    def save_project(self):
        if not self.models:
            messagebox.showwarning("警告", "没有模型可保存！")
            return
        project = {
            "xrange": [self.xmin.get(), self.xmax.get()],
            "models": [],
            "exp_data_file": None
        }
        for model in self.models:
            name_var = model["params"].get("__model_name_var__")
            model_name = name_var.get().strip() if name_var else "未命名模型"
            project["models"].append({
                "formula": model["formula"],
                "params": {k: var.get() for k, var in model["params"].items() if k != "__model_name_var__"},
                "model_name": model_name
            })
        if self.exp_data is not None:
            exp_file = filedialog.asksaveasfilename(title="保存实验数据路径", defaultextension=".csv")
            if exp_file:
                np.savetxt(exp_file, self.exp_data, delimiter=",", header=",".join(["x"]+[f"y{i}" for i in range(1, self.exp_data.shape[1])]), comments="")
                project["exp_data_file"] = exp_file
        file = filedialog.asksaveasfilename(title="保存项目文件", defaultextension=".json")
        if file:
            with open(file, "w", encoding="utf-8") as f:
                json.dump(project, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("成功", f"项目已保存到 {file}")


    def load_project(self):
        file = filedialog.askopenfilename(title="选择项目文件", filetypes=[("JSON files","*.json")])
        if not file:
            return
        with open(file, "r", encoding="utf-8") as f:
            project = json.load(f)

        # 清空当前模型和参数区
        self.models.clear()
        for w in self.params_frame.winfo_children():
            w.destroy()

        # 恢复 x 范围
        xr = project.get("xrange", [0.0, 0.12])
        self.xmin.set(xr[0])
        self.xmax.set(xr[1])

        # 恢复模型
        for m in project.get("models", []):
            expr, x, y = self._parse_rhs(m["formula"].split("=")[-1])
            param_vars = self._build_param_inputs(m["formula"], expr, reserved=RESERVED_VARS, model_name=m.get("model_name"))
            for k,v in m["params"].items():
                if k in param_vars:
                    param_vars[k].set(str(v))
            self.models.append({"formula": m["formula"], "expr": expr, "params": param_vars})

        # 恢复实验数据
        if project.get("exp_data_file"):
            try:
                self.exp_data = np.loadtxt(project["exp_data_file"], delimiter=",", skiprows=1)
            except Exception as e:
                messagebox.showerror("错误", f"实验数据加载失败：{e}")

        # 更新界面
        if self.mode == "multi":
            self.render_multi_param_area()
        self.update_plot()


        # x 范围
        range_frame = tk.Frame(left_frame)
        range_frame.pack(fill="x", pady=(8,0))
        self.xmin = tk.DoubleVar(value=0.0)
        self.xmax = tk.DoubleVar(value=0.12)
        tk.Label(range_frame, text="x最小:").pack(side=tk.LEFT)
        tk.Entry(range_frame, textvariable=self.xmin, width=10).pack(side=tk.LEFT, padx=5)
        tk.Label(range_frame, text="x最大:").pack(side=tk.LEFT)
        tk.Entry(range_frame, textvariable=self.xmax, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(range_frame, text="更新图像", command=self.update_plot).pack(side=tk.LEFT, padx=10)

        # 右侧：绘图区
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _parse_rhs(self, rhs_text):
        # 保留符号
        x = sp.Symbol("x")
        y = sp.Symbol("y")
        # 解析时明确告诉 sympy：x、y 是符号
        # 同时允许常见函数名
        locals_dict = {"x": x, "y": y, "exp": sp.exp, "ln": sp.log, "log": sp.log}
        try:
            expr = sp.sympify(rhs_text, locals=locals_dict)
        except Exception as e:
            raise ValueError(f"公式解析失败：{e}")
        return expr, x, y

    def _build_param_inputs(self, formula, expr, reserved={"x", "y"}, model_name=None):
        global_defaults = load_global_params()
        if self.mode == "single":
            symbols = sorted([s for s in expr.free_symbols if str(s) not in reserved], key=lambda s: str(s))
            param_vars = {}
            frame = tk.LabelFrame(self.params_frame, text=formula)
            frame.pack(pady=6, fill="x")
            # 模型名输入框
            name_var = tk.StringVar(value=model_name or "未命名模型")
            name_row = tk.Frame(frame)
            name_row.pack(fill="x")
            tk.Label(name_row, text="模型名称:", width=10, anchor="e").pack(side=tk.LEFT)
            tk.Entry(name_row, textvariable=name_var, width=20).pack(side=tk.LEFT, padx=5)
            param_vars["__model_name_var__"] = name_var
            for s in symbols:
                name = str(s)
                default = global_defaults.get(name, "1.0")
                var = tk.StringVar(value=default)
                param_vars[name] = var
                row = tk.Frame(frame)
                row.pack(fill="x")
                tk.Label(row, text=f"{name} =", width=10, anchor="e").pack(side=tk.LEFT)
                entry = tk.Entry(row, textvariable=var, width=20)
                entry.pack(side=tk.LEFT, padx=5)
                # 绑定写入全局参数
                var.trace_add("write", lambda *_, n=name, v=var: update_global_param(n, v.get()))
            return param_vars
        else:
            symbols = sorted([s for s in expr.free_symbols if str(s) not in reserved], key=lambda s: str(s))
            param_vars = {}
            name_var = tk.StringVar(value=model_name or "未命名模型")
            param_vars["__model_name_var__"] = name_var
            for s in symbols:
                name = str(s)
                default = global_defaults.get(name, "1.0")
                var = tk.StringVar(value=default)
                param_vars[name] = var
                var.trace_add("write", lambda *_, n=name, v=var: update_global_param(n, v.get()))
            return param_vars
    def render_multi_param_area(self):
        # 清空参数区
        for w in self.params_frame.winfo_children():
            w.destroy()
        reserved = RESERVED_VARS
        # 统计所有参数出现次数
        param_count = {}
        for m in self.models:
            for k in m["params"]:
                if k not in reserved and k != "__model_name_var__":
                    param_count[k] = param_count.get(k, 0) + 1
        model_count = len(self.models)
        # 公共参数：所有模型都包含
        common_params = sorted([k for k, v in param_count.items() if v == model_count])
        # 特有参数：只在部分模型中出现
        special_params = [k for k, v in param_count.items() if v < model_count]
        global_defaults = load_global_params()
        # 默认值优先第一个模型，否则全局
        defaults = {}
        if self.models:
            for k in param_count:
                for m in self.models:
                    if k in m["params"]:
                        defaults[k] = m["params"][k].get()
                        break
        for k in param_count:
            if k not in defaults:
                defaults[k] = global_defaults.get(k, "1.0")
        param_vars = {}
        # 公共参数区
        if common_params:
            frame = tk.LabelFrame(self.params_frame, text="公共参数（所有模型共享）")
            frame.pack(pady=6, fill="x")
            for name in common_params:
                var = tk.StringVar(value=defaults.get(name, "1.0"))
                param_vars[name] = var
                row = tk.Frame(frame)
                row.pack(fill="x")
                tk.Label(row, text=f"{name} =", width=10, anchor="e").pack(side=tk.LEFT)
                entry = tk.Entry(row, textvariable=var, width=20)
                entry.pack(side=tk.LEFT, padx=5)
                # 绑定事件：同步所有模型参数+写入全局参数
                def make_callback(param_name, vref):
                    def callback(*args):
                        for m in self.models:
                            if param_name in m["params"]:
                                m["params"][param_name].set(vref.get())
                        update_global_param(param_name, vref.get())
                    return callback
                var.trace_add("write", make_callback(name, var))
        # 特有参数区
        for idx, m in enumerate(self.models):
            # 只显示该模型独有的参数
            model_special = [k for k in m["params"] if k in special_params]
            if not model_special:
                continue
            name_var = m["params"].get("__model_name_var__")
            model_name = name_var.get().strip() if name_var else f"模型{idx+1}"
            frame = tk.LabelFrame(self.params_frame, text=f"{model_name} 专有参数")
            frame.pack(pady=3, fill="x")
            for name in model_special:
                var = m["params"][name]
                row = tk.Frame(frame)
                row.pack(fill="x")
                tk.Label(row, text=f"{name} =", width=10, anchor="e").pack(side=tk.LEFT)
                entry = tk.Entry(row, textvariable=var, width=20)
                entry.pack(side=tk.LEFT, padx=5)
                # 绑定写入全局参数
                def make_callback2(param_name, vref):
                    def callback(*args):
                        update_global_param(param_name, vref.get())
                    return callback
                var.trace_add("write", make_callback2(name, var))
        # 每个模型独立命名输入框（放在参数区下方，单独一行，后跟删除按钮）
        name_frame = tk.Frame(self.params_frame)
        name_frame.pack(fill="x", pady=2)
        # 检查命名唯一性，若有重复则高亮并禁用删除
        name_count = {}
        for m in self.models:
            name_var = m["params"].get("__model_name_var__")
            name = name_var.get().strip() if name_var else ""
            if name:
                name_count[name] = name_count.get(name, 0) + 1
        for idx, m in enumerate(self.models):
            name_var = m["params"].get("__model_name_var__")
            row = tk.Frame(name_frame)
            row.pack(fill="x")
            tk.Label(row, text=f"模型{idx+1}名称:", width=10, anchor="e").pack(side=tk.LEFT)
            entry = tk.Entry(row, textvariable=name_var, width=20)
            entry.pack(side=tk.LEFT, padx=5)
            # 删除按钮
            btn = tk.Button(row, text="删除", command=lambda i=idx: self.remove_model(i))
            btn.pack(side=tk.LEFT, padx=5)
            # 如果命名重复则高亮
            name = name_var.get().strip() if name_var else ""
            if name and name_count.get(name, 0) > 1:
                entry.config(bg="#ffcccc")
                btn.config(state="disabled")
            else:
                entry.config(bg="white")
                btn.config(state="normal")
        expr, x, y = self._parse_rhs(rhs)
        # 验证依赖 x
        if x not in expr.free_symbols:
            messagebox.showwarning("警告", f"模型不依赖 x：{formula}")
        # 先生成参数结构，获取命名
        param_vars = self._build_param_inputs(formula, expr, reserved=RESERVED_VARS, model_name="未命名模型")
        new_name = param_vars["__model_name_var__"].get().strip()
        # 检查命名唯一性（包括所有现有模型的当前命名）
        exist_names = set()
        for m in self.models:
            exist_name = m["params"].get("__model_name_var__")
            if exist_name:
                exist_names.add(exist_name.get().strip())
        if new_name in exist_names:
            messagebox.showwarning("警告", f"已存在同名模型：{new_name}，请更换名称后再添加。")
            return
        self.models.append({"formula": formula, "expr": expr, "params": param_vars})
        if self.mode == "multi":
            self.render_multi_param_area()

    def load_model(self):
        folder = filedialog.askdirectory(title="选择模型文件夹", initialdir=self.config_dir)
        if not folder:
            return
        config_path = os.path.join(folder, "config.json")
        if not os.path.exists(config_path):
            messagebox.showerror("错误", "未找到配置文件 config.json")
            return
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        formula = config.get("formula", "").strip()
        if not formula:
            messagebox.showerror("错误", "config.json 中缺少 formula")
            return
        rhs = formula.split("=", 1)[-1].strip()
        expr, x, y = self._parse_rhs(rhs)
        # 参数区
        model_name = os.path.basename(folder) or "未命名模型"
        param_vars = self._build_param_inputs(formula, expr, reserved=RESERVED_VARS, model_name=model_name)
        # 回填参数
        for k, v in config.get("params", {}).items():
            if k in param_vars:
                param_vars[k].set(str(v))
        # 回填模型名
        if "__model_name_var__" in param_vars:
            param_vars["__model_name_var__"].set(model_name)
        # 回填 x 范围
        xr = config.get("xrange")
        if isinstance(xr, (list, tuple)) and len(xr) == 2:
            try:
                self.xmin.set(float(xr[0]))
                self.xmax.set(float(xr[1]))
            except:
                pass
        self.models.append({"formula": formula, "expr": expr, "params": param_vars})
        if self.mode == "multi":
            self.render_multi_param_area()

    def load_exp_data(self):
        file = filedialog.askopenfilename(title="选择实验数据 CSV", filetypes=[("CSV files","*.csv")])
        if not file:
            return
        try:
            with open(file, encoding="utf-8") as f:
                data = np.genfromtxt(f, delimiter=",", skip_header=1, filling_values=np.nan)
            if data.ndim != 2 or data.shape[1] < 2:
                raise ValueError("CSV 至少应有两列 (x, y1)")
            self.exp_data = data  # 保留所有列，第一列x，第二列y1，第三列y2...
            messagebox.showinfo("成功", f"已加载实验数据，共 {len(self.exp_data)} 点，{self.exp_data.shape[1]} 列")
            self.update_plot()
        except Exception as e:
            messagebox.showerror("错误", f"读取实验数据失败：{e}")

    def _collect_subs(self, param_dict):
        subs = {}
        # 禁止将保留符号作为参数赋值，且跳过模型名特殊key
        for k, var in param_dict.items():
            if k in RESERVED_VARS or k == "__model_name_var__":
                continue
            txt = var.get().strip()
            if not txt:
                raise ValueError(f"参数 {k} 值为空")
            # 支持表达式，内部可引用已赋值参数
            try:
                subs[k] = float(sp.sympify(txt, locals=subs))
            except Exception:
                subs[k] = float(sp.sympify(txt))
        return subs

    def update_plot(self):
        self.ax.clear()
        x = sp.Symbol("x")

        # 记录所有x/y用于全局缩放
        all_x = []
        all_y = []

        # 绘制模型曲线
        for model in self.models:
            try:
                subs = self._collect_subs(model["params"])
            except Exception as e:
                messagebox.showerror("错误", f"参数解析失败：{e}")
                return

            # 获取模型名称
            name_var = model["params"].get("__model_name_var__")
            model_name = name_var.get().strip() if name_var else "未命名模型"

            y_expr = model["expr"].subs(subs)
            # 再次验证依赖 x
            if x not in y_expr.free_symbols:
                # 如果不依赖 x，就画成常数线（提示）
                try:
                    const_val = float(sp.N(y_expr))
                    xs = np.linspace(self.xmin.get(), self.xmax.get(), 200)
                    ys = np.full_like(xs, const_val, dtype=float)
                    self.ax.plot(xs, ys, label=f"{model_name} (常数)")
                    all_x.extend(xs)
                    all_y.extend(ys)
                except Exception as e:
                    messagebox.showerror("错误", f"表达式不含 x 且无法计算常数：{e}")
                    continue
            else:
                f = sp.lambdify(x, y_expr, modules=["numpy"])
                xs = np.linspace(self.xmin.get(), self.xmax.get(), 400)
                ys = f(xs)
                if np.isscalar(ys):
                    ys = np.full_like(xs, ys, dtype=float)
                self.ax.plot(xs, ys, label=model_name)
                all_x.extend(xs)
                all_y.extend(ys)

        # 绘制实验数据（支持多列y）
        if self.exp_data is not None:
            xdata = self.exp_data[:, 0]
            for col in range(1, self.exp_data.shape[1]):
                ydata = self.exp_data[:, col]
                # 只绘制非全nan列
                if np.all(np.isnan(ydata)):
                    continue
                self.ax.scatter(xdata, ydata, s=30, marker="o", label=f"实验数据{col}" if self.exp_data.shape[1]>2 else "实验数据")
                all_x.extend(xdata[~np.isnan(ydata)])
                all_y.extend(ydata[~np.isnan(ydata)])

        self.ax.legend()
        self.ax.grid(True, linestyle="--", alpha=0.3)
        # 坐标轴缩放：同时考虑模型和所有实验点
        if all_x and all_y:
            self.ax.set_xlim(np.nanmin(all_x), np.nanmax(all_x))
            self.ax.set_ylim(np.nanmin(all_y), np.nanmax(all_y))
        self.canvas.draw()
        self.master.update_idletasks()

    def save_models(self):
        if not self.models:
            messagebox.showwarning("警告", "没有模型可保存！")
            return
        for model in self.models:
            # 取每个模型自己的命名输入框内容
            name_var = model["params"].get("__model_name_var__")
            folder_name = name_var.get().strip() if name_var else "未命名模型"
            folder = os.path.join(self.config_dir, folder_name)
            os.makedirs(folder, exist_ok=True)
            # 保存 config.json
            config = {
                "formula": model["formula"],
                "params": {k: var.get() for k, var in model["params"].items() if k != "__model_name_var__"},
                "xrange": [self.xmin.get(), self.xmax.get()],
                "model_name": folder_name
            }
            with open(os.path.join(folder, "config.json"), "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            # 试着保存当前曲线数据与图像
            try:
                x = sp.Symbol("x")
                subs = self._collect_subs({k: v for k, v in model["params"].items() if k != "__model_name_var__"})
                y_expr = model["expr"].subs(subs)
                xs = np.linspace(self.xmin.get(), self.xmax.get(), 400)
                if x in y_expr.free_symbols:
                    f = sp.lambdify(x, y_expr, modules=["numpy"])
                    ys = f(xs)
                    if np.isscalar(ys):
                        ys = np.full_like(xs, ys, dtype=float)
                else:
                    const_val = float(sp.N(y_expr))
                    ys = np.full_like(xs, const_val, dtype=float)
                np.savetxt(os.path.join(folder, "curve.csv"),
                           np.column_stack([xs, ys]),
                           delimiter=",", header="x,y", comments="")
                # 保存当前图
                self.fig.savefig(os.path.join(folder, "plot.png"), dpi=200, bbox_inches="tight")
            except Exception as e:
                print("保存曲线失败：", e)

        messagebox.showinfo("保存成功", f"已保存 {len(self.models)} 个模型的配置与曲线数据。")


def choose_mode():
    root = tk.Tk()
    root.title("选择模式")
    import sys
    def on_close():
        root.destroy()
        sys.exit(0)
    root.protocol("WM_DELETE_WINDOW", on_close)
    def start_single():
        root.destroy()
        main = tk.Tk()
        def on_main_close():
            main.destroy()
            sys.exit(0)
        main.protocol("WM_DELETE_WINDOW", on_main_close)
        app = ModelPlotterApp(main, mode="single")
        main.mainloop()
    def start_multi():
        root.destroy()
        main = tk.Tk()
        def on_main_close():
            main.destroy()
            sys.exit(0)
        main.protocol("WM_DELETE_WINDOW", on_main_close)
        app = ModelPlotterApp(main, mode="multi")
        main.mainloop()
    tk.Button(root, text="单模型模式", command=start_single).pack(pady=10, padx=15)
    tk.Button(root, text="多模型对比模式", command=start_multi).pack(pady=10, padx=15)
    root.mainloop()

if __name__ == "__main__":
    choose_mode()

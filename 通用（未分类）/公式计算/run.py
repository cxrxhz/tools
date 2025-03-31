#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import messagebox
from sympy import symbols, latex, N
from sympy.parsing.sympy_parser import parse_expr
from sympy import SympifyError
import re
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
import io
import os
import datetime

class FormulaCalculatorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("公式计算器")
        self.center_window(self.master, 600, 200)
        tk.Label(master, text="请输入主公式（SymPy 格式）：").pack(pady=10)
        self.formula_text = tk.Text(master, height=5, width=70)
        self.formula_text.pack()
        tk.Button(master, text="提交公式", command=self.submit_formula).pack(pady=10)
        self.process_log = []
        self.resolved_values = {}

    def center_window(self, win, width, height):
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = int((sw - width) / 2)
        y = int((sh - height) / 2)
        win.geometry(f"{width}x{height}+{x}+{y}")

    def submit_formula(self):
        formula_input = self.formula_text.get("1.0", tk.END).strip()
        try:
            if '=' in formula_input:
                lhs, rhs = formula_input.split('=', 1)
                lhs = lhs.strip()
                rhs = rhs.strip()
            else:
                lhs = None
                rhs = formula_input.strip()
            self.lhs = lhs
        except Exception as e:
            messagebox.showerror("错误", f"处理公式时出错：{e}")
            return
        try:
            vars_in_expr = set(re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', rhs))
            math_funcs = {'sin', 'cos', 'tan', 'tanh', 'sqrt', 'log', 'exp', 'ln',
                          'sinh', 'cosh', 'asin', 'acos', 'atan', 'atanh', 'pi', 'E'}
            vars_in_expr -= math_funcs
            if lhs is not None:
                vars_in_expr.add(lhs)
            self.symbols_list = symbols(list(vars_in_expr))
            self.symbols_dict = {str(s): s for s in self.symbols_list}
            self.expr = parse_expr(rhs, local_dict=self.symbols_dict)
            if lhs is not None and self.expr == self.symbols_dict[lhs]:
                messagebox.showerror("错误", "公式右侧为空或格式不正确，请重新输入公式！")
                return
            self.process_log.append({"variable": lhs if lhs else "Main",
                                     "formula": formula_input,
                                     "assignments": {},
                                     "expr": self.expr})
        except (SympifyError, Exception) as e:
            messagebox.showerror("错误", f"解析公式时出错：\n{e}")
            return

        self.master.destroy()
        self.create_assignment_window(self.expr, self.lhs, self.symbols_dict)

    def create_assignment_window(self, expr, lhs, local_symbols):
        self.assign_window = tk.Toplevel()
        self.assign_window.title("输入变量值")
        self.center_window(self.assign_window, 400, 300)
        tk.Label(self.assign_window, text=f"主公式：{latex(expr)}", wraplength=380).pack(pady=5)
        tk.Label(self.assign_window, text="请为以下变量输入数值（留空表示未赋值）：").pack(pady=5)
        self.assign_entries = {}
        self.entries_order = []
        vars_needed = list(expr.free_symbols)
        var_names = [str(v) for v in vars_needed]
        for var in var_names:
            frame = tk.Frame(self.assign_window)
            frame.pack(pady=3)
            tk.Label(frame, text=f"{var} = ").pack(side=tk.LEFT)
            entry = tk.Entry(frame)
            entry.pack(side=tk.LEFT)
            self.assign_entries[var] = entry
            self.entries_order.append(entry)
            entry.bind("<Return>", self.focus_next_assignment)
        if self.entries_order:
            self.entries_order[0].focus_set()
        tk.Button(self.assign_window, text="下一步", command=lambda: self.process_assignments(expr, lhs)).pack(pady=10)
        self.assign_window.grab_set()

    def focus_next_assignment(self, event):
        idx = self.entries_order.index(event.widget)
        if idx < len(self.entries_order) - 1:
            self.entries_order[idx + 1].focus_set()
        else:
            self.process_assignments(self.expr, self.lhs)

    def process_assignments(self, expr, lhs):
        assignments = {}
        for var, entry in self.assign_entries.items():
            val = entry.get().strip().replace("，", ".")
            if val == "":
                sub_result = self.prompt_subformula(var)
                if sub_result is None:
                    return
                assignments[var] = sub_result[0]
                self.resolved_values[var] = sub_result[0]
                self.process_log.append({
                    "variable": var,
                    "formula": sub_result[2],
                    "assignments": sub_result[1],
                    "expr": sub_result[3]
                })
            else:
                try:
                    num_val = float(val)
                    assignments[var] = num_val
                    self.resolved_values[var] = num_val
                except ValueError:
                    messagebox.showerror("错误", f"变量 {var} 的值无效，请输入有效数值。")
                    return
        main_log = next(log for log in self.process_log if log["variable"] == (lhs if lhs else "Main"))
        main_log["assignments"].update(assignments)

        final_expr = expr.subs(assignments)
        missing = list(final_expr.free_symbols)
        if missing:
            for sym in missing:
                var_name = str(sym)
                sub_result = self.prompt_subformula(var_name)
                if sub_result is None:
                    return
                assignments[var_name] = sub_result[0]
                self.resolved_values[var_name] = sub_result[0]
                self.process_log.append({
                    "variable": var_name,
                    "formula": sub_result[2],
                    "assignments": sub_result[1],
                    "expr": sub_result[3]
                })
                final_expr = final_expr.subs({sym: assignments[var_name]})
        try:
            final_value = float(N(final_expr, 15))
        except Exception as e:
            messagebox.showerror("错误", f"最终计算出错：{e}")
            return
        # 在调用 show_final_result 前销毁赋值窗口
        self.assign_window.destroy()

        self.show_final_result(lhs, final_value)

    def prompt_subformula(self, var_name):
        result_holder = {}
        sub_window = tk.Toplevel()
        sub_window.title(f"请输入变量 {var_name} 的公式")
        self.center_window(sub_window, 600, 200)
        sub_window.grab_set()
        tk.Label(sub_window, text=f"请输入定义 {var_name} 的公式（例如 {var_name} = ...）：").pack(pady=10)
        text = tk.Text(sub_window, height=3, width=70)
        text.pack()
        text.insert("1.0", f"{var_name} = ")

        def submit_subformula():
            sub_formula = text.get("1.0", tk.END).strip()
            try:
                if '=' in sub_formula:
                    left, right = sub_formula.split('=', 1)
                    left = left.strip()
                    right = right.strip()
                    if left != var_name:
                        messagebox.showerror("错误", f"公式左侧必须为 {var_name}！", parent=sub_window)
                        return
                else:
                    messagebox.showerror("错误", "公式格式错误，必须包含 '='。", parent=sub_window)
                    return
                vars_sub = set(re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', right))
                math_funcs = {'sin', 'cos', 'tan', 'tanh', 'sqrt', 'log', 'exp', 'ln',
                              'sinh', 'cosh', 'asin', 'acos', 'atan', 'atanh', 'pi', 'E'}
                vars_sub -= math_funcs
                sub_symbols = symbols(list(vars_sub))
                sub_symbols_dict = {str(s): s for s in sub_symbols}
                sub_expr = parse_expr(right, local_dict=sub_symbols_dict)
                sub_result = self.create_sub_assignment_window(sub_expr, var_name, sub_symbols_dict)
                if sub_result is None:
                    return
                result_holder[var_name] = (sub_result[0], sub_result[1], sub_formula, sub_expr)
                sub_window.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"子公式解析时出错：{e}", parent=sub_window)

        tk.Button(sub_window, text="提交", command=submit_subformula).pack(pady=10)
        sub_window.wait_window()
        return result_holder.get(var_name, None)

    def create_sub_assignment_window(self, expr, target, local_symbols):
        result_holder = {}
        assignments_dict = {}
        sub_assign_window = tk.Toplevel()
        sub_assign_window.title(f"为 {target} 输入变量值")
        self.center_window(sub_assign_window, 400, 300)
        sub_assign_window.grab_set()
        tk.Label(sub_assign_window, text=f"请为公式 {latex(expr)} 输入变量值：", wraplength=380).pack(pady=10)
        assign_entries = {}
        entries_order = []
        var_names = [str(v) for v in expr.free_symbols]
        for var in var_names:
            frame = tk.Frame(sub_assign_window)
            frame.pack(pady=5)
            tk.Label(frame, text=f"{var} = ").pack(side=tk.LEFT)
            entry = tk.Entry(frame)
            entry.pack(side=tk.LEFT)
            assign_entries[var] = entry
            entries_order.append(entry)
            entry.bind("<Return>", lambda event: None)
        if entries_order:
            entries_order[0].focus_set()

        def submit_sub_assignment():
            var_assignments = {}
            for var, entry in assign_entries.items():
                val_str = entry.get().strip().replace("，", ".")
                if val_str == "":
                    messagebox.showerror("错误", f"变量 {var} 未赋值，请输入数值。", parent=sub_assign_window)
                    return
                try:
                    num_val = float(val_str)
                    var_assignments[var] = num_val
                except ValueError:
                    messagebox.showerror("错误", f"变量 {var} 的值无效，请输入正确数值。", parent=sub_assign_window)
                    return
            try:
                final_expr = expr.subs(var_assignments)
                final_value = float(N(final_expr, 15))
                result_holder[target] = final_value
                assignments_dict.update(var_assignments)
            except Exception as e:
                messagebox.showerror("错误", f"子公式计算时出错：{e}", parent=sub_assign_window)
                return
            sub_assign_window.destroy()

        tk.Button(sub_assign_window, text="提交", command=submit_sub_assignment).pack(pady=10)
        sub_assign_window.wait_window()
        if target in result_holder:
            return (result_holder[target], assignments_dict)
        else:
            return None

    def show_final_result(self, lhs, final_value):
        final_window = tk.Toplevel()
        final_window.title("最终计算结果")
        self.center_window(final_window, 600, 400)
        # 添加窗口关闭协议
        final_window.protocol("WM_DELETE_WINDOW", self.quit_app)
        result_str = f"{lhs} = {final_value}" if lhs else f"结果 = {final_value}"
        tk.Label(final_window, text="最终计算结果：").pack(pady=5)
        result_entry = tk.Entry(final_window, width=50)
        result_entry.pack()
        result_entry.insert(0, result_str)
        result_entry.config(state='readonly')

        main_formula = latex(self.expr)
        if lhs:
            main_formula = lhs + " = " + main_formula
        fig = plt.figure(figsize=(8, 2))
        fig.text(0.5, 0.5, f"${main_formula}$", fontsize=24, ha='center', va='center')
        plt.axis('off')
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1, dpi=200)
        buf.seek(0)
        img = Image.open(buf)
        photo = ImageTk.PhotoImage(img)
        label = tk.Label(final_window, image=photo)
        label.image = photo
        label.pack(pady=10)
        plt.close(fig)

        folder = self.save_output_files(lhs, final_value, self.resolved_values, self.process_log)
        tk.Label(final_window, text=f"所有数据已保存至文件夹：\n{folder}", font=("Arial", 12)).pack(pady=5)
        final_window.grab_set()

    def quit_app(self):
        self.master.quit()
        self.master.destroy()

    def save_output_files(self, lhs, final_value, var_values, process_log):
        now = datetime.datetime.now()
        timestamp = now.strftime("%y.%m.%d-%H.%M")
        folder_name = f"{lhs} {timestamp}" if lhs else f"Result {timestamp}"
        result_folder = os.path.join("result", folder_name)
        if not os.path.exists(result_folder):
            os.makedirs(result_folder)

        main_formula = latex(self.expr)
        if lhs:
            main_formula = lhs + " = " + main_formula
        fig = plt.figure(figsize=(8, 2))
        fig.text(0.5, 0.5, f"${main_formula}$", fontsize=24, ha='center', va='center')
        plt.axis('off')
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1, dpi=200)
        buf.seek(0)
        main_formula_path = os.path.join(result_folder, "main_formula.png")
        with open(main_formula_path, "wb") as f:
            f.write(buf.getvalue())
        plt.close(fig)

        variables_txt_path = os.path.join(result_folder, "variables.txt")
        with open(variables_txt_path, "w", encoding="utf-8") as f:
            f.write("变量名\t值\n")
            for var, val in var_values.items():
                f.write(f"{var}\t{val}\n")

        html_path = os.path.join(result_folder, "summary.html")
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>公式计算结果</title>
    <style>
        body {{ text-align: center; font-family: Arial, sans-serif; }}
        img {{ display: block; margin: 0 auto; }}
        table {{ margin: 0 auto; border-collapse: collapse; }}
        th, td {{ padding: 8px 12px; border: 1px solid #aaa; }}
    </style>
</head>
<body>
    <h1>公式计算结果</h1>
    <h2>主公式</h2>
    <img src="main_formula.png" alt="主公式图像">
    <h3>主变量赋值</h3>
    <table>
        <tr><th>变量名</th><th>值</th></tr>
"""
        for var, val in var_values.items():
            html_content += f"        <tr><td>{var}</td><td>{val}</td></tr>\n"
        html_content += f"""    </table>
    <h3>主公式计算结果</h3>
    <p>{lhs} = {final_value}</p>
    <h2>子公式记录</h2>
"""
        for step in process_log:
            if step["variable"] == (lhs if lhs else "Main"):
                continue
            sub_var = step["variable"]
            subfolder = os.path.join(result_folder, sub_var)
            if not os.path.exists(subfolder):
                os.makedirs(subfolder)
            if "expr" in step:
                sub_formula = latex(step["expr"])
            else:
                sub_formula = step["formula"]
            fig = plt.figure(figsize=(8, 2))
            fig.text(0.5, 0.5, f"${sub_var} = {sub_formula}$", fontsize=24, ha='center', va='center')
            plt.axis('off')
            fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
            sub_buf = io.BytesIO()
            plt.savefig(sub_buf, format='png', bbox_inches='tight', pad_inches=0.1, dpi=200)
            sub_buf.seek(0)
            sub_formula_path = os.path.join(subfolder, "formula.png")
            with open(sub_formula_path, "wb") as f:
                f.write(sub_buf.getvalue())
            plt.close(fig)
            sub_variables_path = os.path.join(subfolder, "variables.txt")
            with open(sub_variables_path, "w", encoding="utf-8") as f:
                f.write("变量名\t值\n")
                for var, val in step["assignments"].items():
                    f.write(f"{var}\t{val}\n")
            html_content += f"""<h3>子公式：{sub_var}</h3>
    <img src="{sub_var}/formula.png" alt="子公式 {sub_var} 图像">
    <h4>子公式赋值</h4>
    <table>
        <tr><th>变量名</th><th>值</th></tr>
"""
            for var, val in step["assignments"].items():
                html_content += f"        <tr><td>{var}</td><td>{val}</td></tr>\n"
            html_content += "</table><br>"
        html_content += "</body></html>"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return result_folder

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    app = FormulaCalculatorApp(tk.Toplevel())
    root.mainloop()

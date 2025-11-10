import tkinter as tk
from tkinter import ttk, messagebox
import math


class ThermalConductivityCalculator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("热导率计算器")
        self.geometry("450x400")

        # 选择纳米结构类型：纳米线或纳米带
        self.struct_type = tk.StringVar(value="纳米线")
        frame_type = tk.Frame(self)
        frame_type.pack(pady=10)
        tk.Label(frame_type, text="选择纳米结构类型：").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(frame_type, text="纳米线", variable=self.struct_type, value="纳米线",
                        command=self.update_inputs).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(frame_type, text="纳米带", variable=self.struct_type, value="纳米带",
                        command=self.update_inputs).pack(side=tk.LEFT, padx=5)

        # 斜率 k (R/L) 的输入框及 L 单位选择
        frame_slope = tk.Frame(self)
        frame_slope.pack(pady=5, fill=tk.X, padx=10)
        tk.Label(frame_slope, text="输入斜率 k (R/L): ").grid(row=0, column=0, sticky=tk.W)
        self.entry_slope = tk.Entry(frame_slope, width=15)
        self.entry_slope.grid(row=0, column=1, padx=5)

        tk.Label(frame_slope, text="L 单位: ").grid(row=0, column=2, padx=5)
        self.combo_L_unit = ttk.Combobox(frame_slope, values=["m", "um", "nm"], width=5, state="readonly")
        self.combo_L_unit.set("um")  # 默认选择 um
        self.combo_L_unit.grid(row=0, column=3, padx=5)

        # 根据选择不同显示不同的后续输入框
        # ---- 纳米线输入框：截面直径
        self.frame_nanowire = tk.Frame(self)
        tk.Label(self.frame_nanowire, text="截面直径: ").grid(row=0, column=0, sticky=tk.W)
        self.entry_diameter = tk.Entry(self.frame_nanowire, width=15)
        self.entry_diameter.grid(row=0, column=1, padx=5)
        tk.Label(self.frame_nanowire, text="单位: ").grid(row=0, column=2, padx=5)
        self.combo_diameter_unit = ttk.Combobox(self.frame_nanowire, values=["m", "um", "nm"], width=5,
                                                state="readonly")
        self.combo_diameter_unit.set("nm")  # 默认选择 nm
        self.combo_diameter_unit.grid(row=0, column=3, padx=5)

        # ---- 纳米带输入框：截面长和截面宽
        self.frame_nanobelt = tk.Frame(self)
        tk.Label(self.frame_nanobelt, text="截面长: ").grid(row=0, column=0, sticky=tk.W)
        self.entry_length = tk.Entry(self.frame_nanobelt, width=15)
        self.entry_length.grid(row=0, column=1, padx=5)
        tk.Label(self.frame_nanobelt, text="单位: ").grid(row=0, column=2, padx=5)
        self.combo_length_unit = ttk.Combobox(self.frame_nanobelt, values=["m", "um", "nm"], width=5, state="readonly")
        self.combo_length_unit.set("nm")
        self.combo_length_unit.grid(row=0, column=3, padx=5)

        tk.Label(self.frame_nanobelt, text="截面宽: ").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.entry_width = tk.Entry(self.frame_nanobelt, width=15)
        self.entry_width.grid(row=1, column=1, padx=5)
        tk.Label(self.frame_nanobelt, text="单位: ").grid(row=1, column=2, padx=5)
        self.combo_width_unit = ttk.Combobox(self.frame_nanobelt, values=["m", "um", "nm"], width=5, state="readonly")
        self.combo_width_unit.set("nm")
        self.combo_width_unit.grid(row=1, column=3, padx=5)

        # 默认显示纳米线的输入框
        self.frame_nanowire.pack(pady=5)

        # 计算按钮
        self.btn_calc = tk.Button(self, text="计算", command=self.calculate_kappa)
        self.btn_calc.pack(pady=10)

        # 结果显示及复制按钮
        frame_result = tk.Frame(self)
        frame_result.pack(pady=5, fill=tk.X, padx=10)
        tk.Label(frame_result, text="热导率 κ: ").grid(row=0, column=0, sticky=tk.W)
        self.entry_result = tk.Entry(frame_result, width=25)
        self.entry_result.grid(row=0, column=1, padx=5)
        self.btn_copy = tk.Button(frame_result, text="复制", command=self.copy_result)
        self.btn_copy.grid(row=0, column=2, padx=5)

    def update_inputs(self):
        """根据选择的纳米结构类型调整显示的输入框"""
        self.frame_nanowire.pack_forget()
        self.frame_nanobelt.pack_forget()
        if self.struct_type.get() == "纳米线":
            self.frame_nanowire.pack(pady=5)
        else:
            self.frame_nanobelt.pack(pady=5)

    def convert_to_m(self, value_str, unit):
        """将输入的数字根据单位换算为以 m 为单位的值"""
        try:
            value = float(value_str)
        except ValueError:
            raise ValueError("请输入有效的数值")
        if unit == "m":
            return value
        elif unit == "um":
            return value * 1e-6  # 1 μm = 1e-6 m
        elif unit == "nm":
            return value * 1e-9  # 1 nm = 1e-9 m
        else:
            raise ValueError("未知的单位")

    def calculate_kappa(self):
        """读取所有输入，自动换算为 SI 单位后，计算热导率 κ = 1 / (A*(R/L))"""
        try:
            # 1. 斜率 k (R/L) 输入处理及单位换算
            slope_input = self.entry_slope.get()
            slope_unit = self.combo_L_unit.get()
            slope_val = float(slope_input)
            # 已知输入数值以 R per 用户所选 L 单位给出，
            # 要换算为 R/m，则：
            # 若单位为 m：无转换，若为 um：乘以1e6，若为 nm：乘以1e9
            if slope_unit == "m":
                slope_per_m = slope_val
            elif slope_unit == "um":
                slope_per_m = slope_val * 1e6
            elif slope_unit == "nm":
                slope_per_m = slope_val * 1e9
            else:
                raise ValueError("未知的 L 单位")

            # 2. 根据纳米结构类型获得截面积 A
            if self.struct_type.get() == "纳米线":
                dia_str = self.entry_diameter.get()
                dia_unit = self.combo_diameter_unit.get()
                diameter = self.convert_to_m(dia_str, dia_unit)
                area = math.pi * (diameter / 2) ** 2
            else:  # 纳米带
                length_str = self.entry_length.get()
                width_str = self.entry_width.get()
                length_unit = self.combo_length_unit.get()
                width_unit = self.combo_width_unit.get()
                length_val = self.convert_to_m(length_str, length_unit)
                width_val = self.convert_to_m(width_str, width_unit)
                area = length_val * width_val

            # 3. 根据公式 κ = 1 / (A * (R/L)) 计算热导率
            kappa = 1 / (area * slope_per_m)

            # 结果显示，采用科学计数法并保留6位小数
            self.entry_result.delete(0, tk.END)
            self.entry_result.insert(0, f"{kappa:.6e}")
        except Exception as e:
            messagebox.showerror("输入错误", str(e))

    def copy_result(self):
        """将结果复制到剪贴板"""
        result = self.entry_result.get()
        if result:
            self.clipboard_clear()
            self.clipboard_append(result)
            messagebox.showinfo("复制", "结果已复制到剪贴板")


if __name__ == "__main__":
    app = ThermalConductivityCalculator()
    app.mainloop()

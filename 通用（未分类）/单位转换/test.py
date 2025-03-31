import tkinter as tk
import math
from decimal import Decimal, getcontext, InvalidOperation

# 提高 Decimal 运算精度
getcontext().prec = 50


def format_scientific(dec_val):
    """
    将 Decimal 数值转换为科学计数法字符串，保留所有有效数字，
    并确保指数部分至少两位，例如 "1.555E-05"。
    """
    normalized = dec_val.normalize()
    s = f"{normalized:E}"  # 例如 "1.555000E-5"
    coeff, exp = s.split('E')
    if '.' in coeff:
        coeff = coeff.rstrip('0').rstrip('.')
    sign = exp[0]
    exp_val = exp[1:]
    exp_val = exp_val.zfill(2)
    return coeff + 'E' + sign + exp_val


# 定义标准 SI 前缀（不单独列出 T/G/M/m/u/n/p 的各自选项，用户通过下拉菜单选择）
prefixes = {
    "T": Decimal("1e12"),
    "G": Decimal("1e9"),
    "M": Decimal("1e6"),
    "无": Decimal("1"),
    "m": Decimal("1e-3"),
    "u": Decimal("1e-6"),
    "n": Decimal("1e-9"),
    "p": Decimal("1e-12")
}
prefix_list = ["T", "G", "M", "无", "m", "u", "n", "p"]

# 物理量及单位配置：每个物理量均包含一个可配合前缀的 SI 基本单位（prefix_unit）及其他常用单位（others）
units_config = {
    "长度 (m)": {
        "prefix_unit": {"label": "米", "symbol": "m", "conversion": Decimal("1")},
        "others": [
            {"label": "英尺", "symbol": "ft", "conversion": Decimal("0.3048"), "prefix_compatible": False},
            {"label": "英寸", "symbol": "in", "conversion": Decimal("0.0254"), "prefix_compatible": False},
            {"label": "厘米", "symbol": "cm", "conversion": Decimal("1e-2"), "prefix_compatible": False}
        ]
    },
    "质量 (kg)": {
        "prefix_unit": {"label": "千克", "symbol": "kg", "conversion": Decimal("1")},
        "others": [
            {"label": "磅", "symbol": "lb", "conversion": Decimal("0.45359237"), "prefix_compatible": False},
            {"label": "盎司", "symbol": "oz", "conversion": Decimal("0.0283495"), "prefix_compatible": False},
            {"label": "克", "symbol": "g", "conversion": Decimal("1e-3"), "prefix_compatible": False}
        ]
    },
    "时间 (s)": {
        "prefix_unit": {"label": "秒", "symbol": "s", "conversion": Decimal("1")},
        "others": [
            {"label": "小时", "symbol": "h", "conversion": Decimal("3600"), "prefix_compatible": False},
            {"label": "分钟", "symbol": "min", "conversion": Decimal("60"), "prefix_compatible": False},
            {"label": "天", "symbol": "day", "conversion": Decimal("86400"), "prefix_compatible": False}
        ]
    },
    "电流 (A)": {
        "prefix_unit": {"label": "安培", "symbol": "A", "conversion": Decimal("1")},
        "others": []
    },
    "温度 (K)": {
        "prefix_unit": {"label": "开尔文", "symbol": "K", "conversion": Decimal("1")},
        "others": [
            {"label": "摄氏度", "symbol": "℃", "conversion": Decimal("1"), "prefix_compatible": False,
             "special": "temp"}
        ]
    },
    "发光强度 (cd)": {
        "prefix_unit": {"label": "坎德拉", "symbol": "cd", "conversion": Decimal("1")},
        "others": []
    },
    "物质的量 (mol)": {
        "prefix_unit": {"label": "摩尔", "symbol": "mol", "conversion": Decimal("1")},
        "others": []
    },
    "平面角 (rad)": {
        "prefix_unit": {"label": "弧度", "symbol": "rad", "conversion": Decimal("1")},
        "others": [
            {"label": "度", "symbol": "deg", "conversion": Decimal(str(math.pi / 180)), "prefix_compatible": False}
        ]
    },
    "立体角 (sr)": {
        "prefix_unit": {"label": "球面度", "symbol": "sr", "conversion": Decimal("1")},
        "others": []
    },
    "频率 (Hz)": {
        "prefix_unit": {"label": "赫兹", "symbol": "Hz", "conversion": Decimal("1")},
        "others": [
            {"label": "转/分钟", "symbol": "rpm", "conversion": Decimal(str(1 / 60)), "prefix_compatible": False}
        ]
    },
    "力 (N)": {
        "prefix_unit": {"label": "牛顿", "symbol": "N", "conversion": Decimal("1")},
        "others": [
            {"label": "达因", "symbol": "dyn", "conversion": Decimal("1e-5"), "prefix_compatible": False}
        ]
    },
    "压力 (Pa)": {
        "prefix_unit": {"label": "帕斯卡", "symbol": "Pa", "conversion": Decimal("1")},
        "others": [
            {"label": "巴", "symbol": "bar", "conversion": Decimal("1e5"), "prefix_compatible": False},
            {"label": "托", "symbol": "torr", "conversion": Decimal("133.3223684211"), "prefix_compatible": False}
        ]
    },
    "能量 (J)": {
        "prefix_unit": {"label": "焦耳", "symbol": "J", "conversion": Decimal("1")},
        "others": [
            {"label": "卡", "symbol": "cal", "conversion": Decimal("4.184"), "prefix_compatible": False},
            {"label": "千卡", "symbol": "kcal", "conversion": Decimal("4184"), "prefix_compatible": False}
        ]
    },
    "功率 (W)": {
        "prefix_unit": {"label": "瓦特", "symbol": "W", "conversion": Decimal("1")},
        "others": [
            {"label": "马力", "symbol": "hp", "conversion": Decimal("745.7"), "prefix_compatible": False}
        ]
    },
    "电荷量 (C)": {
        "prefix_unit": {"label": "库仑", "symbol": "C", "conversion": Decimal("1")},
        "others": [
            {"label": "安时", "symbol": "Ah", "conversion": Decimal("3600"), "prefix_compatible": False}
        ]
    },
    "电压 (V)": {
        "prefix_unit": {"label": "伏特", "symbol": "V", "conversion": Decimal("1")},
        "others": []
    },
    "电容 (F)": {
        "prefix_unit": {"label": "法拉", "symbol": "F", "conversion": Decimal("1")},
        "others": []
    },
    "电阻 (Ω)": {
        "prefix_unit": {"label": "欧姆", "symbol": "Ω", "conversion": Decimal("1")},
        "others": []
    },
    "电导 (S)": {
        "prefix_unit": {"label": "西门子", "symbol": "S", "conversion": Decimal("1")},
        "others": []
    },
    "磁通量 (Wb)": {
        "prefix_unit": {"label": "韦伯", "symbol": "Wb", "conversion": Decimal("1")},
        "others": []
    },
    "磁感应强度 (T)": {
        "prefix_unit": {"label": "特斯拉", "symbol": "T", "conversion": Decimal("1")},
        "others": [
            {"label": "高斯", "symbol": "G", "conversion": Decimal("1e-4"), "prefix_compatible": False}
        ]
    },
    "电感 (H)": {
        "prefix_unit": {"label": "亨利", "symbol": "H", "conversion": Decimal("1")},
        "others": []
    },
    "光通量 (lm)": {
        "prefix_unit": {"label": "流明", "symbol": "lm", "conversion": Decimal("1")},
        "others": []
    },
    "光照度 (lx)": {
        "prefix_unit": {"label": "勒克斯", "symbol": "lx", "conversion": Decimal("1")},
        "others": []
    },
    "放射性活度 (Bq)": {
        "prefix_unit": {"label": "贝可勒尔", "symbol": "Bq", "conversion": Decimal("1")},
        "others": [
            {"label": "居里", "symbol": "Ci", "conversion": Decimal("3.7e10"), "prefix_compatible": False}
        ]
    },
    "吸收剂量 (Gy)": {
        "prefix_unit": {"label": "戈瑞", "symbol": "Gy", "conversion": Decimal("1")},
        "others": []
    },
    "剂量当量 (Sv)": {
        "prefix_unit": {"label": "希沃特", "symbol": "Sv", "conversion": Decimal("1")},
        "others": []
    }
}


class UnitConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("单位转换器")

        # 定义变量
        self.selected_quantity = tk.StringVar()
        self.input_value = tk.StringVar()
        self.output_value = tk.StringVar()
        self.selected_prefix = tk.StringVar(value="无")
        self.selected_unit_var = tk.StringVar()
        # 存储单位下拉菜单各项映射数据
        self.unit_map = {}

        # 布局：第一行为物理量选择
        top_frame = tk.Frame(root)
        top_frame.grid(row=0, column=0, columnspan=4, pady=10)
        tk.Label(top_frame, text="选择物理量:").pack(side=tk.LEFT)
        quantities = list(units_config.keys())
        self.selected_quantity.set(quantities[0])
        self.quantity_menu = tk.OptionMenu(top_frame, self.selected_quantity, *quantities, command=self.change_quantity)
        self.quantity_menu.pack(side=tk.LEFT)

        # 第二行：输入数值与转换结果
        tk.Label(root, text="输入数值:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        self.entry_input = tk.Entry(root, textvariable=self.input_value)
        self.entry_input.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(root, text="转换结果 (国际单位制):").grid(row=1, column=2, padx=5, pady=5, sticky=tk.E)
        self.entry_output = tk.Entry(root, textvariable=self.output_value, state="readonly", width=25)
        self.entry_output.grid(row=1, column=3, padx=5, pady=5)

        # 第三行：前缀选择，将始终处于可用状态
        tk.Label(root, text="前缀:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.E)
        self.prefix_menu = tk.OptionMenu(root, self.selected_prefix, *prefix_list)
        self.prefix_menu.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        # 第四行：单位选择（放在输入框下方左侧）
        tk.Label(root, text="单位:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.E)
        self.unit_menu = tk.OptionMenu(root, self.selected_unit_var, "")
        self.unit_menu.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

        # 第五行：转换按钮
        self.convert_button = tk.Button(root, text="转换", command=self.convert)
        self.convert_button.grid(row=4, column=0, columnspan=4, pady=10)

        # 初始化: 更新物理量对应的单位选项
        self.change_quantity()

    def change_quantity(self, event=None):
        """当物理量选择改变时，更新单位下拉菜单（包括支持前缀的基准单位与其他单位）"""
        quantity = self.selected_quantity.get()
        config = units_config[quantity]

        self.unit_map.clear()
        unit_options = []
        # 添加支持前缀的基准单位（标记 is_prefix_unit 为 True）
        if "prefix_unit" in config:
            pu = config["prefix_unit"]
            display = f"{pu['label']} ({pu['symbol']})"
            data = {
                "symbol": pu["symbol"],
                "conversion": pu["conversion"],
                "prefix_compatible": pu.get("prefix_compatible", True),
                "special": pu.get("special", None),
                "is_prefix_unit": True
            }
            unit_options.append(display)
            self.unit_map[display] = data

        # 添加其他单位选项（标记 is_prefix_unit 为 False）
        for entry in config.get("others", []):
            display = f"{entry['label']} ({entry['symbol']})"
            data = {
                "symbol": entry["symbol"],
                "conversion": entry["conversion"],
                "prefix_compatible": entry.get("prefix_compatible", False),
                "special": entry.get("special", None),
                "is_prefix_unit": False
            }
            unit_options.append(display)
            self.unit_map[display] = data

        # 更新单位 OptionMenu 选项
        menu = self.unit_menu["menu"]
        menu.delete(0, "end")
        for option in unit_options:
            menu.add_command(label=option, command=lambda value=option: self.selected_unit_var.set(value))
        # 默认选择第一个选项（通常为 SI 基本单位）
        if unit_options:
            self.selected_unit_var.set(unit_options[0])
        self.output_value.set("")

    def convert(self):
        """读取输入数值、前缀及单位，完成单位换算并以科学计数法显示转换结果"""
        try:
            val = Decimal(self.input_value.get())
        except InvalidOperation:
            self.output_value.set("输入错误")
            return

        unit_key = self.selected_unit_var.get()
        if unit_key not in self.unit_map:
            self.output_value.set("单位错误")
            return
        unit_data = self.unit_map[unit_key]

        # 如果选中单位标记有特殊处理（如摄氏度），则特殊转换：K = ℃ + 273.15（忽略前缀设置）
        if unit_data.get("special") == "temp":
            si_val = val + Decimal("273.15")
        else:
            # 如果选择的是支持前缀的基准单位，则乘以前缀因子；否则直接采用该单位转换因子
            if unit_data.get("is_prefix_unit", False):
                factor = prefixes[self.selected_prefix.get()] * unit_data["conversion"]
            else:
                factor = unit_data["conversion"]
            si_val = val * factor

        formatted = format_scientific(si_val)
        self.output_value.set(formatted)


if __name__ == "__main__":
    root = tk.Tk()
    app = UnitConverter(root)
    root.mainloop()

import tkinter as tk
from tkinter import messagebox
import random
from datetime import datetime, timedelta

class GentleNotifier:
    def __init__(self, root):
        self.root = root
        self.root.title("Gentle Mentor - 随机提醒器")
        self.root.geometry("450x400")
        self.root.resizable(False, False)

        # --- 1. 模式配置 (分钟) ---
        self.modes = {
            "fast": {"name": "🔥 快速模式 (5-15分)", "range": (5, 15)},   
            "normal": {"name": "🍵 普通模式 (25-55分)", "range": (25, 55)}, 
            "focus": {"name": "📚 专注模式 (60-120分)", "range": (60, 120)},
            "random": {"name": "🎲 随机模式", "range": None}  # 新增随机心情模式
        }

        # 状态变量
        self.current_mode_key = tk.StringVar(value="normal") 
        self.is_auto_random = tk.BooleanVar(value=False)  # 新增：自动随机勾选框
        self.running = False
        self.random_mode_current = None  # 记录当前随机模式
        
        # 核心时间控制
        self.target_time = None   # 目标触发时间点
        self.check_loop_id = None # 心跳循环ID
        self.auto_switch_id = None # 自动切换ID

        # --- 位置记忆变量 ---
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.last_x = (screen_w - 400) // 2
        self.last_y = (screen_h - 320) // 2
        self.root.bind("<Configure>", self.save_window_position)

        # UI 初始化
        self.create_widgets()
    # --- 位置追踪逻辑 ---
    def save_window_position(self, event=None):
        if self.root.state() == 'normal':
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            if x > -1000 and y > -1000:
                self.last_x = x
                self.last_y = y

    def create_widgets(self):
        # 标题
        tk.Label(self.root, text="Gentle Mentor 提醒助手", font=("微软雅黑", 14, "bold"), fg="#444").pack(pady=15)

        # 模式选择区
        frame_modes = tk.LabelFrame(self.root, text=" 当前心情 (模式) ", font=("微软雅黑", 10), padx=10, pady=10)
        frame_modes.pack(pady=5, padx=20, fill="x")

        for key, info in self.modes.items():
            rb = tk.Radiobutton(frame_modes, text=info["name"], variable=self.current_mode_key, 
                                value=key, font=("微软雅黑", 10), command=self.on_mode_manual_change)
            rb.pack(anchor="w", pady=2)

        # 自动随机勾选框（恢复）
        tk.Checkbutton(self.root, text="🎲 启用随机心情 (每小时自动切换模式)", 
                   variable=self.is_auto_random, font=("微软雅黑", 9), fg="#555",
                   command=self.toggle_auto_random).pack(pady=5)

        # 状态显示
        self.lbl_status = tk.Label(self.root, text="状态: 等待启动", font=("微软雅黑", 10), fg="gray")
        self.lbl_status.pack(pady=10)

        # 按钮区
        frame_btns = tk.Frame(self.root, bg="#f5f5f5")
        frame_btns.pack(pady=15, padx=20, fill="x")

        self.btn_start = tk.Button(frame_btns, text="▶ 启动", bg="#d0f0c0", font=("微软雅黑", 11), width=12, command=self.start_timer,
                       relief="raised", bd=2, activebackground="#b0e0a0", cursor="hand2", highlightthickness=1, highlightbackground="#a0c090", fg="#222")
        self.btn_start.pack(side="left", padx=30, pady=2, ipadx=2, ipady=4, fill="x", expand=True)

        self.btn_stop = tk.Button(frame_btns, text="⏹ 停止", bg="#f0c0c0", font=("微软雅黑", 11), width=12, command=self.stop_timer, state="disabled",
                      relief="raised", bd=2, activebackground="#e0a0a0", cursor="hand2", highlightthickness=1, highlightbackground="#c09090", fg="#222")
        self.btn_stop.pack(side="left", padx=30, pady=2, ipadx=2, ipady=4, fill="x", expand=True)

    # --- 核心逻辑：时间计算与校准 ---

    def get_random_seconds(self, mode_key):
        """获取指定模式下的随机秒数"""
        if mode_key == "random":
            # 随机模式下，先随机选一个具体模式
            mode_key = self.random_mode_current if self.random_mode_current else random.choice([k for k in self.modes if k != "random"])
        min_m, max_m = self.modes[mode_key]["range"]
        return random.randint(min_m * 60, max_m * 60)

    def start_timer(self):
        self.running = True
        self.btn_start.config(state="disabled", bg="#cccccc")
        self.btn_stop.config(state="normal", bg="#f44336")

        # 1. 随机模式单选框：先随机选一个具体模式并自动切换
        if self.current_mode_key.get() == "random":
            self.random_mode_current = random.choice([k for k in self.modes if k != "random"])
            self.schedule_auto_switch()
        # 2. 勾选框自动随机：从当前选定模式开始，每小时自动切换
        elif self.is_auto_random.get():
            self.random_mode_current = self.current_mode_key.get()
            self.schedule_auto_switch()
        else:
            self.random_mode_current = None

        self.update_ui_status()
        # 安排下一次弹窗
        self.schedule_next_popup()

    def stop_timer(self):
        self.running = False
        self.target_time = None
        self.random_mode_current = None
        self.btn_start.config(state="normal", bg="#4CAF50")
        self.btn_stop.config(state="disabled", bg="#cccccc")
        self.lbl_status.config(text="状态: 已停止")
        # 取消所有循环
        if self.check_loop_id:
            self.root.after_cancel(self.check_loop_id)
        if self.auto_switch_id:
            self.root.after_cancel(self.auto_switch_id)
        self.is_auto_random.set(False)

    def schedule_next_popup(self, override_seconds=None):
        """设定下一次的目标时间"""
        if not self.running:
            return

        wait_seconds = override_seconds
        if wait_seconds is None:
            mode_key = self.current_mode_key.get()
            # 随机模式单选框 or 勾选框
            if mode_key == "random" or self.is_auto_random.get():
                if not self.random_mode_current:
                    self.random_mode_current = random.choice([k for k in self.modes if k != "random"])
                mode_key = self.random_mode_current
            wait_seconds = self.get_random_seconds(mode_key)

        self.target_time = datetime.now() + timedelta(seconds=wait_seconds)
        # 启动每秒检查循环 (心跳)
        self.check_loop()

    def check_loop(self):
        """每秒运行一次，检查是否到达时间"""
        if not self.running or not self.target_time:
            return

        now = datetime.now()
        
        # 如果当前时间超过了目标时间 -> 触发弹窗
        if now >= self.target_time:
            self.show_custom_popup()
            # 弹窗开启期间，停止循环，直到用户关闭弹窗才重新 schedule
            return 
        
        # 否则，继续等待，1秒后再次检查
        self.check_loop_id = self.root.after(1000, self.check_loop)

    # --- 智能模式切换逻辑 (已修复逻辑漏洞) ---

    def on_mode_manual_change(self):
        """当用户手动点击单选框切换模式时"""
        if self.running:
            if self.current_mode_key.get() == "random":
                self.random_mode_current = random.choice([k for k in self.modes if k != "random"])
                self.schedule_auto_switch()
                self.schedule_next_popup()
            elif self.is_auto_random.get():
                self.random_mode_current = self.current_mode_key.get()
                self.schedule_auto_switch()
                self.schedule_next_popup()
            else:
                self.random_mode_current = None
                self.calibrate_time_for_new_mode(force_check=True)
        self.update_ui_status()

    def perform_auto_switch(self):
        """自动切换模式（随机模式单选框或勾选框均可）"""
        if not self.running or (self.current_mode_key.get() != "random" and not self.is_auto_random.get()):
            return
        old_mode = self.random_mode_current
        available_modes = [k for k in self.modes if k != "random"]
        new_mode = random.choice(available_modes)
        # 如果随机到了同一个模式，什么都不做，完全保留现有倒计时！
        if new_mode == old_mode:
            print(f"[System] Random kept same mode: {new_mode}. Timer untouched.")
            self.schedule_auto_switch()
            return
        self.random_mode_current = new_mode
        print(f"[System] Random模式切换到: {new_mode}")
        # 校准时间
        self.calibrate_time_for_new_mode()
        self.update_ui_status()
        self.schedule_auto_switch()

    def calibrate_time_for_new_mode(self, force_check=False):
        """【修复点2】: 进度保护逻辑"""
        if not self.target_time:
            return

        now = datetime.now()
        remaining_seconds = (self.target_time - now).total_seconds()

        # 获取新模式的范围
        if self.current_mode_key.get() == "random":
            current_key = self.random_mode_current
        else:
            current_key = self.current_mode_key.get()
        max_limit = self.modes[current_key]["range"][1] * 60

        # 判定逻辑：
        # 1. 如果剩余时间 > 新模式的最大上限（比如专注切快速，剩60分，快速上限15分）
        #    -> 必须截断，因为用户现在需要"快速"反馈。
        if remaining_seconds > max_limit:
            print(f"Time calibrated: Too long ({remaining_seconds}s) -> Resetting")
            self.schedule_next_popup() 
        else:
            print("Time kept: Remaining time fits or is result of waiting.")

    # --- 辅助逻辑 ---

    # --- 随机模式专用自动切换 ---
    def schedule_auto_switch(self):
        if not self.running or (self.current_mode_key.get() != "random" and not self.is_auto_random.get()):
            return
        self.auto_switch_id = self.root.after(3600 * 1000, self.perform_auto_switch)
    def toggle_auto_random(self):
        if self.is_auto_random.get() and self.running:
            self.random_mode_current = self.current_mode_key.get()
            self.schedule_auto_switch()
        elif not self.is_auto_random.get():
            if self.auto_switch_id:
                self.root.after_cancel(self.auto_switch_id)
        self.update_ui_status()

    def update_ui_status(self):
        if not self.running:
            self.lbl_status.config(text="状态: 已停止")
            return
        if self.current_mode_key.get() == "random":
            self.lbl_status.config(text="当前运行: 🎲 随机模式")
        elif self.is_auto_random.get():
            mode_name = self.modes[self.current_mode_key.get()]["name"]
            self.lbl_status.config(text=f"当前运行: {mode_name} (自动随机)")
        else:
            mode_name = self.modes[self.current_mode_key.get()]["name"]
            self.lbl_status.config(text=f"当前运行: {mode_name}")

    def show_custom_popup(self):
        current_time_str = datetime.now().strftime("%H:%M")
        copy_text = f"新消息[{current_time_str}]"

        popup = tk.Toplevel(self.root)
        popup.title("新消息")

        # 弹窗尺寸
        pop_w = 300
        pop_h = 160
        main_w = 400
        main_h = 320
        # 计算弹窗坐标，让弹窗中心点=主窗口中心点
        center_x = self.last_x + (main_w // 2)
        center_y = self.last_y + (main_h // 2)
        final_x = center_x - (pop_w // 2)
        final_y = center_y - (pop_h // 2)
        popup.geometry(f"{pop_w}x{pop_h}+{final_x}+{final_y}")

        popup.attributes('-topmost', True)
        popup.resizable(False, False)
        self.root.bell()

        tk.Label(popup, text="💌 收到一条新消息", font=("微软雅黑", 12, "bold"), fg="#ff69b4").pack(pady=10)
        entry = tk.Entry(popup, font=("Consolas", 12), justify="center")
        entry.insert(0, copy_text)
        entry.pack(pady=5, padx=20, fill="x")

        def copy_only():
            self.root.clipboard_clear()
            self.root.clipboard_append(copy_text)

        def just_close():
            popup.destroy()
            self.schedule_next_popup()

        popup.bind('<Return>', lambda e: copy_only())
        btn_frame = tk.Frame(popup)
        btn_frame.pack(pady=10, fill="x", padx=20)
        tk.Button(btn_frame, text="复制 (Enter)", bg="#FFD700", font=("微软雅黑", 10), command=copy_only,
                  relief="raised", bd=2, activebackground="#ffe066", cursor="hand2", highlightthickness=1, highlightbackground="#e0c060").pack(side="left", expand=True, fill="x", ipadx=2, ipady=2, padx=5)
        tk.Button(btn_frame, text="关闭", bg="#e0e0e0", font=("微软雅黑", 10), command=just_close,
                  relief="raised", bd=2, activebackground="#cccccc", cursor="hand2", highlightthickness=1, highlightbackground="#cccccc").pack(side="left", expand=True, fill="x", ipadx=2, ipady=2, padx=5)
        popup.protocol("WM_DELETE_WINDOW", just_close)

if __name__ == "__main__":
    root = tk.Tk()
    app = GentleNotifier(root)
    root.mainloop()
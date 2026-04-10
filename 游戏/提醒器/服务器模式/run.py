import tkinter as tk
from tkinter import messagebox
import random
import requests
import json
import threading
import re
from datetime import datetime, timedelta
import time

# Ntfy 服务器地址
NTFY_HOST = "https://ntfy.sh"

class GentleNotifier:
    def __init__(self, root):
        self.root = root
        self.root.title("Gentle Mentor - 终极控制版 (v2.0)")
        # 增加高度以容纳更多选项
        self.root.geometry("460x760") 
        self.root.resizable(False, False)

        # --- 1. 基础配置 (已更新) ---
        self.fixed_modes = {
            "mode1": {"name": "⚡ 模式1 (5-15分)",   "range": (5, 15),   "cmd": "1"},
            "mode2": {"name": "🍵 模式2 (10-30分)",  "range": (10, 30),  "cmd": "2"},
            "mode3": {"name": "📚 模式3 (20-60分)",  "range": (20, 60),  "cmd": "3"},
            "mode4": {"name": "🚀 模式4 (40-80分)",  "range": (40, 80),  "cmd": "4"},
            "mode5": {"name": "🌌 模式5 (60-120分)", "range": (60, 120), "cmd": "5"}
        }
        # 建立指令到键值的映射
        self.fixed_cmd_map = {v["cmd"]: k for k, v in self.fixed_modes.items()}

        self.random_strats = {
            0: {"name": "⛔ 不启用随机", "pool": []},
            1: {"name": "🎲 短随机 (模式1,2)",      "pool": ["mode1", "mode2"]},
            2: {"name": "🎲 中短随机 (模式2,3)",    "pool": ["mode2", "mode3"]},
            3: {"name": "🎲 中随机 (模式2,3,4)",    "pool": ["mode2", "mode3", "mode4"]},
            4: {"name": "🎲 长随机 (模式4,5)",      "pool": ["mode4", "mode5"]},
            5: {"name": "🎲 全随机 (模式1-5)",      "pool": ["mode1", "mode2", "mode3", "mode4", "mode5"]}
        }

        # --- 2. 状态变量 ---
        # 默认选中模式2
        self.current_fixed_key = tk.StringVar(value="mode2")
        self.current_random_id = tk.IntVar(value=0)
        self.ntfy_topic_var = tk.StringVar(value="milkshakesissyxx") 
        self.last_msg_var = tk.StringVar(value="等待发送...")
        
        self.running = False
        self.waiting_for_confirm = False
        
        self.target_time = None   
        self.check_loop_id = None 
        self.auto_switch_id = None 
        
        # 位置记忆
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.last_x = (screen_w - 460) // 2
        self.last_y = (screen_h - 760) // 2
        self.last_monitor_rect = None
        self.root.bind("<Configure>", self.save_window_position)

        self.create_widgets()

    def save_window_position(self, event=None):
        if self.root.state() == 'normal':
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            if x > -1000 and y > -1000:
                self.last_x = x
                self.last_y = y
                rect = self.get_window_monitor_rect()
                if rect:
                    self.last_monitor_rect = rect

    def get_window_monitor_rect(self):
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            MONITOR_DEFAULTTONEAREST = 2
            class POINT(ctypes.Structure): _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]
            class RECT(ctypes.Structure): _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG), ("right", wintypes.LONG), ("bottom", wintypes.LONG)]
            class MONITORINFO(ctypes.Structure): _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT), ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]
            user32.MonitorFromPoint.argtypes = [POINT, wintypes.DWORD]
            user32.MonitorFromPoint.restype = wintypes.HMONITOR
            user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
            user32.GetMonitorInfoW.restype = wintypes.BOOL
            
            wx, wy = self.root.winfo_rootx(), self.root.winfo_rooty()
            ww, wh = max(int(self.root.winfo_width()), 1), max(int(self.root.winfo_height()), 1)
            pt = POINT(wx + ww // 2, wy + wh // 2)
            hmon = user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
            if not hmon: return None
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)): return None
            r = mi.rcMonitor
            return (int(r.left), int(r.top), int(r.right), int(r.bottom))
        except: return None
    
    def show_alert_popup(self, msg):
        popup = tk.Toplevel(self.root)
        popup.title("提醒")
        popup.geometry("320x120")
        popup.resizable(False, False)
        x, y = 100, 100
        rect = self.last_monitor_rect or self.get_window_monitor_rect()
        if rect:
            left, top, right, bottom = rect
            sw, sh = right - left, bottom - top
            x = left + (sw - 320) // 2
            y = top + (sh - 120) // 2
        else:
            x = getattr(self, 'last_x', 100) + 40
            y = getattr(self, 'last_y', 100) + 40
        popup.geometry(f"+{int(x)}+{int(y)}")
        label = tk.Label(popup, text=msg, font=("微软雅黑", 13, "bold"), fg="#d62d20")
        label.pack(pady=18)
        def copy_and_close():
            self.root.clipboard_clear()
            self.root.clipboard_append(msg)
            popup.destroy()
        btn = tk.Button(popup, text="复制并关闭", font=("微软雅黑", 11), command=copy_and_close, bg="#b2fab4")
        btn.pack(pady=5)
        popup.after(60000, popup.destroy)
        popup.attributes('-topmost', True)
        popup.lift()
        popup.focus_force()

    def create_widgets(self):
        # 底部按钮栏：固定在窗口底部，不会被上方内容挤出屏幕
        frame_btns = tk.Frame(self.root, bg="#f5f5f5")
        frame_btns.pack(side="bottom", pady=10, padx=20, fill="x")
        self.btn_start = tk.Button(
            frame_btns,
            text="▶ 启动",
            bg="#d0f0c0",
            command=self.start_timer,
            font=("微软雅黑", 11),
            relief="raised",
        )
        self.btn_start.pack(side="left", padx=10, fill="x", expand=True)
        self.btn_continue = tk.Button(
            frame_btns,
            text="✅ 继续",
            bg="#e0e0e0",
            command=self.on_manual_continue,
            state="disabled",
            font=("微软雅黑", 11),
            relief="raised",
        )
        self.btn_continue.pack(side="left", padx=10, fill="x", expand=True)
        self.btn_stop = tk.Button(
            frame_btns,
            text="⏹ 停止",
            bg="#f0c0c0",
            command=self.stop_timer,
            state="disabled",
            font=("微软雅黑", 11),
            relief="raised",
        )
        self.btn_stop.pack(side="left", padx=10, fill="x", expand=True)

        # 上方内容区：做成可滚动，避免内容变多把按钮顶没
        container = tk.Frame(self.root)
        container.pack(side="top", fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        scroll_frame = tk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfigure(window_id, width=event.width)

        scroll_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except:
                pass

        def _bind_mousewheel(_event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(_event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        tk.Label(scroll_frame, text="Gentle Mentor (Chat Control)", font=("微软雅黑", 14, "bold"), fg="#444").pack(pady=10)

        # Ntfy 配置
        frame_config = tk.LabelFrame(scroll_frame, text=" 📡 Ntfy 频道 ", font=("微软雅黑", 10), padx=10, pady=5)
        frame_config.pack(pady=5, padx=20, fill="x")
        entry_topic = tk.Entry(frame_config, textvariable=self.ntfy_topic_var, font=("Consolas", 10))
        entry_topic.pack(side="left", padx=5, fill="x", expand=True)

        # 区域1: 固定模式 (遍历显示所有5个模式)
        frame_fixed = tk.LabelFrame(scroll_frame, text=" 1. 当前执行模式 (立即生效) ", font=("微软雅黑", 10, "bold"), padx=10, pady=10, fg="#0057e7")
        frame_fixed.pack(pady=5, padx=20, fill="x")

        sorted_keys = sorted(self.fixed_modes.keys(), key=lambda k: int(self.fixed_modes[k]["cmd"]))
        for key in sorted_keys:
            info = self.fixed_modes[key]
            tk.Radiobutton(
                frame_fixed,
                text=f"{info['name']}",
                variable=self.current_fixed_key,
                value=key,
                font=("微软雅黑", 10),
                command=self.on_fixed_mode_change,
            ).pack(anchor="w", pady=2)

        # 区域2: 随机策略 (遍历显示 0-5)
        frame_random = tk.LabelFrame(scroll_frame, text=" 2. 随机策略 (1小时后自动切换) ", font=("微软雅黑", 10, "bold"), padx=10, pady=10, fg="#d62d20")
        frame_random.pack(pady=5, padx=20, fill="x")
        tk.Radiobutton(
            frame_random,
            text="⛔ 关闭自动切换",
            variable=self.current_random_id,
            value=0,
            font=("微软雅黑", 10),
            command=self.on_random_strat_change,
        ).pack(anchor="w", pady=2)
        for rid in range(1, 6):
            info = self.random_strats[rid]
            tk.Radiobutton(
                frame_random,
                text=f"{info['name']} [指令随机{rid}]",
                variable=self.current_random_id,
                value=rid,
                font=("微软雅黑", 10),
                command=self.on_random_strat_change,
            ).pack(anchor="w", pady=2)

        # 区域3: 最近推送记录
        frame_msg = tk.LabelFrame(scroll_frame, text=" 📋 最近推送内容 ", font=("微软雅黑", 10), padx=10, pady=5)
        frame_msg.pack(pady=5, padx=20, fill="x")
        self.entry_last_msg = tk.Entry(frame_msg, textvariable=self.last_msg_var, font=("Consolas", 9), state="readonly", fg="#333")
        self.entry_last_msg.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(frame_msg, text="复制", font=("微软雅黑", 9), command=self.copy_last_msg, bg="#e0e0e0", cursor="hand2").pack(side="left", padx=5)

        # 状态区（给一点固定高度，避免过长文本导致布局抖动）
        self.lbl_status = tk.Label(
            scroll_frame,
            text="状态: 等待启动",
            font=("微软雅黑", 10),
            fg="gray",
            height=3,
            justify="left",
            anchor="w",
            wraplength=420,
        )
        self.lbl_status.pack(pady=5, padx=20, fill="x")

    def on_manual_continue(self):
        if self.waiting_for_confirm:
            self.lbl_status.config(text="✅ 手动确认成功！")
            self.finish_confirmation()

    def copy_last_msg(self):
        content = self.last_msg_var.get()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            original_bg = self.entry_last_msg.cget("bg")
            self.entry_last_msg.config(bg="#b2fab4") 
            self.root.after(200, lambda: self.entry_last_msg.config(bg=original_bg))

    # --- 核心逻辑 ---

    def get_seconds_for_current_mode(self):
        mode_key = self.current_fixed_key.get()
        min_m, max_m = self.fixed_modes[mode_key]["range"]
        return random.randint(min_m * 60, max_m * 60)

    def start_timer(self):
        topic = self.ntfy_topic_var.get().strip()
        if not topic:
            messagebox.showerror("错误", "请输入 Ntfy 频道名！")
            return
        self.running = True
        self.btn_start.config(state="disabled", bg="#cccccc")
        self.btn_stop.config(state="normal", bg="#f44336")
        self.btn_continue.config(state="disabled", bg="#e0e0e0")
        self.start_permanent_listener()
        if self.current_random_id.get() > 0:
            self.schedule_auto_switch()
        self.update_ui_status()
        self.schedule_next_popup()

    def stop_timer(self):
        self.running = False
        self.target_time = None
        self.btn_start.config(state="normal", bg="#4CAF50")
        self.btn_stop.config(state="disabled", bg="#cccccc")
        self.btn_continue.config(state="disabled", bg="#e0e0e0") 
        self.lbl_status.config(text="状态: 已停止")
        if self.check_loop_id: self.root.after_cancel(self.check_loop_id)
        if self.auto_switch_id: self.root.after_cancel(self.auto_switch_id)

    def schedule_next_popup(self, override_seconds=None):
        if not self.running: return
        wait_seconds = override_seconds if override_seconds is not None else self.get_seconds_for_current_mode()
        self.target_time = datetime.now() + timedelta(seconds=wait_seconds)
        print(f"Next alert: {self.target_time.strftime('%H:%M')}")
        self.check_loop()

    def check_loop(self):
        if not self.running or not self.target_time: return
        if self.waiting_for_confirm:
            self.check_loop_id = self.root.after(1000, self.check_loop)
            return
        now = datetime.now()
        if now >= self.target_time:
            self.trigger_alert()
            return 
        self.check_loop_id = self.root.after(1000, self.check_loop)

    def trigger_alert(self):
        self.waiting_for_confirm = True
        now_str = datetime.now().strftime("%H:%M")
        self.lbl_status.config(text=f"🔔 [{now_str}] 等待确认...", fg="#ff9800")
        self.btn_continue.config(state="normal", bg="#fff176", fg="black")
        self.show_alert_popup(f"新消息[{now_str}]")
        threading.Thread(target=lambda: self.send_ntfy_msg(f"新消息[{now_str}]", priority="high", tags=["bell"])).start()

    def finish_confirmation(self):
        self.waiting_for_confirm = False
        self.btn_continue.config(state="disabled", bg="#e0e0e0", fg="black")
        self.update_ui_status()
        self.schedule_next_popup()

    # --- 🎲 随机与自动切换 ---
    def on_fixed_mode_change(self):
        if self.running:
            self.calibrate_time_for_new_mode(force_check=True)
            self.update_ui_status()

    def on_random_strat_change(self):
        if self.running:
            if self.current_random_id.get() == 0:
                if self.auto_switch_id: self.root.after_cancel(self.auto_switch_id)
            else:
                self.schedule_auto_switch()
            self.update_ui_status()

    def schedule_auto_switch(self):
        if self.auto_switch_id: self.root.after_cancel(self.auto_switch_id)
        if not self.running or self.current_random_id.get() == 0: return
        self.auto_switch_id = self.root.after(3600 * 1000, self.perform_auto_switch)

    def perform_auto_switch(self):
        if not self.running: return
        rid = self.current_random_id.get()
        if rid == 0: return
        pool = self.random_strats[rid]["pool"]
        new_mode_key = random.choice(pool)
        self.current_fixed_key.set(new_mode_key)
        self.calibrate_time_for_new_mode()
        self.update_ui_status()
        self.schedule_auto_switch()

    def calibrate_time_for_new_mode(self, force_check=False):
        if not self.target_time or self.waiting_for_confirm: return
        now = datetime.now()
        remaining = (self.target_time - now).total_seconds()
        mode_key = self.current_fixed_key.get()
        max_limit = self.fixed_modes[mode_key]["range"][1] * 60
        if remaining > max_limit:
            self.schedule_next_popup()

    # --- 🚀 Ntfy 交互 ---
    def start_permanent_listener(self):
        t = threading.Thread(target=self.run_permanent_listener)
        t.daemon = True
        t.start()

    def run_permanent_listener(self):
        topic = self.ntfy_topic_var.get()
        while self.running:
            try:
                with requests.get(f"{NTFY_HOST}/{topic}/json", stream=True, timeout=60) as resp:
                    for line in resp.iter_lines():
                        if not self.running: return
                        if line:
                            try:
                                data = json.loads(line)
                                if data.get('event') == 'message':
                                    self.handle_incoming_message(data.get('message', '').strip())
                            except: pass
            except: time.sleep(3)

    def handle_incoming_message(self, raw_msg):
        if raw_msg == '1':
            if self.waiting_for_confirm:
                self.send_ntfy_msg("✅ 继续生成", tags=["white_check_mark"])
                self.root.after(0, self.finish_confirmation)
        elif "模式" in raw_msg or "随机" in raw_msg:
            self.handle_remote_cmd(raw_msg)

    def send_ntfy_msg(self, msg, title="Gentle Mentor", priority="default", tags=[]):
        topic = self.ntfy_topic_var.get()
        self.root.after(0, lambda: self.last_msg_var.set(msg))
        try:
            requests.post(f"{NTFY_HOST}/{topic}", data=msg.encode('utf-8'),
                          headers={"Title": title, "Priority": priority, "Tags": ",".join(tags)})
        except: pass

    def handle_remote_cmd(self, msg):
        # 匹配模式： "模式1" "模式2" ... "随机1" ... "随机5"
        # 兼容例如 "模式3随机4" 的组合指令
        pattern = re.compile(r'(模式(\d))?(随机(\d))?') 
        match = pattern.match(msg)
        if not match: return
        mode_cmd = match.group(2) # 捕获单个数字 1-5
        rand_cmd = match.group(4) # 捕获单个数字 1-5
        self.root.after(0, lambda: self._apply_remote_settings(mode_cmd, rand_cmd))

    def _apply_remote_settings(self, mode_cmd, rand_cmd):
        feedback = []
        if mode_cmd:
            mode_key = self.fixed_cmd_map.get(mode_cmd)
            if mode_key:
                self.current_fixed_key.set(mode_key)
                self.on_fixed_mode_change()
                feedback.append(f"模式->{self.fixed_modes[mode_key]['name']}")
            
            # 如果只发了模式指令，默认关闭随机，除非后面紧跟了随机指令
            if not rand_cmd:
                self.current_random_id.set(0)
                self.on_random_strat_change()
                feedback.append("随机->关闭")
        
        if rand_cmd:
            try:
                rid = int(rand_cmd)
                if rid in self.random_strats and rid > 0:
                    self.current_random_id.set(rid)
                    self.on_random_strat_change()
                    feedback.append(f"策略->{self.random_strats[rid]['name']}")
            except: pass
        
        if feedback:
            self.send_ntfy_msg(" | ".join(feedback), tags=["gear"])

    def update_ui_status(self):
        if not self.running:
            self.lbl_status.config(text="状态: 已停止")
            return
        m_name = self.fixed_modes[self.current_fixed_key.get()]["name"]
        rid = self.current_random_id.get()
        r_name = self.random_strats[rid]["name"] if rid > 0 else "无"
        status = "等待回复..." if self.waiting_for_confirm else "运行中"
        self.lbl_status.config(text=f"[{status}]\n执行: {m_name}\n策略: {r_name}", fg="#0057e7")

if __name__ == "__main__":
    root = tk.Tk()
    app = GentleNotifier(root)
    root.mainloop()
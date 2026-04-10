import tkinter as tk
from tkinter import messagebox
import requests
import json
import threading
from datetime import datetime
import time

# Ntfy 服务器地址
NTFY_HOST = "https://ntfy.sh"

class GentleTester:
    def __init__(self, root):
        self.root = root
        self.root.title("Gentle Mentor - 聊天回复测试版")
        self.root.geometry("400x350")
        self.root.resizable(False, False)

        # 状态变量
        self.testing = False
        self.ntfy_topic_var = tk.StringVar(value="") 

        self.create_widgets()
        self.center_window()

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        tk.Label(self.root, text="Ntfy 聊天模式测试", font=("微软雅黑", 16, "bold"), fg="#333").pack(pady=20)

        frame_input = tk.Frame(self.root)
        frame_input.pack(pady=10, padx=20, fill="x")
        
        tk.Label(frame_input, text="Ntfy 频道名:", font=("微软雅黑", 10)).pack(anchor="w")
        entry = tk.Entry(frame_input, textvariable=self.ntfy_topic_var, font=("Consolas", 12), bg="#f0f0f0")
        entry.pack(fill="x", pady=5, ipady=5)
        
        # 指引文案更新
        tk.Label(frame_input, text="📢 测试流程：\n1. 点击下方按钮，电脑发送通知。\n2. 手机收到后打开 App，在该频道内发送数字 1。\n3. 电脑收到 1 后显示成功。", 
                 font=("微软雅黑", 9), fg="#666", justify="left").pack(anchor="w", pady=5)

        self.lbl_status = tk.Label(self.root, text="准备就绪", font=("微软雅黑", 10), fg="gray")
        self.lbl_status.pack(pady=10)

        self.btn_test = tk.Button(self.root, text="🚀 发送测试消息", bg="#2196F3", fg="white",
                                font=("微软雅黑", 11, "bold"), command=self.start_test_thread,
                                relief="raised", cursor="hand2")
        self.btn_test.pack(pady=10, ipadx=20, ipady=5)

    def start_test_thread(self):
        topic = self.ntfy_topic_var.get().strip()
        if not topic:
            messagebox.showwarning("提示", "请输入 Ntfy 频道名！")
            return

        self.testing = True
        self.btn_test.config(state="disabled", text="⏳ 等待手机回复...", bg="#ccc")
        self.lbl_status.config(text="消息已发送，请在手机 Ntfy 回复 '1'...", fg="#ff9800")
        
        t = threading.Thread(target=self.run_test_logic, args=(topic,))
        t.daemon = True
        t.start()

    def run_test_logic(self, topic):
        # --- 1. 发送纯文本通知 (无按钮) ---
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            target_url = f"{NTFY_HOST}/{topic}"
            
            print(f"[{current_time}] 发送消息到: {target_url}")
            
            # 简化 Payload，不需要 actions 按钮了
            payload = {
                "message": "👋 测试：请回复 1 确认收到！",
                "title": "连接测试",
                "priority": "default",
                "tags": ["speech_balloon"]
            }

            resp = requests.post(target_url, json=payload, timeout=10)
            resp.raise_for_status()
            print("✅ 消息发送成功，进入监听模式...")
            
        except Exception as e:
            err_msg = str(e)
            print(f"❌ 发送错误: {err_msg}")
            self.root.after(0, lambda: self.finish_test(False, f"发送失败: {err_msg}"))
            return

        # --- 2. 监听手机回复 (关键词: 1) ---
        try:
            listen_url = f"{NTFY_HOST}/{topic}/json"
            print(f"正在监听回复: {listen_url}")
            
            with requests.get(listen_url, stream=True, timeout=60) as resp:
                for line in resp.iter_lines():
                    if not self.testing: break
                    if line:
                        try:
                            data = json.loads(line)
                            
                            # 过滤: 必须是 message 事件
                            if data.get('event') == 'message':
                                msg_content = data.get('message', '').strip()
                                
                                # 逻辑: 如果收到的消息是 '1' 或者 'ok'，就算成功
                                # (同时也防止把自己刚才发出的 "请回复1" 当作确认信号)
                                if msg_content in ['1', 'ok', 'OK', '确认']:
                                    print(f"🎉 收到有效回复: {msg_content}")
                                    self.root.after(0, lambda: self.finish_test(True, "测试成功！电脑已收到你的回复。"))
                                    return
                                else:
                                    print(f"忽略无效消息: {msg_content}")
                        except:
                            pass
        except Exception as e:
            err_msg = str(e)
            print(f"❌ 监听错误: {err_msg}")
            self.root.after(0, lambda: self.finish_test(False, f"监听中断: {err_msg}"))

    def finish_test(self, success, message):
        self.testing = False
        self.btn_test.config(state="normal", text="🚀 发送测试消息", bg="#2196F3")
        
        if success:
            self.lbl_status.config(text="✅ 通信成功", fg="#4CAF50")
            messagebox.showinfo("成功", message)
        else:
            self.lbl_status.config(text="❌ 测试失败", fg="#F44336")
            messagebox.showerror("失败", message)

if __name__ == "__main__":
    root = tk.Tk()
    app = GentleTester(root)
    root.mainloop()
"""
Antigravity 模型自动切换工具
=============================
通过 Win32 API 键盘自动化实现模型切换，无需安装第三方包。

使用方式:
  python switch_model.py "Gemini 3 Flash"           # 切换模型并发送 Continue
  python switch_model.py "Claude Opus 4.6 (Thinking)"  # 切换到指定模型
  python switch_model.py "Gemini 3 Flash" --msg "请执行实现计划"  # 自定义消息
  python switch_model.py --monitor                   # 后台监控模式 (监控信号文件)

信号文件模式:
  Agent 只需在工作区写入 .model_switch 文件，内容为目标模型名称。
  后台监控脚本会自动检测并执行切换。
"""

import ctypes
import ctypes.wintypes
import time
import sys
import os
import argparse

# ==================== Win32 API 常量 ====================

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Virtual Key Codes
VK_RETURN = 0x0D
VK_CONTROL = 0x11
VK_SLASH = 0xBF  # '/' key (OEM_2)
VK_BACK = 0x08
VK_ESCAPE = 0x1B
VK_TAB = 0x09

# SendInput constants
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

# Window constants
SW_RESTORE = 9
SW_SHOW = 5


# ==================== Win32 结构体 ====================

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("_input", _INPUT),
    ]


# ==================== 核心函数 ====================

def send_key(vk, flags=0):
    """发送单个按键事件，强制附加硬件扫描码以穿透 Chromium 拦截"""
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp._input.ki.wVk = vk
    
    # 动态计算硬件扫描码
    scan_code = user32.MapVirtualKeyW(vk, 0) 
    inp._input.ki.wScan = scan_code
    
    # 强制加上 KEYEVENTF_SCANCODE (0x0008) 标志位
    # 如果原 flags 有 KEYUP (0x0002)，要通过按位或 (|) 保留下来
    inp._input.ki.dwFlags = flags | 0x0008 
    
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def press_key(vk):
    """按下并释放一个键。"""
    send_key(vk, 0)
    time.sleep(0.02)
    send_key(vk, KEYEVENTF_KEYUP)
    time.sleep(0.02)


def send_unicode_char(char):
    """发送一个 Unicode 字符。"""
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp._input.ki.wScan = ord(char)
    inp._input.ki.dwFlags = KEYEVENTF_UNICODE
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    time.sleep(0.01)

    inp._input.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    time.sleep(0.01)


def type_string(text):
    """逐字符输入文本（支持中文等 Unicode）。"""
    for char in text:
        send_unicode_char(char)
    time.sleep(0.1)


def combo_key(modifier_vk, key_vk):
    """发送组合键（如 Ctrl+/）。"""
    send_key(modifier_vk, 0)
    time.sleep(0.05)
    send_key(key_vk, 0)
    time.sleep(0.05)
    send_key(key_vk, KEYEVENTF_KEYUP)
    time.sleep(0.05)
    send_key(modifier_vk, KEYEVENTF_KEYUP)
    time.sleep(0.1)


def find_antigravity_window():
    """查找 Antigravity 主窗口句柄。"""
    result = []

    @ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def enum_callback(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                if "Antigravity" in title and "Tools" not in title:
                    result.append((hwnd, title))
        return True

    user32.EnumWindows(enum_callback, 0)
    return result


def activate_window(hwnd):
    """激活并前置指定窗口。"""
    user32.ShowWindow(hwnd, SW_RESTORE)
    time.sleep(0.2)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)


def switch_model(model_name, message="Continue"):
    """
    自动切换 Antigravity 的模型。
    
    步骤:
    1. 找到 Antigravity 窗口并激活
    2. 发送 Ctrl+/ 打开模型选择器
    3. 输入模型名称进行筛选
    4. 按 Enter 选择
    5. 在聊天框输入消息并发送
    """
    # 1. 查找窗口
    windows = find_antigravity_window()
    if not windows:
        print("❌ 未找到 Antigravity 窗口!")
        return False

    hwnd, title = windows[0]
    print(f"✅ 找到窗口: {title} (hwnd={hwnd})")

    # 2. 激活窗口
    activate_window(hwnd)
    print("✅ 窗口已激活")

    # 3. 发送 Ctrl+/ 打开模型选择器
    time.sleep(0.3)
    combo_key(VK_CONTROL, VK_SLASH)
    print("✅ 已发送 Ctrl+/ (打开模型选择器)")
    time.sleep(0.8)  # 等待模型选择器弹出

    # 4. 输入模型名称
    type_string(model_name)
    print(f"✅ 已输入模型名称: {model_name}")
    time.sleep(0.5)  # 等待搜索过滤

    # 5. 按 Enter 选择第一个匹配结果
    press_key(VK_RETURN)
    print("✅ 已按 Enter 选择模型")
    time.sleep(0.5)

    # 6. 如果需要发送消息
    if message:
        time.sleep(0.5)
        type_string(message)
        print(f"✅ 已输入消息: {message}")
        time.sleep(0.3)
        press_key(VK_RETURN)
        print("✅ 已发送消息")

    print(f"\n🎉 模型切换完成: → {model_name}")
    return True


def monitor_signal_file(signal_path, check_interval=2.0):
    """
    后台监控信号文件，实现 Agent 触发模型切换。
    
    Agent 只需创建信号文件，内容格式:
      第1行: 目标模型名称
      第2行 (可选): 要发送的消息 (默认 "Continue")
    """
    print(f"👀 监控信号文件: {signal_path}")
    print(f"   检查间隔: {check_interval}s")
    print(f"   按 Ctrl+C 停止\n")

    while True:
        try:
            if os.path.exists(signal_path):
                with open(signal_path, 'r', encoding='utf-8') as f:
                    lines = f.read().strip().split('\n')

                model_name = lines[0].strip()
                message = lines[1].strip() if len(lines) > 1 else "Continue"

                print(f"\n📡 检测到切换信号: {model_name}")
                os.remove(signal_path)  # 立即删除信号文件

                time.sleep(1.0)  # 等待一小段时间
                success = switch_model(model_name, message)
                if not success:
                    print("⚠️ 切换失败，将在下次信号时重试")

            time.sleep(check_interval)

        except KeyboardInterrupt:
            print("\n🛑 监控已停止")
            break
        except Exception as e:
            print(f"⚠️ 错误: {e}")
            time.sleep(check_interval)


# ==================== 命令行接口 ====================

def main():
    parser = argparse.ArgumentParser(
        description="Antigravity 模型自动切换工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python switch_model.py "Gemini 3 Flash"
  python switch_model.py "Claude Sonnet 4.6 (Thinking)" --msg "请审查代码"
  python switch_model.py --monitor
  python switch_model.py --monitor --signal-file ./workspace/.model_switch
  python switch_model.py --list-windows
        """
    )
    parser.add_argument("model", nargs="?", help="目标模型名称")
    parser.add_argument("--msg", default="Continue", help="切换后发送的消息 (默认: Continue)")
    parser.add_argument("--no-msg", action="store_true", help="切换后不发送消息")
    parser.add_argument("--monitor", action="store_true", help="后台监控信号文件模式")
    parser.add_argument("--signal-file", default=".model_switch", help="信号文件路径 (默认: .model_switch)")
    parser.add_argument("--interval", type=float, default=2.0, help="监控检查间隔秒数 (默认: 2.0)")
    parser.add_argument("--list-windows", action="store_true", help="列出所有 Antigravity 窗口")

    args = parser.parse_args()

    if args.list_windows:
        windows = find_antigravity_window()
        if windows:
            print("找到的 Antigravity 窗口:")
            for hwnd, title in windows:
                print(f"  hwnd={hwnd}: {title}")
        else:
            print("未找到 Antigravity 窗口")
        return

    if args.monitor:
        monitor_signal_file(args.signal_file, args.interval)
        return

    if not args.model:
        parser.print_help()
        return

    message = None if args.no_msg else args.msg
    switch_model(args.model, message)


if __name__ == "__main__":
    main()

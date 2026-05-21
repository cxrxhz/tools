import originpro as op
import sys
import os
import time

# 【防坑机制】接管系统异常钩子。如果在运行中途你的代码写错了报错，
# 这个机制会确保 Origin 接收到关闭指令，防止它变成后台删不掉的僵尸进程。
sys.excepthook = op.excepthook

def main():
    print("正在尝试通过 COM 接口唤醒 Origin 引擎...")
    
    # 将 show 设置为 True。测试阶段建议打开，让你能用肉眼看到 Origin 弹出来操作；
    # 未来部署自动化脚本时，可以改为 False 让它在后台静默光速运行。
    op.set_show(True) 

    try:
        # 1. 新建一个工作簿 (Workbook)
        wks = op.new_sheet('w')
        print("-> 成功创建工作簿")

        # 2. 写入极其简单的测试数据 (X轴和Y轴)
        wks.from_list(0, [1, 2, 3, 4, 5], 'X')
        wks.from_list(1, [15, 28, 36, 42, 59], 'Y')
        print("-> 成功写入测试数据")

        # 3. 调用内置模板绘制散点图
        graph = op.new_graph(template='scatter')
        layer = graph[0]
        # 把工作簿的第1列(Y)和第0列(X)扔进图层
        layer.add_plot(wks, 1, 0) 
        layer.rescale()
        print("-> 成功绘制散点图")

        # 4. 获取桌面路径并保存工程文件
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        save_file = os.path.join(desktop_path, "Origin_API_Test.opju")
        op.save(save_file)
        print(f"-> 测试流跑通！文件已保存至: {save_file}")

        # 悬停 3 秒让你看清软件界面的变化，然后再关闭
        time.sleep(3)

    except Exception as e:
        print(f"X 运行过程中发生错误，请检查: {e}")
        
    finally:
        # 5. 安全退出，断开连接并清理内存
        if op and op.oext:
            op.exit()
        print("Origin 引擎已安全关闭，COM 资源已释放。")

if __name__ == '__main__':
    main()
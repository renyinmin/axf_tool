#!/usr/bin/env python3
"""
Modbus AXF工具 - 简化启动器（延迟导入pymodbus）
"""

import sys
import os
import io

# 设置标准输出编码为UTF-8
if sys.stdout is not None and sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except:
        pass

def main():
    """主函数"""
    print("=" * 60)
    print("Modbus AXF工具")
    print("=" * 60)
    print()
    print("功能:")
    print("  1. 解析AXF/ELF文件，提取变量地址")
    print("  2. 通过Modbus协议读写内存（支持串口和WebSocket）")
    print("  3. 支持多种数据显示类型")
    print()

    # 检查基本依赖
    try:
        import tkinter
        from elftools.elf.elffile import ELFFile
        print("[OK] 基本依赖已安装")
    except ImportError as e:
        print(f"[ERROR] 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        input("\n按回车键退出...")
        return 1

    # 检查pymodbus（延迟导入以避免asyncio问题）
    print("[检查] pymodbus库...")
    try:
        # 尝试导入，如果失败则提供替代方案
        import importlib
        spec = importlib.util.find_spec("pymodbus")
        if spec is None:
            print("[警告] pymodbus未安装")
            print("串口通信功能将不可用")
            print("但WebSocket通信功能仍可使用")
            print()
            print("要启用串口通信，请运行:")
            print("  pip install pymodbus")
            print()
        else:
            print("[OK] pymodbus已安装")
    except Exception as e:
        print(f"[警告] 检查pymodbus时出错: {e}")
        print("将继续尝试启动程序...")
        print()

    # 启动GUI
    try:
        print("正在导入GUI模块...")

        # 尝试导入修复版本的GUI
        try:
            from gui_fixed import main as gui_main
            print("使用修复版GUI")
        except ImportError:
            # 如果修复版不存在，使用原版
            from gui import main as gui_main
            print("使用原版GUI")

        print("GUI模块导入成功")
        print("启动GUI界面...")
        print("注意：如果GUI卡住，请按Ctrl+C或关闭窗口")
        print()

        gui_main()
        print("GUI界面已关闭")
        return 0
    except ImportError as e:
        print(f"GUI模块导入失败: {e}")
        print("\n建议使用命令行模式：")
        print("  1. 解析AXF文件: python main.py parse <axf文件> --list")
        print("  2. 读取内存: python main.py read --port COM3 --address 0x20000000")
        input("\n按回车键退出...")
        return 1
    except Exception as e:
        print(f"启动GUI失败: {e}")
        print("\nGUI可能因系统兼容性问题卡住")
        print("请尝试：")
        print("  1. 运行命令行模式 (见上)")
        print("  2. 运行演示脚本: python demo.py")
        print("  3. 运行基础测试: python minimal_test.py")
        input("\n按回车键退出...")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n程序出错: {e}")
        import traceback
        traceback.print_exc()
        print("\n按任意键退出...")
        input()

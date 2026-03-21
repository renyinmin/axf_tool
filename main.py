#!/usr/bin/env python3
"""
Modbus AXF工具 - 主入口点
"""

import sys
import os
import io

# 设置标准输出编码为UTF-8，避免中文字符输出问题
# 注意：PyInstaller --windowed 模式下 sys.stdout 可能为 None
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
    print("  2. 通过Modbus协议读写内存")
    print("  3. 支持多种数据显示类型")
    print()

    # 检查依赖
    try:
        import tkinter
        from elftools.elf.elffile import ELFFile
        from pymodbus.client import ModbusSerialClient
        print("[OK] 所有依赖已安装")
    except ImportError as e:
        print(f"[ERROR] 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        input("\n按回车键退出...")
        return 1

    # 启动GUI - 使用修复版本
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

def cli_mode():
    """命令行模式"""
    import argparse
    from axf_parser import AXFParser
    from modbus_client import ModbusMemoryClient, DisplayType

    parser = argparse.ArgumentParser(description="Modbus AXF工具命令行模式")
    subparsers = parser.add_subparsers(dest='command', help='命令')

    # 解析AXF文件
    axf_parser = subparsers.add_parser('parse', help='解析AXF文件')
    axf_parser.add_argument('axf_file', help='AXF文件路径')
    axf_parser.add_argument('--list', action='store_true', help='列出所有全局变量')
    axf_parser.add_argument('--search', type=str, help='搜索变量名')

    # 读取内存
    read_parser = subparsers.add_parser('read', help='读取内存')
    read_parser.add_argument('--port', required=True, help='串口端口')
    read_parser.add_argument('--address', type=lambda x: int(x, 0), required=True, help='内存地址')
    read_parser.add_argument('--type', type=str, default='hex', help='显示类型')

    args = parser.parse_args()

    if args.command == 'parse':
        if not os.path.exists(args.axf_file):
            print(f"错误: 文件不存在: {args.axf_file}")
            return 1

        axf = AXFParser(args.axf_file)
        print(f"已加载: {args.axf_file}")
        print(f"符号数量: {len(axf.symbols)}")

        if args.search:
            address = axf.get_variable_address(args.search)
            if address:
                print(f"{args.search}: 0x{address:08X}")
            else:
                print(f"未找到变量: {args.search}")

        if args.list:
            variables = axf.list_global_variables()
            print(f"\n全局变量 ({len(variables)} 个):")
            for name, addr in sorted(variables.items(), key=lambda x: x[0])[:50]:
                print(f"  {name}: 0x{addr:08X}")
            if len(variables) > 50:
                print(f"  ... (只显示前50个)")

    elif args.command == 'read':
        client = ModbusMemoryClient(port=args.port, baudrate=115200)
        if not client.connect():
            print(f"连接失败: {args.port}")
            return 1

        try:
            display_type = DisplayType(args.type)
        except:
            display_type = DisplayType.HEX

        value = client.read_memory(args.address, display_type)
        if value is not None:
            print(f"地址 0x{args.address:08X}: {value}")
        else:
            print("读取失败")

        client.disconnect()

    else:
        parser.print_help()

    return 0

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            sys.exit(cli_mode())
        else:
            sys.exit(main())
    except Exception as e:
        print(f"\n程序出错: {e}")
        import traceback
        traceback.print_exc()
        print("\n按任意键退出...")
        input()
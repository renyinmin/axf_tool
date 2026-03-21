#!/usr/bin/env python3
"""
模拟gui_fixed.py导入过程
"""
import sys
import os

# 模拟gui_fixed.py的导入逻辑
print("模拟gui_fixed.py导入过程...")

# 添加项目目录到路径
sys.path.insert(0, os.path.dirname(__file__))
print(f"sys.path[0]: {sys.path[0]}")

# 尝试导入核心模块
print("\n尝试导入axf_parser...")
try:
    from axf_parser import AXFParser
    print(f"[OK] axf_parser导入成功")
    print(f"    AXFParser模块: {AXFParser.__module__}")
    print(f"    AXFParser类: {AXFParser}")
except ImportError as e:
    print(f"[ERROR] axf_parser导入失败: {e}")
    import traceback
    traceback.print_exc()

print("\n尝试导入elftools.elf.elffile...")
try:
    from elftools.elf.elffile import ELFFile
    print(f"[OK] ELFFile导入成功")
except ImportError as e:
    print(f"[ERROR] ELFFile导入失败: {e}")
    import traceback
    traceback.print_exc()

print("\n检查axf_parser中的导入...")
# 尝试导入axf_parser并检查其依赖
try:
    import axf_parser
    print(f"[OK] 成功导入axf_parser模块")
    print(f"    文件位置: {axf_parser.__file__}")

    # 检查模块内容
    import inspect
    source = inspect.getsource(axf_parser)
    if "from elftools.elf.elffile import ELFFile" in source:
        print(f"[OK] axf_parser中包含ELFFile导入")
    else:
        print(f"[WARNING] axf_parser中未找到ELFFile导入")

except Exception as e:
    print(f"[ERROR] 检查失败: {e}")
    import traceback
    traceback.print_exc()
#!/usr/bin/env python3
import sys
import os

# 模拟gui_fixed.py中的导入
try:
    from axf_parser import AXFParser
    from modbus_client import ModbusMemoryClient, DisplayType
    MODULES_LOADED = True
    print(f"[DEBUG] 模块导入成功: axf_parser, modbus_client")
    print(f"[DEBUG] AXFParser模块: {AXFParser.__module__}")
    print(f"[DEBUG] ModbusMemoryClient模块: {ModbusMemoryClient.__module__}")
except ImportError as e:
    MODULES_LOADED = False
    print(f"[DEBUG] 模块导入失败: {e}")

print(f"[DEBUG] 模块名称: {__name__}")
print(f"[DEBUG] MODULES_LOADED: {MODULES_LOADED}")
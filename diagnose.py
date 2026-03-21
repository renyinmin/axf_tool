#!/usr/bin/env python3
"""
诊断elftools导入问题
"""
import sys
import os

print("=" * 60)
print("诊断信息")
print("=" * 60)

print(f"Python 可执行文件: {sys.executable}")
print(f"Python 版本: {sys.version}")
print(f"当前目录: {os.getcwd()}")
print(f"文件位置: {__file__}")

print("\n1. 检查 elftools 导入...")
try:
    import elftools
    print(f"   [OK] elftools 版本: {elftools.__version__}")
except ImportError as e:
    print(f"   [ERROR] 导入失败: {e}")
    print(f"   尝试导入 pyelftools...")
    try:
        import pyelftools
        print(f"   [OK] pyelftools 可用: {pyelftools}")
    except ImportError:
        print("   [ERROR] pyelftools 也未安装")

print("\n2. 检查 ELFFile 导入...")
try:
    from elftools.elf.elffile import ELFFile
    print("   [OK] ELFFile 导入成功")
except ImportError as e:
    print(f"   [ERROR] 导入失败: {e}")

print("\n3. 检查 axf_parser 导入...")
try:
    from axf_parser import AXFParser
    print("   [OK] AXFParser 导入成功")
except ImportError as e:
    print(f"   [ERROR] 导入失败: {e}")
    print(f"   错误详情: {e}")

print("\n4. 检查 sys.path...")
for i, path in enumerate(sys.path[:10]):
    print(f"   [{i}] {path}")
if len(sys.path) > 10:
    print(f"   ... 还有 {len(sys.path)-10} 个路径")

print("\n5. 检查已安装的包...")
try:
    import pkg_resources
    packages = ['pyelftools', 'pymodbus', 'pyserial', 'pyusb', 'python-dotenv']
    for pkg in packages:
        try:
            version = pkg_resources.get_distribution(pkg).version
            print(f"   [OK] {pkg}=={version}")
        except pkg_resources.DistributionNotFound:
            print(f"   [ERROR] {pkg} 未安装")
except Exception as e:
    print(f"   无法检查包: {e}")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
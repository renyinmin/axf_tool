#!/usr/bin/env python3
"""
Modbus客户端，用于与目标设备通信。
支持通过特定寄存器读写内存地址。
"""

import time
import struct
from enum import Enum
from typing import Optional, Union, List, Tuple

ModbusSerialClient = None
ModbusException = None
ExceptionResponse = None

def _ensure_pymodbus():
    global ModbusSerialClient, ModbusException, ExceptionResponse
    if ModbusSerialClient is None:
        from pymodbus.client import ModbusSerialClient as _MSC
        from pymodbus.exceptions import ModbusException as _ME
        from pymodbus.pdu import ExceptionResponse as _ER
        ModbusSerialClient = _MSC
        ModbusException = _ME
        ExceptionResponse = _ER

class DisplayType(Enum):
    """数据显示类型"""
    HEX = "hex"           # 十六进制
    DECIMAL = "decimal"   # 十进制
    FLOAT = "float"       # 单精度浮点数
    INT32 = "int32"       # 有符号32位整数
    UINT32 = "uint32"    # 无符号32位整数
    INT16 = "int16"       # 有符号16位整数
    UINT16 = "uint16"    # 无符号16位整数

class ModbusMemoryClient:
    """Modbus内存读写客户端"""

    # 寄存器地址定义
    ADDR_WRITE_ADDR = 49999  # 写入要读取的内存地址
    ADDR_READ_DATA = 50000   # 读取内存数据

    def __init__(self, port: str = 'COM1', baudrate: int = 115200,
                 timeout: float = 1.0, **kwargs):
        """
        初始化Modbus客户端

        Args:
            port: 串口端口，如 'COM1' 或 '/dev/ttyUSB0'
            baudrate: 波特率，默认115200
            timeout: 超时时间（秒）
            **kwargs: 其他ModbusSerialClient参数
        """
        _ensure_pymodbus()
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        # 创建Modbus客户端
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            **kwargs
        )

        self.connected = False

    def connect(self) -> bool:
        """连接到Modbus设备"""
        try:
            self.connected = self.client.connect()
            return self.connected
        except Exception as e:
            print(f"连接失败: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """断开连接"""
        if self.client:
            self.client.close()
        self.connected = False

    def read_memory(self, address: int, display_type: DisplayType = DisplayType.UINT32) -> Optional[Union[int, float]]:
        """
        读取指定内存地址的数据

        Args:
            address: 内存地址（32位）
            display_type: 数据显示类型

        Returns:
            读取到的数据，如果失败则返回None
        """
        if not self.connected:
            if not self.connect():
                return None

        try:
            # 步骤1: 将内存地址写入ADDR_WRITE_ADDR寄存器
            # 地址可能是32位，需要拆分为两个16位寄存器
            addr_high = (address >> 16) & 0xFFFF
            addr_low = address & 0xFFFF

            # 写入地址高位和低位
            write_result = self.client.write_registers(
                self.ADDR_WRITE_ADDR,
                [addr_high, addr_low]
            )

            if isinstance(write_result, ExceptionResponse):
                print(f"写入地址失败: {write_result}")
                return None

            # 短暂延迟，确保设备处理
            time.sleep(0.01)

            # 步骤2: 从ADDR_READ_DATA寄存器读取数据
            # 读取2个寄存器（32位数据）
            read_result = self.client.read_holding_registers(
                self.ADDR_READ_DATA,
                2
            )

            if isinstance(read_result, ExceptionResponse):
                print(f"读取数据失败: {read_result}")
                return None

            # 提取数据
            data_high = read_result.registers[0]
            data_low = read_result.registers[1]

            # 合并为32位整数
            raw_value = (data_high << 16) | data_low

            # 根据显示类型转换数据
            return self._convert_value(raw_value, display_type)

        except ModbusException as e:
            print(f"Modbus通信错误: {e}")
            return None
        except Exception as e:
            print(f"未知错误: {e}")
            return None

    def write_memory(self, address: int, value: int, value_type: DisplayType = DisplayType.UINT32) -> bool:
        """
        向指定内存地址写入数据

        Args:
            address: 内存地址（32位）
            value: 要写入的值
            value_type: 值的数据类型

        Returns:
            成功返回True，失败返回False
        """
        if not self.connected:
            if not self.connect():
                return False

        try:
            # 将值转换为原始32位整数
            raw_value = self._value_to_raw(value, value_type)

            # 步骤1: 写入内存地址
            addr_high = (address >> 16) & 0xFFFF
            addr_low = address & 0xFFFF
            write_addr_result = self.client.write_registers(
                self.ADDR_WRITE_ADDR,
                [addr_high, addr_low]
            )

            if isinstance(write_addr_result, ExceptionResponse):
                print(f"写入地址失败: {write_addr_result}")
                return False

            time.sleep(0.01)

            # 步骤2: 写入数据到ADDR_READ_DATA（假设该寄存器也可写）
            data_high = (raw_value >> 16) & 0xFFFF
            data_low = raw_value & 0xFFFF
            write_data_result = self.client.write_registers(
                self.ADDR_READ_DATA,
                [data_high, data_low]
            )

            if isinstance(write_data_result, ExceptionResponse):
                print(f"写入数据失败: {write_data_result}")
                return False

            return True

        except ModbusException as e:
            print(f"Modbus通信错误: {e}")
            return False
        except Exception as e:
            print(f"未知错误: {e}")
            return False

    def _convert_value(self, raw_value: int, display_type: DisplayType) -> Union[int, float]:
        """将原始32位值转换为指定类型"""
        if display_type == DisplayType.HEX:
            return raw_value
        elif display_type == DisplayType.DECIMAL:
            return raw_value
        elif display_type == DisplayType.FLOAT:
            # 将32位整数解释为IEEE 754单精度浮点数
            return struct.unpack('f', struct.pack('I', raw_value))[0]
        elif display_type == DisplayType.INT32:
            # 有符号32位整数
            if raw_value >= 0x80000000:
                return raw_value - 0x100000000
            return raw_value
        elif display_type == DisplayType.UINT32:
            return raw_value
        elif display_type == DisplayType.INT16:
            # 取低16位作为有符号整数
            low16 = raw_value & 0xFFFF
            if low16 >= 0x8000:
                return low16 - 0x10000
            return low16
        elif display_type == DisplayType.UINT16:
            return raw_value & 0xFFFF
        else:
            return raw_value

    def _value_to_raw(self, value: Union[int, float], value_type: DisplayType) -> int:
        """将值转换为原始32位整数"""
        if value_type == DisplayType.FLOAT:
            # 浮点数转换为32位整数表示
            return struct.unpack('I', struct.pack('f', value))[0]
        elif value_type == DisplayType.INT32:
            # 有符号32位整数转换为无符号表示
            if value < 0:
                return value + 0x100000000
            return value
        elif value_type == DisplayType.INT16:
            # 有符号16位整数
            if value < 0:
                value = value + 0x10000
            return value & 0xFFFF
        elif value_type == DisplayType.UINT16:
            return value & 0xFFFF
        else:
            # HEX, DECIMAL, UINT32直接使用
            return int(value) & 0xFFFFFFFF

    def scan_ports(self) -> List[str]:
        """扫描可用的串口（简化实现）"""
        import serial.tools.list_ports
        ports = [port.device for port in serial.tools.list_ports.comports()]
        return ports

    def test_connection(self) -> bool:
        """测试连接是否正常"""
        if not self.connected:
            return False

        try:
            # 尝试读取保持寄存器（可能不支持）
            result = self.client.read_holding_registers(0, 1)
            return not isinstance(result, ExceptionResponse)
        except:
            return False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def test():
    """测试函数"""
    import sys

    # 测试参数
    if len(sys.argv) < 2:
        print("用法: python modbus_client.py <串口> [地址]")
        print("示例: python modbus_client.py COM3 0x20000000")
        return

    port = sys.argv[1]
    address = 0x20000000 if len(sys.argv) < 3 else int(sys.argv[2], 0)

    client = ModbusMemoryClient(port=port, baudrate=115200)

    print(f"连接到 {port}...")
    if not client.connect():
        print("连接失败")
        return

    print(f"读取地址 0x{address:08X}...")

    # 测试不同显示类型
    for display_type in DisplayType:
        value = client.read_memory(address, display_type)
        if value is not None:
            print(f"  {display_type.value}: {value}")
        else:
            print(f"  {display_type.value}: 读取失败")

    client.disconnect()

if __name__ == "__main__":
    test()
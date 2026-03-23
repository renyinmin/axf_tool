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
    FLOAT = "float"       # 单精度浮点数
    INT32 = "int32"       # 有符号32位整数
    UINT32 = "uint32"    # 无符号32位整数
    INT16 = "int16"       # 有符号16位整数
    UINT16 = "uint16"    # 无符号16位整数
    INT8 = "int8"        # 有符号8位整数
    UINT8 = "uint8"      # 无符号8位整数

class ModbusMemoryClient:
    """Modbus内存读写客户端"""

    ADDR_WRITE_ADDR = 43507
    ADDR_READ_DATA = 43509

    def __init__(self, port: str = 'COM1', baudrate: int = 115200,
                 timeout: float = 1.0, debug: bool = True, packet_callback=None, **kwargs):
        _ensure_pymodbus()
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.debug = debug
        self.packet_callback = packet_callback

        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            **kwargs
        )

        self.connected = False

    def _print_packet(self, direction: str, data: bytes, description: str = ""):
        """打印报文"""
        hex_str = ' '.join(f'{b:02X}' for b in data)
        if self.debug:
            print(f"\n[{direction}] {description}")
            print(f"  报文: {hex_str}")
            print(f"  长度: {len(data)} 字节")
        if self.packet_callback:
            self.packet_callback(direction, hex_str, len(data), description)

    def _build_write_registers_request(self, address: int, values: list, slave_id: int = 1) -> bytes:
        """构建写多个寄存器请求报文 (功能码16)"""
        packet = bytearray()
        packet.append(slave_id)
        packet.append(0x10)
        packet.append((address >> 8) & 0xFF)
        packet.append(address & 0xFF)
        packet.append((len(values) >> 8) & 0xFF)
        packet.append(len(values) & 0xFF)
        packet.append(len(values) * 2)
        for val in values:
            packet.append((val >> 8) & 0xFF)
            packet.append(val & 0xFF)
        crc = self._calculate_crc(packet)
        packet.extend(crc)
        return bytes(packet)

    def _build_read_registers_request(self, address: int, count: int, slave_id: int = 1) -> bytes:
        """构建读保持寄存器请求报文 (功能码03)"""
        packet = bytearray()
        packet.append(slave_id)
        packet.append(0x03)
        packet.append((address >> 8) & 0xFF)
        packet.append(address & 0xFF)
        packet.append((count >> 8) & 0xFF)
        packet.append(count & 0xFF)
        crc = self._calculate_crc(packet)
        packet.extend(crc)
        return bytes(packet)

    def _calculate_crc(self, data: bytearray) -> bytes:
        """计算Modbus RTU CRC16"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return bytes([crc & 0xFF, (crc >> 8) & 0xFF])

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
        if not self.connected:
            if not self.connect():
                return None

        if isinstance(display_type, str):
            display_type = DisplayType(display_type)

        try:
            addr_high = (address >> 16) & 0xFFFF
            addr_low = address & 0xFFFF

            print(f"\n{'='*60}")
            print(f"读取内存地址: 0x{address:08X}")
            print(f"显示类型: {display_type.value}")
            print(f"{'='*60}")

            write_req = self._build_write_registers_request(
                self.ADDR_WRITE_ADDR, [addr_high, addr_low]
            )
            self._print_packet("发送", write_req, f"写寄存器 {self.ADDR_WRITE_ADDR} (设置内存地址)")

            write_result = self.client.write_registers(
                self.ADDR_WRITE_ADDR,
                [addr_high, addr_low]
            )

            if isinstance(write_result, ExceptionResponse):
                print(f"写入地址失败: {write_result}")
                return None

            write_resp = bytes([0x01, 0x10,
                               (self.ADDR_WRITE_ADDR >> 8) & 0xFF, self.ADDR_WRITE_ADDR & 0xFF,
                               0x00, 0x02])
            crc = self._calculate_crc(bytearray(write_resp))
            write_resp = write_resp + crc
            self._print_packet("接收", write_resp, "写寄存器响应")

            time.sleep(0.01)

            read_req = self._build_read_registers_request(self.ADDR_READ_DATA, 2)
            self._print_packet("发送", read_req, f"读寄存器 {self.ADDR_READ_DATA} (读取内存数据)")

            read_result = self.client.read_holding_registers(
                address=self.ADDR_READ_DATA,
                count=2
            )

            if isinstance(read_result, ExceptionResponse):
                print(f"读取数据失败: {read_result}")
                return None

            data_high = read_result.registers[0]
            data_low = read_result.registers[1]

            read_resp = bytes([0x01, 0x03, 0x04,
                              (data_high >> 8) & 0xFF, data_high & 0xFF,
                              (data_low >> 8) & 0xFF, data_low & 0xFF])
            crc = self._calculate_crc(bytearray(read_resp))
            read_resp = read_resp + crc
            self._print_packet("接收", read_resp, f"读寄存器响应 (数据: 0x{data_high:04X} 0x{data_low:04X})")

            if display_type in [DisplayType.INT16, DisplayType.UINT16]:
                raw_value = data_low
            elif display_type in [DisplayType.INT8, DisplayType.UINT8]:
                raw_value = data_low & 0xFF
            else:
                raw_value = (data_high << 16) | data_low

            result = self._convert_value(raw_value, display_type)

            print(f"\n结果: {result}")
            print(f"原始值: 0x{raw_value:08X}")

            return result

        except ModbusException as e:
            print(f"Modbus通信错误: {e}")
            return None
        except Exception as e:
            print(f"未知错误: {e}")
            return None

    def write_memory(self, address: int, value: int, value_type: DisplayType = DisplayType.UINT32) -> bool:
        if not self.connected:
            if not self.connect():
                return False

        if isinstance(value_type, str):
            value_type = DisplayType(value_type)

        try:
            raw_value = self._value_to_raw(value, value_type)

            print(f"\n{'='*60}")
            print(f"写入内存地址: 0x{address:08X}")
            print(f"写入值: {value} (原始: 0x{raw_value:08X})")
            print(f"值类型: {value_type.value}")
            print(f"{'='*60}")

            addr_high = (address >> 16) & 0xFFFF
            addr_low = address & 0xFFFF

            write_addr_req = self._build_write_registers_request(
                self.ADDR_WRITE_ADDR, [addr_high, addr_low]
            )
            self._print_packet("发送", write_addr_req, f"写寄存器 {self.ADDR_WRITE_ADDR} (设置内存地址)")

            write_addr_result = self.client.write_registers(
                self.ADDR_WRITE_ADDR,
                [addr_high, addr_low]
            )

            if isinstance(write_addr_result, ExceptionResponse):
                print(f"写入地址失败: {write_addr_result}")
                return False

            write_addr_resp = bytes([0x01, 0x10,
                                     (self.ADDR_WRITE_ADDR >> 8) & 0xFF, self.ADDR_WRITE_ADDR & 0xFF,
                                     0x00, 0x02])
            crc = self._calculate_crc(bytearray(write_addr_resp))
            write_addr_resp = write_addr_resp + crc
            self._print_packet("接收", write_addr_resp, "写寄存器响应")

            time.sleep(0.01)

            data_high = (raw_value >> 16) & 0xFFFF
            data_low = raw_value & 0xFFFF

            write_data_req = self._build_write_registers_request(
                self.ADDR_READ_DATA, [data_high, data_low]
            )
            self._print_packet("发送", write_data_req, f"写寄存器 {self.ADDR_READ_DATA} (写入数据)")

            write_data_result = self.client.write_registers(
                self.ADDR_READ_DATA,
                [data_high, data_low]
            )

            if isinstance(write_data_result, ExceptionResponse):
                print(f"写入数据失败: {write_data_result}")
                return False

            write_data_resp = bytes([0x01, 0x10,
                                     (self.ADDR_READ_DATA >> 8) & 0xFF, self.ADDR_READ_DATA & 0xFF,
                                     0x00, 0x02])
            crc = self._calculate_crc(bytearray(write_data_resp))
            write_data_resp = write_data_resp + crc
            self._print_packet("接收", write_data_resp, "写寄存器响应")

            print(f"\n写入成功!")
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
        elif display_type == DisplayType.FLOAT:
            return struct.unpack('f', struct.pack('I', raw_value))[0]
        elif display_type == DisplayType.INT32:
            if raw_value >= 0x80000000:
                return raw_value - 0x100000000
            return raw_value
        elif display_type == DisplayType.UINT32:
            return raw_value
        elif display_type == DisplayType.INT16:
            low16 = raw_value & 0xFFFF
            if low16 >= 0x8000:
                return low16 - 0x10000
            return low16
        elif display_type == DisplayType.UINT16:
            return raw_value & 0xFFFF
        elif display_type == DisplayType.INT8:
            low8 = raw_value & 0xFF
            if low8 >= 0x80:
                return low8 - 0x100
            return low8
        elif display_type == DisplayType.UINT8:
            return raw_value & 0xFF
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
            result = self.client.read_holding_registers(address=0, count=1)
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
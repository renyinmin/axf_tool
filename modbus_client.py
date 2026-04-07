#!/usr/bin/env python3
"""
Modbus客户端，用于与目标设备通信。
支持通过特定寄存器读写内存地址。
支持串口和WebSocket两种通信方式。
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

WebSocketClient = None

def _ensure_websocket():
    global WebSocketClient
    if WebSocketClient is None:
        try:
            from websocket_client import WebSocketClient as _WSC
            WebSocketClient = _WSC
        except ImportError:
            WebSocketClient = None

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

    def __init__(self, port: str = 'COM1', baudrate: int = 9600,
                 timeout: float = 1.0, debug: bool = True, packet_callback=None,
                 comm_type: str = 'serial', **kwargs):
        self.comm_type = comm_type
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.debug = debug
        self.packet_callback = packet_callback

        self.serial_client = None
        self.ws_client = None
        self.connected = False

        if comm_type == 'serial':
            _ensure_pymodbus()
            self.serial_client = ModbusSerialClient(
                port=port,
                baudrate=baudrate,
                timeout=timeout,
                **kwargs
            )
        elif comm_type == 'websocket':
            _ensure_websocket()
            if WebSocketClient:
                self.ws_client = WebSocketClient(packet_callback=packet_callback)
            else:
                raise ImportError("WebSocket客户端不可用，请安装websocket-client库")
        else:
            raise ValueError(f"不支持的通信类型: {comm_type}")

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

    def _build_preset_multiple_registers(self, address: int, values: List[int], slave_id: int = 1) -> bytes:
        """构建预置多个寄存器请求报文 (功能码10)"""
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

    def connect(self) -> bool:
        """连接到Modbus设备"""
        try:
            if self.comm_type == 'serial' and self.serial_client:
                self.connected = self.serial_client.connect()
                return self.connected
            elif self.comm_type == 'websocket' and self.ws_client:
                self.connected = self.ws_client.connect()
                return self.connected
            else:
                print(f"连接失败: 无效的通信类型 {self.comm_type}")
                return False
        except Exception as e:
            print(f"连接失败: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """断开连接"""
        if self.comm_type == 'serial' and self.serial_client:
            self.serial_client.close()
        elif self.comm_type == 'websocket' and self.ws_client:
            self.ws_client.disconnect()
        self.connected = False

    def read_memory(self, address: int, display_type: DisplayType = DisplayType.UINT32, 
                  write_addr: int = None, read_addr: int = None, return_raw: bool = False) -> Optional[Union[int, float, tuple]]:
        if not self.connected:
            if not self.connect():
                return None

        if isinstance(display_type, str):
            display_type = DisplayType(display_type)

        if self.comm_type == 'websocket' and self.ws_client:
            return self._read_memory_ws(address, display_type, write_addr, read_addr, return_raw)
        elif self.comm_type == 'serial' and self.serial_client:
            return self._read_memory_serial(address, display_type, write_addr, read_addr, return_raw)
        else:
            print(f"读取失败: 无效的通信类型 {self.comm_type}")
            return None

    def _read_memory_serial(self, address: int, display_type: DisplayType, 
                           write_addr: int, read_addr: int, return_raw: bool) -> Optional[Union[int, float, tuple]]:
        """通过串口读取内存"""
        # 使用指定的写地址和读地址，如果没有指定则使用默认值
        write_addr = write_addr if write_addr is not None else self.ADDR_WRITE_ADDR
        read_addr = read_addr if read_addr is not None else self.ADDR_READ_DATA

        try:
            addr_high = (address >> 16) & 0xFFFF
            addr_low = address & 0xFFFF

            print(f"\n{'='*60}")
            print(f"读取内存地址: 0x{address:08X}")
            print(f"显示类型: {display_type.value}")
            print(f"{'='*60}")

            write_req = self._build_write_registers_request(
                write_addr, [addr_high, addr_low]
            )
            self._print_packet("发送", write_req, f"写寄存器 {write_addr} (设置内存地址)")

            write_result = self.serial_client.write_registers(
                write_addr,
                [addr_high, addr_low]
            )

            if isinstance(write_result, ExceptionResponse):
                print(f"写入地址失败: {write_result}")
                return None

            write_resp = bytes([0x01, 0x10,
                               (write_addr >> 8) & 0xFF, write_addr & 0xFF,
                               0x00, 0x02])
            crc = self._calculate_crc(bytearray(write_resp))
            write_resp = write_resp + crc
            self._print_packet("接收", write_resp, "写寄存器响应")

            time.sleep(0.01)

            read_req = self._build_read_registers_request(read_addr, 2)
            self._print_packet("发送", read_req, f"读寄存器 {read_addr} (读取内存数据)")

            read_result = self.serial_client.read_holding_registers(
                address=read_addr,
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

            if return_raw:
                return (result, raw_value)
            return result

        except ModbusException as e:
            print(f"Modbus通信错误: {e}")
            return None
        except Exception as e:
            print(f"未知错误: {e}")
            return None

    def _read_memory_ws(self, address: int, display_type: DisplayType,
                        write_addr: int, read_addr: int, return_raw: bool) -> Optional[Union[int, float, tuple]]:
        """通过WebSocket读取内存"""
        write_addr = write_addr if write_addr is not None else self.ADDR_WRITE_ADDR
        read_addr = read_addr if read_addr is not None else self.ADDR_READ_DATA
        
        print(f"[DEBUG] WebSocket读取: write_addr={write_addr}, read_addr={read_addr}")

        try:
            if address is None:
                print(f"错误: address 参数为 None")
                return None
            
            if isinstance(display_type, str):
                display_type = DisplayType(display_type)
            
            addr_high = (address >> 16) & 0xFFFF
            addr_low = address & 0xFFFF

            print(f"\n{'='*60}")
            print(f"读取内存地址: 0x{address:08X}")
            print(f"显示类型: {display_type.value}")
            print(f"{'='*60}")

            # 写入地址（使用功能码16写多个寄存器，和串口一样）
            # 向 write_addr 写入 addr_high 和 addr_low 两个寄存器
            parsed_data, _ = self.ws_client.send_modbus_command_with_raw(1, 16, write_addr, 2, 
                f"{addr_high:04X} {addr_low:04X}")
            # 功能码16的响应不包含数据，返回空列表是正常的，只要原始响应不为空即可
            if parsed_data is None:
                if self.ws_client._device_offline:
                    print(f"写入地址失败（offline）")
                else:
                    print(f"写入地址失败")
                return None

            time.sleep(0.01)

            # 读取数据
            print(f"[DEBUG] 开始发送读数据命令...")
            parsed_data, raw_response = self.ws_client.send_modbus_command_with_raw(1, 3, read_addr, 2)
            print(f"[DEBUG] WebSocket读取返回: parsed_data={parsed_data}, raw_response={raw_response}")
            
            if not parsed_data or len(parsed_data) < 2:
                if self.ws_client._device_offline:
                    print(f"读取数据失败（offline）")
                else:
                    print(f"读取数据失败: parsed_data={parsed_data}")
                return None

            data_high = parsed_data[0]
            data_low = parsed_data[1]
            print(f"[DEBUG] data_high=0x{data_high:04X}, data_low=0x{data_low:04X}")

            if display_type in [DisplayType.INT16, DisplayType.UINT16]:
                raw_value = data_low
            elif display_type in [DisplayType.INT8, DisplayType.UINT8]:
                raw_value = data_low & 0xFF
            else:
                raw_value = (data_high << 16) | data_low

            result = self._convert_value(raw_value, display_type)

            print(f"\n结果: {result}")
            print(f"原始值: 0x{raw_value:08X}")

            if return_raw:
                return (result, raw_value)
            return result

        except Exception as e:
            print(f"WebSocket读取错误: {e}")
            return None

    def write_memory(self, address: int, value: int, value_type: DisplayType = DisplayType.UINT32) -> bool:
        if not self.connected:
            if not self.connect():
                return False

        if isinstance(value_type, str):
            value_type = DisplayType(value_type)

        if self.comm_type == 'websocket' and self.ws_client:
            return self._write_memory_ws(address, value, value_type)
        elif self.comm_type == 'serial' and self.serial_client:
            return self._write_memory_serial(address, value, value_type)
        else:
            print(f"写入失败: 无效的通信类型 {self.comm_type}")
            return False

    def _write_memory_serial(self, address: int, value: int, value_type: DisplayType) -> bool:
        """通过串口写入内存"""
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

            write_addr_result = self.serial_client.write_registers(
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

            write_data_result = self.serial_client.write_registers(
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

    def _write_memory_ws(self, address: int, value: int, value_type: DisplayType) -> bool:
        """通过WebSocket写入内存"""
        try:
            if address is None:
                print(f"错误: address 参数为 None")
                return False
            
            if value is None:
                print(f"错误: value 参数为 None")
                return False
            
            if isinstance(value_type, str):
                value_type = DisplayType(value_type)
            
            raw_value = self._value_to_raw(value, value_type)

            print(f"\n{'='*60}")
            print(f"写入内存地址: 0x{address:08X}")
            print(f"写入值: {value} (原始: 0x{raw_value:08X})")
            print(f"值类型: {value_type.value}")
            print(f"{'='*60}")

            addr_high = (address >> 16) & 0xFFFF
            addr_low = address & 0xFFFF

            # 写入地址（写入2个寄存器：地址高16位和低16位）
            parsed_data, _ = self.ws_client.send_modbus_command_with_raw(1, 16, self.ADDR_WRITE_ADDR, 2,
                f"{addr_high:04X} {addr_low:04X}")
            if not parsed_data:
                print(f"写入地址失败")
                return False

            time.sleep(0.01)

            # 写入数据（写入2个寄存器：数据高16位和低16位）
            data_high = (raw_value >> 16) & 0xFFFF
            data_low = raw_value & 0xFFFF
            parsed_data, _ = self.ws_client.send_modbus_command_with_raw(1, 16, self.ADDR_READ_DATA, 2,
                f"{data_high:04X} {data_low:04X}")
            if not parsed_data:
                print(f"写入数据失败")
                return False

            print(f"\n写入成功!")
            return True

        except Exception as e:
            print(f"WebSocket写入错误: {e}")
            return False

    def _convert_value(self, raw_value: int, display_type: DisplayType) -> Union[int, float, str]:
        """将原始32位值转换为指定类型"""
        if display_type == DisplayType.HEX:
            return f"0x{raw_value:08X}"
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

    def batch_read_memory(self, addresses: List[int], display_types: List[DisplayType],
                           write_addrs: List[int], read_addrs: List[int],
                           return_raw: bool = False) -> Optional[List[Union[int, float, tuple]]]:
        """批量读取内存（支持连续读写，一次发送所有地址）"""
        if not self.connected:
            if not self.connect():
                return None

        results = []
        try:
            if self.comm_type == 'websocket' and self.ws_client:
                return self._batch_read_memory_ws(addresses, display_types, write_addrs, read_addrs, return_raw)
            elif self.comm_type == 'serial' and self.serial_client:
                return self._batch_read_memory_serial(addresses, display_types, write_addrs, read_addrs, return_raw)
            else:
                print(f"批量读取失败: 无效的通信类型 {self.comm_type}")
                return None
        except Exception as e:
            print(f"批量读取错误: {e}")
            return None

    def _batch_read_memory_serial(self, addresses: List[int], display_types: List[DisplayType],
                                 write_addrs: List[int], read_addrs: List[int],
                                 return_raw: bool) -> Optional[List[Union[int, float, tuple]]]:
        """通过串口批量读取内存（使用功能码10连续写入所有地址）"""
        print(f"\n{'='*60}")
        print(f"批量读取 {len(addresses)} 个变量")
        print(f"{'='*60}")

        try:
            # 准备所有要写入的地址数据（固定4组，每组2个寄存器，共8个寄存器）
            all_write_data = []
            for address in addresses:
                addr_high = (address >> 16) & 0xFFFF
                addr_low = address & 0xFFFF
                all_write_data.extend([addr_high, addr_low])

            # 使用功能码10一次性写入所有地址到第一个写地址（43507）
            first_write_addr = write_addrs[0]
            write_req = self._build_preset_multiple_registers(first_write_addr, all_write_data)
            self._print_packet("发送", write_req, f"预置寄存器 {first_write_addr} (设置所有内存地址)")

            write_result = self.serial_client.write_registers(first_write_addr, all_write_data)

            if isinstance(write_result, ExceptionResponse):
                print(f"写入地址失败: {write_result}")
                return None

            write_resp = bytes([0x01, 0x10, (first_write_addr >> 8) & 0xFF, first_write_addr & 0xFF,
                               (len(all_write_data) >> 8) & 0xFF, len(all_write_data) & 0xFF,
                               len(all_write_data) * 2])
            crc = self._calculate_crc(bytearray(write_resp))
            write_resp = write_resp + crc
            self._print_packet("接收", write_resp, "预置寄存器响应")

            time.sleep(0.01)

            # 一次性读取所有数据（从第一个读地址43515开始读取8个寄存器）
            first_read_addr = read_addrs[0]
            read_req = self._build_read_registers_request(first_read_addr, 8)
            self._print_packet("发送", read_req, f"读寄存器 {first_read_addr} (读取所有数据)")

            read_result = self.serial_client.read_holding_registers(address=first_read_addr, count=8)

            if isinstance(read_result, ExceptionResponse):
                print(f"读取数据失败: {read_result}")
                return None

            # 解析所有数据
            results = []
            for i, (address, display_type, write_addr, read_addr) in enumerate(zip(addresses, display_types, write_addrs, read_addrs)):
                if address == 0:
                    results.append(None)
                    continue

                if isinstance(display_type, str):
                    display_type = DisplayType(display_type)

                # 每组数据占用2个寄存器
                data_high = read_result.registers[i * 2]
                data_low = read_result.registers[i * 2 + 1]

                read_resp = bytes([0x01, 0x03, 0x04, (data_high >> 8) & 0xFF, data_high & 0xFF, (data_low >> 8) & 0xFF, data_low & 0xFF])
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

                print(f"结果: {result} (原始值: 0x{raw_value:08X})")

                if return_raw:
                    results.append((result, raw_value))
                else:
                    results.append(result)

            return results

        except ModbusException as e:
            print(f"Modbus通信错误: {e}")
            return None
        except Exception as e:
            print(f"未知错误: {e}")
            return None

    def _batch_read_memory_ws(self, addresses: List[int], display_types: List[DisplayType],
                              write_addrs: List[int], read_addrs: List[int],
                              return_raw: bool) -> Optional[List[Union[int, float, tuple]]]:
        """通过WebSocket批量读取内存（使用功能码10连续写入所有地址）"""
        print(f"\n{'='*60}")
        print(f"批量读取 {len(addresses)} 个变量")
        print(f"{'='*60}")

        results = []
        try:
            # 准备所有要写入的地址数据（固定4组，每组2个寄存器，共8个寄存器）
            all_write_data = []
            for address in addresses:
                addr_high = (address >> 16) & 0xFFFF
                addr_low = address & 0xFFFF
                all_write_data.extend([addr_high, addr_low])

            # 使用功能码10一次性写入所有地址到第一个写地址（43507）
            first_write_addr = write_addrs[0]
            hex_data = ' '.join([f"{val:04X}" for val in all_write_data])
            parsed_data, _ = self.ws_client.send_modbus_command_with_raw(1, 16, first_write_addr, len(all_write_data), hex_data)
            if not parsed_data:
                print(f"写入地址失败")
                return None

            time.sleep(0.01)

            # 一次性读取所有数据（从第一个读地址43515开始读取8个寄存器）
            first_read_addr = read_addrs[0]
            all_parsed_data, raw_response = self.ws_client.send_modbus_command_with_raw(1, 3, first_read_addr, 8)
            if not all_parsed_data or len(all_parsed_data) < 8:
                print(f"读取数据失败: all_parsed_data={all_parsed_data}")
                return None

            # 解析所有数据
            results = []
            for i, (address, display_type, write_addr, read_addr) in enumerate(zip(addresses, display_types, write_addrs, read_addrs)):
                if address == 0:
                    results.append(None)
                    continue

                if isinstance(display_type, str):
                    display_type = DisplayType(display_type)

                # 每组数据占用2个寄存器
                data_high = all_parsed_data[i * 2]
                data_low = all_parsed_data[i * 2 + 1]

                if display_type in [DisplayType.INT16, DisplayType.UINT16]:
                    raw_value = data_low
                elif display_type in [DisplayType.INT8, DisplayType.UINT8]:
                    raw_value = data_low & 0xFF
                else:
                    raw_value = (data_high << 16) | data_low

                result = self._convert_value(raw_value, display_type)

                print(f"结果: {result} (原始值: 0x{raw_value:08X})")

                if return_raw:
                    results.append((result, raw_value))
                else:
                    results.append(result)

            return results

        except Exception as e:
            print(f"WebSocket批量读取错误: {e}")
            return None


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
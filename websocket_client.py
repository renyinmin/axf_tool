#!/usr/bin/env python3
"""
WebSocket客户端 - 用于Modbus AXF工具
"""

import json
import threading
import time

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


class WebSocketClient:
    """WebSocket通信客户端"""

    SERVERS = {
        "测试服": "wss://test.maitian-yun.com/hub/v0/websocket/console",
        "欧服": "wss://www.foxesscloud.com/hub/v0/websocket/console"
    }
    X7_SERVERS = {
        "测试服": "wss://test.maitian-yun.com/fra/v0/websocket/console",
        "欧服": "wss://www.foxesscloud.com/fra/v0/websocket/console"
    }
    DEFAULT_TOKENS = {
        "测试服": "admeyJpZCI6ImU3ZGQ2MTFhLWQ5ZmEtNDcyNi1hOTJkLTc1ZjNlYWFkNTE0ZCIsInNlY3JldCI6ImY0OGE5ZmFlNjc1ZDY5NTU1YWI2MDhhNWE4N2FlZWNjZWVjZDM4YjRkMWQ3ZmVmZDA4ZWQ0ZDVjYWNlMzhjOGYiLCJwYXlsb2FkIjoiTHBJOXo1cjgrQlVFWElFZEYzaS9Dc3FKNlo0dGV6QndJUnlId0FBaUhQSE5mUVNFVnUwdElrcWFVT2NyWFJKNFhIVHExMXN1ZXZ3WkxsRU1LTW9ZNktSQjhydGNmUkV2QUx3TUYvblNlaFFnYmZDZmhVMk8yZndSaHpldlplNmxjWGVjVnlabmo3TGdCTHM4NEFOK0dqM0pOY2Y1U1ozYWFTaDF0RjhrQms5bDU2MDZRdXhDOVc4S0RtL3FrS2twRnhuS2ViSnZzTDE5VU1EWGpUNHR0UVNWVDBVZXdWUHZpekMzODl1aWRRTlpPcTRCUURaajhmUDBqSUVhMEdDMSJ9",
        "欧服": "admeyJpZCI6IjUxZjcyYjllLTM2NGItNDIxYS04M2IwLTQyZWFhZjU2YjQ2NiIsInNlY3JldCI6ImIyNGYyOWI2ZjJhYmRkMTYwNjQ3OGVkNjBmZTVlZTJhMDZkNDFhNzI2Njg0NTNlZmFjYmY0M2NlZWZjYjAzYTAiLCJwYXlsb2FkIjoiM0lvL2k5R0daeW41b1RHSEk4MGluUDQ2UHFqbGpIcGpUM2tXNVFwNXBTNFUwOEs3cXd5a1J1V2FWcEZ3L1BFcXJacUcvV0ZtZnY5SUJDVkw0dEg5WmhwbE04SmxkZlJQeVdQR0xrR1hVNmZPY3ZSdld3b3V4WFFRUTVpdE1OeHZSWDBhMmNvbG1STkpGUzNVSG5OZStuZGxvQWZ1eDZWTzJ2blNzQVJOWUFkajNjRmExaEtaSUlNQkZzZ25JQVNZc2N5cXl3NmRVb2VQZ0JpVnlLR1l2NzBlblRBUW9icDhUWlFKMk83eW1sK2RLM3ZFREJ0VVFGQ005N1p1cm9WNCJ9"
    }
    DEFAULT_SN = "60HPB02054CA999"
    DEFAULT_RESOURCE = "/hub/v0/websocket/console"
    X7_RESOURCE = "/fra/v0/websocket/console"
    DEFAULT_TIMEZONE = "Asia/Hong_Kong"
    
    RECONNECT_DELAY = 3
    MAX_RECONNECT_ATTEMPTS = 5
    
    def __init__(self, packet_callback=None):
        if not WEBSOCKET_AVAILABLE:
            raise ImportError("websocket-client库未安装，请运行: pip install websocket-client")

        self.ws = None
        self.ws_thread = None
        self.running = False
        self.connected = False
        self.listening = False

        self.server_type = "测试服"
        self.ws_url = self.SERVERS[self.server_type]
        self.token = self.DEFAULT_TOKENS[self.server_type]
        self.sn = self.DEFAULT_SN
        self.device_type = "H3PLUS"  # H3PLUS 或 X7

        self._reconnect_count = 0
        self._auto_reconnect = True
        self._response_buffer = []
        self._response_lock = threading.Lock()
        self._response_event = threading.Event()
        self._pending_command = None
        self._device_offline = False
        self.packet_callback = packet_callback

    def set_connection_params(self, ws_url=None, token=None, sn=None, server_type=None, device_type=None):
        """设置连接参数"""
        if ws_url:
            self.ws_url = ws_url
        if server_type:
            self.server_type = server_type
            self.token = self.DEFAULT_TOKENS.get(server_type, self.DEFAULT_TOKENS["测试服"])
            if self.device_type == "X7":
                self.ws_url = self.X7_SERVERS.get(server_type, self.X7_SERVERS["测试服"])
            else:
                self.ws_url = self.SERVERS.get(server_type, self.SERVERS["测试服"])
        elif token:
            self.token = token
        if sn:
            self.sn = sn
        if device_type:
            self.device_type = device_type
            if device_type == "X7":
                self.ws_url = self.X7_SERVERS.get(self.server_type, self.X7_SERVERS["测试服"])
            else:
                self.ws_url = self.SERVERS.get(self.server_type, self.SERVERS["测试服"])
            
    def connect(self, ws_url=None, token=None, sn=None):
        """建立WebSocket连接"""
        self.set_connection_params(ws_url, token, sn)
        
        try:
            self.running = True
            
            websocket.enableTrace(False)
            
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            self.ws_thread = threading.Thread(target=self._run_websocket)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            wait_count = 0
            while not self.connected and wait_count < 50:
                time.sleep(0.1)
                wait_count += 1
            
            if self.connected:
                print(f'WebSocket已连接: {self.ws_url}')
                return True
            else:
                print('WebSocket连接超时')
                return False
                
        except Exception as e:
            print(f'WebSocket连接失败: {str(e)}')
            return False
    
    def disconnect(self):
        """断开WebSocket连接"""
        self.running = False
        self._auto_reconnect = False
        self.connected = False
        self.listening = False
        
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None
        
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=2)
        
        print('WebSocket已断开')
    
    def _run_websocket(self):
        """运行WebSocket连接"""
        while self.running:
            try:
                self.ws.run_forever()
            except Exception as e:
                print(f"[WebSocket] 运行错误: {e}")
            
            if self.running and self._auto_reconnect:
                self._reconnect_count += 1
                if self._reconnect_count <= self.MAX_RECONNECT_ATTEMPTS:
                    print(f'WebSocket断开，{self.RECONNECT_DELAY}秒后尝试重连 ({self._reconnect_count}/{self.MAX_RECONNECT_ATTEMPTS})')
                    time.sleep(self.RECONNECT_DELAY)
                    if self.running:
                        continue
            break
        
        self.connected = False
        self.listening = False
    
    def _on_open(self, ws):
        """WebSocket连接打开回调"""
        print("[WebSocket] 连接已建立")
        self.connected = True
        self._device_offline = False
        self._reconnect_count = 0
    
    def _on_message(self, ws, message):
        """WebSocket消息接收回调"""
        try:
            data = json.loads(message)
            print(f"[WebSocket] 收到消息: {data}")
            
            if 'errno' in data:
                if data['errno'] == 0 and 'result' in data:
                    result = data['result']
                    operation = result.get('operation', '')
                    
                    if operation == 'recv':
                        content = result.get('content', '')
                        if content:
                            self._handle_data_response(content)
                    elif operation == 'send':
                        pass
                    elif operation == 'info':
                        content = result.get('content', '')
                        if content == 'offline':
                            print('[WebSocket] 设备离线')
                            self._device_offline = True
                            self._response_event.set()
                        elif content:
                            self._handle_data_response(content)
                    else:
                        content = result.get('content', '')
                        if content:
                            self._handle_data_response(content)
                elif data['errno'] != 0:
                    error_msg = data.get('msg', '')
                    if not error_msg and 'result' in data:
                        result = data['result']
                        if isinstance(result, dict):
                            error_msg = result.get('content', '未知错误')
                    if not error_msg:
                        error_msg = '未知错误'
                    print(f'服务端错误: {error_msg}')
            elif 'cmd' in data:
                pass
                
        except json.JSONDecodeError as e:
            print(f"[WebSocket] JSON解析错误: {e}")
        except Exception as e:
            print(f"[WebSocket] 消息处理错误: {e}")
    
    def _on_error(self, ws, error):
        """WebSocket错误回调"""
        error_str = str(error)
        print(f"[WebSocket] 错误: {error_str}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket关闭回调"""
        print(f"[WebSocket] 连接关闭: {close_status_code} - {close_msg}")
        self.connected = False
        self.listening = False
    
    def _handle_data_response(self, content):
        """处理数据响应（自动解包）"""
        try:
            hex_str = content.replace(' ', '').strip()
            if not hex_str:
                return

            try:
                frame_bytes = bytes.fromhex(hex_str)
            except ValueError:
                return

            modbus_data = self._parse_frame(frame_bytes)
            if modbus_data is None:
                return

            # 回调接收报文
            if self.packet_callback:
                hex_with_spaces = ' '.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)])
                self.packet_callback("RX", hex_with_spaces, len(frame_bytes), "WebSocket帧")

            with self._response_lock:
                self._response_buffer.append(modbus_data)

            self._response_event.set()
                    
        except Exception as e:
            print(f"[WebSocket] 处理响应错误: {e}")
    
    def _send_json_message(self, cmd, content=""):
        """发送JSON消息"""
        if not self.connected or not self.ws:
            print('WebSocket未连接')
            return False

        message = {
            "cmd": cmd,
            "resource": self.X7_RESOURCE if self.device_type == "X7" else self.DEFAULT_RESOURCE,
            "token": self.token,
            "timezone": self.DEFAULT_TIMEZONE,
            "sequence": "",
            "parameters": {
                "sn": self.sn,
                "encode": "hex",
                "content": content,
                "interval": 0,
                "repeat": False
            }
        }

        try:
            json_str = json.dumps(message)
            self.ws.send(json_str)
            print(f"[WebSocket] 发送HTTP请求: {json_str}")
            return True
        except Exception as e:
            print(f'发送消息失败: {str(e)}')
            return False
    
    def start_listening(self):
        """开始监听设备"""
        if not self.connected:
            print('WebSocket未连接，无法开始监听')
            return False
        
        if self.listening:
            return True
        
        success = self._send_json_message("listen")
        if success:
            self.listening = True
            print(f'开始监听设备: {self.sn}')
            return True
        return False
    
    def stop_listening(self):
        """停止监听设备"""
        self.listening = False
        print('停止监听设备')
    
    def send_data(self, hex_data):
        """发送十六进制数据（自动组包）"""
        if not self.connected:
            print('WebSocket未连接')
            return False
        
        if not self.listening:
            if not self.start_listening():
                return False
            time.sleep(0.5)
        
        hex_str = hex_data.replace(' ', '').strip()
        modbus_data = bytes.fromhex(hex_str)
        
        # 去掉Modbus数据的CRC（最后2字节），只保留地址、功能码、数据
        modbus_data_without_crc = modbus_data[:-2]

        frame = self._build_frame(modbus_data_without_crc)
        frame_hex = frame.hex().upper()
        hex_with_spaces = ' '.join([frame_hex[i:i+2] for i in range(0, len(frame_hex), 2)])

        success = self._send_json_message("send", hex_with_spaces)
        if success:
            # 回调发送报文
            if self.packet_callback:
                self.packet_callback("TX", hex_with_spaces, len(frame), "WebSocket帧")

            return True
        return False
    
    def send_modbus_command(self, slave_id, function_code, start_address, count, data_bytes=None):
        """发送Modbus命令"""
        parsed_data, _ = self.send_modbus_command_with_raw(slave_id, function_code, start_address, count, data_bytes)
        return parsed_data
    
    def send_modbus_command_with_raw(self, slave_id, function_code, start_address, count, data_bytes=None):
        """发送Modbus命令并返回解析结果和原始响应"""
        if not self.connected:
            print('WebSocket未连接')
            return [], None
        
        if not self.listening:
            if not self.start_listening():
                return [], None
            time.sleep(0.3)
        
        command = bytearray()
        command.append(slave_id)
        command.append(function_code)
        
        if function_code == 3:
            command.append(start_address >> 8)
            command.append(start_address & 0xFF)
            command.append(count >> 8)
            command.append(count & 0xFF)
        elif function_code == 6:
            value = count
            if data_bytes:
                try:
                    byte_values = [int(b, 16) for b in data_bytes.split()]
                    if len(byte_values) >= 2:
                        value = (byte_values[0] << 8) | byte_values[1]
                except ValueError:
                    pass
            command.append(start_address >> 8)
            command.append(start_address & 0xFF)
            command.append(value >> 8)
            command.append(value & 0xFF)
        elif function_code == 16:
            command.append(start_address >> 8)
            command.append(start_address & 0xFF)
            command.append(count >> 8)
            command.append(count & 0xFF)
            byte_count = count * 2
            command.append(byte_count)
            
            if data_bytes:
                try:
                    byte_values = [int(b, 16) for b in data_bytes.split()]
                    for i in range(min(len(byte_values), count)):
                        val = byte_values[i]
                        command.append((val >> 8) & 0xFF)
                        command.append(val & 0xFF)
                    while len(command) < 7 + byte_count:
                        command.append(0x00)
                except ValueError:
                    for _ in range(count * 2):
                        command.append(0x00)
            else:
                for _ in range(count * 2):
                    command.append(0x00)
        else:
            print(f'不支持的功能码: {function_code}')
            return [], None
        
        crc = self._calculate_crc(command)
        command.append(crc & 0xFF)
        command.append(crc >> 8)
        
        command_hex = command.hex()
        command_with_spaces = ' '.join([command_hex[i:i+2] for i in range(0, len(command_hex), 2)])
        
        with self._response_lock:
            self._response_buffer.clear()
        self._response_event.clear()
        
        self._pending_command = {
            'slave_id': slave_id,
            'function_code': function_code,
            'start_address': start_address,
            'count': count
        }
        
        if not self.send_data(command_hex):
            self._pending_command = None
            return [], None

        if self._response_event.wait(timeout=5.0):
            with self._response_lock:
                if self._response_buffer:
                    response = self._response_buffer.pop(0)
                else:
                    response = None
        else:
            response = None
            if self._device_offline:
                print('[WebSocket] 设备离线，无法读取数据')
            else:
                print('等待响应超时')

        self._pending_command = None
        
        if response:
            print(f"[WebSocket] 返回响应数据: 长度={len(response)}, 前10字节={response[:10].hex()}")

            parsed_data = self._parse_modbus_response(response)

            if parsed_data is not None:
                return parsed_data, response
            else:
                print(f"[WebSocket] Modbus解析失败，返回原始响应")
                return None, response

        print("[WebSocket] 无响应数据返回")
        return None, None
    
    def _calculate_crc(self, data):
        """计算Modbus RTU CRC校验"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc
    
    def _build_frame(self, modbus_data):
        """
        构建WebSocket数据帧
        帧格式：
        - 帧头：2字节，固定为 0x7F 0x7F
        - 功能码：1字节，H3PLUS为0x11，X7为0x12
        - 请求序列：4字节
        - 数据长度：2字节，modbus数据长度
        - X7额外字节：00 01
        - 指令数据：modbus数据
        - 校验：2字节，从功能码到指令数据的CRC16
        - 帧尾：2字节，固定为 0xF7 0xF7
        """
        frame = bytearray()

        frame.append(0x7F)
        frame.append(0x7F)

        if len(modbus_data) >= 2:
            modbus_function_code = modbus_data[1]
            if modbus_function_code in [0x06, 0x10, 0x16]:
                frame.append(0x12)
            else:
                frame.append(0x11)
        else:
            frame.append(0x11)

        if self.device_type == "X7":
            frame.append(0xF9)
            frame.append(0x03)
            frame.append(0x96)
            frame.append(0xD1)

            data_len = len(modbus_data) + 2  # X7需要加2字节的00 01
            frame.append((data_len >> 8) & 0xFF)
            frame.append(data_len & 0xFF)

            frame.append(0x00)
            frame.append(0x01)
        else:
            frame.append(0x4D)
            frame.append(0x64)
            frame.append(0x57)
            frame.append(0x10)

            data_len = len(modbus_data)
            frame.append((data_len >> 8) & 0xFF)
            frame.append(data_len & 0xFF)

        frame.extend(modbus_data)

        crc_data = frame[2:]
        crc = self._calculate_crc(crc_data)
        frame.append(crc & 0xFF)
        frame.append((crc >> 8) & 0xFF)

        frame.append(0xF7)
        frame.append(0xF7)

        return bytes(frame)
    
    def _parse_frame(self, frame_data):
        """
        解析WebSocket响应帧
        响应帧格式：
        - 帧头：2字节 0x7F 0x7F
        - 功能码：1字节 0x91(H3PLUS) 或 0x92(X7)
        - 应答序列：4字节（与请求序列相同）
        - 数据长度：2字节
        - 指令数据：N字节
        - CRC：2字节
        - 帧尾：2字节 0xF7 0xF7

        返回：解包后的modbus数据，解析失败返回None
        """
        try:
            if len(frame_data) < 13:
                print(f"[WebSocket] 响应帧长度不足: {len(frame_data)}")
                return None
            
            if frame_data[0] != 0x7F or frame_data[1] != 0x7F:
                print(f"[WebSocket] 响应帧头错误: {frame_data[0]:02X} {frame_data[1]:02X}")
                return None
            
            if frame_data[-2] != 0xF7 or frame_data[-1] != 0xF7:
                print(f"[WebSocket] 响应帧尾错误: {frame_data[-2]:02X} {frame_data[-1]:02X}")
                return None
            
            # 功能码可以是 0x91 或 0x92
            if frame_data[2] not in [0x91, 0x92]:
                # print(f"[WebSocket] 响应帧功能码错误: {frame_data[2]:02X} (应为0x91或0x92)")
                return None
            
            # 数据长度：大端序（高字节在前）
            data_len = (frame_data[7] << 8) | frame_data[8]

            # 查找帧尾 F7 F7 来确定 Modbus 数据边界
            if frame_data[-2] == 0xF7 and frame_data[-1] == 0xF7:
                modbus_data = frame_data[9:-2]
                return modbus_data
            else:
                print(f"[WebSocket] 未找到帧尾 F7 F7")
                return None
            
        except Exception as e:
            print(f"[WebSocket] 解析帧异常: {e}")
            return None
    
    def _parse_modbus_response(self, response):
        """解析Modbus响应数据"""
        if len(response) < 5:
            print(f"[WebSocket] 响应长度不足: {len(response)}")
            return None

        try:
            slave_id = response[0]
            function_code = response[1]

            if function_code & 0x80:
                print(f"[WebSocket] Modbus错误响应: 功能码={function_code & 0x7F}, 错误码={response[2]}")
                return None

            # 根据功能码选择解析方式
            if function_code in [3, 4]:  # 读取保持/输入寄存器
                byte_count = response[2]
                if len(response) < 3 + byte_count:
                    print(f"[WebSocket] 响应数据长度不匹配: 期望{3+byte_count}, 实际{len(response)}")
                    return None
                data = response[3:3+byte_count]
                if not data:
                    print(f"[WebSocket] 响应数据为空")
                    return None
                register_count = byte_count // 2
                result = []
                for i in range(register_count):
                    if i * 2 < len(data):
                        value = (data[i * 2] << 8) | data[i * 2 + 1]
                        result.append(value)
                print(f"[WebSocket] 解析功能码{function_code}: 寄存器数量={register_count}, 值={result}")
                return result

            elif function_code == 6:  # 写单个寄存器
                print(f"[WebSocket] 解析功能码6: 写单个寄存器响应")
                return []

            elif function_code == 16:  # 写多个寄存器
                # 响应格式: slave_id(1) + function_code(1) + start_address(2) + quantity(2) + CRC(2)
                if len(response) < 8:
                    print(f"[WebSocket] 响应长度不足: 期望8, 实际{len(response)}")
                    return None
                start_address = (response[2] << 8) | response[3]
                quantity = (response[4] << 8) | response[5]
                print(f"[WebSocket] 解析功能码16: 起始地址={start_address}, 数量={quantity}")
                # 返回成功标记，用于判断写入是否成功
                return [True]

            else:
                # 默认返回字节数组
                print(f"[WebSocket] 解析功能码{function_code}: 返回字节数组")
                return list(response)

        except Exception as e:
            print(f"[WebSocket] Modbus解析异常: {e}")
            return None

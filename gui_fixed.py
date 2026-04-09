#!/usr/bin/env python3
"""
修复版GUI - 简化但稳定的Modbus AXF工具界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import json
import threading
import queue
import sys
import traceback

# 添加项目目录到路径
sys.path.insert(0, os.path.dirname(__file__))

MODULES_LOADED = True
AXFParser = None
ModbusMemoryClient = None
DisplayType = None

def _import_modules():
    global AXFParser, ModbusMemoryClient, DisplayType, MODULES_LOADED
    try:
        from axf_parser import AXFParser as _AXFParser
        from modbus_client import ModbusMemoryClient as _ModbusMemoryClient, DisplayType as _DisplayType
        AXFParser = _AXFParser
        ModbusMemoryClient = _ModbusMemoryClient
        DisplayType = _DisplayType
        print(f"[DEBUG] 模块导入成功: axf_parser, modbus_client")
        return True
    except ImportError as e:
        print(f"[DEBUG] 模块导入失败: {e}")
        print("=" * 50)
        print("错误: 缺少必要的依赖库!")
        print("请执行以下命令安装依赖:")
        print("  pip install -r requirements.txt")
        print("=" * 50)
        MODULES_LOADED = False
        return False

# 不在导入时检查，延迟到 main() 函数中
# _import_modules()
# if not MODULES_LOADED:
#     sys.exit(1)

print(f"[DEBUG] 模块名称: {__name__}")

class FixedModbusGUI:
    """修复版GUI，更简单稳定"""

    CONFIG_FILE = "config_fixed.json"

    def __init__(self, root):
        self.root = root
        self.root.title("Modbus AXF工具 - 修复版")
        self.root.geometry("800x700")

        # 设置最小大小
        self.root.minsize(600, 400)

        # 配置
        self.config = self._load_config()

        # 状态变量
        self.axf_parser = None
        self.modbus_client = None
        self._packets = []

        # 消息队列（简化）
        self.message_queue = queue.Queue()

        print("修复版GUI初始化...")

        # 创建UI（简化）
        self._create_simple_widgets()

        # 启动队列处理器
        self._start_queue_processor()

        print("修复版GUI就绪")

    def _load_config(self):
        """加载配置"""
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(__file__)
        config_path = os.path.join(exe_dir, self.CONFIG_FILE)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass

        return {
            "recent_axf_files": [],
            "port": "COM3",
            "baudrate": 9600,
            "timeout": 1.0,
            "variable_history": [],
            "comm_type": "serial",
            "server": "测试服",
            "ws_url": "wss://test.maitian-yun.com/hub/v0/websocket/console",
            "ws_token": "admeyJpZCI6Ijk5ZDIzZWM1LWJiNjUtNDEyNi05NzZlLWI0NzVjN2JlZDE5OCIsInNlY3JldCI6IjllNTI5ZmU0OGRlNWViNzgyODAzNGEyNGRhYmU5M2E1NTU4YzU2YTlmZjRjOGUxNzAzYThiYzM3MDE5ODMxNmYiLCJwYXlsb2FkIjoiYVJxS1RFU1FJV29iZFFmRFlMZjk0ZWRXLzhoako1TjE5dHFiMHhjMUV3YzR0dmljNzBRajhTTVB4SFAwZlpFY1VIamQ4VlRxVkhHYmFXSEtNY3lMVmY1bnF3VFViMS96eUZ1QnZ1NmsyYk9yei9iaWU1YTU1am9qcVgwbnRSL2pGK1hsRndLSWNQSlJ5OTErS2tQZ2E2amxvT3ZmNU13bjIxazRudDc5N3k2WnlPY3ZONHYrZzducnM3Mmg0WmlBeEIxTjJUcE5pUmdXYVViNTRZdXpINU9DQUlpQXNiL0w5TFoxVWFXQXRacXpmSmZtMW5OOVYwVlJnOGxqdmF0aSJ9",
            "ws_sn": "60HPB02054CA999"
        }

    def _save_config(self):
        """保存配置"""
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(__file__)
        config_path = os.path.join(exe_dir, self.CONFIG_FILE)
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def _create_simple_widgets(self):
        """创建简化UI"""
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 通信设置区域（最上面）
        conn_frame = ttk.LabelFrame(main_frame, text="通信设置", padding=10)
        conn_frame.pack(fill=tk.X, pady=(0, 10))

        # 通信方式选择
        ttk.Label(conn_frame, text="通信方式:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.comm_type_var = tk.StringVar(value=self.config.get("comm_type", "serial"))
        comm_combo = ttk.Combobox(conn_frame, textvariable=self.comm_type_var, width=12)
        comm_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        comm_combo['values'] = ['serial', 'websocket']
        comm_combo.bind('<<ComboboxSelected>>', self._on_comm_type_changed)

        # 串口设置
        self.serial_frame = ttk.Frame(conn_frame)
        self.serial_frame.grid(row=1, column=0, columnspan=6, sticky=tk.W+tk.E, pady=5)

        ttk.Label(self.serial_frame, text="串口:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.port_var = tk.StringVar(value=self.config.get("port", "COM3"))
        port_combo = ttk.Combobox(self.serial_frame, textvariable=self.port_var, width=12)
        port_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        try:
            import serial.tools.list_ports
            ports = [port.device for port in serial.tools.list_ports.comports()]
            if not ports:
                ports = ["COM1", "COM2", "COM3", "COM4", "COM5", "COM6"]
        except:
            ports = ["COM1", "COM2", "COM3", "COM4", "COM5", "COM6"]
        port_combo['values'] = ports

        ttk.Label(self.serial_frame, text="波特率:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(15,0))
        self.baudrate_var = tk.StringVar(value=str(self.config.get("baudrate", 9600)))
        baud_combo = ttk.Combobox(self.serial_frame, textvariable=self.baudrate_var, width=10)
        baud_combo.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        baud_combo['values'] = ['9600', '19200', '38400', '57600', '115200', '230400']

        # WebSocket设置
        self.ws_frame = ttk.Frame(conn_frame)

        # 第一行：服务器选择和SN
        ttk.Label(self.ws_frame, text="服务器:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.server_var = tk.StringVar(value=self.config.get("server", "测试服"))
        server_combo = ttk.Combobox(self.ws_frame, textvariable=self.server_var, width=12)
        server_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        server_combo['values'] = ['测试服', '欧服']
        server_combo.bind('<<ComboboxSelected>>', self._on_server_changed)

        ttk.Label(self.ws_frame, text="SN:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(20,0))
        ws_sn_from_config = self.config.get("ws_sn", "")
        self.ws_sn_var = tk.StringVar(value=ws_sn_from_config if ws_sn_from_config else "60HPB02054CA999")
        ws_sn_entry = ttk.Entry(self.ws_frame, textvariable=self.ws_sn_var, width=20)
        ws_sn_entry.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        ttk.Label(self.ws_frame, text="设备类型:").grid(row=0, column=4, sticky=tk.W, pady=5, padx=(20,0))
        self.device_type_var = tk.StringVar(value=self.config.get("device_type", "H3PLUS"))
        device_type_combo = ttk.Combobox(self.ws_frame, textvariable=self.device_type_var, width=10)
        device_type_combo.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        device_type_combo['values'] = ['H3PLUS', 'X7']
        device_type_combo.bind('<<ComboboxSelected>>', self._on_device_type_changed)

        # 连接按钮
        self.connect_btn = ttk.Button(conn_frame, text="连接", command=self._toggle_connection)
        self.connect_btn.grid(row=2, column=4, padx=15, pady=5)

        self.conn_status = ttk.Label(conn_frame, text="未连接", foreground="red")
        self.conn_status.grid(row=2, column=5, padx=5, pady=5)

        # 根据通信方式显示/隐藏设置
        self._on_comm_type_changed(None)

        # 2. 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="AXF文件", padding=10)
        file_frame.pack(fill=tk.NONE, anchor=tk.W, pady=(0, 10))

        ttk.Label(file_frame, text="文件路径:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.axf_file_var = tk.StringVar()
        axf_entry = ttk.Entry(file_frame, textvariable=self.axf_file_var, width=50)
        axf_entry.grid(row=0, column=1, padx=(5, 2), pady=5, sticky=tk.W)

        browse_btn = tk.Button(file_frame, text="浏览...", command=self._browse_file,
                               bg="#607D8B", fg="white", padx=20, pady=5)
        browse_btn.grid(row=0, column=2, padx=(0, 5), pady=5)

        # 3. 批量读取区域（4组数据，每行一组）
        batch_frame = ttk.LabelFrame(main_frame, text="批量读取（4组数据）", padding=10)
        batch_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 4组数据，每行一组
        self.batch_vars = [tk.StringVar() for _ in range(4)]
        self.batch_types = [tk.StringVar(value="hex") for _ in range(4)]
        self.batch_addresses = [tk.StringVar() for _ in range(4)]
        self.batch_values = [tk.StringVar() for _ in range(4)]
        self.batch_raw_values = [None for _ in range(4)]  # 保存原始数据用于类型转换
        self.batch_var_combos = []

        # 表头
        ttk.Label(batch_frame, text="变量").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(batch_frame, text="地址").grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(batch_frame, text="值").grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(batch_frame, text="类型").grid(row=0, column=3, padx=5, pady=5)

        # 为每组创建控件（每行一组）
        for i in range(4):
            # 变量输入（Combobox，支持输入和选择历史）
            var_combo = ttk.Combobox(batch_frame, textvariable=self.batch_vars[i], width=30, state="normal")
            var_combo.grid(row=i+1, column=0, padx=2, pady=2)
            var_combo['values'] = self.config.get("variable_history", [])
            var_combo.bind('<<ComboboxSelected>>', lambda e, idx=i: self._on_batch_var_selected(e, idx))
            self.batch_var_combos.append(var_combo)
            
            # 地址显示
            addr_entry = ttk.Entry(batch_frame, textvariable=self.batch_addresses[i], width=15, state="readonly")
            addr_entry.grid(row=i+1, column=1, padx=2, pady=2)
            
            # 值显示
            val_entry = ttk.Entry(batch_frame, textvariable=self.batch_values[i], width=15, state="readonly")
            val_entry.grid(row=i+1, column=2, padx=2, pady=2)
            
            # 类型选择
            type_combo = ttk.Combobox(batch_frame, textvariable=self.batch_types[i], width=10)
            type_combo.grid(row=i+1, column=3, padx=2, pady=2)
            type_combo['values'] = ["hex", "float", "int32", "uint32", "int16", "uint16", "int8", "uint8"]
            type_combo.bind('<<ComboboxSelected>>', lambda e, idx=i: self._on_type_selected(e, idx))

        # 批量操作按钮
        batch_btn_frame = ttk.Frame(batch_frame)
        batch_btn_frame.grid(row=5, column=0, columnspan=4, pady=10)
        
        batch_read_btn = tk.Button(batch_btn_frame, text="批量读取",
                                  bg="#9C27B0", fg="white", padx=15, pady=5)
        batch_read_btn.pack(side=tk.LEFT, padx=5)
        batch_read_btn.bind('<ButtonRelease-1>', lambda e: self._batch_read())

        batch_clear_btn = tk.Button(batch_btn_frame, text="清空",
                                  bg="#FF9800", fg="white", padx=15, pady=5)
        batch_clear_btn.pack(side=tk.LEFT, padx=5)
        batch_clear_btn.bind('<ButtonRelease-1>', lambda e: self._batch_clear())

        # 4. 结果显示区域
        result_frame = ttk.LabelFrame(main_frame, text="结果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.result_text = scrolledtext.ScrolledText(result_frame, height=20)
        self.result_text.pack(fill=tk.BOTH, expand=True)

        self.result_text.insert(tk.END, "结果将显示在这里...\n")
        self.result_text.insert(tk.END, "="*50 + "\n")

        # 5. 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var,
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        file_frame.columnconfigure(1, weight=1)

        print("简化UI创建完成")

    def _start_queue_processor(self):
        """启动队列处理器"""
        def process_queue():
            try:
                while not self.message_queue.empty():
                    msg = self.message_queue.get_nowait()
                    if isinstance(msg, tuple):
                        func, args = msg
                        func(*args)
            except queue.Empty:
                pass
            except Exception as e:
                print(f"队列处理错误: {e}")

            # 每100ms检查一次
            self.root.after(100, process_queue)

        self.root.after(100, process_queue)

    def _queue_update(self, func, *args):
        """将更新请求放入队列"""
        self.message_queue.put((func, args))

    def _log_result(self, message):
        """将日志信息同时输出到控制台和结果框"""
        print(message)
        self.result_text.insert(tk.END, message + "\n")
        self.result_text.see(tk.END)

    def _browse_file(self):
        """浏览文件并自动加载"""
        filename = filedialog.askopenfilename(
            title="选择AXF文件",
            filetypes=[("AXF files", "*.axf"), ("ELF files", "*.elf"), ("All files", "*.*")]
        )
        if filename:
            self.axf_file_var.set(filename)
            # 自动加载文件
            self._load_axf()

    def _load_axf(self):
        """加载AXF文件"""
        print("[DEBUG] _load_axf 被调用")
        filename = self.axf_file_var.get().strip()
        print(f"[DEBUG] filename = '{filename}'")
        if not filename:
            self.result_text.insert(tk.END, "警告: 请选择AXF文件\n")
            self.result_text.see(tk.END)
            return

        if not os.path.exists(filename):
            self.result_text.insert(tk.END, f"错误: 文件不存在: {filename}\n")
            self.result_text.see(tk.END)
            return

        self._update_status(f"正在加载: {os.path.basename(filename)}")

        def load_thread():
            try:
                print(f"[DEBUG] load_thread中AXFParser模块: {AXFParser.__module__}")
                print(f"[DEBUG] AXFParser类: {AXFParser}")
                print(f"[DEBUG] 加载文件: {filename}")
                parser = AXFParser(filename)
                print(f"[DEBUG] parser类型: {type(parser)}")
                vars_count = len(parser.list_global_variables())
                print(f"[DEBUG] 找到变量数: {vars_count}")

                # 更新GUI
                self._queue_update(self._axf_loaded, parser, filename, vars_count)
                self._queue_update(self._update_status, f"加载成功: {vars_count}个变量")

                # 更新最近文件
                recent = self.config.get("recent_axf_files", [])
                if filename in recent:
                    recent.remove(filename)
                recent.insert(0, filename)
                self.config["recent_axf_files"] = recent[:5]
                self._save_config()

            except Exception as e:
                self._queue_update(self._update_status, f"加载失败: {e}")
                self._queue_update(lambda: messagebox.showerror("错误", f"加载失败: {e}"))

        threading.Thread(target=load_thread, daemon=True).start()

    def _axf_loaded(self, parser, filename, vars_count):
        """AXF文件加载完成"""
        self.axf_parser = parser
        self.result_text.insert(tk.END, f"已加载: {os.path.basename(filename)}\n")
        self.result_text.insert(tk.END, f"找到 {vars_count} 个全局变量\n")
        self.result_text.insert(tk.END, "="*50 + "\n")
        self.result_text.see(tk.END)

        self.result_text.insert(tk.END, "="*50 + "\n")

    def _on_packet(self, direction, hex_str, length, description):
        """报文回调"""
        self._packets.append((direction, hex_str, length, description))

        # 接收报文必须以 7F 7F 91 或 7F 7F 92 开头
        if direction == "RX":
            valid_headers = ["7F 7F 91", "7F 7F 92"]
            if not any(hex_str.startswith(header) for header in valid_headers):
                return

        # 在结果框中显示原始报文
        direction_text = "发送" if direction == "TX" else "接收"
        packet_info = f"[{direction_text}] {description}\n  报文: {hex_str}"
        self._log_result(packet_info)

    def _on_batch_var_selected(self, event, idx):
        """批量变量下拉框选择事件"""
        selected = self.batch_var_combos[idx].get()
        
        if selected and self.axf_parser:
            # 解析地址
            address = self.axf_parser.get_variable_address(selected)
            if address is not None:
                self.batch_addresses[idx].set(f"0x{address:08X}")
            else:
                self.batch_addresses[idx].set("0x00000000")

    def _batch_read(self):
        """批量读取"""
        if not self.axf_parser:
            messagebox.showwarning("警告", "请先加载AXF文件")
            return

        if not self.modbus_client or not hasattr(self.modbus_client, 'connected'):
            messagebox.showwarning("警告", "请先连接Modbus设备")
            return

        self._packets = []

        # 每组的写地址和读地址
        group_addresses = [
            {"write": 43507, "read": 43515},  # 第1组
            {"write": 43509, "read": 43517},  # 第2组
            {"write": 43511, "read": 43519},  # 第3组
            {"write": 43513, "read": 43521}   # 第4组
        ]

        def batch_read_thread():
            self._queue_update(self._log_result, "开始批量读取...")
            self._queue_update(self._log_result, "="*50)
            
            # 先获取所有地址
            addresses = []
            for i in range(4):
                var_path = self.batch_vars[i].get().strip()
                if not var_path:
                    # 未选择变量，地址设为0
                    addresses.append(0)
                    self._queue_update(self.batch_addresses[i].set, "0x00000000")
                else:
                    address = self.axf_parser.get_variable_address(var_path)
                    if address is not None:
                        addresses.append(address)
                        self._queue_update(self.batch_addresses[i].set, f"0x{address:08X}")
                        # 添加到历史记录
                        self._queue_update(self._add_to_history, var_path)
                    else:
                        # 未找到变量，地址设为0
                        addresses.append(0)
                        self._queue_update(self.batch_addresses[i].set, "0x00000000")

            # 准备批量读取参数（始终传递4组地址，未选择的变量地址为0）
            all_addresses = addresses
            all_types = []
            all_write_addrs = []
            all_read_addrs = []

            for i in range(4):
                all_types.append(self.batch_types[i].get())
                all_write_addrs.append(group_addresses[i]["write"])
                all_read_addrs.append(group_addresses[i]["read"])

            # 批量读取
            self._queue_update(self._log_result, "开始批量读取...")
            self._queue_update(self._log_result, "="*50)

            try:
                results = self.modbus_client.batch_read_memory(
                    all_addresses, all_types, all_write_addrs, all_read_addrs, return_raw=True
                )

                if results is None:
                    self._queue_update(self._log_result, "批量读取失败")
                    return

                # 更新结果
                for i, result in enumerate(results):
                    var_path = self.batch_vars[i].get().strip()
                    if not var_path:
                        continue

                    if result is not None:
                        value, raw_value = result
                        self._queue_update(self._update_batch_value_with_raw, i, value, raw_value)
                        self._queue_update(self._update_status, f"组{i+1}读取成功: {value}")
                        self._queue_update(self._log_result, f"  结果: {value} (原始值: 0x{raw_value:08X})")
                    else:
                        offline_suffix = "（offline）" if self.modbus_client.ws_client._device_offline else ""
                        self._queue_update(self._update_batch_value, i, "读取失败")
                        self._queue_update(self._log_result, f"  结果: 读取失败{offline_suffix}")

            except Exception as e:
                self._queue_update(self._log_result, f"批量读取错误: {e}")
                for i in range(4):
                    var_path = self.batch_vars[i].get().strip()
                    if not var_path:
                        continue
                    self._queue_update(self._update_batch_value, i, f"错误: {str(e)}")
                    self._queue_update(self._update_status, f"组{i+1}读取错误: {e}")
                    self._queue_update(self._log_result, f"  错误: {e}")

            self._queue_update(self._log_result, "="*50)
            self._queue_update(self._log_result, "批量读取完成")

        self._update_status("正在批量读取...")
        threading.Thread(target=batch_read_thread, daemon=True).start()

    def _update_batch_value(self, idx, value):
        """更新批量读取的值"""
        self.batch_values[idx].set(str(value))

    def _update_batch_value_with_raw(self, idx, value, raw_value):
        """更新批量读取的值并保存原始数据"""
        self.batch_values[idx].set(str(value))
        self.batch_raw_values[idx] = raw_value

    def _on_type_selected(self, event, idx):
        """类型下拉框选择事件"""
        raw_value = self.batch_raw_values[idx]
        if raw_value is None:
            return
        
        new_type = self.batch_types[idx].get()
        converted_value = self._convert_raw_value(raw_value, new_type)
        self.batch_values[idx].set(str(converted_value))

    def _convert_raw_value(self, raw_value, display_type):
        """将原始32位值转换为指定类型"""
        import struct
        
        if display_type == "hex":
            return f"0x{raw_value:08X}"
        elif display_type == "float":
            return struct.unpack('f', struct.pack('I', raw_value))[0]
        elif display_type == "int32":
            if raw_value >= 0x80000000:
                return raw_value - 0x100000000
            return raw_value
        elif display_type == "uint32":
            return raw_value
        elif display_type == "int16":
            low16 = raw_value & 0xFFFF
            if low16 >= 0x8000:
                return low16 - 0x10000
            return low16
        elif display_type == "uint16":
            return raw_value & 0xFFFF
        elif display_type == "int8":
            low8 = raw_value & 0xFF
            if low8 >= 0x80:
                return low8 - 0x100
            return low8
        elif display_type == "uint8":
            return raw_value & 0xFF
        else:
            return raw_value

    def _add_to_history(self, var_path):
        """添加变量到历史记录"""
        history = self.config.get("variable_history", [])
        if var_path in history:
            history.remove(var_path)
        history.insert(0, var_path)
        self.config["variable_history"] = history[:10]
        for combo in self.batch_var_combos:
            combo['values'] = self.config["variable_history"]
        self._save_config()

    def _batch_clear(self):
        """清空批量读取区域"""
        for i in range(4):
            self.batch_vars[i].set("")
            self.batch_addresses[i].set("")
            self.batch_values[i].set("")
            self.batch_raw_values[i] = None
            if i < len(self.batch_var_combos):
                self.batch_var_combos[i].set("")
        
        self._update_status("已清空")
        self._log_result("批量读取区域已清空")

    def _show_result(self, result):
        """显示结果"""
        self.result_text.insert(tk.END, result)
        self.result_text.see(tk.END)

    def _on_comm_type_changed(self, event):
        """通信方式改变事件"""
        comm_type = self.comm_type_var.get()
        if comm_type == 'serial':
            self.serial_frame.grid(row=1, column=0, columnspan=6, sticky=tk.W+tk.E, pady=5)
            self.ws_frame.grid_forget()
        elif comm_type == 'websocket':
            self.serial_frame.grid_forget()
            self.ws_frame.grid(row=1, column=0, columnspan=6, sticky=tk.W+tk.E, pady=5)

    def _on_server_changed(self, event):
        """服务器选择改变事件"""
        pass

    def _on_device_type_changed(self, event):
        """设备类型选择改变事件"""
        device_type = self.device_type_var.get()
        self.config["device_type"] = device_type
        self._save_config()
        if self.modbus_client and hasattr(self.modbus_client, 'ws_client') and self.modbus_client.ws_client:
            self.modbus_client.ws_client.device_type = device_type
        self._update_status(f"设备类型: {device_type}")

    def _toggle_connection(self):
        """连接/断开连接"""
        if hasattr(self.modbus_client, 'connected') and self.modbus_client.connected:
            # 断开连接
            self.modbus_client.disconnect()
            self.connect_btn.config(text="连接")
            self.conn_status.config(text="未连接", foreground="red")
            self._update_status("已断开连接")
        else:
            # 连接
            comm_type = self.comm_type_var.get()

            # 保存配置
            self.config["comm_type"] = comm_type
            if comm_type == 'serial':
                port = self.port_var.get().strip()
                baudrate = int(self.baudrate_var.get())
                self.config["port"] = port
                self.config["baudrate"] = baudrate
            elif comm_type == 'websocket':
                self.config["ws_sn"] = self.ws_sn_var.get()
            self._save_config()

            # 创建客户端
            try:
                if comm_type == 'serial':
                    self.modbus_client = ModbusMemoryClient(
                        port=port,
                        baudrate=baudrate,
                        timeout=float(self.config.get("timeout", 1.0)),
                        packet_callback=self._on_packet,
                        comm_type='serial'
                    )
                elif comm_type == 'websocket':
                    self.modbus_client = ModbusMemoryClient(
                        comm_type='websocket',
                        timeout=float(self.config.get("timeout", 1.0)),
                        packet_callback=self._on_packet
                    )
                    # 设置WebSocket连接参数（使用默认值，SN需要设置）
                    if hasattr(self.modbus_client, 'ws_client') and self.modbus_client.ws_client:
                        self.modbus_client.ws_client.set_connection_params(
                            sn=self.ws_sn_var.get(),
                            server_type=self.server_var.get(),
                            device_type=self.device_type_var.get()
                        )
            except Exception as e:
                messagebox.showerror("错误", f"创建客户端失败: {e}")
                return

            # 连接
            self.connect_btn.config(state=tk.DISABLED, text="连接中...")
            self.conn_status.config(text="连接中...", foreground="orange")

            def connect_thread():
                try:
                    connected = self.modbus_client.connect()
                    if connected:
                        self._queue_update(self._connection_success, comm_type)
                    else:
                        self._queue_update(self._connection_failed, "连接失败")
                except Exception as e:
                    self._queue_update(self._connection_failed, str(e))

            threading.Thread(target=connect_thread, daemon=True).start()

    def _connection_success(self, comm_type):
        """连接成功"""
        self.connect_btn.config(state=tk.NORMAL, text="断开连接")
        self.conn_status.config(text="已连接", foreground="green")
        if comm_type == 'serial':
            port = self.port_var.get().strip()
            self._update_status(f"已连接到 {port}")
            self._log_result(f"已连接到串口: {port}")
        elif comm_type == 'websocket':
            self._update_status(f"已连接到 WebSocket 服务器")

    def _connection_failed(self, error_msg):
        """连接失败"""
        self.connect_btn.config(state=tk.NORMAL, text="连接")
        self.conn_status.config(text="未连接", foreground="red")
        self._update_status(f"连接失败: {error_msg}")
        self._log_result(f"连接失败: {error_msg}")
        messagebox.showerror("连接失败", f"无法连接到设备: {error_msg}")

    def _update_status(self, text):
        """更新状态"""
        self.status_var.set(text)
        print(f"状态: {text}")

    def on_closing(self):
        """窗口关闭事件"""
        if self.modbus_client and hasattr(self.modbus_client, 'connected'):
            self.modbus_client.disconnect()
        self._save_config()
        self.root.destroy()

def main():
    """主函数"""
    print("启动修复版GUI...")

    # 导入模块
    if not _import_modules():
        print("模块导入失败，无法启动GUI")
        return 1

    try:
        root = tk.Tk()
        app = FixedModbusGUI(root)

        # 设置关闭事件
        root.protocol("WM_DELETE_WINDOW", app.on_closing)

        print("开始主循环...")
        root.mainloop()
        print("主循环结束")

    except Exception as e:
        print(f"GUI启动失败: {e}")
        traceback.print_exc()
        messagebox.showerror("启动失败", f"GUI启动失败: {e}\n\n请检查控制台输出。")

if __name__ == "__main__":
    main()
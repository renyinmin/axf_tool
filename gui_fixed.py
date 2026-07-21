#!/usr/bin/env python3
"""
简化但稳定的Modbus AXF工具界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import json
import threading
import queue
import sys
import traceback
import datetime

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
    """更简单稳定的Modbus AXF工具GUI"""

    CONFIG_FILE = "config_fixed.json"

    def __init__(self, root):
        self.root = root
        self.root.title("Modbus AXF工具")
        self.root.geometry("800x700")

        # 设置最小大小
        self.root.minsize(600, 400)

        # 设置窗口图标
        try:
            import sys as _sys
            if getattr(_sys, 'frozen', False):
                ico_path = os.path.join(os.path.dirname(_sys.executable), 'fox.ico')
            else:
                ico_path = os.path.join(os.path.dirname(__file__), 'fox.ico')
            if os.path.exists(ico_path):
                self.root.iconbitmap(ico_path)
        except Exception:
            pass

        # 下拉框列表高度（显示更多条目，减少滚动）
        self.root.option_add('*TCombobox*Listbox.height', 10)

        # 配置
        self.config = self._load_config()

        # 状态变量
        self.axf_parser = None
        self.modbus_client = None
        self._packets = []

        # 消息队列（简化）
        self.message_queue = queue.Queue()

        print("GUI初始化...")

        # 创建UI（简化）
        self._create_simple_widgets()

        # 启动队列处理器
        self._start_queue_processor()

        print("GUI就绪")

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
        """创建UI"""
        # ========== 全局样式 ==========
        style = ttk.Style()
        style.configure("TLabelframe", font=("", 9, "bold"))
        style.configure("TLabelframe.Label", foreground="#37474F")
        style.configure("TLabel", font=("", 9))
        style.configure("TButton", font=("", 9))
        style.configure("TEntry", font=("", 9))
        style.configure("TCombobox", font=("", 9))

        # 通用按钮样式工厂
        def _styled_btn(parent, text, bg, active_bg, command=None, padx=12, pady=4, font_size=9):
            btn = tk.Button(parent, text=text, bg=bg, fg="white",
                           activebackground=active_bg, activeforeground="white",
                           relief=tk.FLAT, bd=0, padx=padx, pady=pady,
                           font=("", font_size, "bold"), cursor="hand2")
            if command:
                btn.configure(command=command)
            return btn

        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ========== 1. 通信设置 ==========
        conn_frame = ttk.LabelFrame(main_frame, text="📡 通信设置", padding=(12, 8))
        conn_frame.pack(fill=tk.X, pady=(0, 8))

        # 通信方式选择（紧凑排列在标签后面）
        comm_type_frame = ttk.Frame(conn_frame)
        comm_type_frame.grid(row=0, column=0, sticky=tk.W, pady=5)

        ttk.Label(comm_type_frame, text="通信方式:").pack(side=tk.LEFT)
        self.comm_type_var = tk.StringVar(value=self.config.get("comm_type", "serial"))
        comm_combo = ttk.Combobox(comm_type_frame, textvariable=self.comm_type_var, width=12)
        comm_combo.pack(side=tk.LEFT, padx=5)
        comm_combo['values'] = ['serial', 'websocket']
        comm_combo.bind('<<ComboboxSelected>>', self._on_comm_type_changed)

        # 串口设置
        self.serial_frame = ttk.Frame(conn_frame)
        self.serial_frame.grid(row=1, column=0, columnspan=6, sticky=tk.W+tk.E, pady=5)

        ttk.Label(self.serial_frame, text="串口:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.port_var = tk.StringVar(value=self.config.get("port", "COM3"))
        self.port_combo = ttk.Combobox(self.serial_frame, textvariable=self.port_var, width=34)
        self.port_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # 刷新按钮
        refresh_btn = ttk.Button(self.serial_frame, text="刷新", command=self._refresh_ports, width=6)
        refresh_btn.grid(row=0, column=2, padx=2, pady=5)

        self._refresh_ports()

        ttk.Label(self.serial_frame, text="波特率:").grid(row=0, column=4, sticky=tk.W, pady=5, padx=(15,0))
        self.baudrate_var = tk.StringVar(value=str(self.config.get("baudrate", 9600)))
        baud_combo = ttk.Combobox(self.serial_frame, textvariable=self.baudrate_var, width=10)
        baud_combo.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        baud_combo['values'] = ['9600', '19200', '38400', '57600', '115200', '230400']

        # WebSocket设置
        self.ws_frame = ttk.Frame(conn_frame)

        # 第一行：服务器选择、设备类型、SN
        ttk.Label(self.ws_frame, text="服务器:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.server_var = tk.StringVar(value=self.config.get("server", "测试服"))
        server_combo = ttk.Combobox(self.ws_frame, textvariable=self.server_var, width=12)
        server_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        server_combo['values'] = ['测试服', '欧服']
        server_combo.bind('<<ComboboxSelected>>', self._on_server_changed)

        ttk.Label(self.ws_frame, text="设备类型:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(20,0))
        self.device_type_var = tk.StringVar(value=self.config.get("device_type", "H3PLUS"))
        device_type_combo = ttk.Combobox(self.ws_frame, textvariable=self.device_type_var, width=10)
        device_type_combo.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        device_type_combo['values'] = ['H3PLUS', 'X7']
        device_type_combo.bind('<<ComboboxSelected>>', self._on_device_type_changed)

        # SN 历史（按设备类型分别保存）
        self.ws_sn_history = self.config.get("ws_sn_history", {"H3PLUS": [], "X7": []})
        if not isinstance(self.ws_sn_history, dict):
            self.ws_sn_history = {"H3PLUS": [], "X7": []}
        current_device = self.device_type_var.get()
        sn_default = self.config.get("ws_sn", self.ws_sn_history.get(current_device, [""])[0] if self.ws_sn_history.get(current_device) else "60HPB02054CA999")

        ttk.Label(self.ws_frame, text="SN:").grid(row=0, column=4, sticky=tk.W, pady=5, padx=(20,0))
        self.ws_sn_var = tk.StringVar(value=sn_default)
        self.ws_sn_combo = ttk.Combobox(self.ws_frame, textvariable=self.ws_sn_var, width=20)
        self.ws_sn_combo.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        self.ws_sn_combo['values'] = self.ws_sn_history.get(current_device, [])
        self._update_sn_combo_values()

        # 连接按钮与状态（居中）
        conn_btn_frame = tk.Frame(conn_frame, bg=self.root.cget("bg"))
        conn_btn_frame.grid(row=2, column=0, columnspan=6, pady=8)

        self.connect_btn = _styled_btn(conn_btn_frame, "🔌 连接", "#2196F3", "#1976D2", self._toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=4)

        self.conn_status = tk.Label(conn_btn_frame, text="● 未连接", fg="#F44336",
                                    font=("", 9, "bold"), bg=self.root.cget("bg"))
        self.conn_status.pack(side=tk.LEFT, padx=8)

        # 居中整个按钮组
        conn_frame.grid_rowconfigure(2, weight=0)
        conn_frame.grid_columnconfigure(0, weight=1)
        conn_btn_frame.grid_configure(sticky="")

        # 根据通信方式显示/隐藏设置
        self._on_comm_type_changed(None)

        # ========== 2. 文件选择 ==========
        file_frame = ttk.LabelFrame(main_frame, text="📁 AXF 文件", padding=(12, 8))
        file_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(file_frame, text="文件路径:").pack(side=tk.LEFT, pady=4)
        self.axf_file_var = tk.StringVar()
        axf_entry = ttk.Entry(file_frame, textvariable=self.axf_file_var, width=44)
        axf_entry.pack(side=tk.LEFT, padx=8, pady=4, fill=tk.X, expand=True)

        browse_btn = _styled_btn(file_frame, "📂 浏览", "#607D8B", "#455A64", self._browse_file)
        browse_btn.pack(side=tk.LEFT, padx=(4, 0), pady=4)

        # ========== 3. 批量读写 ==========
        batch_frame = ttk.LabelFrame(main_frame, text="📊 批量读写（4组数据）", padding=(12, 8))
        batch_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # 4组数据，每行一组
        self.batch_vars = [tk.StringVar() for _ in range(4)]
        self.batch_types = [tk.StringVar(value="hex") for _ in range(4)]
        self.batch_addresses = [tk.StringVar() for _ in range(4)]
        self.batch_values = [tk.StringVar() for _ in range(4)]
        self.batch_raw_values = [None for _ in range(4)]  # 保存原始数据用于类型转换
        self.batch_var_combos = []

        # 表头样式
        header_font = ("", 9, "bold")
        header_bg = "#E0E0E0"

        # 表头
        headers = [
            ("#", 3), ("变量", 39), ("地址", 14), ("值", 14), ("类型", 8), ("操作", 6)
        ]
        for col, (text, width) in enumerate(headers):
            lbl = tk.Label(batch_frame, text=text, font=header_font, bg=header_bg,
                          width=width, relief=tk.GROOVE, anchor=tk.CENTER)
            lbl.grid(row=0, column=col, padx=1, pady=(5, 2), sticky=tk.EW, ipady=2)

        # 交替行颜色
        row_colors = ["#FFFFFF", "#F5F5F5"]

        # 为每组创建控件（每行一组）
        for i in range(4):
            row_bg = row_colors[i % 2]

            # 行号
            num_lbl = tk.Label(batch_frame, text=str(i + 1), width=3, bg=row_bg,
                              anchor=tk.CENTER, font=("", 9))
            num_lbl.grid(row=i + 1, column=0, padx=1, pady=1, sticky=tk.EW)

            # 变量输入（Combobox，支持输入和选择历史）
            var_combo = ttk.Combobox(batch_frame, textvariable=self.batch_vars[i], width=35, state="normal")
            var_combo.grid(row=i + 1, column=1, padx=1, pady=1)
            var_combo['values'] = self.config.get("variable_history", [])
            var_combo.bind('<<ComboboxSelected>>', lambda e, idx=i: self._on_batch_var_selected(e, idx))
            self.batch_var_combos.append(var_combo)

            # 地址显示
            addr_entry = ttk.Entry(batch_frame, textvariable=self.batch_addresses[i], width=14, state="readonly")
            addr_entry.grid(row=i + 1, column=2, padx=1, pady=1)

            # 值显示（可编辑，支持写入）
            val_entry = ttk.Entry(batch_frame, textvariable=self.batch_values[i], width=14, state="normal")
            val_entry.grid(row=i + 1, column=3, padx=1, pady=1)

            # 类型选择
            type_combo = ttk.Combobox(batch_frame, textvariable=self.batch_types[i], width=8)
            type_combo.grid(row=i + 1, column=4, padx=1, pady=1)
            type_combo['values'] = ["hex", "float", "int32", "uint32", "int16", "uint16", "int8", "uint8"]
            type_combo.bind('<<ComboboxSelected>>', lambda e, idx=i: self._on_type_selected(e, idx))

            # 写入按钮
            write_btn = tk.Button(batch_frame, text="✎ 写入", bg="#4CAF50", fg="white",
                                 activebackground="#388E3C", activeforeground="white",
                                 relief=tk.FLAT, bd=0, padx=10,
                                 font=("", 9, "bold"), cursor="hand2")
            write_btn.grid(row=i + 1, column=5, padx=2, pady=1, ipady=2, sticky=tk.NSEW)
            write_btn.bind('<ButtonRelease-1>', lambda e, idx=i: self._single_write(idx))

        # 批量操作按钮
        batch_btn_frame = ttk.Frame(batch_frame)
        batch_btn_frame.grid(row=5, column=0, columnspan=6, pady=(10, 0))

        batch_read_btn = _styled_btn(batch_btn_frame, "📥 批量读取", "#2196F3", "#1976D2", self._batch_read)
        batch_read_btn.pack(side=tk.LEFT, padx=5)

        batch_clear_btn = _styled_btn(batch_btn_frame, "🗑 清空", "#FF9800", "#F57C00", self._batch_clear)
        batch_clear_btn.pack(side=tk.LEFT, padx=5)

        # 自动读取控制
        auto_read_frame = ttk.Frame(batch_btn_frame)
        auto_read_frame.pack(side=tk.RIGHT, padx=5)

        ttk.Label(auto_read_frame, text="自动读取:", font=("", 9)).pack(side=tk.LEFT, padx=(0, 5))
        self.auto_read_interval_var = tk.StringVar(value="2S")
        self.auto_read_combo = ttk.Combobox(auto_read_frame, textvariable=self.auto_read_interval_var, width=10)
        self.auto_read_combo['values'] = ["500ms", "1S", "2S", "5S", "10S", "20S"]
        self.auto_read_combo.pack(side=tk.LEFT, padx=2)
        self.auto_read_combo.bind('<<ComboboxSelected>>', self._on_auto_read_interval_changed)

        self.auto_read_btn = tk.Button(auto_read_frame, text="▶ 开始",
                                       bg="#4CAF50", fg="white",
                                       activebackground="#388E3C", activeforeground="white",
                                       relief=tk.FLAT, bd=0, padx=8, pady=3,
                                       font=("", 9, "bold"), cursor="hand2")
        self.auto_read_btn.pack(side=tk.LEFT, padx=5)
        self.auto_read_btn.bind('<ButtonRelease-1>', lambda e: self._toggle_auto_read())

        # 自动读取定时器
        self._auto_read_timer = None
        self._auto_read_running = False

        # ========== 4. 结果 ==========
        result_frame = ttk.LabelFrame(main_frame, text="📋 结果", padding=(12, 8))
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.result_text = scrolledtext.ScrolledText(result_frame, height=20,
                                                     font=("Consolas", 9),
                                                     bg="#FAFAFA", fg="#212121",
                                                     insertbackground="#212121",
                                                     selectbackground="#BBDEFB")
        self.result_text.pack(fill=tk.BOTH, expand=True)

        self.result_text.insert(tk.END, "就绪 — 请加载 AXF 文件并连接设备\n")
        self.result_text.insert(tk.END, "─" * 50 + "\n")

        # ========== 5. 状态栏 ==========
        status_frame = tk.Frame(main_frame, bg="#37474F", height=28)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        status_frame.pack_propagate(False)

        self.status_var = tk.StringVar(value="就绪")
        status_bar = tk.Label(status_frame, textvariable=self.status_var,
                             bg="#37474F", fg="#ECEFF1",
                             anchor=tk.W, font=("", 8), padx=10)
        status_bar.pack(fill=tk.BOTH, expand=True)

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
            now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self._queue_update(self._log_result, f"[{now}] 开始批量读取...")
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
                        now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        self._queue_update(self._log_result, f"[{now}] [{var_path}] 结果: {value} (原始值: 0x{raw_value:08X})")
                    else:
                        offline_suffix = "（offline）" if self.modbus_client.ws_client._device_offline else ""
                        self._queue_update(self._update_batch_value, i, "读取失败")
                        now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        self._queue_update(self._log_result, f"[{now}] [{var_path}] 结果: 读取失败{offline_suffix}")

            except Exception as e:
                self._queue_update(self._log_result, f"批量读取错误: {e}")
                for i in range(4):
                    var_path = self.batch_vars[i].get().strip()
                    if not var_path:
                        continue
                    self._queue_update(self._update_batch_value, i, f"错误: {str(e)}")
                    self._queue_update(self._update_status, f"组{i+1}读取错误: {e}")
                    now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    self._queue_update(self._log_result, f"[{now}] [{var_path}] 错误: {e}")

            self._queue_update(self._log_result, "="*50)

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
        self.config["variable_history"] = history[:20]
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

    def _toggle_auto_read(self):
        """切换自动读取状态"""
        if self._auto_read_running:
            self._stop_auto_read()
        else:
            if not self.axf_parser:
                messagebox.showwarning("警告", "请先加载AXF文件")
                return
            if not self.modbus_client or not hasattr(self.modbus_client, 'connected') or not self.modbus_client.connected:
                messagebox.showwarning("警告", "请先连接Modbus设备")
                return
            self._start_auto_read()

    def _start_auto_read(self):
        """启动自动读取"""
        self._stop_auto_read()
        
        interval_str = self.auto_read_interval_var.get()
        interval_ms = self._parse_interval(interval_str)
        
        self._auto_read_running = True
        self.auto_read_btn.config(text="⏹ 停止", bg="#F44336", activebackground="#D32F2F")
        self.auto_read_combo.config(state="disabled")
        
        self._update_status(f"自动读取中，间隔 {interval_str}")
        self._log_result(f"开始自动读取，间隔 {interval_str}")
        
        self._auto_read_callback()

    def _stop_auto_read(self):
        """停止自动读取"""
        if self._auto_read_timer:
            self.root.after_cancel(self._auto_read_timer)
            self._auto_read_timer = None
        
        self._auto_read_running = False
        self.auto_read_btn.config(text="▶ 开始", bg="#4CAF50", activebackground="#388E3C")
        self.auto_read_combo.config(state="normal")
        
        if hasattr(self, 'status_var'):
            self._update_status("自动读取已停止")

    def _auto_read_callback(self):
        """自动读取回调"""
        if not self._auto_read_running:
            return
        
        self._batch_read()
        
        interval_str = self.auto_read_interval_var.get()
        interval_ms = self._parse_interval(interval_str)
        
        self._auto_read_timer = self.root.after(interval_ms, self._auto_read_callback)

    def _parse_interval(self, interval_str):
        """解析间隔字符串为毫秒"""
        interval_map = {
            "500ms": 500,
            "1S": 1000,
            "2S": 2000,
            "5S": 5000,
            "10S": 10000,
            "20S": 20000
        }
        return interval_map.get(interval_str, 2000)

    def _on_auto_read_interval_changed(self, event):
        """自动读取间隔改变事件"""
        if self._auto_read_running:
            self._start_auto_read()

    def _parse_display_value(self, value_str: str, display_type: str):
        """将用户输入的文本值解析为Python int/float"""
        value_str = value_str.strip()
        if not value_str:
            raise ValueError("值为空")

        if display_type == "hex":
            return int(value_str, 16)
        elif display_type == "float":
            return float(value_str)
        elif display_type in ("int32", "int16", "int8"):
            return int(value_str)
        elif display_type in ("uint32", "uint16", "uint8"):
            return int(value_str)
        else:
            raise ValueError(f"不支持的显示类型: {display_type}")

    def _typed_to_raw(self, value, display_type: str) -> int:
        """将Python值转换为原始32位整数（与modbus_client._value_to_raw逻辑一致）"""
        import struct

        if display_type == "float":
            return struct.unpack('I', struct.pack('f', float(value)))[0]
        elif display_type == "int32":
            if value < 0:
                return value + 0x100000000
            return int(value) & 0xFFFFFFFF
        elif display_type == "int16":
            if value < 0:
                value = value + 0x10000
            return value & 0xFFFF
        elif display_type == "uint16":
            return int(value) & 0xFFFF
        elif display_type == "int8":
            if value < 0:
                value = value + 0x100
            return value & 0xFF
        elif display_type == "uint8":
            return int(value) & 0xFF
        else:
            return int(value) & 0xFFFFFFFF

    def _single_write(self, idx):
        """单行写入"""
        if not self.axf_parser:
            messagebox.showwarning("警告", "请先加载AXF文件")
            return

        if not self.modbus_client or not hasattr(self.modbus_client, 'connected') or not self.modbus_client.connected:
            messagebox.showwarning("警告", "请先连接Modbus设备")
            return

        var_path = self.batch_vars[idx].get().strip()
        if not var_path:
            messagebox.showwarning("警告", f"第{idx+1}行: 请先选择变量")
            return

        value_str = self.batch_values[idx].get().strip()
        if not value_str:
            messagebox.showwarning("警告", f"第{idx+1}行: 请输入要写入的值")
            return

        display_type = self.batch_types[idx].get()

        # 解析用户输入的值
        try:
            value = self._parse_display_value(value_str, display_type)
        except (ValueError, TypeError) as e:
            messagebox.showerror("错误", f"第{idx+1}行 值解析错误: {e}")
            return

        # 小类型（int16/uint16/int8/uint8）写入不足4字节，需要合并回读值的高位字节
        small_types = {"int16", "uint16", "int8", "uint8"}
        if display_type in small_types:
            if self.batch_raw_values[idx] is None:
                messagebox.showwarning("警告",
                    f"第{idx+1}行: {display_type}类型仅写入{'2' if display_type in ('int16','uint16') else '1'}字节，\n"
                    "请先点击「批量读取」获取当前值后再写入")
                return
            # 合并：高位字节保留回读值，低位字节替换为新值
            old_raw = self.batch_raw_values[idx]
            new_raw = self._typed_to_raw(value, display_type)
            if display_type in ("int16", "uint16"):
                raw_value = (old_raw & 0xFFFF0000) | (new_raw & 0xFFFF)
            else:  # int8, uint8
                raw_value = (old_raw & 0xFFFFFF00) | (new_raw & 0xFF)
        else:
            raw_value = self._typed_to_raw(value, display_type)

        # 每组的写地址和读地址
        group_addresses = [
            {"write": 43507, "read": 43515},  # 第1组
            {"write": 43509, "read": 43517},  # 第2组
            {"write": 43511, "read": 43519},  # 第3组
            {"write": 43513, "read": 43521}   # 第4组
        ]

        # 构建确认提示：显示旧值 → 新值
        if self.batch_raw_values[idx] is not None:
            old_display = str(self._convert_raw_value(self.batch_raw_values[idx], display_type))
            if display_type in small_types:
                old_hex = f"0x{self.batch_raw_values[idx]:08X}"
                new_hex = f"0x{raw_value:08X}"
                detail = f"旧值: {old_display}  →  新值: {value_str}\n({old_hex} → {new_hex})"
            else:
                detail = f"旧值: {old_display}  →  新值: {value_str}"
        else:
            detail = f"旧值: 未读取  →  新值: {value_str}"

        if not self._confirm_write(var_path, display_type, detail):
            return

        self._packets = []

        def write_thread():
            # 解析地址
            address = self.axf_parser.get_variable_address(var_path)
            if address is None:
                self._queue_update(self._log_result, f"第{idx+1}行: 变量地址未找到")
                return

            self._queue_update(self.batch_addresses[idx].set, f"0x{address:08X}")
            self._queue_update(self._add_to_history, var_path)
            self._queue_update(self._log_result, f"第{idx+1}行 写入: {var_path} = {value_str}")
            self._queue_update(self._update_status, f"第{idx+1}行 正在写入...")

            try:
                # 传入合并后的完整32位raw值，用uint32避免_value_to_raw二次转换
                success = self.modbus_client.write_memory(
                    address, raw_value, "uint32",
                    write_addr=group_addresses[idx]["write"],
                    read_addr=group_addresses[idx]["read"]
                )

                if success:
                    # 缓存合并后的完整32位原始值，按类型格式化显示
                    display_str = str(self._convert_raw_value(raw_value, display_type))
                    self._queue_update(self._update_batch_raw, idx, raw_value, display_str)
                    self._queue_update(self._log_result, f"第{idx+1}行 写入成功: {display_str}")
                    self._queue_update(self._update_status, f"第{idx+1}行 写入成功")
                else:
                    self._queue_update(self._log_result, f"第{idx+1}行 写入失败")
                    self._queue_update(self._update_status, f"第{idx+1}行 写入失败")

            except Exception as e:
                self._queue_update(self._log_result, f"第{idx+1}行 写入错误: {e}")
                self._queue_update(self._update_status, f"第{idx+1}行 写入错误: {e}")

        threading.Thread(target=write_thread, daemon=True).start()

    def _confirm_write(self, var_path, display_type, detail):
        """自定义确认对话框"""
        dlg = tk.Toplevel(self.root)
        dlg.title("写入确认")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        # 居中
        w, h = 420, 210
        x = self.root.winfo_rootx() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")

        dlg.configure(bg="#FAFAFA")

        # 标题栏
        title_frame = tk.Frame(dlg, bg="#FF9800", height=36)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="⚠ 写入确认", fg="white", bg="#FF9800",
                 font=("", 11, "bold")).pack(side=tk.LEFT, padx=12, pady=6)

        # 内容
        content = tk.Frame(dlg, bg="#FAFAFA")
        content.pack(fill=tk.BOTH, expand=True, padx=16, pady=(14, 8))

        tk.Label(content, text=f"变量: {var_path}", bg="#FAFAFA",
                 font=("", 9)).pack(anchor=tk.W, pady=2)
        tk.Label(content, text=f"类型: {display_type}", bg="#FAFAFA",
                 font=("", 9)).pack(anchor=tk.W, pady=2)

        # 变更详情（用不同颜色）
        detail_frame = tk.Frame(content, bg="#FFF3E0", relief=tk.GROOVE, bd=1)
        detail_frame.pack(fill=tk.X, pady=(8, 4), ipady=4)
        tk.Label(detail_frame, text=detail, bg="#FFF3E0", fg="#E65100",
                 font=("", 10, "bold"), wraplength=370).pack(padx=10, pady=6)

        tk.Label(content, text="请谨慎操作，确定要继续写入吗？", bg="#FAFAFA",
                 fg="#757575", font=("", 8)).pack(anchor=tk.CENTER, pady=(2, 0))

        # 按钮
        result = [False]

        def on_confirm():
            result[0] = True
            dlg.destroy()

        def on_cancel():
            dlg.destroy()

        btn_frame = tk.Frame(dlg, bg="#FAFAFA")
        btn_frame.pack(fill=tk.X, padx=16, pady=(0, 12))

        confirm_btn = tk.Button(btn_frame, text="确定写入", command=on_confirm,
                                bg="#F44336", fg="white", activebackground="#D32F2F",
                                relief=tk.FLAT, padx=20, pady=4, font=("", 9, "bold"))
        confirm_btn.pack(side=tk.LEFT, expand=True, padx=4)

        cancel_btn = tk.Button(btn_frame, text="取消", command=on_cancel,
                               bg="#BDBDBD", fg="white", activebackground="#9E9E9E",
                               relief=tk.FLAT, padx=20, pady=4, font=("", 9))
        cancel_btn.pack(side=tk.LEFT, expand=True, padx=4)

        dlg.protocol("WM_DELETE_WINDOW", on_cancel)
        dlg.wait_window()
        return result[0]

    def _update_batch_raw(self, idx, raw_value, display_str):
        """更新写入后缓存的原始值并显示"""
        self.batch_raw_values[idx] = raw_value
        self.batch_values[idx].set(display_str)

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
        server_type = self.server_var.get()
        self.config["server"] = server_type
        self._save_config()
        if self.modbus_client and hasattr(self.modbus_client, 'ws_client') and self.modbus_client.ws_client:
            self.modbus_client.ws_client.server_type = server_type
        self._update_status(f"服务器: {server_type}")

    def _refresh_ports(self):
        """刷新串口列表"""
        try:
            import serial.tools.list_ports
            ports = [f"{port.device} - {port.description}" for port in serial.tools.list_ports.comports()]
            if not ports:
                ports = ["COM1", "COM2", "COM3", "COM4", "COM5", "COM6"]
        except:
            ports = ["COM1", "COM2", "COM3", "COM4", "COM5", "COM6"]
        self.port_combo['values'] = ports
        if hasattr(self, 'status_var'):
            self._update_status(f"串口列表已刷新，共 {len(ports)} 个串口")

    def _on_device_type_changed(self, event):
        """设备类型选择改变事件"""
        device_type = self.device_type_var.get()
        self.config["device_type"] = device_type
        self._save_config()
        # 切换设备类型时，更新 SN 下拉列表
        sn_list = self.ws_sn_history.get(device_type, [])
        self.ws_sn_combo['values'] = sn_list
        if sn_list:
            self.ws_sn_var.set(sn_list[0])
        if self.modbus_client and hasattr(self.modbus_client, 'ws_client') and self.modbus_client.ws_client:
            self.modbus_client.ws_client.device_type = device_type
        self._update_status(f"设备类型: {device_type}")

    def _update_sn_combo_values(self):
        """初始化SN下拉框值"""
        device_type = self.device_type_var.get()
        sn_list = self.ws_sn_history.get(device_type, [])
        self.ws_sn_combo['values'] = sn_list

    def _save_sn_to_history(self, sn):
        """保存SN到当前设备类型的历史记录（最多10条）"""
        device_type = self.device_type_var.get()
        if device_type not in self.ws_sn_history:
            self.ws_sn_history[device_type] = []
        sn_list = self.ws_sn_history[device_type]
        if sn in sn_list:
            sn_list.remove(sn)
        sn_list.insert(0, sn)
        self.ws_sn_history[device_type] = sn_list[:10]
        self.config["ws_sn_history"] = self.ws_sn_history
        self.config["ws_sn"] = sn
        self.ws_sn_combo['values'] = self.ws_sn_history[device_type]
        self._save_config()

    def _toggle_connection(self):
        """连接/断开连接"""
        if hasattr(self.modbus_client, 'connected') and self.modbus_client.connected:
            # 断开连接
            self.modbus_client.disconnect()
            self.connect_btn.config(text="🔌 连接", bg="#2196F3")
            self.conn_status.config(text="● 未连接", fg="#F44336")
            self._stop_auto_read()
            self._update_status("已断开连接")
        else:
            # 连接
            comm_type = self.comm_type_var.get()

            # 保存配置
            self.config["comm_type"] = comm_type
            if comm_type == 'serial':
                port_full = self.port_var.get().strip()
                port = port_full.split(' - ')[0] if ' - ' in port_full else port_full
                baudrate = int(self.baudrate_var.get())
                self.config["port"] = port
                self.config["baudrate"] = baudrate
            elif comm_type == 'websocket':
                self._save_sn_to_history(self.ws_sn_var.get())


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
            self.connect_btn.config(state=tk.DISABLED, text="连接中...", bg="#90A4AE")
            self.conn_status.config(text="◉ 连接中...", fg="#FF9800")

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
        self.connect_btn.config(state=tk.NORMAL, text="🔌 断开", bg="#F44336")
        self.conn_status.config(text="● 已连接", fg="#4CAF50")
        if comm_type == 'serial':
            port_full = self.port_var.get().strip()
            port_display = port_full.split(' - ')[1] if ' - ' in port_full else port_full
            port = port_full.split(' - ')[0] if ' - ' in port_full else port_full
            self._update_status(f"已连接到 {port}")
            self._log_result(f"已连接到串口: {port_display}")
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
        self._stop_auto_read()
        if self.modbus_client and hasattr(self.modbus_client, 'connected'):
            self.modbus_client.disconnect()
        self._save_config()
        self.root.destroy()

def main():
    """主函数"""
    print("启动GUI...")

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
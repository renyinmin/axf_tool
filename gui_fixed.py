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
        self.root.geometry("800x600")

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
        config_path = os.path.join(os.path.dirname(__file__), self.CONFIG_FILE)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass

        return {
            "recent_axf_files": [],
            "port": "COM3",
            "baudrate": 115200,
            "timeout": 1.0,
            "variable_history": []
        }

    def _save_config(self):
        """保存配置"""
        config_path = os.path.join(os.path.dirname(__file__), self.CONFIG_FILE)
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def _create_simple_widgets(self):
        """创建简化UI"""
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 串口设置区域（最上面）
        conn_frame = ttk.LabelFrame(main_frame, text="串口设置", padding=10)
        conn_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(conn_frame, text="串口:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.port_var = tk.StringVar(value=self.config.get("port", "COM3"))
        port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, width=12)
        port_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        try:
            import serial.tools.list_ports
            ports = [port.device for port in serial.tools.list_ports.comports()]
            if not ports:
                ports = ["COM1", "COM2", "COM3", "COM4", "COM5", "COM6"]
        except:
            ports = ["COM1", "COM2", "COM3", "COM4", "COM5", "COM6"]
        port_combo['values'] = ports

        ttk.Label(conn_frame, text="波特率:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(15,0))
        self.baudrate_var = tk.StringVar(value=str(self.config.get("baudrate", 115200)))
        baud_combo = ttk.Combobox(conn_frame, textvariable=self.baudrate_var, width=10)
        baud_combo.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        baud_combo['values'] = ['9600', '19200', '38400', '57600', '115200', '230400']

        self.connect_btn = ttk.Button(conn_frame, text="连接", command=self._toggle_connection)
        self.connect_btn.grid(row=0, column=4, padx=15, pady=5)

        self.conn_status = ttk.Label(conn_frame, text="未连接", foreground="red")
        self.conn_status.grid(row=0, column=5, padx=5, pady=5)

        # 2. 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="AXF文件", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(file_frame, text="文件路径:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.axf_file_var = tk.StringVar()
        axf_entry = ttk.Entry(file_frame, textvariable=self.axf_file_var, width=50)
        axf_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)

        browse_btn = tk.Button(file_frame, text="浏览...", command=self._browse_file,
                               bg="#607D8B", fg="white", padx=20, pady=5)
        browse_btn.grid(row=0, column=2, padx=5, pady=5)

        # 3. 变量操作区域
        var_frame = ttk.LabelFrame(main_frame, text="变量操作", padding=10)
        var_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(var_frame, text="变量路径:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.var_path_var = tk.StringVar()
        var_entry = ttk.Entry(var_frame, textvariable=self.var_path_var, width=40)
        var_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)

        self.var_history_combo = ttk.Combobox(var_frame, width=40)
        self.var_history_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        self.var_history_combo['values'] = self.config.get("variable_history", [])
        self.var_history_combo.bind('<<ComboboxSelected>>', self._on_history_selected)
        ttk.Label(var_frame, text="历史:").grid(row=1, column=0, sticky=tk.W, pady=5)

        ttk.Label(var_frame, text="显示类型:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.display_type_var = tk.StringVar(value="hex")
        type_combo = ttk.Combobox(var_frame, textvariable=self.display_type_var, width=15)
        type_combo.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        type_combo['values'] = ["hex", "float", "int32", "uint32", "int16", "uint16"]

        btn_frame = ttk.Frame(var_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)

        get_addr_btn = tk.Button(btn_frame, text="获取地址", 
                                  bg="#4CAF50", fg="white", padx=10, pady=5)
        get_addr_btn.pack(side=tk.LEFT, padx=5)
        get_addr_btn.bind('<ButtonRelease-1>', lambda e: self._get_address())
        print(f"[DEBUG] 获取地址按钮已创建")
        
        read_btn = tk.Button(btn_frame, text="读取",
                             bg="#2196F3", fg="white", padx=10, pady=5)
        read_btn.pack(side=tk.LEFT, padx=5)
        read_btn.bind('<ButtonRelease-1>', lambda e: self._read_variable())

        # 4. 结果显示区域
        result_frame = ttk.LabelFrame(main_frame, text="结果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.result_text = scrolledtext.ScrolledText(result_frame, height=15)
        self.result_text.pack(fill=tk.BOTH, expand=True)

        self.result_text.insert(tk.END, "结果将显示在这里...\n")
        self.result_text.insert(tk.END, "="*50 + "\n")

        # 5. 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var,
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        file_frame.columnconfigure(1, weight=1)
        var_frame.columnconfigure(1, weight=1)
        var_entry.bind('<Return>', lambda e: self._get_address())

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

        # 在状态栏显示一些示例变量
        variables = parser.list_global_variables()
        print(f"[DEBUG] variables: {list(variables.items())[:3] if variables else 'empty'}")
        example_vars = list(variables.items())[:3]
        for name, addr in example_vars:
            self.result_text.insert(tk.END, f"  {name}: 0x{addr:08X}\n")
        if vars_count > 3:
            self.result_text.insert(tk.END, f"  ... 还有 {vars_count-3} 个变量\n")
        self.result_text.insert(tk.END, "="*50 + "\n")

    def _get_address(self):
        """获取变量地址"""
        var_path = self.var_path_var.get().strip()
        print(f"[DEBUG] _get_address called, var_path='{var_path}'")
        
        if not var_path:
            self.result_text.insert(tk.END, "警告: 请输入变量路径\n")
            self.result_text.see(tk.END)
            self._update_status("请输入变量路径")
            return

        if not self.axf_parser:
            self.result_text.insert(tk.END, "警告: 请先加载AXF文件\n")
            self.result_text.see(tk.END)
            self._update_status("请先加载AXF文件")
            return

        # 添加到历史
        history = self.config.get("variable_history", [])
        if var_path in history:
            history.remove(var_path)
        history.insert(0, var_path)
        self.config["variable_history"] = history[:10]
        self.var_history_combo['values'] = self.config["variable_history"]
        self._save_config()

        # 获取地址
        print(f"[DEBUG] axf_parser type: {type(self.axf_parser)}")
        print(f"[DEBUG] symbols count: {len(self.axf_parser.symbols)}")
        address = self.axf_parser.get_variable_address(var_path)
        print(f"[DEBUG] address result: {address}")
        
        if address is not None:
            result = f"变量: {var_path}\n地址: 0x{address:08X}\n"
            self.result_text.insert(tk.END, result)
            self.result_text.insert(tk.END, "-"*40 + "\n")
            self.result_text.see(tk.END)
            self._update_status(f"找到地址: 0x{address:08X}")
        else:
            self.result_text.insert(tk.END, f"错误: 未找到变量 '{var_path}'\n")
            self.result_text.insert(tk.END, f"提示: 检查变量名是否正确\n")
            self.result_text.see(tk.END)
            self._update_status(f"未找到变量: {var_path}")

    def _on_history_selected(self, event):
        """历史下拉框选择事件"""
        selected = self.var_history_combo.get()
        if selected:
            self.var_path_var.set(selected)
            # 自动获取地址
            self._get_address()

    def _read_variable(self):
        """读取变量"""
        var_path = self.var_path_var.get().strip()
        if not var_path:
            messagebox.showwarning("警告", "请输入变量路径")
            return

        if not self.axf_parser:
            messagebox.showwarning("警告", "请先加载AXF文件")
            return

        if not self.modbus_client or not hasattr(self.modbus_client, 'connected'):
            messagebox.showwarning("警告", "请先连接Modbus设备")
            return

        address = self.axf_parser.get_variable_address(var_path)
        if address is None:
            messagebox.showerror("错误", f"未找到变量: {var_path}")
            return

        display_type = self.display_type_var.get()

        self._packets = []

        def read_thread():
            try:
                value = self.modbus_client.read_memory(address, display_type)
                if value is not None:
                    result = f"变量: {var_path}\n"
                    result += f"地址: 0x{address:08X}\n"
                    result += f"类型: {display_type}\n"
                    result += f"值: {value}\n"
                    result += "-"*40 + "\n"
                    result += "报文:\n"
                    for pkt in self._packets:
                        result += f"  [{pkt[0]}] {pkt[1]} ({pkt[2]}字节)\n"
                    result += "="*50 + "\n"

                    self._queue_update(lambda r=result: self._show_result(r))
                    self._queue_update(self._update_status, f"读取成功: {value}")
                else:
                    self._queue_update(self._update_status, "读取失败")
                    self._queue_update(lambda: messagebox.showerror("错误", "读取失败"))
            except Exception as e:
                self._queue_update(self._update_status, f"读取错误: {e}")
                self._queue_update(lambda: messagebox.showerror("错误", f"读取错误: {e}"))

        self._update_status(f"正在读取: {var_path}")
        threading.Thread(target=read_thread, daemon=True).start()

    def _on_packet(self, direction, hex_str, length, description):
        """报文回调"""
        self._packets.append((direction, hex_str, length, description))

    def _show_result(self, result):
        """显示结果"""
        self.result_text.insert(tk.END, result)
        self.result_text.see(tk.END)

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
            port = self.port_var.get().strip()
            baudrate = int(self.baudrate_var.get())

            # 保存配置
            self.config["port"] = port
            self.config["baudrate"] = baudrate
            self._save_config()

            # 创建客户端
            try:
                self.modbus_client = ModbusMemoryClient(
                    port=port,
                    baudrate=baudrate,
                    timeout=float(self.config.get("timeout", 1.0)),
                    packet_callback=self._on_packet
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
                        self._queue_update(self._connection_success, port)
                    else:
                        self._queue_update(self._connection_failed, "连接失败")
                except Exception as e:
                    self._queue_update(self._connection_failed, str(e))

            threading.Thread(target=connect_thread, daemon=True).start()

    def _connection_success(self, port):
        """连接成功"""
        self.connect_btn.config(state=tk.NORMAL, text="断开连接")
        self.conn_status.config(text="已连接", foreground="green")
        self._update_status(f"已连接到 {port}")

    def _connection_failed(self, error_msg):
        """连接失败"""
        self.connect_btn.config(state=tk.NORMAL, text="连接")
        self.conn_status.config(text="未连接", foreground="red")
        self._update_status(f"连接失败: {error_msg}")
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
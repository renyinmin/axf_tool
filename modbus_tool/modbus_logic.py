import sys
import serial
import struct
import time
import json
import os
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer, Qt, QSettings
from PyQt5.QtGui import QTextCursor, QFont, QColor, QTextCharFormat

class ModbusLogic:
    def __init__(self, ui, main_window):
        self.ui = ui
        self.main_window = main_window
        self.serial_port = None
        self.config_file = "modbus_config.ini"
        self.init_serial()
        self.setup_ui()
        self.setup_connections()
        self.load_config()  # 启动时自动加载配置
        
    def init_serial(self):
        """初始化串口"""
        self.serial_port = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_serial_data)
        
    def setup_ui(self):
        """设置UI初始状态"""
        # 设置字体
        font = QFont("Arial", 10)
        self.main_window.setFont(font)
        
        # 设置串口参数选项
        self.ui.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.ui.baud_combo.setCurrentText("9600")
        
        self.ui.data_bits_combo.addItems(["5", "6", "7", "8"])
        self.ui.data_bits_combo.setCurrentText("8")
        
        self.ui.stop_bits_combo.addItems(["1", "1.5", "2"])
        self.ui.stop_bits_combo.setCurrentText("1")
        
        self.ui.parity_combo.addItems(["无", "偶校验", "奇校验"])
        self.ui.parity_combo.setCurrentText("无")
        
        # 设置功能码选项
        self.ui.func_code_combo.addItems([
            "01 - 读线圈",
            "02 - 读离散输入", 
            "03 - 读保持寄存器",
            "04 - 读输入寄存器",
            "05 - 写单个线圈",
            "06 - 写单个寄存器",
            "0F - 写多个线圈",
            "10 - 写多个寄存器"
        ])
        
        # 设置数据格式选项
        self.ui.addr_format_combo.addItems(["十进制", "十六进制"])
        self.ui.data_format_combo.addItems(["十进制", "十六进制"])
        
        # 设置通信数据显示框字体
        self.ui.communication_text.setFont(QFont("Courier New", 9))
        
        # 初始化功能码对应的UI状态
        self.on_func_code_changed(self.ui.func_code_combo.currentText())
        
        # 刷新端口列表
        self.refresh_ports()
        
    def setup_connections(self):
        """连接信号和槽"""
        # 串口操作
        self.ui.refresh_btn.clicked.connect(self.refresh_ports)
        self.ui.open_btn.clicked.connect(self.toggle_serial)
        
        # 通信数据操作
        self.ui.clear_packet_btn.clicked.connect(self.clear_communication)
        self.ui.copy_packet_btn.clicked.connect(self.copy_communication)
        
        # Modbus操作
        self.ui.generate_btn.clicked.connect(self.generate_modbus_frame)
        self.ui.send_btn.clicked.connect(self.send_modbus_request)
        self.ui.func_code_combo.currentTextChanged.connect(self.on_func_code_changed)
        
        # 自定义报文操作
        self.ui.generate_custom_btn.clicked.connect(self.generate_custom_frame)
        
    def save_config(self):
        """保存配置到文件"""
        try:
            settings = QSettings(self.config_file, QSettings.IniFormat)
            
            # 保存串口配置（不保存端口号）
            settings.setValue("serial/baudrate", self.ui.baud_combo.currentText())
            settings.setValue("serial/databits", self.ui.data_bits_combo.currentText())
            settings.setValue("serial/stopbits", self.ui.stop_bits_combo.currentText())
            settings.setValue("serial/parity", self.ui.parity_combo.currentText())
            
            # 保存Modbus配置
            settings.setValue("modbus/slave_addr", self.ui.slave_addr_edit.text())
            settings.setValue("modbus/func_code", self.ui.func_code_combo.currentText())
            settings.setValue("modbus/start_addr", self.ui.start_addr_edit.text())
            settings.setValue("modbus/reg_count", self.ui.reg_count_edit.text())
            settings.setValue("modbus/addr_format", self.ui.addr_format_combo.currentText())
            settings.setValue("modbus/data_format", self.ui.data_format_combo.currentText())
            
            # 同步保存到文件
            settings.sync()
            
        except Exception as e:
            # 在关闭时保存配置，如果出错不显示消息框，避免干扰关闭过程
            print(f"保存配置失败: {str(e)}")
            
    def load_config(self):
        """从文件加载配置"""
        try:
            settings = QSettings(self.config_file, QSettings.IniFormat)
            
            # 加载串口配置（不加载端口号）
            baudrate = settings.value("serial/baudrate", "9600")
            if self.ui.baud_combo.findText(baudrate) >= 0:
                self.ui.baud_combo.setCurrentText(baudrate)
                
            databits = settings.value("serial/databits", "8")
            if self.ui.data_bits_combo.findText(databits) >= 0:
                self.ui.data_bits_combo.setCurrentText(databits)
                
            stopbits = settings.value("serial/stopbits", "1")
            if self.ui.stop_bits_combo.findText(stopbits) >= 0:
                self.ui.stop_bits_combo.setCurrentText(stopbits)
                
            parity = settings.value("serial/parity", "无")
            if self.ui.parity_combo.findText(parity) >= 0:
                self.ui.parity_combo.setCurrentText(parity)
            
            # 加载Modbus配置
            self.ui.slave_addr_edit.setText(settings.value("modbus/slave_addr", "1"))
            
            func_code = settings.value("modbus/func_code", "03 - 读保持寄存器")
            if self.ui.func_code_combo.findText(func_code) >= 0:
                self.ui.func_code_combo.setCurrentText(func_code)
                
            self.ui.start_addr_edit.setText(settings.value("modbus/start_addr", "0"))
            self.ui.reg_count_edit.setText(settings.value("modbus/reg_count", "1"))
            
            addr_format = settings.value("modbus/addr_format", "十进制")
            if self.ui.addr_format_combo.findText(addr_format) >= 0:
                self.ui.addr_format_combo.setCurrentText(addr_format)
                
            data_format = settings.value("modbus/data_format", "十进制")
            if self.ui.data_format_combo.findText(data_format) >= 0:
                self.ui.data_format_combo.setCurrentText(data_format)
            
            # 更新功能码对应的UI状态
            self.on_func_code_changed(self.ui.func_code_combo.currentText())
            
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.append_communication(f"[{timestamp}] [SYS] 配置已从 {self.config_file} 加载", "system")
            
        except Exception as e:
            # 加载配置失败时使用默认值，不显示错误消息
            print(f"加载配置失败: {str(e)}")
        
    def refresh_ports(self):
        """刷新可用串口列表"""
        import serial.tools.list_ports
        self.ui.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.ui.port_combo.addItem(port.device)
            
    def toggle_serial(self):
        """打开/关闭串口"""
        if self.serial_port and self.serial_port.is_open:
            self.close_serial()
        else:
            self.open_serial()
            
    def open_serial(self):
        """打开串口"""
        try:
            port = self.ui.port_combo.currentText()
            baudrate = int(self.ui.baud_combo.currentText())
            bytesize = int(self.ui.data_bits_combo.currentText())
            stopbits = float(self.ui.stop_bits_combo.currentText())
            
            parity_map = {"无": serial.PARITY_NONE, "偶校验": serial.PARITY_EVEN, "奇校验": serial.PARITY_ODD}
            parity = parity_map[self.ui.parity_combo.currentText()]
            
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                timeout=0.1
            )
            
            self.timer.start(50)  # 每50ms检查一次串口数据
            self.ui.open_btn.setText("关闭串口")
            self.append_communication(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [SYS] 串口已打开: {port}", "system")
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "错误", f"无法打开串口: {str(e)}")
            
    def close_serial(self):
        """关闭串口"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.timer.stop()
        self.ui.open_btn.setText("打开串口")
        self.append_communication(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [SYS] 串口已关闭", "system")
        
    def read_serial_data(self):
        """读取串口数据"""
        if self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    if data:
                        self.display_received_data(data)
            except Exception as e:
                self.append_communication(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [SYS] 读取错误: {str(e)}", "error")
                
    def display_received_data(self, data):
        """显示接收到的数据"""
        # 显示十六进制
        hex_str = ' '.join([f'{b:02X}' for b in data])
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # 精确到毫秒
        
        # 添加RX标记
        self.append_communication(f"[{timestamp}] [RX] {hex_str}", "received")
        
        # 尝试解析Modbus响应
        try:
            parsed = self.parse_modbus_response(data)
            if parsed:
                self.append_communication(f"[{timestamp}] [RX] 解析: {parsed}", "received")
        except Exception as e:
            self.append_communication(f"[{timestamp}] [RX] 解析错误: {str(e)}", "error")
            
    def append_communication(self, text, message_type="normal"):
        """在通信数据显示区域添加文本，支持高亮显示"""
        cursor = self.ui.communication_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # 设置文本格式
        format = QTextCharFormat()
        
        # 根据消息类型设置颜色
        if message_type == "system":
            format.setForeground(QColor(128, 128, 128))  # 灰色
        elif message_type == "sent":
            format.setForeground(QColor(0, 100, 0))  # 深绿色
            format.setFontWeight(QFont.Bold)
        elif message_type == "received":
            format.setForeground(QColor(0, 0, 150))  # 深蓝色
            format.setFontWeight(QFont.Bold)
        elif message_type == "error":
            format.setForeground(QColor(200, 0, 0))  # 红色
            format.setFontWeight(QFont.Bold)
        elif message_type == "custom":
            format.setForeground(QColor(128, 0, 128))  # 紫色
            format.setFontWeight(QFont.Bold)
        else:
            format.setForeground(QColor(0, 0, 0))  # 黑色
        
        # 插入文本
        cursor.insertText(text + "\n", format)
        
        # 自动滚动到底部
        cursor.movePosition(QTextCursor.End)
        self.ui.communication_text.setTextCursor(cursor)
    
    def append_separator(self):
        """在通信数据显示区域添加分割线"""
        # 获取当前文本
        current_text = self.ui.communication_text.toPlainText()
        
        # 如果最后一行不是分割线，则添加分割线
        if not current_text.endswith("─" * 80 + "\n"):
            cursor = self.ui.communication_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            
            # 设置分割线格式
            format = QTextCharFormat()
            format.setForeground(QColor(180, 180, 180))  # 浅灰色
            
            cursor.insertText("─" * 80 + "\n", format)
            
            # 自动滚动到底部
            cursor.movePosition(QTextCursor.End)
            self.ui.communication_text.setTextCursor(cursor)
        
    def clear_communication(self):
        """清空通信数据显示区域"""
        self.ui.communication_text.clear()
        
    def copy_communication(self):
        """复制通信数据内容到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.ui.communication_text.toPlainText())
        QMessageBox.information(self.main_window, "成功", "通信数据已复制到剪贴板")
        
    def on_func_code_changed(self, func_text):
        """功能码改变时的处理"""
        func_code = func_text.split(' ')[0]
        
        # 根据功能码显示/隐藏相应的输入控件
        if func_code in ['01', '02', '03', '04']:  # 读操作
            self.ui.single_value_edit.setVisible(False)
            self.ui.multi_value_edit.setVisible(False)
            self.ui.coil_on_radio.setVisible(False)
            self.ui.coil_off_radio.setVisible(False)
        elif func_code == '05':  # 写单个线圈
            self.ui.single_value_edit.setVisible(False)
            self.ui.multi_value_edit.setVisible(False)
            self.ui.coil_on_radio.setVisible(True)
            self.ui.coil_off_radio.setVisible(True)
        elif func_code == '06':  # 写单个寄存器
            self.ui.single_value_edit.setVisible(True)
            self.ui.multi_value_edit.setVisible(False)
            self.ui.coil_on_radio.setVisible(False)
            self.ui.coil_off_radio.setVisible(False)
        elif func_code in ['0F', '10']:  # 写多个
            self.ui.single_value_edit.setVisible(False)
            self.ui.multi_value_edit.setVisible(True)
            self.ui.coil_on_radio.setVisible(False)
            self.ui.coil_off_radio.setVisible(False)
            
    def build_modbus_frame(self):
        """构建Modbus帧"""
        try:
            # 获取基本参数
            slave_addr = int(self.ui.slave_addr_edit.text())
            func_code_str = self.ui.func_code_combo.currentText().split(' ')[0]
            func_code = int(func_code_str, 16)
            
            # 获取地址和数量
            if self.ui.addr_format_combo.currentText() == "十进制":
                start_addr = int(self.ui.start_addr_edit.text())
            else:
                start_addr = int(self.ui.start_addr_edit.text(), 16)
                
            reg_count = int(self.ui.reg_count_edit.text())
            
            # 根据功能码生成报文
            if func_code in [1, 2, 3, 4]:  # 读操作
                pdu = self.build_read_pdu(func_code, start_addr, reg_count)
            elif func_code == 5:  # 写单个线圈
                coil_value = 0xFF00 if self.ui.coil_on_radio.isChecked() else 0x0000
                pdu = self.build_write_single_coil_pdu(start_addr, coil_value)
            elif func_code == 6:  # 写单个寄存器
                if self.ui.data_format_combo.currentText() == "十进制":
                    reg_value = int(self.ui.single_value_edit.text())
                else:
                    reg_value = int(self.ui.single_value_edit.text(), 16)
                pdu = self.build_write_single_register_pdu(start_addr, reg_value)
            elif func_code == 15:  # 写多个线圈
                values_str = self.ui.multi_value_edit.text()
                if self.ui.data_format_combo.currentText() == "十进制":
                    values = [int(v.strip()) for v in values_str.split(',')]
                else:
                    values = [int(v.strip(), 16) for v in values_str.split(',')]
                pdu = self.build_write_multiple_coils_pdu(start_addr, values)
            elif func_code == 16:  # 写多个寄存器
                values_str = self.ui.multi_value_edit.text()
                if self.ui.data_format_combo.currentText() == "十进制":
                    values = [int(v.strip()) for v in values_str.split(',')]
                else:
                    values = [int(v.strip(), 16) for v in values_str.split(',')]
                pdu = self.build_write_multiple_registers_pdu(start_addr, values)
            else:
                raise ValueError(f"不支持的功能码: {func_code}")
                
            # 添加从站地址和CRC
            frame = bytes([slave_addr]) + pdu
            crc = self.calculate_crc(frame)
            frame += crc
            
            return frame
            
        except Exception as e:
            raise e
            
    def generate_modbus_frame(self):
        """生成Modbus报文并显示"""
        try:
            frame = self.build_modbus_frame()
            
            # 显示报文
            hex_str = ' '.join([f'{b:02X}' for b in frame])
            
            # 获取当前时间戳
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # 精确到毫秒
            
            # 在通信数据显示区域添加生成的报文，使用[TX]标记
            self.append_communication(f"[{timestamp}] [TX] modbus报文 ({len(frame)}字节): {hex_str}", "sent")
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "错误", f"生成报文失败: {str(e)}")
            
    def send_modbus_request(self):
        """发送Modbus请求"""
        if not self.serial_port or not self.serial_port.is_open:
            QMessageBox.warning(self.main_window, "警告", "请先打开串口")
            return
            
        try:
            frame = self.build_modbus_frame()
            
            # 显示报文
            hex_str = ' '.join([f'{b:02X}' for b in frame])
            
            # 获取当前时间戳
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # 精确到毫秒
            
            # 使用[TX]标记发送的报文
            self.append_communication(f"[{timestamp}] [TX] {hex_str}", "sent")
            
            # 发送报文
            self.serial_port.write(frame)
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "错误", f"发送失败: {str(e)}")
            
    def build_read_pdu(self, func_code, start_addr, count):
        """构建读操作PDU"""
        return struct.pack('>BHH', func_code, start_addr, count)
    
    def build_write_single_coil_pdu(self, addr, value):
        """构建写单个线圈PDU"""
        return struct.pack('>BHH', 5, addr, value)
    
    def build_write_single_register_pdu(self, addr, value):
        """构建写单个寄存器PDU"""
        return struct.pack('>BHH', 6, addr, value)
    
    def build_write_multiple_coils_pdu(self, addr, values):
        """构建写多个线圈PDU"""
        # 将值转换为字节
        byte_count = (len(values) + 7) // 8
        bytes_data = 0
        for i, val in enumerate(values):
            if val:
                bytes_data |= (1 << i)
                
        data_bytes = bytes_data.to_bytes(byte_count, byteorder='big')
        return struct.pack('>BHHB', 15, addr, len(values), byte_count) + data_bytes
    
    def build_write_multiple_registers_pdu(self, addr, values):
        """构建写多个寄存器PDU"""
        byte_count = len(values) * 2
        data_bytes = b''
        for val in values:
            data_bytes += struct.pack('>H', val)
        return struct.pack('>BHHB', 16, addr, len(values), byte_count) + data_bytes
    
    def calculate_crc(self, data):
        """计算Modbus CRC校验"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc = crc >> 1
        return struct.pack('<H', crc)
    
    def parse_modbus_response(self, data):
        """解析Modbus响应"""
        if len(data) < 3:  # 最小响应长度
            return None
            
        slave_addr = data[0]
        func_code = data[1]
        
        # 检查异常响应
        if func_code & 0x80:
            exception_code = data[2]
            return f"异常响应: 从站{slave_addr}, 异常码{exception_code}"
        
        if func_code in [1, 2]:  # 读线圈/离散输入
            byte_count = data[2]
            coil_data = data[3:3+byte_count]
            coils = []
            for byte in coil_data:
                for i in range(8):
                    coils.append((byte >> i) & 1)
            return f"从站{slave_addr}: 线圈状态 {coils[:byte_count*8]}"
        
        elif func_code in [3, 4]:  # 读寄存器
            byte_count = data[2]
            reg_data = data[3:3+byte_count]
            registers = []
            for i in range(0, byte_count, 2):
                registers.append(struct.unpack('>H', reg_data[i:i+2])[0])
            return f"从站{slave_addr}: 寄存器值 {registers}"
        
        elif func_code in [5, 6]:  # 写单个
            addr = struct.unpack('>H', data[2:4])[0]
            value = struct.unpack('>H', data[4:6])[0]
            return f"从站{slave_addr}: 地址{addr}写入成功, 值={value}"
        
        elif func_code in [15, 16]:  # 写多个
            addr = struct.unpack('>H', data[2:4])[0]
            count = struct.unpack('>H', data[4:6])[0]
            return f"从站{slave_addr}: 从地址{addr}开始写入{count}个数据成功"
        
        return None

    def generate_custom_frame(self):
        """生成带固定报文头和尾的自定义Modbus报文"""
        try:
            # 首先构建标准的Modbus帧
            standard_frame = self.build_modbus_frame()
            
            # 去掉标准帧的CRC（最后2字节）
            frame_without_crc = standard_frame[:-2]
            
            # 构建新帧的数据部分
            frame_length = len(frame_without_crc)
            data_for_crc = struct.pack('>H', frame_length) + frame_without_crc
            
            # 获取功能码
            func_code_str = self.ui.func_code_combo.currentText().split(' ')[0]
            func_code = int(func_code_str, 16)
            
            # 构建固定头：如果是03命令，第三个字节改为0x11，否则使用0x12
            if func_code == 3:  # 03 - 读保持寄存器
                fixed_header = bytes([0x7F, 0x7F, 0x11, 0x19, 0xC6, 0xFD, 0x1A])
            else:
                fixed_header = bytes([0x7F, 0x7F, 0x12, 0x19, 0xC6, 0xFD, 0x1A])
            
            fixed_tail = bytes([0xF7, 0xF7])
            
            # 计算CRC：从第三个字节开始，到固定尾之前
            # 需要计算CRC的数据包括：固定头的后5字节 + 数据部分
            crc_data = fixed_header[2:] + data_for_crc  # 从第三个字节开始
            
            # 计算CRC
            new_crc = self.calculate_crc(crc_data)
            
            # 构建完整帧：固定头 + 数据部分 + 新CRC + 固定尾
            custom_frame = fixed_header + data_for_crc + new_crc + fixed_tail
            
            # 显示报文
            hex_str = ' '.join([f'{b:02X}' for b in custom_frame])
            
            # 获取当前时间戳
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # 在通信数据显示区域添加生成的报文，使用紫色高亮显示
            self.append_communication(f"[{timestamp}] [TX] 自定义报文 ({len(custom_frame)}字节): {hex_str}", "custom")
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "错误", f"生成自定义报文失败: {str(e)}")

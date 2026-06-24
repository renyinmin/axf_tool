import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QButtonGroup
from PyQt5.QtCore import Qt
from ui_main_window import Ui_MainWindow
from modbus_logic import ModbusLogic

class MainApplication(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        # 初始化Modbus逻辑
        self.modbus_logic = ModbusLogic(self, self)
        
        # 初始化转换器工具
        self.setup_converter()
        
        # 连接菜单信号
        self.setup_connections()
        
    def setup_converter(self):
        """设置转换器工具"""
        # 创建按钮组
        self.from_button_group = QButtonGroup()
        self.to_button_group = QButtonGroup()
        
        # 进制按钮
        from_bases = ["2进制", "4进制", "8进制", "10进制", "16进制", "32进制"]
        to_bases = ["2进制", "4进制", "8进制", "10进制", "16进制", "32进制"]
        
        # 添加从进制按钮
        for i, base in enumerate(from_bases):
            button = self.create_tool_button(base)
            self.from_buttons_layout.addWidget(button)
            self.from_button_group.addButton(button, i)
            if base == "10进制":
                button.setChecked(True)
        
        # 添加到进制按钮
        for i, base in enumerate(to_bases):
            button = self.create_tool_button(base)
            self.to_buttons_layout.addWidget(button)
            self.to_button_group.addButton(button, i)
            if base == "16进制":
                button.setChecked(True)
        
        # 连接转换器信号
        self.convert_button.clicked.connect(self.convert_radix)
        self.to_hex_button.clicked.connect(self.decimal_to_hex)
        self.to_decimal_button.clicked.connect(self.hex_to_decimal)
    
    def create_tool_button(self, text):
        """创建工具按钮"""
        from PyQt5.QtWidgets import QPushButton
        button = QPushButton(text)
        button.setCheckable(True)
        button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #2c3e50;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        return button
    
    def setup_connections(self):
        """连接信号"""
        self.actionModbus.triggered.connect(self.show_modbus_tool)
        self.actionConverter.triggered.connect(self.show_converter_tool)
        self.actionAbout.triggered.connect(self.show_about)
    
    def show_modbus_tool(self):
        """显示Modbus工具"""
        self.stackedWidget.setCurrentIndex(0)
        self.setWindowTitle("工具集 - Modbus串口工具")
    
    def show_converter_tool(self):
        """显示进制转换器"""
        self.stackedWidget.setCurrentIndex(1)
        self.setWindowTitle("工具集 - 进制转换器")
    
    def show_about(self):
        """显示关于信息"""
        QMessageBox.about(self, "关于", 
                         "工具集 v1.0\n\n"
                         "包含以下工具：\n"
                         "- Modbus串口调试工具\n"
                         "- 进制与IEEE 754浮点数转换工具\n\n"
                         "使用菜单切换不同工具。")
    
    # 转换器功能方法
    def get_selected_base(self, button_group):
        """获取选中的进制"""
        checked_button = button_group.checkedButton()
        if checked_button:
            bases = [2, 4, 8, 10, 16, 32]
            return bases[button_group.id(checked_button)]
        return 10
    
    def convert_radix(self):
        """进制转换功能"""
        import struct
        
        number_input = self.radix_input.text().strip()
        
        if not number_input:
            QMessageBox.warning(self, "输入错误", "请输入要转换的数字")
            return
        
        from_base = self.get_selected_base(self.from_button_group)
        to_base = self.get_selected_base(self.to_button_group)
        
        try:
            decimal_value = int(number_input, from_base)
            result = self.convert_base(decimal_value, to_base)
            
            # 自动补零
            if to_base in [2, 4, 8, 16]:
                min_digits = {2: 8, 4: 4, 8: 3, 16: 2}.get(to_base, 0)
                while len(result) < min_digits:
                    result = '0' + result
            
            self.radix_result.setPlainText(result)
            
        except Exception as e:
            QMessageBox.critical(self, "转换错误", f"转换失败: {str(e)}")
    
    def convert_base(self, number, base):
        """将数字转换为指定进制"""
        if number == 0:
            return "0"
        
        digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        result = ""
        
        is_negative = number < 0
        number = abs(number)
        
        while number > 0:
            result = digits[number % base] + result
            number //= base
        
        return "-" + result if is_negative else result
    
    def decimal_to_hex(self):
        """IEEE 754 10进制转16进制"""
        import struct
        
        decimal_input = self.decimal_input.text().strip()
        
        if not decimal_input:
            QMessageBox.warning(self, "输入错误", "请输入10进制浮点数")
            return
        
        try:
            float_value = float(decimal_input)
            hex_bytes = struct.pack('>f', float_value)
            hex_result = ' '.join(f'{b:02X}' for b in hex_bytes)
            self.ieee_result.setPlainText(hex_result)
            
        except Exception as e:
            QMessageBox.critical(self, "转换错误", f"转换失败: {str(e)}")
    
    def hex_to_decimal(self):
        """IEEE 754 16进制转10进制"""
        import struct
        
        hex_input = self.hex_input.text().strip()
        
        if not hex_input:
            QMessageBox.warning(self, "输入错误", "请输入16进制浮点数")
            return
        
        try:
            clean_hex = hex_input.replace(' ', '')
            if len(clean_hex) != 8:
                QMessageBox.critical(self, "输入错误", "16进制数必须是8位（4字节）")
                return
            
            hex_bytes = bytes.fromhex(clean_hex)
            float_value = struct.unpack('>f', hex_bytes)[0]
            self.ieee_result.setPlainText(str(float_value))
            
        except Exception as e:
            QMessageBox.critical(self, "转换错误", f"转换失败: {str(e)}")
    
    def closeEvent(self, event):
        """重写关闭事件"""
        self.modbus_logic.save_config()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MainApplication()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

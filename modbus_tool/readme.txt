使用说明
保存UI文件：将上面的XML内容保存为 modbus_tool.ui

生成UI代码：运行 pyuic5 modbus_tool.ui -o ui_modbus_tool.py

创建其他文件：创建 modbus_logic.py 和 main.py

运行程序：运行 python main.py



# 基本打包
pyinstaller crc32.py

# 打包为单个文件
pyinstaller --onefile crc32.py

# 打包为单个文件，不显示控制台窗口（适合GUI程序）
pyinstaller --onefile --windowed crc32.py

# 添加图标
pyinstaller --onefile --icon=myicon.ico crc32.py

# 指定名称
pyinstaller --onefile --name "CRC32计算器" crc32.py
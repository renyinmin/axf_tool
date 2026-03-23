# AXF Tool - Modbus AXF Debug Tool

一个用于解析 AXF/ELF 文件并通过 Modbus RTU 协议读取嵌入式设备内存变量的工具。

## 功能特点

- 解析 AXF/ELF 文件中的符号表和 DWARF 调试信息
- 支持嵌套结构体成员地址计算
- 支持数组索引访问
- 通过 Modbus RTU 协议读取设备内存
- **Modbus 报文调试打印** - 显示发送和接收的原始报文
- 图形化用户界面，操作简单

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

1. 运行程序：
```bash
python main.py
```

2. 点击"浏览..."选择 AXF 文件（自动加载）

3. 输入变量路径，例如：
   - `g_single_invter.runInfo.product_type`
   - `g_meter_data[1].mCommNormal`
   - `Wilan4G_PowerCtrl.StartFlag`

4. 点击"获取地址"查看变量地址

5. 连接 Modbus 设备后可读取变量值

## Modbus 报文调试

读取变量时会在控制台和结果显示框中打印完整的 Modbus RTU 报文：

```
============================================================
读取内存地址: 0x240286C0
显示类型: hex
============================================================

[发送] 写寄存器 43507 (设置内存地址)
  报文: 01 10 A9 F3 00 02 04 24 02 86 C0 XX XX
  长度: 13 字节

[接收] 写寄存器响应
  报文: 01 10 A9 F3 00 02 XX XX
  长度: 8 字节

[发送] 读寄存器 43509 (读取内存数据)
  报文: 01 03 A9 F5 00 02 XX XX
  长度: 8 字节

[接收] 读寄存器响应 (数据: 0x1234 0x5678)
  报文: 01 03 04 12 34 56 78 XX XX
  长度: 9 字节

结果: 0x12345678
原始值: 0x12345678
```

### 寄存器地址

| 寄存器 | 地址 | 用途 |
|--------|------|------|
| 写寄存器 | 43507 | 设置要读取的内存地址（32位） |
| 读寄存器 | 43509-43510 | 读取内存数据（2个寄存器，32位） |

### 报文格式说明

| 功能码 | 名称 | 用途 |
|--------|------|------|
| 0x03 | 读保持寄存器 | 读取内存数据 |
| 0x10 | 写多个寄存器 | 设置内存地址、写入数据 |

## 命令行模式

```bash
# 解析AXF文件并列出所有变量
python main.py parse <axf文件> --list

# 搜索特定变量
python main.py parse <axf文件> --search g_single_invter

# 读取内存
python main.py read --port COM3 --address 0x20000000
```

## 支持的变量路径格式

- 简单变量：`variable_name`
- 结构体成员：`struct_name.member_name`
- 嵌套结构体：`struct_name.nested_member.leaf_member`
- 数组元素：`array_name[index]`
- 数组元素成员：`array_name[index].member_name`

## 支持的数据类型

| 类型 | 说明 |
|------|------|
| hex | 十六进制显示 |
| float | 单精度浮点数 |
| int32 | 有符号32位整数 |
| uint32 | 无符号32位整数 |
| int16 | 有符号16位整数 |
| uint16 | 无符号16位整数 |
| int8 | 有符号8位整数 |
| uint8 | 无符号8位整数 |

## 技术实现

- 使用 `pyelftools` 解析 ELF/DWARF 调试信息
- 正确处理 ULEB128 编码的 DWARF 表达式
- 支持 DW_FORM_ref2 等多种 DWARF 引用类型
- 自动跳过 typedef、const、volatile 等类型修饰符
- Modbus RTU CRC16 校验计算

## 项目结构

```
modbus_axf_tool/
├── main.py           # 主程序入口
├── gui_fixed.py      # GUI界面
├── axf_parser.py     # AXF/ELF文件解析
├── modbus_client.py  # Modbus通信客户端
├── requirements.txt  # 依赖列表
└── README.md         # 说明文档
```

## 许可证

MIT License

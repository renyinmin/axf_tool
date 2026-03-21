# AXF Tool - Modbus AXF Debug Tool

一个用于解析 AXF/ELF 文件并通过 Modbus RTU 协议读取嵌入式设备内存变量的工具。

## 功能特点

- 解析 AXF/ELF 文件中的符号表和 DWARF 调试信息
- 支持嵌套结构体成员地址计算
- 支持数组索引访问
- 通过 Modbus RTU 协议读取设备内存
- 图形化用户界面，操作简单

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

1. 运行 GUI 程序：
```bash
python gui_fixed.py
```

2. 点击"浏览..."选择 AXF 文件（自动加载）

3. 输入变量路径，例如：
   - `g_single_invter.runInfo.product_type`
   - `g_meter_data[1].mCommNormal`
   - `Wilan4G_PowerCtrl.StartFlag`

4. 点击"获取地址"查看变量地址

5. 连接 Modbus 设备后可读取变量值

## 支持的变量路径格式

- 简单变量：`variable_name`
- 结构体成员：`struct_name.member_name`
- 嵌套结构体：`struct_name.nested_member.leaf_member`
- 数组元素：`array_name[index]`
- 数组元素成员：`array_name[index].member_name`

## 技术实现

- 使用 `pyelftools` 解析 ELF/DWARF 调试信息
- 正确处理 ULEB128 编码的 DWARF 表达式
- 支持 DW_FORM_ref2 等多种 DWARF 引用类型
- 自动跳过 typedef、const、volatile 等类型修饰符

## 许可证

MIT License

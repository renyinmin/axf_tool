#!/usr/bin/env python3
import os
import re
from elftools.elf.elffile import ELFFile

class AXFParser:
    def __init__(self, axf_path: str):
        self.axf_path = axf_path
        self.symbols = {}
        self.dwarf_info = None
        self._load_file()

    def _load_file(self):
        if not os.path.exists(self.axf_path): return
        with open(self.axf_path, 'rb') as f:
            elffile = ELFFile(f)
            for section in elffile.iter_sections():
                if section.header['sh_type'] in ('SHT_SYMTAB', 'SHT_DYNSYM'):
                    for symbol in section.iter_symbols():
                        if symbol['st_info']['type'] == 'STT_OBJECT':
                            self.symbols[symbol.name] = symbol['st_value']
            if elffile.has_dwarf_info():
                self.dwarf_info = elffile.get_dwarf_info()

    def get_variable_address(self, variable_path: str):
        tokens = self._tokenize_path(variable_path)
        if not tokens:
            return None
            
        base_name = tokens[0]
        if base_name not in self.symbols: 
            return None
        
        current_addr = self.symbols[base_name]
        if len(tokens) == 1 or not self.dwarf_info:
            return current_addr

        return self._resolve_dwarf_path(base_name, tokens[1:], current_addr)

    def _tokenize_path(self, path):
        tokens = []
        i = 0
        current = ""
        
        while i < len(path):
            if path[i] == '.':
                if current:
                    tokens.append(current)
                    current = ""
                i += 1
            elif path[i] == '[':
                if current:
                    tokens.append(current)
                    current = ""
                j = i + 1
                while j < len(path) and path[j] != ']':
                    j += 1
                tokens.append(path[i:j+1])
                i = j + 1
            else:
                current += path[i]
                i += 1
        
        if current:
            tokens.append(current)
        
        return tokens

    def _resolve_dwarf_path(self, base_name, members, addr):
        var_die, var_cu = self._find_variable_die(base_name)
        if not var_die:
            print(f"[DEBUG] 未找到变量: {base_name}")
            return addr

        print(f"[DEBUG] 找到变量 {base_name}, 基地址: 0x{addr:08X}")

        current_die = var_die
        current_cu = var_cu

        for member_name in members:
            array_match = re.match(r'\[(\d+)\]', member_name)
            if array_match:
                index = int(array_match.group(1))
                type_die, type_cu = self._get_type_die(current_die, current_cu)
                if not type_die:
                    print(f"[DEBUG] 无法获取数组类型，停止解析")
                    return addr
                
                element_size = self._get_array_element_size(type_die, type_cu)
                offset = index * element_size
                addr += offset
                print(f"[DEBUG] 数组索引 [{index}], 元素大小: {element_size}, 偏移: {offset} (0x{offset:X}), 新地址: 0x{addr:08X}")
                
                current_die = type_die
                current_cu = type_cu
            else:
                type_die, type_cu = self._get_type_die(current_die, current_cu)
                if not type_die:
                    print(f"[DEBUG] 无法获取类型，停止解析")
                    return addr

                print(f"[DEBUG] 类型: {type_die.tag}")

                member_die = self._find_member_in_type(type_die, member_name)
                if not member_die:
                    print(f"[DEBUG] 未找到成员: {member_name}")
                    return addr

                offset = self._get_member_offset(member_die)
                addr += offset
                print(f"[DEBUG] 成员 '{member_name}' 偏移: {offset} (0x{offset:X}), 新地址: 0x{addr:08X}")

                current_die = member_die
                current_cu = type_cu

        return addr

    def _get_array_element_size(self, array_die, cu):
        """获取数组元素大小"""
        if array_die.tag != 'DW_TAG_array_type':
            return self._get_type_size(array_die)
        
        element_type_die, element_cu = self._get_type_die(array_die, cu)
        if not element_type_die:
            return 0
        
        return self._get_type_size(element_type_die)

    def _get_type_size(self, type_die):
        """获取类型大小"""
        if 'DW_AT_byte_size' in type_die.attributes:
            return type_die.attributes['DW_AT_byte_size'].value
        return 0

    def _find_variable_die(self, name):
        for cu in self.dwarf_info.iter_CUs():
            for die in cu.iter_DIEs():
                if die.tag == 'DW_TAG_variable':
                    die_name = die.attributes.get('DW_AT_name')
                    if die_name and die_name.value.decode(errors='ignore') == name:
                        return die, cu
        return None, None

    def _get_type_die(self, die, cu):
        if 'DW_AT_type' not in die.attributes:
            return None, None

        type_attr = die.attributes['DW_AT_type']
        type_offset = type_attr.value
        form = type_attr.form

        print(f"[DEBUG] _get_type_die: offset={type_offset}, form={form}")

        if form == 'DW_FORM_ref_addr':
            search_offset = type_offset
        else:
            search_offset = cu.cu_offset + type_offset

        for cu_iter in self.dwarf_info.iter_CUs():
            try:
                type_die = cu_iter.get_DIE_from_refaddr(search_offset)
                if type_die:
                    while type_die and type_die.tag in ('DW_TAG_typedef', 'DW_TAG_const_type', 'DW_TAG_volatile_type', 'DW_TAG_pointer_type'):
                        if 'DW_AT_type' not in type_die.attributes:
                            return type_die, cu_iter
                        next_attr = type_die.attributes['DW_AT_type']
                        next_offset = next_attr.value
                        next_form = next_attr.form
                        
                        if next_form == 'DW_FORM_ref_addr':
                            next_search = next_offset
                        else:
                            next_search = cu_iter.cu_offset + next_offset
                        
                        try:
                            type_die = cu_iter.get_DIE_from_refaddr(next_search)
                        except:
                            break
                    
                    return type_die, cu_iter
            except:
                continue

        return None, None

    def _find_member_in_type(self, type_die, member_name):
        try:
            for child in type_die.iter_children():
                if child.tag == 'DW_TAG_member':
                    name_attr = child.attributes.get('DW_AT_name')
                    if name_attr:
                        child_name = name_attr.value.decode(errors='ignore')
                        print(f"[DEBUG]   发现成员: {child_name}")
                        if child_name == member_name:
                            return child
        except Exception as e:
            print(f"[DEBUG] iter_children 错误: {e}")
        return None

    def _decode_uleb128(self, data):
        result = 0
        shift = 0
        for byte in data:
            result |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                break
            shift += 7
        return result

    def _get_member_offset(self, die):
        offset_attr = die.attributes.get('DW_AT_data_member_location')
        if not offset_attr:
            return 0
        
        val = offset_attr.value
        print(f"[DEBUG] offset_attr value: {val}")
        
        if isinstance(val, int):
            return val
        elif isinstance(val, (list, tuple)):
            if len(val) >= 2:
                if val[0] == 0x23 or val[0] == 35:
                    uleb_value = self._decode_uleb128(val[1:])
                    print(f"[DEBUG] ULEB128 解码值: {uleb_value}")
                    return uleb_value
            return 0
        else:
            try:
                return int(val)
            except:
                return 0

    def list_global_variables(self):
        return self.symbols

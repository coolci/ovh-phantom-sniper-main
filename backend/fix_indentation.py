#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
这个脚本用于修复app.py中的缩进错误
"""

def fix_indentation():
    # 读取文件
    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"读取了 {len(lines)} 行代码")
    
    # 修复第826-827行的缩进错误
    if len(lines) > 826:
        print(f"修复第826-827行的缩进错误")
        # 修复try语句后的缩进
        print(f"原始行826: {lines[826]}")
        lines[826] = '                try:\n'
        lines[827] = '                    if plan.get("addonFamilies") and isinstance(plan.get("addonFamilies"), list):\n'
        print(f"修改后行826: {lines[826]}")
    
    # 修复第847行附近的for循环缩进错误
    for i in range(845, 855):
        if i < len(lines) and 'bandwidth_options = []' in lines[i]:
            print(f"找到bandwidth_options定义在行 {i}")
            # 确保后面的for循环缩进正确
            if i + 1 < len(lines) and 'for family' in lines[i+1]:
                print(f"修复for循环缩进在行 {i+1}")
                print(f"原始行: {lines[i+1]}")
                lines[i+1] = '                            for family in plan.get("addonFamilies"):\n'
                print(f"修改后行: {lines[i+1]}")
    
    # 修复第894行附近的continue语句缩进错误
    for i in range(890, 900):
        if i < len(lines) and 'if not isinstance(addon_code, str):' in lines[i]:
            print(f"找到instanceof检查在行 {i}")
            # 确保continue语句缩进正确
            if i + 1 < len(lines) and 'continue' in lines[i+1]:
                print(f"修复continue缩进在行 {i+1}")
                print(f"原始行: {lines[i+1]}")
                lines[i+1] = '                                        continue\n'
                print(f"修改后行: {lines[i+1]}")
    
    # 写回文件
    with open('app.py.fixed', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("缩进修复完成，结果保存在 app.py.fixed")

if __name__ == "__main__":
    print("开始修复缩进错误...")
    fix_indentation()
    print("修复完成!") 
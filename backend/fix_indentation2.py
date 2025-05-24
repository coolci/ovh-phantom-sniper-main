#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
这个脚本用于修复app.py中的缩进错误，并直接写回原文件
"""

def fix_indentation():
    # 读取文件
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 修复第826-827行try语句的缩进
        content = content.replace(
            "                try:\nif plan.get(\"addonFamilies\") and isinstance(plan.get(\"addonFamilies\"), list):",
            "                try:\n                    if plan.get(\"addonFamilies\") and isinstance(plan.get(\"addonFamilies\"), list):"
        )
        
        # 修复for循环的缩进
        content = content.replace(
            "                            bandwidth_options = []\n                    for family in plan.get(\"addonFamilies\"):",
            "                            bandwidth_options = []\n                            for family in plan.get(\"addonFamilies\"):"
        )
        
        # 修复continue语句的缩进
        content = content.replace(
            "                                    if not isinstance(addon_code, str):\n                                continue",
            "                                    if not isinstance(addon_code, str):\n                                        continue"
        )
        
        # 修复第1237行左右的break语句缩进
        content = content.replace(
            "                            \n                            add_log(\"INFO\", f\"从文本中提取存储: {server_info['storage']} 给 {plan_code}\")\n                                break",
            "                            \n                            add_log(\"INFO\", f\"从文本中提取存储: {server_info['storage']} 给 {plan_code}\")\n                            break"
        )
        
        # 写回文件
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("成功修复了app.py中的缩进错误")
        return True
    except Exception as e:
        print(f"修复过程中出错: {str(e)}")
        return False

if __name__ == "__main__":
    print("开始修复app.py中的缩进错误...")
    success = fix_indentation()
    if success:
        print("修复完成！你现在可以运行app.py了")
    else:
        print("修复失败，请手动检查和修复代码") 
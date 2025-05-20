# Windows系统下Python运行环境配置说明

## PowerShell执行策略修改
如果遇到"因为在此系统上禁止运行脚本"的错误，请使用以下命令：

### 临时修改（仅当前会话有效）
```
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

### 用户级别修改（推荐）
```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 系统级别修改（需要管理员权限）
```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
```

## Python虚拟环境操作

### 创建虚拟环境
```
python -m venv venv
```

### 激活虚拟环境
在命令提示符(CMD)中：
```
venv\Scripts\activate.bat
```

在PowerShell中：
```
.\venv\Scripts\Activate.ps1
```

### 退出虚拟环境
```
deactivate
```

### 安装项目依赖
激活虚拟环境后，运行：
```
pip install -r requirements.txt
```

## 启动后端
激活虚拟环境后，进入后端目录，运行：
```
python app.py
```

虚拟环境激活成功后，命令行前面会显示(venv)标识。

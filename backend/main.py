import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
import traceback

import ovh
import requests
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException, Depends, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from contextlib import asynccontextmanager

# Helper function to parse FQN (simple version) - Moved to top
def parse_fqn(fqn: str) -> Dict[str, Optional[str]]:
    parts = fqn.split('.')
    result = {"planCode": None, "memory": None, "storage": None}
    if len(parts) > 0: result["planCode"] = parts[0]
    if len(parts) > 1: result["memory"] = parts[1]
    if len(parts) > 2: result["storage"] = parts[2]
    # Add more parsing logic if FQN format is more complex
    return result

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ovh_sniper.log"),
    ],
)

logger = logging.getLogger("ovh-sniper")

# 创建API通信日志处理器
# 确保logs目录存在
os.makedirs("logs", exist_ok=True)
api_logger = logging.getLogger("ovh-api-communication")
api_logger.setLevel(logging.DEBUG)
api_handler = logging.FileHandler("logs/api_communication.log")
api_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
api_logger.addHandler(api_handler)
api_logger.propagate = False  # 防止API日志也输出到主日志中

# 为每个任务创建单独的日志处理函数
def get_task_logger(task_id):
    """为特定任务创建或获取日志记录器"""
    if not task_id:
        return api_logger
        
    # 确保任务日志目录存在
    task_log_dir = os.path.join("logs", "tasks")
    os.makedirs(task_log_dir, exist_ok=True)
    
    # 获取任务特定的记录器
    task_logger = logging.getLogger(f"task-{task_id}")
    
    # 如果已经配置过处理器，直接返回
    if task_logger.handlers:
        return task_logger
        
    # 配置新的记录器
    task_logger.setLevel(logging.DEBUG)
    log_file = os.path.join(task_log_dir, f"{task_id}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    task_logger.addHandler(file_handler)
    task_logger.propagate = False  # 防止日志重复输出
    
    return task_logger

# 配置设置
class Settings(BaseSettings):
    APP_KEY: str = ""
    APP_SECRET: str = ""
    CONSUMER_KEY: str = ""
    ENDPOINT: str = "ovh-eu"
    TG_TOKEN: str = ""
    TG_CHAT_ID: str = ""
    IAM: str = "go-ovh-ie"
    ZONE: str = "IE"
    TARGET_OS: str = "none_64.en"
    TARGET_DURATION: str = "P1M"
    TASK_INTERVAL: int = 60  # 单位：秒

    class Config:
        env_file = ".env"

settings = Settings()

# 自定义OVH客户端类，用于记录API通信
class LoggingOVHClient(ovh.Client):
    def __init__(self, *args, **kwargs):
        self.task_id = kwargs.pop('task_id', None)  # 提取并移除task_id
        super().__init__(*args, **kwargs)
        # 获取适当的日志记录器
        self.logger = get_task_logger(self.task_id)
    
    # 重写OVH客户端的call方法，使用与原始库相同的方法签名
    def call(self, method, path, data=None, need_auth=True):
        """
        重写原始客户端的call方法，添加日志记录功能
        :param method: HTTP方法 (GET, POST, PUT, DELETE)
        :param path: API路径
        :param data: 请求数据（对于POST和PUT）
        :param need_auth: 是否需要身份验证
        :return: API响应
        """
        request_id = str(uuid.uuid4())[:8]
        task_prefix = f"[任务: {self.task_id}]" if self.task_id else ""
        
        # 记录请求信息
        self.logger.info(f"{task_prefix} 请求 {request_id}: {method} {path}")
        if data:
            # 隐藏可能的敏感信息
            safe_data = self._sanitize_params(data) if isinstance(data, dict) else data
            data_str = json.dumps(safe_data, ensure_ascii=False) if isinstance(safe_data, dict) else str(safe_data)
            self.logger.info(f"{task_prefix} 请求 {request_id} 数据: {data_str}")
        
        try:
            # 调用原始方法
            start_time = time.time()
            result = super().call(method, path, data, need_auth)
            end_time = time.time()
            
            # 记录响应信息
            duration = round((end_time - start_time) * 1000)
            self.logger.info(f"{task_prefix} 响应 {request_id}: 耗时 {duration}ms")
            
            # 尝试记录响应内容，但要避免记录过大的响应
            if result:
                # 同时记录到主日志和任务特定日志
                api_logger.info(f"{task_prefix} 响应概要 {request_id}: OVH成功返回数据")
                
                # 详细内容记录到任务特定日志
                result_str = str(result)
                if len(result_str) > 5000:  # 对于非常大的响应，只记录概要
                    result_summary = f"{result_str[:4997]}... (总长度: {len(result_str)}字节)"
                    self.logger.info(f"{task_prefix} 响应 {request_id} 内容(截断): {result_summary}")
                else:
                    self.logger.info(f"{task_prefix} 响应 {request_id} 内容: {result_str}")
            
            return result
        except Exception as e:
            # 记录错误信息
            error_message = f"{task_prefix} 请求 {request_id} 失败: {str(e)}"
            self.logger.error(error_message)
            api_logger.error(error_message)  # 同时记录到主日志
            
            error_details = f"{task_prefix} 错误详情: {traceback.format_exc()}"
            self.logger.error(error_details)
            api_logger.error(error_details)  # 同时记录到主日志
            raise
    
    def _sanitize_params(self, params):
        """去除参数中可能的敏感信息"""
        if not isinstance(params, dict):
            return params
            
        safe_params = params.copy()
        sensitive_keys = ['password', 'token', 'secret', 'key']
        
        for k, v in safe_params.items():
            if any(sensitive in k.lower() for sensitive in sensitive_keys) and v:
                safe_params[k] = "******"
        
        return safe_params

# 数据模型
class ServerAvailability(BaseModel):
    fqn: str
    planCode: str
    datacenters: List[Dict[str, str]]

class ApiConfig(BaseModel):
    appKey: str
    appSecret: str
    consumerKey: str
    endpoint: str = "ovh-eu"
    zone: str = "IE"
    iam: str = "go-ovh-ie"
    tgToken: Optional[str] = None
    tgChatId: Optional[str] = None
    
    def update_api_part(self, api_part: Dict[str, Any]):
        """只更新API相关的配置部分"""
        for key in ["appKey", "appSecret", "consumerKey", "endpoint", "zone", "iam"]:
            if key in api_part:
                setattr(self, key, api_part[key])
        return self
    
    def update_telegram_part(self, tg_part: Dict[str, Any]):
        """只更新Telegram相关的配置部分"""
        for key in ["tgToken", "tgChatId"]:
            if key in tg_part:
                setattr(self, key, tg_part[key])
        return self

class AddonOption(BaseModel):
    label: str    # 选项类别，如"memory", "storage"等
    value: str    # 选项值，如"ram64", "ssd500"等
    price: Optional[str] = None
    description: Optional[str] = None

class ServerConfig(BaseModel):
    planCode: str
    datacenter: str
    quantity: int = 1
    os: str = "none_64.en"
    duration: str = "P1M"
    options: List[AddonOption] = []
    name: str
    maxRetries: int = -1  # -1表示无限重试
    taskInterval: int = 60  # 默认60秒检查一次

class OrderHistory(BaseModel):
    id: str
    planCode: str
    name: str
    datacenter: str
    orderTime: str
    status: str
    orderId: Optional[str] = None
    orderUrl: Optional[str] = None
    error: Optional[str] = None

class TaskStatus(BaseModel):
    id: str
    name: str
    planCode: str
    datacenter: str
    status: str
    createdAt: str
    lastChecked: Optional[str] = None
    retryCount: int = 0
    maxRetries: int = -1
    nextRetryAt: Optional[str] = None
    message: Optional[str] = None
    taskInterval: int = 60  # 添加任务间隔属性，默认60秒
    options: List[AddonOption] = []  # 添加选项字段，保存用户选择的配置

# 添加配置持久化
CONFIG_FILE = "config.json"

# 添加订单历史持久化功能
ORDERS_FILE = "orders.json"

# 添加任务持久化功能
TASKS_FILE = "tasks.json"

# 添加全局字典，用于记录各服务器型号的问题参数
# server_problem_params = {}
# 记录服务器型号尝试次数的字典
# server_attempt_counts = {}
# 最大尝试次数，超过这个次数就使用完全默认配置
# MAX_PARAM_ATTEMPTS = 3

# 添加特定参数类型的初始列表，帮助系统更好地识别和分类参数
# COMMON_PARAM_TYPES = {
#     "memory": ["ram", "memory"],
#     "storage": ["storage", "disk", "hdd", "ssd", "raid", "noraid"],
#     "bandwidth": ["bandwidth", "traffic", "network"]
# }

# 保存配置到文件
def save_config_to_file():
    global api_config
    if api_config:
        try:
            with open(CONFIG_FILE, "w") as f:
                # 转换为字典并保存
                config_dict = api_config.dict()
                # 记录日志，但不包含敏感信息
                log_dict = config_dict.copy()
                for key in ["appKey", "appSecret", "consumerKey", "tgToken"]:
                    if log_dict.get(key):
                        log_dict[key] = "******"
                
                add_log("info", f"保存配置到文件: {log_dict}")
                # 特别记录Telegram相关字段
                add_log("info", f"Telegram配置状态: tgToken={'已设置' if config_dict.get('tgToken') else '未设置'}, " 
                      f"tgChatId={config_dict.get('tgChatId') or '未设置'}")
                
                json.dump(config_dict, f)
            add_log("info", f"API配置已保存到文件 {CONFIG_FILE}")
            
            # 验证文件是否成功保存
            if os.path.exists(CONFIG_FILE):
                file_size = os.path.getsize(CONFIG_FILE)
                add_log("info", f"配置文件存在，大小: {file_size} 字节")
                
                # 尝试读取回来验证内容
                try:
                    with open(CONFIG_FILE, "r") as check_f:
                        saved_config = json.load(check_f)
                        # 验证Telegram相关字段
                        tg_token_saved = bool(saved_config.get("tgToken"))
                        tg_chat_id_saved = bool(saved_config.get("tgChatId"))
                        add_log("info", f"配置验证: tgToken已保存: {tg_token_saved}, tgChatId已保存: {tg_chat_id_saved}")
                except Exception as read_error:
                    add_log("error", f"读取已保存配置进行验证时出错: {str(read_error)}")
            else:
                add_log("error", f"配置文件保存后未找到: {CONFIG_FILE}")
        except Exception as e:
            add_log("error", f"保存API配置到文件失败: {str(e)}")
            add_log("error", f"错误详情: {traceback.format_exc()}")

# 从文件加载配置
def load_config_from_file():
    global api_config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config_dict = json.load(f)
                api_config = ApiConfig(**config_dict)
            add_log("info", f"已从文件 {CONFIG_FILE} 加载API配置")
        except Exception as e:
            add_log("error", f"从文件加载API配置失败: {str(e)}")

# 保存订单到文件
def save_orders_to_file():
    global orders
    try:
        with open(ORDERS_FILE, "w") as f:
            # 将订单列表转换为可序列化的字典列表
            serializable_orders = [order.dict() for order in orders]
            json.dump(serializable_orders, f)
        add_log("info", f"订单历史已保存到文件 {ORDERS_FILE}")
    except Exception as e:
        add_log("error", f"保存订单历史到文件失败: {str(e)}")

# 从文件加载订单
def load_orders_from_file():
    global orders
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r") as f:
                orders_data = json.load(f)
                orders = [OrderHistory(**order_dict) for order_dict in orders_data]
            add_log("info", f"已从文件 {ORDERS_FILE} 加载 {len(orders)} 条订单历史")
        except Exception as e:
            add_log("error", f"从文件加载订单历史失败: {str(e)}")

# 保存任务到文件
def save_tasks_to_file():
    global tasks
    try:
        with open(TASKS_FILE, "w") as f:
            # 将任务字典转换为可序列化的字典列表
            serializable_tasks = [task.dict() for task in tasks.values()]
            json.dump(serializable_tasks, f)
        add_log("debug", f"任务已保存到文件 {TASKS_FILE}，共 {len(tasks)} 条")
    except Exception as e:
        add_log("error", f"保存任务到文件失败: {str(e)}")

# 从文件加载任务
def load_tasks_from_file():
    global tasks
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, "r") as f:
                tasks_data = json.load(f)
                # 将列表转换为以任务ID为键的字典
                tasks = {task_dict["id"]: TaskStatus(**task_dict) for task_dict in tasks_data}
            add_log("info", f"已从文件 {TASKS_FILE} 加载 {len(tasks)} 条任务")
        except Exception as e:
            add_log("error", f"从文件加载任务失败: {str(e)}")

# 向订单列表添加新订单并持久化
def add_order(order: OrderHistory):
    global orders
    
    # 检查是否已有相同planCode和datacenter的订单
    for i, existing_order in enumerate(orders):
        if (existing_order.planCode == order.planCode and 
            existing_order.datacenter.lower() == order.datacenter.lower() and
            existing_order.status == order.status):
            # 替换现有订单
            orders[i] = order
            save_orders_to_file()
            add_log("info", f"已更新现有订单记录: {order.id} (替换 {existing_order.id})")
            return
    
    # 如果没有找到匹配的订单，添加新记录
    orders.append(order)
    # 添加后立即保存到文件
    save_orders_to_file()
    add_log("info", f"新订单已添加到历史记录并保存: {order.id}")

# **** 重新加入 task_execution_loop 函数定义 ****
async def task_execution_loop():
    while True:
        now = datetime.now().timestamp()
        
        # 检查所有待处理任务
        active_tasks = list(tasks.items()) # 创建副本以安全迭代
        if not active_tasks:
            # add_log("debug", "任务执行循环：当前无活动任务")
            pass # 避免在没有任务时频繁记录日志
            
        for task_id, task in active_tasks:
            if task.status not in ["pending", "error"]:
                continue
            
            # 如果达到最大重试次数，跳过
            # maxRetries <= 0 表示无限重试
            if task.maxRetries > 0 and task.retryCount >= task.maxRetries:
                if task.status != "max_retries_reached": # 避免重复记录日志
                    add_log("info", f"任务 {task_id} ({task.name}) 达到最大重试次数 ({task.maxRetries})，停止重试")
                    update_task_status(task_id, "max_retries_reached", f"达到最大重试次数 ({task.maxRetries})")
                continue
            
            # 检查是否到达下次重试时间
            next_retry_time = datetime.fromisoformat(task.nextRetryAt) if task.nextRetryAt else datetime.now()
            time_until_retry = next_retry_time.timestamp() - now
            
            if now < next_retry_time.timestamp():
                 # 只在调试时记录等待状态的日志，避免日志过多
                 # if task.retryCount > 0 and time_until_retry < 60: 
                 #     add_log("debug", f"任务 {task_id} ({task.name}) 将在 {int(time_until_retry)} 秒后进行第 {task.retryCount + 1} 次尝试")
                 continue
            
            # 增加重试计数 (放在实际执行前)
            task.retryCount += 1
            # 更新状态为 'running' 并重置消息
            update_task_status(task_id, "running", f"开始第 {task.retryCount} 次尝试...")
            
            if task.maxRetries <= 0:
                # 仅在前10次重试或重试次数是10的倍数时记录日志，减少日志量
                if task.retryCount <= 10 or task.retryCount % 10 == 0:
                    add_log("info", f"开始第 {task.retryCount} 次尝试任务 {task_id} ({task.name})（无限重试模式），间隔时间为 {task.taskInterval} 秒")
            else:
                add_log("info", f"开始第 {task.retryCount}/{task.maxRetries} 次尝试任务 {task_id} ({task.name})，间隔时间为 {task.taskInterval} 秒")
            
            # 创建服务器配置
            server_config = ServerConfig(
                planCode=task.planCode,
                datacenter=task.datacenter,
                name=task.name,
                maxRetries=task.maxRetries,
                taskInterval=task.taskInterval,
                options=task.options # 恢复选项信息
            )
            
            # 执行订购 (后台执行，不阻塞循环)
            try:
                add_log("debug", f"在后台为任务 {task_id} 创建 order_server 协程")
                asyncio.create_task(order_server(task_id, server_config))
                # 注意：这里启动后并不等待结果，order_server 内部会更新任务状态
            except Exception as e:
                error_msg = f"启动任务 {task_id} (尝试 {task.retryCount}) 失败: {str(e)}"
                add_log("error", error_msg)
                # 启动失败，将任务状态设置回 pending 或 error，以便下次重试
                update_task_status(task_id, "error", error_msg)
        
        # 等待下一个检查周期
        await asyncio.sleep(5)  # 每5秒检查一次任务状态

# 添加心跳检测和连接状态报告机制

# 每隔一段时间广播连接状态
async def broadcast_connection_status():
    """定期广播服务器状态，确保所有前端组件同步"""
    while True:
        try:
            if connections:  # 只有在有连接时才广播
                await broadcast_message({
                    "type": "connection_status",
                    "data": {
                        "is_connected": True,
                        "active_connections": len(connections),
                        "timestamp": datetime.now().isoformat()
                    }
                })
            await asyncio.sleep(5)  # 每5秒广播一次状态
        except Exception as e:
            add_log("error", f"广播连接状态时出错: {str(e)}")
            await asyncio.sleep(5)  # 出错时等待5秒后重试

# 在lifespan中启动状态广播
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件
    # 加载配置和订单历史
    load_config_from_file()
    load_orders_from_file()
    load_tasks_from_file()  # 加载保存的任务
    
    # 启动任务执行循环和状态广播
    asyncio.create_task(task_execution_loop())
    asyncio.create_task(broadcast_connection_status())  # 添加状态广播
    
    add_log("info", "OVH Titan Sniper 后端已启动")
    yield
    # 关闭事件
    # 保存配置和订单历史
    save_config_to_file()
    save_orders_to_file()
    save_tasks_to_file()  # 保存任务
    
    add_log("info", "OVH Titan Sniper 后端已关闭，所有数据已保存")

# 创建应用
app = FastAPI(title="OVH Titan Sniper API", lifespan=lifespan)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化状态变量
api_config: Optional[ApiConfig] = None
tasks: Dict[str, TaskStatus] = {}
orders: List[OrderHistory] = []
connections: List[WebSocket] = []
logs: List[Dict[str, str]] = []

# OVH客户端实例
ovh_client = None

# WebSocket连接管理
async def broadcast_message(message: Dict[str, Any]):
    """广播消息给所有WebSocket连接"""
    # 只为非日志消息和非心跳消息记录广播信息
    if message['type'] not in ['log', 'ping', 'pong']:
        add_log("debug", f"广播消息: type={message['type']}")
    
    global connections  # 确保我们使用全局连接列表
    disconnected = []
    
    # 在开始前先检查连接是否有效
    for i, websocket in enumerate(connections):
        try:
            # 检查连接是否打开
            if websocket.client_state != 1:  # CONNECTED状态
                add_log("debug", f"连接 {i} 已关闭，标记为断开")
                disconnected.append(websocket)
                continue
                
            await websocket.send_json(message)
            # 取消每次发送的成功日志，减少日志数量
        except WebSocketDisconnect:
            add_log("warning", f"广播消息时发现断开的连接 (索引 {i})")
            disconnected.append(websocket)
        except Exception as e:
            add_log("error", f"广播消息失败 (索引 {i}): {str(e)}")
            # 任何错误都表示连接可能有问题，添加到断开列表
            disconnected.append(websocket)
    
    # 移除已断开的连接
    if disconnected:
        connections = [conn for conn in connections if conn not in disconnected]
        add_log("info", f"已清理 {len(disconnected)} 个断开的WebSocket连接，剩余 {len(connections)} 个活动连接")

def add_log(level: str, message: str):
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "level": level,
        "message": message
    }
    logs.append(log_entry)
    
    # 保持日志数量在合理范围内
    if len(logs) > 1000:
        logs.pop(0)
    
    # 将日志广播给所有连接的客户端
    asyncio.create_task(broadcast_message({
        "type": "log",
        "data": log_entry
    }))

# 初始化OVH客户端
def get_ovh_client(task_id=None):
    global api_config, ovh_client
    
    if not api_config:
        raise HTTPException(status_code=400, detail="API配置未设置，请先配置API")
    
    if not ovh_client:
        try:
            ovh_client = LoggingOVHClient(
                endpoint=api_config.endpoint,
                application_key=api_config.appKey,
                application_secret=api_config.appSecret,
                consumer_key=api_config.consumerKey,
                task_id=task_id
            )
            add_log("info", "OVH客户端初始化成功")
        except Exception as e:
            add_log("error", f"初始化OVH客户端失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"初始化OVH客户端失败: {str(e)}")
    
    return ovh_client

# 发送Telegram消息
def send_telegram_msg(message: str):
    if not api_config:
        add_log("warning", "Telegram消息未发送: API配置不存在")
        return False
    
    # 检查Telegram配置是否完整
    if not api_config.tgToken:
        add_log("warning", "Telegram消息未发送: Bot Token未设置")
        return False
    
    if not api_config.tgChatId:
        add_log("warning", "Telegram消息未发送: Chat ID未设置")
        return False
    
    add_log("info", f"准备发送Telegram消息，ChatID: {api_config.tgChatId}, TokenLength: {len(api_config.tgToken)}")
    
    url = f"https://api.telegram.org/bot{api_config.tgToken}/sendMessage"
    payload = {
        "chat_id": api_config.tgChatId,
        "text": message
    }
    headers = {"Content-Type": "application/json"}

    try:
        add_log("info", f"发送HTTP请求到Telegram API: {url[:45]}...")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        add_log("info", f"Telegram API响应: 状态码={response.status_code}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                add_log("info", f"Telegram响应数据: {response_data}")
                add_log("info", "成功发送消息到Telegram")
                return True
            except Exception as json_error:
                add_log("error", f"解析Telegram响应JSON时出错: {str(json_error)}")
        else:
            add_log("error", f"发送消息到Telegram失败: 状态码={response.status_code}, 响应={response.text}")
            return False
    except requests.exceptions.Timeout:
        add_log("error", "发送Telegram消息超时")
        return False
    except requests.exceptions.RequestException as e:
        add_log("error", f"发送Telegram消息时发生网络错误: {str(e)}")
        return False
    except Exception as e:
        add_log("error", f"发送Telegram消息时发生未预期错误: {str(e)}")
        add_log("error", f"错误详情: {traceback.format_exc()}")
        return False

# 获取服务器列表
async def fetch_product_catalog(subsidiary: str = 'IE'):
    try:
        response = requests.get(
            f"https://eu.api.ovh.com/v1/order/catalog/public/eco?ovhSubsidiary={subsidiary}",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        add_log("error", f"获取产品目录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取产品目录失败: {str(e)}")

# 检查服务器可用性
async def check_availability(planCode: str, options=None, task_id=None):
    client = get_ovh_client(task_id)
    
    try:
        # 添加详细日志记录
        add_log("info", f"正在请求服务器 {planCode} 的可用性信息，配置选项: {options}")
        
        # 基本查询参数
        query_params = {"planCode": planCode}
        
        # 如果提供了选项，将其添加到OVH API请求中
        if options and len(options) > 0:
            # 将options添加到查询参数
            add_log("info", f"使用配置选项检查可用性: {options}")
            for option in options:
                family = option.label  # 直接访问属性而不是使用get方法
                value = option.value   # 直接访问属性而不是使用get方法
                if family and value:
                    # 添加到查询参数
                    query_params[f"option.{family}"] = value
        
        # 使用构建好的查询参数调用API - 确保使用关键字参数
        response = client.get('/dedicated/server/datacenter/availabilities', **query_params)
        
        # 记录完整响应的关键信息
        response_summary = f"响应类型: {type(response)}, 是否为列表: {isinstance(response, list)}, "
        if isinstance(response, list):
            response_summary += f"列表长度: {len(response)}"
            if len(response) > 0:
                first_item = response[0]
                response_summary += f", 第一项类型: {type(first_item)}"
                if isinstance(first_item, dict):
                    response_summary += f", 第一项键: {', '.join(first_item.keys())}"
        
        add_log("info", f"服务器 {planCode} 可用性API响应: {response_summary}")
        
        # 如果有数据中心信息，记录每个数据中心的状态
        if response and isinstance(response, list):
            if not response:
                add_log("warning", f"服务器 {planCode} 返回了空列表，没有可用性信息")
            else:
                add_log("info", f"获取到 {len(response)} 个可用性记录")
                
                for i, item in enumerate(response):
                    if isinstance(item, dict):
                        fqn = item.get("fqn", "未知")
                        datacenters = item.get("datacenters", [])
                        add_log("info", f"记录 #{i+1}: 服务器型号={fqn}, 包含 {len(datacenters)} 个数据中心")
                        
                        # 列出所有数据中心状态
                        if datacenters:
                            for j, dc in enumerate(datacenters):
                                dc_name = dc.get("datacenter", "未知")
                                dc_avail = dc.get("availability", "未知")
                                add_log("info", f"  - 数据中心 #{j+1}: {dc_name}, 可用性: {dc_avail}")
                        else:
                            add_log("warning", f"记录 #{i+1} 没有数据中心信息")
                    else:
                        add_log("warning", f"记录 #{i+1} 不是字典格式: {type(item)}")
        
        return response
    except Exception as e:
        add_log("error", f"检查服务器 {planCode} 可用性失败: {str(e)}")
        add_log("error", f"错误详情: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"检查可用性失败: {str(e)}")

# 添加一个调试端点，返回可用性数据的详细信息
@app.get("/api/debug/availability/{plan_code}")
async def debug_availability(plan_code: str):
    try:
        result = await check_availability(plan_code)
        # 返回详细信息，包括数据结构和类型
        return {
            "status": "success",
            "plan_code": plan_code,
            "result_type": str(type(result)),
            "is_list": isinstance(result, list),
            "length": len(result) if isinstance(result, list) else 0,
            "raw_data": result
        }
    except Exception as e:
        return {
            "status": "error",
            "plan_code": plan_code,
            "error": str(e)
        }

# 添加广播订单失败的函数
async def broadcast_order_failed(order: OrderHistory):
    """广播订单失败消息"""
    try:
        await broadcast_message({
            "type": "order_failed",
            "data": order.dict()
        })
        add_log("info", f"订单失败消息已广播: {order.id}")
    except Exception as e:
        add_log("error", f"广播订单失败消息失败: {str(e)}")

# 订购服务器 (采用 options 端点添加硬件)
async def order_server(task_id: str, config: ServerConfig):
    client = get_ovh_client(task_id)
    cart_id = None
    item_id = None # Store the base item ID
    task_logger = get_task_logger(task_id)
    
    task_logger.info(f"开始处理任务 {task_id} (使用 /eco/options 添加硬件)")
    task_logger.info(f"用户请求配置: planCode={config.planCode}, datacenter={config.datacenter}, OS={config.os}")
    wanted_options_values = {opt.value for opt in config.options if opt.value} # Set of wanted option values
    task_logger.info(f"用户请求选项值: {wanted_options_values}")

    update_task_status(task_id, "running", "检查服务器可用性...")
    
    # --- 可用性检查 (保持不变，只检查 planCode) ---
    available_dc = None
    found_available = False
    try:
        task_logger.info(f"正在检查计划代码 {config.planCode} 的可用性...")
        availabilities = await check_availability(config.planCode, None, task_id)
        if not availabilities:
            # ... (handle no availability) ...
            message = f"未找到计划代码 {config.planCode} 的可用性信息。"
            task_logger.info(message)
            update_task_status(task_id, "pending", message)
            return
        
        target_dc_upper = config.datacenter.upper() if config.datacenter else None
        task_logger.info(f"将在 {len(availabilities)} 个配置中查找 {target_dc_upper} 的可用性...")
        for item in availabilities:
            current_fqn = item.get("fqn") # Still useful for logging/notification
            datacenters = item.get("datacenters", [])
            for dc_info in datacenters:
                availability = dc_info.get("availability")
                datacenter_name = dc_info.get("datacenter")
                if datacenter_name and target_dc_upper and datacenter_name.upper() == target_dc_upper:
                    if availability not in ["unavailable", "unknown", None]:
                        found_available = True
                        available_dc = datacenter_name
                        task_logger.info(f"在数据中心 {available_dc} 找到基础 planCode {config.planCode} 可用 (FQN 可能不同: {current_fqn})!")
                        break
            if found_available: break
        
        if not found_available:
            # ... (handle not found in target DC) ...
            message = f"计划代码 {config.planCode} 在数据中心 {config.datacenter} 当前无可用服务器。"
            task_logger.info(message)
            update_task_status(task_id, "pending", message)
            return
            
        # --- 开始购买流程 --- 
        msg = f"{api_config.iam}: 在 {available_dc} 找到基础 {config.planCode} 可用，准备下单包含选项的订单..."
        # 注释掉这行，不在找到服务器可用时发送Telegram通知
        # send_telegram_msg(msg)
        # 仅记录日志
        task_logger.info(msg)
        
        # 1. 创建购物车
        update_task_status(task_id, "running", "创建购物车...")
        task_logger.info(f"为区域 {api_config.zone} 创建购物车...")
        cart_result = client.post('/order/cart', ovhSubsidiary=api_config.zone)
        cart_id = cart_result["cartId"]
        task_logger.info(f"购物车创建成功，ID: {cart_id}")
        
        # 2. 添加基础商品 (使用 /eco)
        update_task_status(task_id, "running", f"添加基础商品 {config.planCode}...")
        task_logger.info(f"将基础商品 {config.planCode} 添加到购物车 {cart_id} (使用 /eco)...")
        item_payload = {
            "planCode": config.planCode,
            "pricingMode": "default",
            "duration": config.duration,
            "quantity": config.quantity
        }
        item_result = client.post(f'/order/cart/{cart_id}/eco', **item_payload)
        item_id = item_result["itemId"]
        task_logger.info(f"基础商品添加成功，项目 ID: {item_id}")
        
        # 3. 设置必需配置 (DC, OS, Region 使用 /configuration)
        update_task_status(task_id, "running", f"设置项目 {item_id} 的必需配置...")
        task_logger.info(f"检查并设置项目 {item_id} 的必需配置...")
        required_configs = []
        try:
            required_configs = client.get(f'/order/cart/{cart_id}/item/{item_id}/requiredConfiguration')
            task_logger.info(f"获取到必需配置项: {json.dumps(required_configs, indent=2)}")
        except Exception as req_conf_error:
             task_logger.warning(f"获取必需配置项失败或无必需配置: {req_conf_error}")
             # Continue even if fetching required fails, core ones are set below

        configurations_to_set = {}
        # 推断 region...
        # ... (region inference logic remains the same)
        region_by_dc = None
        dc = available_dc.lower() if available_dc else None
        EU_DATACENTERS = ['gra', 'rbx', 'sbg', 'eri', 'lim', 'waw', 'par', 'fra', 'lon'] 
        CANADA_DATACENTERS = ['bhs', 'beauharnois']
        US_DATACENTERS = ['vin', 'hil', 'vint', 'hill']
        APAC_DATACENTERS = ['syd', 'sgp', 'mum']
        determined_region = None
        if dc:
            if any(dc.startswith(prefix) for prefix in EU_DATACENTERS): determined_region = "europe"
            elif any(dc.startswith(prefix) for prefix in CANADA_DATACENTERS): determined_region = "canada"
            elif any(dc.startswith(prefix) for prefix in US_DATACENTERS): determined_region = "usa"
            elif any(dc.startswith(prefix) for prefix in APAC_DATACENTERS): determined_region = "apac"
            if determined_region: task_logger.info(f"根据数据中心 {available_dc} 推断区域为 {determined_region}")
            else: task_logger.warning(f"无法根据数据中心 {available_dc} 推断区域")
        
        region_required = False
        region_label = "region"
        for conf in required_configs:
            label = conf.get("label")
            if label == "region":
                region_label = label
                region_required = conf.get("required", False)
                break
        
        # Set core mandatory configurations
        configurations_to_set["dedicated_datacenter"] = available_dc
        configurations_to_set["dedicated_os"] = config.os
        if determined_region:
            configurations_to_set[region_label] = determined_region
        elif region_required:
             task_logger.error(f"必需配置项 '{region_label}' 无法确定值，中止任务")
             raise Exception(f"无法确定必需的 {region_label} 配置")

        task_logger.info(f"准备使用 /configuration 设置必需配置: {json.dumps(configurations_to_set)}")
        for label, value in configurations_to_set.items():
            if value is None: continue
            try:
                task_logger.info(f"配置项目 {item_id}: 设置必需项 {label} = {value}")
                client.post(f'/order/cart/{cart_id}/item/{item_id}/configuration', label=label, value=str(value))
                task_logger.info(f"成功设置必需项: {label} = {value}")
            except ovh.exceptions.APIError as config_error:
                task_logger.error(f"设置必需项 {label} = {value} 失败: {config_error}")
                if label in ["dedicated_datacenter", region_label, "dedicated_os"]:
                     raise Exception(f"关键必需配置项 {label} 设置失败，中止购买。") from config_error
        
        # **** 4. 获取并添加硬件选项 (使用 /eco/options) ****
        update_task_status(task_id, "running", f"获取并添加硬件选项 (Eco)...")
        added_options_count = 0
        if wanted_options_values: # Only proceed if user requested options
            try:
                task_logger.info(f"获取购物车 {cart_id} 的可用 Eco 硬件选项 (针对 planCode={config.planCode})...")
                available_options = client.get(f'/order/cart/{cart_id}/eco/options', planCode=config.planCode)
                task_logger.info(f"找到 {len(available_options)} 个与基础商品 {config.planCode} 兼容的 Eco 硬件选项。")
                
                # task_logger.debug(f"可用 Eco 选项详情: {json.dumps(available_options)}") # Verbose

                options_added_plan_codes = set()
                # Ensure item_id is available before proceeding
                if not item_id:
                    raise Exception("无法添加选项，因为基础商品的 item_id 未知。")
                    
                task_logger.info(f"将使用基础项目 ID {item_id} 来添加选项。")

                for avail_opt in available_options:
                    avail_opt_plan_code = avail_opt.get("planCode")
                    if not avail_opt_plan_code:
                        continue
                    
                    # Check if this available option matches any wanted option
                    match_found = False
                    wanted_value_matched = None
                    for wanted_val in wanted_options_values:
                        if avail_opt_plan_code.startswith(wanted_val):
                            match_found = True
                            wanted_value_matched = wanted_val 
                            break
                    
                    if match_found and avail_opt_plan_code not in options_added_plan_codes:
                        task_logger.info(f"找到匹配的 Eco 选项: {avail_opt_plan_code} (匹配用户请求: {wanted_value_matched})，准备添加到购物车...")
                        try:
                            # ** Crucial: Add itemId to the payload for POST /eco/options **
                            option_payload = {
                                "itemId": item_id, # Link option to the base item
                                "planCode": avail_opt_plan_code, # Use the exact plan code from the API
                                "duration": avail_opt.get("duration", config.duration), # Use option's duration or fallback
                                "pricingMode": avail_opt.get("pricingMode", "default"),
                                "quantity": 1
                            }
                            task_logger.info(f"添加 Eco 选项 payload: {option_payload}")
                            # Use the POST /eco/options endpoint
                            client.post(f'/order/cart/{cart_id}/eco/options', **option_payload)
                            task_logger.info(f"成功添加 Eco 选项: {avail_opt_plan_code}")
                            options_added_plan_codes.add(avail_opt_plan_code)
                            added_options_count += 1
                        except ovh.exceptions.APIError as add_opt_error:
                             error_detail = str(add_opt_error)
                             task_logger.warning(f"添加 Eco 选项 {avail_opt_plan_code} 失败: {error_detail}")
                             if "Invalid parameters" in error_detail or "incompatible" in error_detail.lower():
                                 task_logger.warning(f"选项 {avail_opt_plan_code} 可能与基础商品 {item_id} 不兼容或参数无效。")
                        except Exception as general_add_opt_error:
                            task_logger.warning(f"添加 Eco 选项 {avail_opt_plan_code} 时发生未知错误: {general_add_opt_error}")
                
                # Check if all wanted options were added
                satisfied_options = {val for added_pc in options_added_plan_codes for val in wanted_options_values if added_pc.startswith(val)}
                missing_options = wanted_options_values - satisfied_options
                if missing_options:
                     task_logger.warning(f"未能找到或添加以下用户请求的 Eco 选项: {missing_options}")

            except ovh.exceptions.APIError as get_opts_error:
                task_logger.error(f"获取 Eco 硬件选项列表失败 (针对 planCode={config.planCode}): {get_opts_error}")
                task_logger.warning("无法获取 Eco 硬件选项列表，将继续尝试下单（可能只有基础配置）。")
            except Exception as e:
                 task_logger.error(f"处理 Eco 硬件选项时发生未知错误: {e}")
                 task_logger.warning("处理 Eco 硬件选项出错，将继续尝试下单（可能只有基础配置）。")
        else:
            task_logger.info("用户未请求硬件选项，跳过添加步骤。")
        
        # **** 5. 绑定购物车 (Assign Cart) - 移到所有项目和配置添加之后 ****
        update_task_status(task_id, "running", "绑定购物车...")
        task_logger.info(f"在添加完所有项目和选项后，绑定购物车 {cart_id}...")
        client.post(f'/order/cart/{cart_id}/assign')
        task_logger.info("购物车绑定成功")

        # 6. 获取结账信息
        update_task_status(task_id, "running", "准备结账...")
        task_logger.info(f"获取购物车 {cart_id} 的结账信息...")
        checkout_info = client.get(f'/order/cart/{cart_id}/checkout')
        task_logger.info(f"结账信息获取成功: {checkout_info}") # Log checkout info

        # 7. 执行结账
        task_logger.info(f"对购物车 {cart_id} 执行结账...")
        checkout_payload = {"autoPayWithPreferredPaymentMethod": False, "waiveRetractationPeriod": True}
        checkout_result = client.post(f'/order/cart/{cart_id}/checkout', **checkout_payload)
        task_logger.info("结账请求已提交！")
        
        # 8. 处理成功结果
        order_url = checkout_result.get("url", "N/A")
        order_id = checkout_result.get("orderId")
        task_logger.info(f"订单创建成功! 订单ID: {order_id}, 订单URL: {order_url}")
        
        now = datetime.now().isoformat()
        history_entry = OrderHistory(
            id=str(uuid.uuid4()), planCode=config.planCode, name=config.name,
            datacenter=available_dc, # 使用 API 返回的 DC
            orderTime=now, status="success",
            orderId=safe_str(order_id, "N/A"), orderUrl=safe_str(order_url, "N/A"),
            error=f"Options added: {added_options_count}" # Indicate options were processed
        )
        add_order(history_entry)
        update_task_status(task_id, "completed", f"订单 {order_id} (选项数: {added_options_count}) 已成功创建")
        await broadcast_order_completed(history_entry)
        
        # Build display string with actual options added if possible (or just FQN if easier)
        # For simplicity, just use planCode and note options were added.
        success_msg = f"{api_config.iam}: 订单 {order_id} 已成功创建并支付！\n服务器 Plan: {config.planCode}\n数据中心: {available_dc}\n(处理了 {added_options_count} 个硬件选项)\n订单链接: {order_url}"
        send_telegram_msg(success_msg)
        
        return history_entry
    
    # --- 错误处理 (保持不变) ---
    except ovh.exceptions.APIError as e:
        # 检查是否是"不可用"错误
        error_str = str(e)
        is_unavailable_error = "is not available in" in error_str
        
        # 根据不同错误类型设置不同的状态
        if is_unavailable_error:
            error_msg = f"服务器配置暂时不可用: {error_str}"
            add_log("info", error_msg)
            task_logger.info(error_msg)
            update_task_status(task_id, "pending", error_msg)
        else:
            # 其他API错误仍然按原来方式处理
            error_msg = f"OVH API 操作失败: {error_str}"
            add_log("error", error_msg)
        add_log("error", error_msg)
        update_task_status(task_id, "error", error_msg)
        
        # 记录查询ID，便于调试
        if "OVH-Query-ID:" in error_str:
            try:
                query_id = error_str.split("OVH-Query-ID:")[1].strip()
                task_logger.error(f"OVH查询ID: {query_id}")
            except Exception as parse_error:
                task_logger.error(f"无法解析OVH查询ID: {parse_error}")
        if cart_id: task_logger.error(f"购物车ID: {cart_id}")
        
        # 无论哪种情况都创建订单历史记录
        now = datetime.now().isoformat()
        history_entry = OrderHistory(
            id=str(uuid.uuid4()), planCode=config.planCode, name=config.name,
            datacenter=config.datacenter, orderTime=now, status="failed",
            error=error_msg
        )
        add_order(history_entry)
        
        # 仅在非不可用错误时广播失败消息
        if not is_unavailable_error:
            await broadcast_order_failed(history_entry)
            error_tg_msg = f"{api_config.iam}: OVH 操作失败 - {error_str}"
            if cart_id: error_tg_msg += f"\nCart ID: {cart_id}"
            send_telegram_msg(error_tg_msg)
        else:
            # 对于不可用错误，只广播消息到前端，不发送Telegram通知
            await broadcast_order_failed(history_entry)
            add_log("info", f"服务器暂不可用，跳过Telegram通知: {config.planCode} 在 {config.datacenter}")
        
        return history_entry

    except Exception as e:
        # 其他一般错误处理
        error_msg = f"订购服务器时发生未知错误: {str(e)}"
        add_log("error", error_msg)
        task_logger.error(error_msg)
        task_logger.error(f"完整错误堆栈: {traceback.format_exc()}")
        if cart_id: task_logger.error(f"购物车ID: {cart_id}")
        update_task_status(task_id, "error", error_msg)
        now = datetime.now().isoformat()
        history_entry = OrderHistory(
            id=str(uuid.uuid4()), planCode=config.planCode, name=config.name,
            datacenter=config.datacenter, orderTime=now, status="failed",
            error=error_msg
        )
        add_order(history_entry)
        await broadcast_order_failed(history_entry)
        error_tg_msg = f"{api_config.iam}: 发生意外错误 - {str(e)}"
        if cart_id: error_tg_msg += f"\nCart ID: {cart_id}"
        send_telegram_msg(error_tg_msg)
        return history_entry

def update_task_status(task_id: str, status: str, message: Optional[str] = None):
    # 实现更新任务状态的逻辑
    if task_id in tasks:
        task = tasks[task_id]
        task.status = status
        task.message = message if message else task.message # Keep old message if none provided
        task.lastChecked = datetime.now().isoformat()
        
        # Calculate next retry time if status is error or pending
        if status in ["error", "pending"]:
            next_retry_delay = task.taskInterval
            # Implement exponential backoff or other retry strategies if needed
            # For now, simple interval
            task.nextRetryAt = datetime.fromtimestamp(datetime.now().timestamp() + next_retry_delay).isoformat()
        else:
            task.nextRetryAt = None # Clear next retry time for completed/running/etc.
        
        # Broadcast task update
        try:
            # Run broadcast in background to avoid blocking
            asyncio.create_task(broadcast_message({
            "type": "task_updated",
            "data": task.dict()
        }))
        except Exception as broadcast_error:
            add_log("error", f"广播任务更新失败: {broadcast_error}")
        
        # Save tasks to file (maybe less frequently?)
        save_tasks_to_file()
    else:
        add_log("warning", f"尝试更新不存在的任务状态: {task_id}")

@app.delete("/api/tasks")
async def clear_tasks():
    global tasks
    tasks_count = len(tasks)
    tasks = {}
    save_tasks_to_file()
    add_log("info", f"已清除 {tasks_count} 个任务")
    
    # 广播所有任务已清除
    await broadcast_message({
        "type": "tasks_cleared",
        "data": {"count": tasks_count}
    })
    
    return {"message": f"已清除 {tasks_count} 个任务"}

@app.get("/api/orders")
async def get_orders():
    return orders

@app.delete("/api/orders/{order_id}")
async def delete_order(order_id: str):
    global orders
    # 查找订单
    for i, order in enumerate(orders):
        if order.id == order_id:
            # 删除订单
            removed_order = orders.pop(i)
            save_orders_to_file()
            add_log("info", f"已删除订单: {order_id}")
            return {"message": f"已删除订单: {order_id}"}
    
    # 如果没有找到订单，返回404
    raise HTTPException(status_code=404, detail=f"未找到订单: {order_id}")

@app.delete("/api/orders")
async def clear_orders():
    global orders
    orders_count = len(orders)
    orders = []
    save_orders_to_file()
    add_log("info", f"已清除 {orders_count} 条订单历史记录")
    return {"message": f"已清除 {orders_count} 条订单历史记录"}

@app.get("/api/logs")
async def get_logs(limit: int = 100):
    return logs[-limit:] if limit < len(logs) else logs

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    connection_id = len(connections)  # 简单的连接ID
    add_log("info", f"新的WebSocket连接已建立 (ID: {connection_id}, 总连接数: {len(connections)})")
    
    try:
        # 准备安全的API配置（隐藏敏感信息）
        safe_config = None
        if api_config:
            safe_config = api_config.dict()
            # 隐藏敏感字段
            if safe_config.get("appKey"):
                safe_config["appKey"] = "******"
            if safe_config.get("appSecret"):
                safe_config["appSecret"] = "******" 
            if safe_config.get("consumerKey"):
                safe_config["consumerKey"] = "******"
            if safe_config.get("tgToken"):
                safe_config["tgToken"] = "******"
        
        # 发送初始数据，包含API配置状态和所有订单
        await websocket.send_json({
            "type": "initial_data",
            "data": {
                "tasks": [task.dict() for task in tasks.values()],
                "orders": [order.dict() for order in orders],  # 确保包含所有订单
                "logs": logs[-100:],
                "api_config": safe_config,  # 发送安全版本的API配置
                "connection_status": {
                    "is_connected": True,
                    "connection_id": connection_id,
                    "total_connections": len(connections),
                    "server_time": datetime.now().isoformat()
                }
            }
        })
        add_log("info", f"已向客户端 {connection_id} 发送初始数据: {len(tasks)} 个任务, {len(orders)} 个订单, {min(len(logs), 100)} 条日志")
        
        # 立即广播连接状态通知所有客户端
        await broadcast_message({
            "type": "connection_status",
            "data": {
                "is_connected": True,
                "active_connections": len(connections),
                "timestamp": datetime.now().isoformat()
            }
        })
        
        while True:
            # 检测连接健康状态
            if websocket.client_state != 1:  # 如果不是CONNECTED状态
                add_log("warning", f"客户端 {connection_id} 连接状态异常，关闭WebSocket")
                break
                
            # 保持连接，接收客户端的消息
            try:
                data = await websocket.receive_text()
                
                # 处理客户端消息
                try:
                    message = json.loads(data)
                    if isinstance(message, dict) and "type" in message:
                        # 处理心跳消息
                        if message["type"] == "ping":
                            await websocket.send_json({
                                "type": "pong",
                                "data": {
                                    "timestamp": datetime.now().isoformat(),
                                    "is_connected": True,
                                    "connection_id": connection_id
                                }
                            })
                        # 处理状态检查请求
                        elif message["type"] == "check_connection":
                            await websocket.send_json({
                                "type": "connection_status",
                                "data": {
                                    "is_connected": True,
                                    "active_connections": len(connections),
                                    "connection_id": connection_id,
                                    "timestamp": datetime.now().isoformat()
                                }
                            })
                            add_log("debug", f"客户端 {connection_id} 请求检查连接状态")
                except json.JSONDecodeError:
                    add_log("warning", f"收到无效的WebSocket消息 (客户端 {connection_id})")
                except Exception as e:
                    add_log("error", f"处理WebSocket消息时出错 (客户端 {connection_id}): {str(e)}")
            except WebSocketDisconnect:
                add_log("info", f"WebSocket接收消息时连接断开 (客户端 {connection_id})")
                break
            except Exception as e:
                add_log("error", f"WebSocket接收消息时发生错误 (客户端 {connection_id}): {str(e)}")
                break
    except WebSocketDisconnect:
        add_log("info", f"WebSocket连接已关闭 (客户端 {connection_id})")
    except Exception as e:
        add_log("error", f"WebSocket错误 (客户端 {connection_id}): {str(e)}")
    finally:
        # 确保连接被移除
        if websocket in connections:
            connections.remove(websocket)
            add_log("info", f"连接已移除 (客户端 {connection_id}), 剩余连接数: {len(connections)}")
            
            # 广播连接状态更新，告知所有客户端连接数变化
            try:
                await broadcast_message({
                    "type": "connection_status",
                    "data": {
                        "is_connected": True,
                        "active_connections": len(connections),
                        "timestamp": datetime.now().isoformat(),
                        "client_disconnected": connection_id
                    }
                })
            except Exception as e:
                add_log("error", f"断开连接后广播状态更新失败: {str(e)}")

# 添加安全的类型转换辅助函数
def safe_str(value, default=""):
    """安全地将值转换为字符串"""
    if value is None:
        return default
    return str(value)

# 修复广播订单完成消息的函数
async def broadcast_order_completed(order: OrderHistory):
    """广播订单完成消息"""
    try:
        await broadcast_message({
            "type": "order_completed",
            "data": order.dict()
        })
        add_log("info", f"订单完成消息已广播: {order.orderId}")
    except Exception as e:
        add_log("error", f"广播订单完成消息失败: {str(e)}")

# 添加连接状态检查API端点
@app.get("/api/connection/status")
async def get_connection_status():
    """获取当前连接状态的API端点"""
    return {
        "status": "connected",
        "active_connections": len(connections),
        "timestamp": datetime.now().isoformat()
    }

# 添加应用状态信息API端点
@app.get("/api/status")
async def get_application_status():
    """获取应用程序状态信息"""
    return {
        "status": "running",
        "active_connections": len(connections),
        "tasks_count": len(tasks),
        "orders_count": len(orders),
        "logs_count": len(logs),
        "server_time": datetime.now().isoformat(),
        "uptime": get_uptime()
    }

# 添加获取应用运行时间的函数
start_time = datetime.now()
def get_uptime():
    """获取应用的运行时间（秒）"""
    uptime = (datetime.now() - start_time).total_seconds()
    return int(uptime)

@app.post("/api/config/ovh")
async def set_ovh_api_config(config: dict):
    """仅更新OVH API相关的配置"""
    global api_config, ovh_client
    
    # 如果尚未初始化，则创建一个空配置
    if not api_config:
        api_config = ApiConfig(appKey="", appSecret="", consumerKey="")
    
    # 记录日志（屏蔽敏感信息）
    safe_log = config.copy()
    for key in ["appKey", "appSecret", "consumerKey"]:
        if key in safe_log and safe_log[key]:
            safe_log[key] = "***" + safe_log[key][-4:] if len(safe_log[key]) > 4 else "***"
    
    add_log("info", f"更新OVH API配置: {safe_log}")
    
    # 仅更新API相关的配置部分
    api_config.update_api_part(config)
    ovh_client = None  # 重置客户端，下次会重新初始化
    
    # 保存配置到文件
    save_config_to_file()
    
    add_log("info", "OVH API配置已更新")
    return {"message": "OVH API配置已更新"}

@app.post("/api/config/telegram")
async def set_telegram_config(config: dict):
    """仅更新Telegram通知相关的配置"""
    global api_config
    
    # 如果尚未初始化，则创建一个空配置
    if not api_config:
        api_config = ApiConfig(appKey="", appSecret="", consumerKey="")
    
    # 记录日志（屏蔽敏感信息）
    safe_log = config.copy()
    if "tgToken" in safe_log and safe_log["tgToken"]:
        safe_log["tgToken"] = "***" + safe_log["tgToken"][-4:] if len(safe_log["tgToken"]) > 4 else "***"
    
    add_log("info", f"更新Telegram通知配置: tgChatId={safe_log.get('tgChatId')}, tgToken={'已设置' if safe_log.get('tgToken') else '未设置'}")
    
    # 仅更新Telegram相关的配置部分
    api_config.update_telegram_part(config)
    
    # 保存配置到文件
    save_config_to_file()
    
    # 尝试发送测试消息到Telegram
    if api_config.tgToken and api_config.tgChatId:
        test_result = send_telegram_msg("OVH Titan Sniper: Telegram通知已成功配置")
        if test_result:
            add_log("info", "Telegram测试消息发送成功")
        else:
            add_log("warning", "Telegram测试消息发送失败，请检查Token和ChatID")
    
    add_log("info", "Telegram通知配置已更新")
    return {"message": "Telegram通知配置已更新"}

# **** 恢复 GET /api/servers 路由 ****
@app.get("/api/servers")
async def get_servers(subsidiary: str = 'IE'):
    catalog = await fetch_product_catalog(subsidiary)
    return catalog

# **** 恢复 GET /api/tasks 路由 ****
@app.get("/api/tasks")
async def get_tasks():
    return list(tasks.values())

# **** 恢复 GET /api/servers/{plan_code}/availability (如果需要) ****
# 这个端点似乎在日志中没有报错，但为了完整性可以检查
@app.get("/api/servers/{plan_code}/availability")
async def get_server_availability(plan_code: str, request: Request):
    try:
        add_log("info", f"GET请求获取服务器 {plan_code} 的可用性数据")
        options = None
        try:
            body = await request.json()
            options_data = body.get("options", [])
            # 将字典列表转换为 AddonOption 对象列表
            options = [AddonOption(**opt) for opt in options_data]
            add_log("info", f"从GET请求体中解析出选项: {options}")
        except Exception as parse_error:
            add_log("info", f"GET请求没有提供选项或无法解析请求体 ({parse_error})，使用默认配置")
        
        result = await check_availability(plan_code, options)
        return result
    except Exception as e:
        add_log("error", f"获取服务器 {plan_code} 可用性数据时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# **** 保留 POST /api/servers/{plan_code}/availability ****
@app.post("/api/servers/{plan_code}/availability")
async def post_server_availability(plan_code: str, data: dict):
    try:
        add_log("info", f"POST请求获取服务器 {plan_code} 的可用性数据，请求体: {data}")
        options_data = data.get("options", [])
        # 将字典列表转换为 AddonOption 对象列表
        options = [AddonOption(**opt) for opt in options_data]
        add_log("info", f"从请求体中解析出选项: {options}")
        
        result = await check_availability(plan_code, options)
        return result
    except Exception as e:
        add_log("error", f"POST获取服务器 {plan_code} 可用性数据时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# **** 保留 POST /api/tasks ****
@app.post("/api/tasks")
async def create_task(config: ServerConfig):
    # ... (函数内容保持不变)
    task_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    next_check = datetime.fromtimestamp(datetime.now().timestamp() + 5).isoformat()
    
    options_log = []
    for opt in config.options:
        options_log.append(f"{opt.label}:{opt.value}")
    
    add_log("info", f"创建任务请求: planCode={config.planCode}, 数据中心={config.datacenter}, 原始选项=[{', '.join(options_log)}]")
    
    datacenter = config.datacenter.strip()
    
    new_task = TaskStatus(
        id=task_id,
        name=config.name,
        planCode=config.planCode,
        datacenter=datacenter,
        status="pending",
        createdAt=now,
        lastChecked=now,
        maxRetries=config.maxRetries,
        nextRetryAt=next_check,
        message="任务已创建，等待执行",
        taskInterval=config.taskInterval if config.taskInterval else 60,
        options=config.options
    )
    
    tasks[task_id] = new_task
    add_log("info", f"创建了新任务: {config.name} ({task_id}), 数据中心: {datacenter}, 重试间隔: {new_task.taskInterval}秒, 最大重试次数: {new_task.maxRetries}, 配置选项: {len(new_task.options)}个")
    
    save_tasks_to_file()
    
    try:
        await broadcast_message({
            "type": "task_created",
            "data": new_task.dict()
        })
    except Exception as e:
        add_log("error", f"广播任务创建消息失败: {str(e)}")
        
    return new_task

# **** 保留 DELETE /api/tasks/{task_id} ****
@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    # ... (函数内容保持不变)
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    
    task_name = tasks[task_id].name
    del tasks[task_id]
    add_log("info", f"删除了任务: {task_name} ({task_id})")
    
    save_tasks_to_file()
    
    await broadcast_message({
        "type": "task_deleted",
        "data": {"id": task_id}
    })
    
    return {"message": f"任务 {task_id} 已删除"}

# **** 保留 POST /api/tasks/{task_id}/retry ****
@app.post("/api/tasks/{task_id}/retry")
async def retry_task(task_id: str):
    # ... (函数内容保持不变)
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    
    task = tasks[task_id]
    
    if task.status == "error" or task.status == "max_retries_reached": # 允许重置达到最大次数的任务
        task.retryCount = 0 # 重置计数
        update_task_status(task_id, "pending", "任务已手动重置，将重新尝试")
        add_log("info", f"任务 {task_id} ({task.name}) 已被手动重置为等待状态")
        return {"message": f"任务 {task_id} 已重置为等待状态"}
    else:
        return {"message": f"任务 {task_id} 当前状态为 {task.status}，无需重置"}

# 添加一个新的端点，用于直接使用默认配置下单
@app.post("/api/queue/new")
async def create_default_task(data: dict):
    """
    创建一个不带任何可选配置的任务
    请求体格式:
    {
        "name": "KS-A | Intel i7-6700k",  # 服务器名称
        "planCode": "24ska01",            # 服务器型号代码
        "datacenter": "gra"               # 数据中心
    }
    """
    try:
        # 从请求体中提取基本信息
        name = data.get("name")
        plan_code = data.get("planCode")
        datacenter = data.get("datacenter")
        
        # 验证必要参数
        if not all([name, plan_code, datacenter]):
            raise HTTPException(status_code=400, detail="缺少必要参数: name, planCode, datacenter")
        
        # 创建服务器配置对象，不包含任何可选参数
        config = ServerConfig(
            planCode=plan_code,
            datacenter=datacenter,
            name=name,
            maxRetries=-1,  # 无限重试
            taskInterval=60,  # 默认60秒
            options=[]  # 空列表，不传递任何配置选项
        )
        
        # 记录日志
        add_log("info", f"使用默认配置创建任务: {name} (型号: {plan_code}, 数据中心: {datacenter})")
        
        # 调用现有的创建任务函数
        new_task = await create_task(config)
        
        return {
            "status": "success",
            "message": f"已使用默认配置创建任务: {name}",
            "task_id": new_task.id
        }
        
    except Exception as e:
        add_log("error", f"创建默认配置任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

# 运行服务器
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

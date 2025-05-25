import os
import time
import json
import logging
import uuid
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import ovh
import re
import traceback
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Data storage (in-memory for this example, should be persisted in production)
CONFIG_FILE = "config.json"
LOGS_FILE = "logs.json"
QUEUE_FILE = "queue.json"
HISTORY_FILE = "history.json"
SERVERS_FILE = "servers.json"

config = {
    "appKey": "",
    "appSecret": "",
    "consumerKey": "",
    "endpoint": "ovh-eu",
    "tgToken": "",
    "tgChatId": "",
    "iam": "go-ovh-ie",
    "zone": "IE",
}

logs = []
queue = []
purchase_history = []
server_plans = []
stats = {
    "activeQueues": 0,
    "totalServers": 0,
    "availableServers": 0,
    "purchaseSuccess": 0,
    "purchaseFailed": 0
}

# Load data from files if they exist
def load_data():
    global config, logs, queue, purchase_history, server_plans, stats
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError:
            print(f"警告: {CONFIG_FILE}文件格式不正确，使用默认值")
    
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, 'r') as f:
                content = f.read().strip()
                if content:  # 确保文件不是空的
                    logs = json.loads(content)
                else:
                    print(f"警告: {LOGS_FILE}文件为空，使用空列表")
        except json.JSONDecodeError:
            print(f"警告: {LOGS_FILE}文件格式不正确，使用空列表")
    
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, 'r') as f:
                content = f.read().strip()
                if content:  # 确保文件不是空的
                    queue = json.loads(content)
                else:
                    print(f"警告: {QUEUE_FILE}文件为空，使用空列表")
        except json.JSONDecodeError:
            print(f"警告: {QUEUE_FILE}文件格式不正确，使用空列表")
    
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                content = f.read().strip()
                if content:  # 确保文件不是空的
                    purchase_history = json.loads(content)
                else:
                    print(f"警告: {HISTORY_FILE}文件为空，使用空列表")
        except json.JSONDecodeError:
            print(f"警告: {HISTORY_FILE}文件格式不正确，使用空列表")
    
    if os.path.exists(SERVERS_FILE):
        try:
            with open(SERVERS_FILE, 'r') as f:
                content = f.read().strip()
                if content:  # 确保文件不是空的
                    server_plans = json.loads(content)
                else:
                    print(f"警告: {SERVERS_FILE}文件为空，使用空列表")
        except json.JSONDecodeError:
            print(f"警告: {SERVERS_FILE}文件格式不正确，使用空列表")
    
    # Update stats
    update_stats()
    
    logging.info("Data loaded from files")

# Save data to files
def save_data():
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        with open(LOGS_FILE, 'w') as f:
            json.dump(logs, f)
        with open(QUEUE_FILE, 'w') as f:
            json.dump(queue, f)
        with open(HISTORY_FILE, 'w') as f:
            json.dump(purchase_history, f)
        with open(SERVERS_FILE, 'w') as f:
            json.dump(server_plans, f)
        logging.info("Data saved to files")
    except Exception as e:
        logging.error(f"保存数据时出错: {str(e)}")
        print(f"保存数据时出错: {str(e)}")
        # 尝试单独保存每个文件
        try_save_file(CONFIG_FILE, config)
        try_save_file(LOGS_FILE, logs)
        try_save_file(QUEUE_FILE, queue)
        try_save_file(HISTORY_FILE, purchase_history)
        try_save_file(SERVERS_FILE, server_plans)

# 尝试保存单个文件
def try_save_file(filename, data):
    try:
        with open(filename, 'w') as f:
            json.dump(data, f)
        print(f"成功保存 {filename}")
    except Exception as e:
        print(f"保存 {filename} 时出错: {str(e)}")

# Add a log entry
def add_log(level, message, source="system"):
    global logs
    log_entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
        "source": source
    }
    logs.append(log_entry)
    
    # Keep logs at a reasonable size (last 1000 entries)
    if len(logs) > 1000:
        logs = logs[-1000:]
    
    # Save logs to file
    with open(LOGS_FILE, 'w') as f:
        json.dump(logs, f)
    
    # Also print to console
    if level == "ERROR":
        logging.error(f"[{source}] {message}")
    elif level == "WARNING":
        logging.warning(f"[{source}] {message}")
    else:
        logging.info(f"[{source}] {message}")

# Update statistics
def update_stats():
    global stats
    active_count = sum(1 for item in queue if item["status"] == "running")
    available_count = 0
    
    # Count available servers
    for server in server_plans:
        for dc in server["datacenters"]:
            if dc["availability"] not in ["unavailable", "unknown"]:
                available_count += 1
                break
    
    success_count = sum(1 for item in purchase_history if item["status"] == "success")
    failed_count = sum(1 for item in purchase_history if item["status"] == "failed")
    
    stats = {
        "activeQueues": active_count,
        "totalServers": len(server_plans),
        "availableServers": available_count,
        "purchaseSuccess": success_count,
        "purchaseFailed": failed_count
    }

# Initialize OVH client
def get_ovh_client():
    if not config["appKey"] or not config["appSecret"] or not config["consumerKey"]:
        add_log("ERROR", "Missing OVH API credentials")
        return None
    
    try:
        client = ovh.Client(
            endpoint=config["endpoint"],
            application_key=config["appKey"],
            application_secret=config["appSecret"],
            consumer_key=config["consumerKey"]
        )
        return client
    except Exception as e:
        add_log("ERROR", f"Failed to initialize OVH client: {str(e)}")
        return None

# Check availability of servers
def check_server_availability(plan_code):
    client = get_ovh_client()
    if not client:
        return None
    
    try:
        availabilities = client.get('/dedicated/server/datacenter/availabilities', planCode=plan_code)
        result = {}
        
        for item in availabilities:
            datacenters = item.get("datacenters", [])
            
            for dc_info in datacenters:
                availability = dc_info.get("availability", "unknown")
                datacenter_name = dc_info.get("datacenter")
                
                # 确保可用性状态有正确的值
                if not availability or availability == "unknown":
                    result[datacenter_name] = "unknown"
                elif availability == "unavailable":
                    result[datacenter_name] = "unavailable"
                else:
                    # 任何非"unavailable"或"unknown"的状态都被视为"available"
                    result[datacenter_name] = availability
                
        add_log("INFO", f"成功检查 {plan_code} 的可用性: {result}")
        return result
    except Exception as e:
        add_log("ERROR", f"Failed to check availability for {plan_code}: {str(e)}")
        return None

# Purchase server
def purchase_server(queue_item):
    client = get_ovh_client()
    if not client:
        return False
    
    cart_id = None # Initialize cart_id to None
    item_id = None # Initialize item_id to None
    
    try:
        # Check availability first
        add_log("INFO", f"开始为 {queue_item['planCode']} 在 {queue_item['datacenter']} 的购买流程，选项: {queue_item.get('options')}", "purchase")
        availabilities = client.get('/dedicated/server/datacenter/availabilities', planCode=queue_item["planCode"])
        
        found_available = False
        for item in availabilities:
            datacenters = item.get("datacenters", [])
            
            for dc_info in datacenters:
                if dc_info.get("datacenter") == queue_item["datacenter"] and dc_info.get("availability") not in ["unavailable", "unknown"]:
                    found_available = True
                    break
            
            if found_available:
                break
        
        if not found_available:
            add_log("INFO", f"服务器 {queue_item['planCode']} 在数据中心 {queue_item['datacenter']} 当前无货", "purchase")
            # Even if not available, we might want to record this attempt in history if it's the first one
            # For now, returning False will prevent history update here, purchase_server is called in a loop by queue processor
            return False
        
        # Create cart
        add_log("INFO", f"为区域 {config['zone']} 创建购物车", "purchase")
        cart_result = client.post('/order/cart', ovhSubsidiary=config["zone"])
        cart_id = cart_result["cartId"]
        add_log("INFO", f"购物车创建成功，ID: {cart_id}", "purchase")
        
        # Add base item to cart using /eco endpoint
        add_log("INFO", f"添加基础商品 {queue_item['planCode']} 到购物车 (使用 /eco)", "purchase")
        item_payload = {
            "planCode": queue_item["planCode"],
            "pricingMode": "default",
            "duration": "P1M",  # 1 month
            "quantity": 1
        }
        item_result = client.post(f'/order/cart/{cart_id}/eco', **item_payload)
        item_id = item_result["itemId"] # This is the itemId for the base server
        add_log("INFO", f"基础商品添加成功，项目 ID: {item_id}", "purchase")
        
        # Configure item (datacenter, OS, region)
        add_log("INFO", f"为项目 {item_id} 设置必需配置", "purchase")
        dc_lower = queue_item["datacenter"].lower()
        region = None
        EU_DATACENTERS = ['gra', 'rbx', 'sbg', 'eri', 'lim', 'waw', 'par', 'fra', 'lon']
        CANADA_DATACENTERS = ['bhs']
        US_DATACENTERS = ['vin', 'hil']
        APAC_DATACENTERS = ['syd', 'sgp'] 

        if any(dc_lower.startswith(prefix) for prefix in EU_DATACENTERS): region = "europe"
        elif any(dc_lower.startswith(prefix) for prefix in CANADA_DATACENTERS): region = "canada"
        elif any(dc_lower.startswith(prefix) for prefix in US_DATACENTERS): region = "usa"
        elif any(dc_lower.startswith(prefix) for prefix in APAC_DATACENTERS): region = "apac"

        configurations_to_set = {
            "dedicated_datacenter": queue_item["datacenter"],
            "dedicated_os": "none_64.en" 
        }
        if region:
            configurations_to_set["region"] = region
        else:
            add_log("WARNING", f"无法为数据中心 {dc_lower} 推断区域，可能导致配置失败", "purchase")
            try:
                required_configs_list = client.get(f'/order/cart/{cart_id}/item/{item_id}/requiredConfiguration')
                if any(conf.get("label") == "region" and conf.get("required") for conf in required_configs_list):
                    raise Exception("必需的区域配置无法确定。")
            except Exception as rc_err:
                 add_log("WARNING", f"获取必需配置失败或区域为必需但未确定: {rc_err}", "purchase")

        for label, value in configurations_to_set.items():
            if value is None: continue
            add_log("INFO", f"配置项目 {item_id}: 设置必需项 {label} = {value}", "purchase")
            client.post(f'/order/cart/{cart_id}/item/{item_id}/configuration',
                       label=label,
                       value=str(value))
            add_log("INFO", f"成功设置必需项: {label} = {value}", "purchase")

        user_requested_options = queue_item.get("options", [])
        if user_requested_options:
            add_log("INFO", f"处理用户请求的硬件选项: {user_requested_options}", "purchase")
            filtered_hardware_options = []
            for option_plan_code in user_requested_options:
                if not option_plan_code or not isinstance(option_plan_code, str):
                    add_log("WARNING", f"跳过无效的选项值: {option_plan_code}", "purchase")
                    continue
                opt_lower = option_plan_code.lower()
                if any(skip_term in opt_lower for skip_term in [
                    "windows-server", "sql-server", "cpanel-license", "plesk-",
                    "-license-", "os-", "control-panel", "panel", "license", "security"
                ]):
                    add_log("INFO", f"跳过非硬件/许可证选项: {option_plan_code}", "purchase")
                    continue
                filtered_hardware_options.append(option_plan_code)
            
            if filtered_hardware_options:
                add_log("INFO", f"过滤后的硬件选项计划代码: {filtered_hardware_options}", "purchase")
                try:
                    add_log("INFO", f"获取购物车 {cart_id} 中与基础商品 {queue_item['planCode']} 兼容的 Eco 硬件选项...", "purchase")
                    available_eco_options = client.get(f'/order/cart/{cart_id}/eco/options', planCode=queue_item['planCode'])
                    add_log("INFO", f"找到 {len(available_eco_options)} 个可用的 Eco 硬件选项。", "purchase")
                    added_options_count = 0
                    for wanted_option_plan_code in filtered_hardware_options:
                        option_added_successfully = False
                        for avail_opt in available_eco_options:
                            avail_opt_plan_code = avail_opt.get("planCode")
                            if not avail_opt_plan_code:
                                continue
                            if avail_opt_plan_code == wanted_option_plan_code:
                                add_log("INFO", f"找到匹配的 Eco 选项: {avail_opt_plan_code} (匹配用户请求: {wanted_option_plan_code})", "purchase")
                                try:
                                    option_payload_eco = {
                                        "itemId": item_id, 
                                        "planCode": avail_opt_plan_code, 
                                        "duration": avail_opt.get("duration", "P1M"),
                                        "pricingMode": avail_opt.get("pricingMode", "default"),
                                        "quantity": 1
                                    }
                                    add_log("INFO", f"准备添加 Eco 选项: {option_payload_eco}", "purchase")
                                    client.post(f'/order/cart/{cart_id}/eco/options', **option_payload_eco)
                                    add_log("INFO", f"成功添加 Eco 选项: {avail_opt_plan_code} 到购物车 {cart_id}", "purchase")
                                    added_options_count += 1
                                    option_added_successfully = True
                                    break 
                                except ovh.exceptions.APIError as add_opt_error:
                                    add_log("WARNING", f"添加 Eco 选项 {avail_opt_plan_code} 失败: {add_opt_error}", "purchase")
                                except Exception as general_add_opt_error:
                                    add_log("WARNING", f"添加 Eco 选项 {avail_opt_plan_code} 时发生未知错误: {general_add_opt_error}", "purchase")
                        if not option_added_successfully:
                             add_log("WARNING", f"用户请求的硬件选项 {wanted_option_plan_code} 未在可用Eco选项中找到或添加失败。", "purchase")
                    add_log("INFO", f"共成功添加 {added_options_count} 个硬件选项。", "purchase")
                except ovh.exceptions.APIError as get_opts_error:
                    add_log("ERROR", f"获取 Eco 硬件选项列表失败: {get_opts_error}", "purchase")
                except Exception as e:
                    add_log("ERROR", f"处理 Eco 硬件选项时发生未知错误: {e}", "purchase")
            else:
                add_log("INFO", "用户未请求有效的硬件选项，或所有请求的选项都是非硬件类型。", "purchase")
        else:
            add_log("INFO", "用户未提供任何硬件选项。", "purchase")

        add_log("INFO", f"绑定购物车 {cart_id}", "purchase")
        client.post(f'/order/cart/{cart_id}/assign')
        add_log("INFO", "购物车绑定成功", "purchase")
        
        add_log("INFO", f"对购物车 {cart_id} 执行结账", "purchase")
        checkout_payload = {
            "autoPayWithPreferredPaymentMethod": False, 
            "waiveRetractationPeriod": True
        }
        checkout_result = client.post(f'/order/cart/{cart_id}/checkout', **checkout_payload)
        
        order_id_val = checkout_result.get("orderId", "")
        order_url_val = checkout_result.get("url", "")
        
        # Update or create purchase history entry for SUCCESS
        existing_history_entry = next((h for h in purchase_history if h.get("taskId") == queue_item["id"]), None)
        current_time_iso = datetime.now().isoformat()

        if existing_history_entry:
            existing_history_entry["status"] = "success"
            existing_history_entry["orderId"] = order_id_val
            existing_history_entry["orderUrl"] = order_url_val
            existing_history_entry["errorMessage"] = None # Clear previous error on success
            existing_history_entry["purchaseTime"] = current_time_iso
            existing_history_entry["attemptCount"] = queue_item["retryCount"]
            existing_history_entry["options"] = queue_item.get("options", [])
            add_log("INFO", f"更新抢购历史(成功) 任务ID: {queue_item['id']}", "purchase")
        else:
            history_entry = {
                "id": str(uuid.uuid4()),
                "taskId": queue_item["id"],
                "planCode": queue_item["planCode"],
                "datacenter": queue_item["datacenter"],
                "options": queue_item.get("options", []),
                "status": "success",
                "orderId": order_id_val,
                "orderUrl": order_url_val,
                "errorMessage": None,
                "purchaseTime": current_time_iso,
                "attemptCount": queue_item["retryCount"]
            }
            purchase_history.append(history_entry)
            add_log("INFO", f"创建抢购历史(成功) 任务ID: {queue_item['id']}", "purchase")
        
        save_data()
        update_stats()
        
        add_log("INFO", f"成功购买 {queue_item['planCode']} 在 {queue_item['datacenter']} (订单ID: {order_id_val}, URL: {order_url_val})", "purchase")

        # 发送 Telegram 成功通知
        if config.get("tgToken") and config.get("tgChatId"):
            success_message = (
                f"🎉 OVH 服务器抢购成功！🎉\n\n"
                f"服务器型号 (Plan Code): {queue_item['planCode']}\n"
                f"数据中心: {queue_item['datacenter']}\n"
                f"订单 ID: {order_id_val}\n"
                f"订单链接: {order_url_val}\n"
            )
            options_list = queue_item.get("options", [])
            if options_list:
                options_str = ", ".join(options_list)
                success_message += f"自定义配置: {options_str}\n"
            
            success_message += f"\n抢购任务ID: {queue_item['id']}"
            
            send_telegram_msg(success_message)
            add_log("INFO", f"已为订单 {order_id_val} 发送 Telegram 成功通知。", "purchase")
        else:
            add_log("INFO", "未配置 Telegram Token 或 Chat ID，跳过成功通知发送。", "purchase")

        return True
    
    except ovh.exceptions.APIError as api_e:
        error_msg = str(api_e)
        add_log("ERROR", f"购买 {queue_item['planCode']} 时发生 OVH API 错误: {error_msg}", "purchase")
        if cart_id: add_log("ERROR", f"错误发生时的购物车ID: {cart_id}", "purchase")
        if item_id: add_log("ERROR", f"错误发生时的基础商品ID: {item_id}", "purchase")
        
        # Update or create purchase history entry for API FAILURE
        existing_history_entry = next((h for h in purchase_history if h.get("taskId") == queue_item["id"]), None)
        current_time_iso = datetime.now().isoformat()

        if existing_history_entry:
            existing_history_entry["status"] = "failed"
            existing_history_entry["orderId"] = None
            existing_history_entry["orderUrl"] = None
            existing_history_entry["errorMessage"] = error_msg
            existing_history_entry["purchaseTime"] = current_time_iso
            existing_history_entry["attemptCount"] = queue_item["retryCount"]
            existing_history_entry["options"] = queue_item.get("options", [])
            add_log("INFO", f"更新抢购历史(API失败) 任务ID: {queue_item['id']}", "purchase")
        else:
            history_entry = {
                "id": str(uuid.uuid4()),
                "taskId": queue_item["id"],
                "planCode": queue_item["planCode"],
                "datacenter": queue_item["datacenter"],
                "options": queue_item.get("options", []),
                "status": "failed",
                "orderId": None,
                "orderUrl": None,
                "errorMessage": error_msg,
                "purchaseTime": current_time_iso,
                "attemptCount": queue_item["retryCount"]
            }
            purchase_history.append(history_entry)
            add_log("INFO", f"创建抢购历史(API失败) 任务ID: {queue_item['id']}", "purchase")

        save_data()
        update_stats()
        return False

    except Exception as e:
        error_msg = str(e)
        add_log("ERROR", f"购买 {queue_item['planCode']} 时发生未知错误: {error_msg}", "purchase")
        add_log("ERROR", f"完整错误堆栈: {traceback.format_exc()}", "purchase")
        if cart_id: add_log("ERROR", f"错误发生时的购物车ID: {cart_id}", "purchase")
        if item_id: add_log("ERROR", f"错误发生时的基础商品ID: {item_id}", "purchase")

        # Update or create purchase history entry for GENERAL FAILURE
        existing_history_entry = next((h for h in purchase_history if h.get("taskId") == queue_item["id"]), None)
        current_time_iso = datetime.now().isoformat()

        if existing_history_entry:
            existing_history_entry["status"] = "failed"
            existing_history_entry["orderId"] = None
            existing_history_entry["orderUrl"] = None
            existing_history_entry["errorMessage"] = error_msg
            existing_history_entry["purchaseTime"] = current_time_iso
            existing_history_entry["attemptCount"] = queue_item["retryCount"]
            existing_history_entry["options"] = queue_item.get("options", [])
            add_log("INFO", f"更新抢购历史(通用失败) 任务ID: {queue_item['id']}", "purchase")
        else:
            history_entry = {
                "id": str(uuid.uuid4()),
                "taskId": queue_item["id"],
                "planCode": queue_item["planCode"],
                "datacenter": queue_item["datacenter"],
                "options": queue_item.get("options", []),
                "status": "failed",
                "orderId": None,
                "orderUrl": None,
                "errorMessage": error_msg,
                "purchaseTime": current_time_iso,
                "attemptCount": queue_item["retryCount"]
            }
            purchase_history.append(history_entry)
            add_log("INFO", f"创建抢购历史(通用失败) 任务ID: {queue_item['id']}", "purchase")
        
        save_data()
        update_stats()
        return False

# Process queue items
def process_queue():
    while True:
        items_to_process = list(queue) # Create a copy to iterate over
        for item in items_to_process:
            if item["status"] == "running":
                current_time = time.time()
                last_check_time = item.get("lastCheckTime", 0)
                
                # 如果是首次尝试 (lastCheckTime为0) 或者到达重试间隔
                if last_check_time == 0 or (current_time - last_check_time >= item["retryInterval"]):
                    if last_check_time == 0:
                        add_log("INFO", f"首次尝试任务 {item['id']}: {item['planCode']} 在 {item['datacenter']}", "queue")
                    else:
                        add_log("INFO", f"重试检查任务 {item['id']} (尝试次数: {item['retryCount'] + 1}): {item['planCode']} 在 {item['datacenter']}", "queue")
                    
                    # 更新检查时间和重试计数
                    item["lastCheckTime"] = current_time
                    item["retryCount"] += 1
                    item["updatedAt"] = datetime.now().isoformat()
                    
                    # 尝试购买
                    if purchase_server(item):
                        item["status"] = "completed"
                        item["updatedAt"] = datetime.now().isoformat()
                        log_message_verb = "首次尝试购买成功" if item["retryCount"] == 1 else f"重试购买成功 (尝试次数: {item['retryCount']})"
                        add_log("INFO", f"{log_message_verb}: {item['planCode']} 在 {item['datacenter']} (ID: {item['id']})", "queue")
                    else:
                        log_message_verb = "首次尝试购买失败或服务器暂无货" if item["retryCount"] == 1 else f"重试购买失败或服务器仍无货 (尝试次数: {item['retryCount']})"
                        add_log("INFO", f"{log_message_verb}: {item['planCode']} 在 {item['datacenter']} (ID: {item['id']})。将根据重试间隔再次尝试。", "queue")
                    
                    save_data() # 保存队列状态
                    update_stats() # 更新统计信息
        
        time.sleep(1) # 每秒检查一次队列

# Start queue processing thread
def start_queue_processor():
    thread = threading.Thread(target=process_queue)
    thread.daemon = True
    thread.start()

# Load server list from OVH API
def load_server_list():
    global config
    client = get_ovh_client()
    if not client:
        return []
    
    try:
        # 保存完整的API原始响应
        try:
            # 创建一个目录来存储API数据
            if not os.path.exists("api_data"):
                os.makedirs("api_data")
                
            # 尝试获取并保存原始目录响应
            catalog = client.get(f'/order/catalog/public/eco?ovhSubsidiary={config["zone"]}')
            with open(os.path.join("api_data", "ovh_catalog_raw.json"), "w") as f:
                json.dump(catalog, f, indent=2)
            add_log("INFO", "已保存完整的API原始响应")
        except Exception as e:
            add_log("WARNING", f"保存API原始响应时出错: {str(e)}")
        
        # Get server models
        catalog = client.get(f'/order/catalog/public/eco?ovhSubsidiary={config["zone"]}')
        plans = []
        
        # 创建一个计数器，记录硬件信息提取成功的服务器数量
        hardware_info_counter = {
            "total": 0,
            "cpu_success": 0,
            "memory_success": 0,
            "storage_success": 0,
            "bandwidth_success": 0
        }
        
        for plan in catalog.get("plans", []):
            plan_code = plan.get("planCode")
            if not plan_code:
                continue
            
            hardware_info_counter["total"] += 1
            
            # Get availability
            availabilities = client.get('/dedicated/server/datacenter/availabilities', planCode=plan_code)
            datacenters = []
            
            for item in availabilities:
                for dc in item.get("datacenters", []):
                    datacenters.append({
                        "datacenter": dc.get("datacenter"),
                        "availability": dc.get("availability", "unknown")
                    })
            
            # 添加数据中心的名称和区域信息
            for dc in datacenters:
                dc_code = dc.get("datacenter", "").lower()[:3]  # 取前三个字符作为数据中心代码
                
                # 根据代码设置名称和区域
                if dc_code == "gra":
                    dc["dcName"] = "格拉夫尼茨"
                    dc["region"] = "法国"
                elif dc_code == "sbg":
                    dc["dcName"] = "斯特拉斯堡"
                    dc["region"] = "法国"
                elif dc_code == "rbx":
                    dc["dcName"] = "鲁贝"
                    dc["region"] = "法国"
                elif dc_code == "bhs":
                    dc["dcName"] = "博阿尔诺"
                    dc["region"] = "加拿大"
                elif dc_code == "hil":
                    dc["dcName"] = "希尔斯伯勒"
                    dc["region"] = "美国"
                elif dc_code == "vin":
                    dc["dcName"] = "维也纳"
                    dc["region"] = "美国"
                elif dc_code == "lim":
                    dc["dcName"] = "利马索尔"
                    dc["region"] = "塞浦路斯"
                elif dc_code == "sgp":
                    dc["dcName"] = "新加坡"
                    dc["region"] = "新加坡"
                elif dc_code == "syd":
                    dc["dcName"] = "悉尼"
                    dc["region"] = "澳大利亚"
                elif dc_code == "waw":
                    dc["dcName"] = "华沙"
                    dc["region"] = "波兰"
                elif dc_code == "fra":
                    dc["dcName"] = "法兰克福"
                    dc["region"] = "德国"
                elif dc_code == "lon":
                    dc["dcName"] = "伦敦"
                    dc["region"] = "英国"
                elif dc_code == "eri":
                    dc["dcName"] = "厄斯沃尔"
                    dc["region"] = "英国"
                else:
                    dc["dcName"] = dc.get("datacenter", "未知")
                    dc["region"] = "未知"
            
            # Extract server details
            default_options = []
            available_options = []
            
            # 创建初始服务器信息对象 - 确保在解析特定字段前就已创建
            server_info = {
                "planCode": plan_code,
                "name": plan.get("invoiceName", ""),
                "description": plan.get("description", ""),
                "cpu": "N/A",
                "memory": "N/A",
                "storage": "N/A",
                "bandwidth": "N/A",
                "vrackBandwidth": "N/A",
                "datacenters": datacenters,
                "defaultOptions": default_options,
                "availableOptions": available_options
            }
            
            # 保存服务器详细数据，以便于调试
            try:
                # 创建一个目录来存储服务器数据
                server_data_dir = os.path.join("api_data", plan_code)
                if not os.path.exists(server_data_dir):
                    os.makedirs(server_data_dir)
                
                # 保存详细的plan数据
                with open(os.path.join(server_data_dir, "plan_data.json"), "w") as f:
                    json.dump(plan, f, indent=2)
                
                # 保存addonFamilies数据，如果存在
                if plan.get("addonFamilies") and isinstance(plan.get("addonFamilies"), list):
                    with open(os.path.join(server_data_dir, "addonFamilies.json"), "w") as f:
                        json.dump(plan.get("addonFamilies"), f, indent=2)
                
                add_log("INFO", f"已保存服务器{plan_code}的详细数据用于调试")
            except Exception as e:
                add_log("WARNING", f"保存服务器详细数据时出错: {str(e)}")
            
            # 处理特殊系列处理逻辑
            special_server_processed = False
            try:
                # 检查是否为SYSLE系列服务器
                if "sysle" in plan_code.lower():
                    add_log("INFO", f"检测到SYSLE系列服务器: {plan_code}")
                    
                    # 尝试从plan_code提取信息
                    # 通常SYSLE的格式为"25sysle021"，可能包含CPU型号或配置信息
                    # 根据不同型号添加更具体的CPU信息
                    if "011" in plan_code:
                        server_info["cpu"] = "SYSLE 011系列 (入门级服务器CPU)"
                    elif "021" in plan_code:
                        server_info["cpu"] = "SYSLE 021系列 (中端服务器CPU)"
                    elif "031" in plan_code:
                        server_info["cpu"] = "SYSLE 031系列 (高端服务器CPU)"
                    else:
                        server_info["cpu"] = "SYSLE系列CPU"
                    
                    # 获取服务器显示名称和描述，可能包含CPU信息
                    display_name = plan.get("displayName", "")
                    invoice_name = plan.get("invoiceName", "")
                    description = plan.get("description", "")
                    
                    # 检查名称中是否包含具体CPU型号信息
                    found_cpu = False
                    for name in [display_name, invoice_name, description]:
                        if not name:
                            continue
                            
                        # 查找CPU型号关键词
                        cpu_keywords = ["i7-", "i9-", "i5-", "xeon", "epyc", "ryzen"]
                        for keyword in cpu_keywords:
                            if keyword.lower() in name.lower():
                                # 提取包含CPU型号的部分
                                start_pos = name.lower().find(keyword.lower())
                                end_pos = min(start_pos + 30, len(name))  # 提取最多30个字符
                                cpu_info = name[start_pos:end_pos].split(",")[0].strip()
                                server_info["cpu"] = cpu_info
                                add_log("INFO", f"从关键词中提取SYSLE CPU型号: {cpu_info} 给 {plan_code}")
                                found_cpu = True
                                break
                        
                        if found_cpu:
                            break
                    
                    # 尝试寻找更具体的信息
                    # 保存原始数据以便分析
                    try:
                        with open(f"sysle_server_{plan_code}.json", "w") as f:
                            json.dump(plan, f, indent=2)
                        add_log("INFO", f"已保存SYSLE服务器{plan_code}的原始数据")
                    except Exception as e:
                        add_log("WARNING", f"保存SYSLE服务器数据时出错: {str(e)}")
                    
                    special_server_processed = True
                
                # 检查是否为SK系列服务器
                elif "sk" in plan_code.lower():
                    add_log("INFO", f"检测到SK系列服务器: {plan_code}")
                    
                    # 获取服务器显示名称和描述，可能包含CPU信息
                    display_name = plan.get("displayName", "")
                    invoice_name = plan.get("invoiceName", "")
                    description = plan.get("description", "")
                    
                    # 检查名称中是否包含具体CPU型号信息
                    found_cpu = False
                    for name in [display_name, invoice_name, description]:
                        if not name:
                            continue
                            
                        # 查找典型的CPU信息格式，例如"KS-A | Intel i7-6700k"
                        if "|" in name:
                            parts = name.split("|")
                            if len(parts) > 1:
                                cpu_part = parts[1].strip()
                                if "intel" in cpu_part.lower() or "amd" in cpu_part.lower() or "xeon" in cpu_part.lower() or "i7" in cpu_part.lower():
                                    server_info["cpu"] = cpu_part
                                    add_log("INFO", f"从名称中提取CPU型号: {cpu_part} 给 {plan_code}")
                                    found_cpu = True
                        
                        # 直接查找CPU型号关键词
                        cpu_keywords = ["i7-", "i9-", "i5-", "xeon", "epyc", "ryzen"]
                        for keyword in cpu_keywords:
                            if keyword.lower() in name.lower():
                                # 提取包含CPU型号的部分
                                start_pos = name.lower().find(keyword.lower())
                                end_pos = min(start_pos + 30, len(name))  # 提取最多30个字符
                                cpu_info = name[start_pos:end_pos].split(",")[0].strip()
                                server_info["cpu"] = cpu_info
                                add_log("INFO", f"从关键词中提取CPU型号: {cpu_info} 给 {plan_code}")
                                found_cpu = True
                                break
                        
                        if found_cpu:
                            break
                    
                    # 如果没有找到详细的CPU型号，使用默认值
                    if not found_cpu:
                        server_info["cpu"] = "SK系列专用CPU"
                    
                    # 尝试寻找更具体的信息
                    # 保存原始数据以便分析
                    try:
                        with open(f"sk_server_{plan_code}.json", "w") as f:
                            json.dump(plan, f, indent=2)
                        add_log("INFO", f"已保存SK服务器{plan_code}的原始数据")
                    except Exception as e:
                        add_log("WARNING", f"保存SK服务器数据时出错: {str(e)}")
                    
                    special_server_processed = True
                
                # 添加更多特殊系列处理...
                
                # 确保所有服务器都有CPU信息
                if server_info["cpu"] == "N/A":
                    add_log("INFO", f"服务器 {plan_code} 无法从API提取CPU信息，尝试从名称提取")
                    
                    # 尝试从名称中提取CPU信息
                    display_name = plan.get("displayName", "")
                    invoice_name = plan.get("invoiceName", "")
                    description = plan.get("description", "")
                    
                    found_cpu = False
                    for name in [display_name, invoice_name, description]:
                        if not name:
                            continue
                            
                        # 检查是否有CPU型号信息
                        cpu_keywords = ["i7-", "i9-", "i5-", "xeon", "epyc", "ryzen", "processor", "cpu"]
                        for keyword in cpu_keywords:
                            if keyword.lower() in name.lower():
                                # 提取包含CPU型号的部分
                                start_pos = name.lower().find(keyword.lower())
                                end_pos = min(start_pos + 30, len(name))  # 提取最多30个字符
                                cpu_info = name[start_pos:end_pos].split(",")[0].strip()
                                server_info["cpu"] = cpu_info
                                add_log("INFO", f"从名称关键词中提取CPU型号: {cpu_info} 给 {plan_code}")
                                found_cpu = True
                                break
                        
                        if found_cpu:
                            break
                    
                    # 如果仍然没有找到CPU信息，使用默认值
                    if not found_cpu:
                        if "sysle" in plan_code.lower():
                            server_info["cpu"] = "SYSLE系列专用CPU"
                        elif "rise" in plan_code.lower():
                            server_info["cpu"] = "RISE系列专用CPU"
                        elif "game" in plan_code.lower():
                            server_info["cpu"] = "GAME系列专用CPU"
                        else:
                            server_info["cpu"] = "专用服务器CPU"
            except Exception as e:
                add_log("WARNING", f"处理特殊系列服务器时出错: {str(e)}")
                add_log("WARNING", f"错误详情: {traceback.format_exc()}")
                
                # 出错时也确保有默认CPU信息
                if server_info["cpu"] == "N/A":
                    server_info["cpu"] = "专用服务器CPU"
            
            # 如果是特殊处理的服务器，记录日志
            if special_server_processed:
                add_log("INFO", f"已对服务器 {plan_code} 应用特殊处理逻辑")
            
            # 获取服务器名称和描述，确保它们不为空
            if not server_info["name"] and plan.get("displayName"):
                server_info["name"] = plan.get("displayName")
            
            if not server_info["description"] and plan.get("displayName"):
                server_info["description"] = plan.get("displayName")
            
            # 尝试从服务器名称标签中提取CPU信息
            # 例如"KS-A | Intel i7-6700k"格式
            if server_info["cpu"] == "N/A" or "系列" in server_info["cpu"]:
                try:
                    display_name = plan.get("displayName", "")
                    invoice_name = plan.get("invoiceName", "")
                    
                    for name in [display_name, invoice_name]:
                        if not name or "|" not in name:
                            continue
                            
                        parts = name.split("|")
                        if len(parts) > 1:
                            cpu_part = parts[1].strip()
                            if "intel" in cpu_part.lower() or "amd" in cpu_part.lower() or "xeon" in cpu_part.lower() or "i7" in cpu_part.lower():
                                server_info["cpu"] = cpu_part
                                add_log("INFO", f"从服务器名称标签中提取CPU: {cpu_part} 给 {plan_code}")
                                break
                except Exception as e:
                    add_log("WARNING", f"从名称提取CPU时出错: {str(e)}")
            
            # 获取推荐配置和可选配置 - 使用多种方法处理不同格式
            try:
                # 方法 1: 检查plan.default.options
                if plan.get("default") and isinstance(plan.get("default"), dict) and plan.get("default").get("options"):
                    for default_opt in plan.get("default").get("options"):
                        if isinstance(default_opt, dict):
                            option_code = default_opt.get("planCode")
                            option_name = default_opt.get("description", option_code)
                            
                            if option_code:
                                default_options.append({
                                    "label": option_name,
                                    "value": option_code
                                })
                
                # 方法 2: 检查plan.addons
                if plan.get("addons") and isinstance(plan.get("addons"), list):
                    for addon in plan.get("addons"):
                        if not isinstance(addon, dict):
                            continue
                            
                        addon_plan_code = addon.get("planCode")
                        if not addon_plan_code:
                            continue
                        
                        # 跳过已经在默认选项中的配置
                        if any(opt["value"] == addon_plan_code for opt in default_options):
                            continue
                        
                        # 添加到可选配置列表
                        available_options.append({
                            "label": addon.get("description", addon_plan_code),
                            "value": addon_plan_code
                        })
                
                # 方法 3: 检查plan.product.options
                if plan.get("product") and isinstance(plan.get("product"), dict) and plan.get("product").get("options"):
                    product_options = plan.get("product").get("options")
                    if isinstance(product_options, list):
                        for product_opt in product_options:
                            if not isinstance(product_opt, dict):
                                continue
                                
                            option_code = product_opt.get("planCode")
                            option_name = product_opt.get("description", option_code)
                            
                            if option_code and not any(opt["value"] == option_code for opt in available_options) and not any(opt["value"] == option_code for opt in default_options):
                                available_options.append({
                                    "label": option_name,
                                    "value": option_code
                                })
                
                # 方法 4: 尝试从plan.addonFamilies中提取硬件信息
                printed_example = False
                try:
                    if plan.get("addonFamilies") and isinstance(plan.get("addonFamilies"), list):
                        # 尝试保存完整的addonFamilies数据用于更深入分析
                        try:
                            with open(f"addonFamilies_{plan_code}.json", "w") as f:
                                json.dump(plan.get("addonFamilies"), f, indent=2)
                            add_log("INFO", f"已保存服务器 {plan_code} 的addonFamilies数据")
                        except Exception as e:
                            add_log("WARNING", f"保存addonFamilies数据时出错: {str(e)}")
                        
                        # 打印一个完整的addonFamilies示例用于调试
                        if len(plan.get("addonFamilies")) > 0 and not printed_example:
                            try:
                                add_log("INFO", f"addonFamilies示例: {json.dumps(plan.get('addonFamilies')[0], indent=2)}")
                                printed_example = True
                            except Exception as e:
                                add_log("WARNING", f"无法序列化addonFamilies示例: {str(e)}")
                        
                        # 尝试保存所有带宽相关的选项用于调试
                        try:
                            bandwidth_options = []
                            for family in plan.get("addonFamilies"):
                                family_name = family.get("name", "").lower()
                                if ("bandwidth" in family_name or "traffic" in family_name or "network" in family_name):
                                    bandwidth_options.append({
                                        "family": family.get("name"),
                                        "default": family.get("default"),
                                        "addons": family.get("addons")
                                    })
                            
                            if bandwidth_options:
                                with open(f"bandwidth_options_{plan_code}.json", "w") as f:
                                    json.dump(bandwidth_options, f, indent=2)
                                add_log("INFO", f"已保存{plan_code}的带宽选项到bandwidth_options_{plan_code}.json")
                        except Exception as e:
                            add_log("WARNING", f"保存带宽选项时出错: {str(e)}")
                        
                        # 重置可选配置列表
                        temp_available_options = []
                        
                        # 提取addonFamilies信息
                        for family in plan.get("addonFamilies"):
                            if not isinstance(family, dict):
                                add_log("WARNING", f"addonFamily不是字典类型: {family}")
                                continue
                                
                            family_name = family.get("name", "").lower()  # 注意: 在API响应中是'name'而不是'family'
                            default_addon = family.get("default")  # 获取默认选项
                            
                            # 提取可选配置
                            if family.get("addons") and isinstance(family.get("addons"), list):
                                for addon_code in family.get("addons"):
                                    # 在API响应中，addons是字符串数组而不是对象数组
                                    if not isinstance(addon_code, str):
                                        continue
                            
                                    # 标记是否为默认选项
                                    is_default = (addon_code == default_addon)
                                    
                                    # 从addon_code解析描述信息
                                    addon_desc = addon_code
                                    
                                    # 过滤掉许可证相关选项
                                    if (
                                        # Windows许可证
                                        "windows-server" in addon_code.lower() or
                                        # SQL Server许可证
                                        "sql-server" in addon_code.lower() or
                                        # cPanel许可证
                                        "cpanel-license" in addon_code.lower() or
                                        # Plesk许可证
                                        "plesk-" in addon_code.lower() or
                                        # 其他常见许可证
                                        "-license-" in addon_code.lower() or
                                        # 操作系统选项
                                        addon_code.lower().startswith("os-") or
                                        # 控制面板
                                        "control-panel" in addon_code.lower() or
                                        "panel" in addon_code.lower()
                                    ):
                                        # 跳过许可证类选项
                                        continue
                            
                                    if addon_code:
                                        temp_available_options.append({
                                            "label": addon_desc,
                                            "value": addon_code,
                                            "family": family_name,
                                            "isDefault": is_default
                                        })
                                        
                                        # 如果是默认选项，添加到默认选项列表
                                        if is_default:
                                            default_options.append({
                                                "label": addon_desc,
                                                "value": addon_code
                                            })
                            
                            # 根据family名称设置对应的硬件信息
                            if family_name and family.get("addons") and isinstance(family.get("addons"), list):
                                # 获取默认选项的值
                                default_value = family.get("default")
                                
                                # CPU信息
                                if ("cpu" in family_name or "processor" in family_name) and server_info["cpu"] == "N/A":
                                    if default_value:
                                        server_info["cpu"] = default_value
                                        add_log("INFO", f"从addonFamilies默认选项提取CPU: {default_value} 给 {plan_code}")
                                        
                                        # 尝试从CPU选项中提取更详细信息
                                        try:
                                            # 记录CPU选项的完整列表，方便调试
                                            if family.get("addons") and isinstance(family.get("addons"), list):
                                                cpu_options = []
                                                for cpu_addon in family.get("addons"):
                                                    if isinstance(cpu_addon, str):
                                                        cpu_options.append(cpu_addon)
                                                
                                                if cpu_options:
                                                    add_log("INFO", f"服务器 {plan_code} 的CPU选项: {', '.join(cpu_options)}")
                                                    
                                                    # 保存到文件以便更详细分析
                                                    try:
                                                        with open(f"cpu_options_{plan_code}.json", "w") as f:
                                                            json.dump({"options": cpu_options, "default": default_value}, f, indent=2)
                                                    except Exception as e:
                                                        add_log("WARNING", f"保存CPU选项时出错: {str(e)}")
                                        except Exception as e:
                                            add_log("WARNING", f"解析CPU选项时出错: {str(e)}")
                                
                                # 内存信息
                                elif ("memory" in family_name or "ram" in family_name) and server_info["memory"] == "N/A":
                                    if default_value:
                                        # 尝试提取内存大小
                                        ram_size = ""
                                        ram_match = re.search(r'ram-(\d+)g', default_value, re.IGNORECASE)
                                        if ram_match:
                                            ram_size = f"{ram_match.group(1)} GB"
                                            server_info["memory"] = ram_size
                                            add_log("INFO", f"从addonFamilies默认选项提取内存: {ram_size} 给 {plan_code}")
                                        else:
                                            server_info["memory"] = default_value
                                            add_log("INFO", f"从addonFamilies默认选项提取内存(原始值): {default_value} 给 {plan_code}")
                                
                                # 存储信息
                                elif ("storage" in family_name or "disk" in family_name or "drive" in family_name or "ssd" in family_name or "hdd" in family_name) and server_info["storage"] == "N/A":
                                    if default_value:
                                        # 尝试匹配混合RAID格式
                                        hybrid_storage_match = re.search(r'hybridsoftraid-(\d+)x(\d+)(sa|ssd|hdd)-(\d+)x(\d+)(nvme|ssd|hdd)', default_value, re.IGNORECASE)
                                        if hybrid_storage_match:
                                            count1 = hybrid_storage_match.group(1)
                                            size1 = hybrid_storage_match.group(2)
                                            type1 = hybrid_storage_match.group(3).upper()
                                            count2 = hybrid_storage_match.group(4)
                                            size2 = hybrid_storage_match.group(5)
                                            type2 = hybrid_storage_match.group(6).upper()
                                            server_info["storage"] = f"混合RAID {count1}x {size1}GB {type1} + {count2}x {size2}GB {type2}"
                                            add_log("INFO", f"从addonFamilies默认选项提取混合存储: {server_info['storage']} 给 {plan_code}")
                                        else:
                                            # 尝试从存储代码中提取信息
                                            storage_match = re.search(r'(raid|softraid)-(\d+)x(\d+)(ssd|hdd|nvme|sa)', default_value, re.IGNORECASE)
                                            if storage_match:
                                                raid_type = storage_match.group(1).upper()
                                                count = storage_match.group(2)
                                                size = storage_match.group(3)
                                                type_str = storage_match.group(4).upper()
                                                server_info["storage"] = f"{raid_type} {count}x {size}GB {type_str}"
                                                add_log("INFO", f"从addonFamilies默认选项提取存储: {server_info['storage']} 给 {plan_code}")
                                            else:
                                                server_info["storage"] = default_value
                                                add_log("INFO", f"从addonFamilies默认选项提取存储(原始值): {default_value} 给 {plan_code}")
                                
                                # 带宽信息
                                elif ("bandwidth" in family_name or "traffic" in family_name or "network" in family_name) and server_info["bandwidth"] == "N/A":
                                    if default_value:
                                        add_log("DEBUG", f"处理带宽选项: {default_value}")
                                        
                                        # 格式1: traffic-5tb-100-24sk-apac (带宽限制和流量限制)
                                        traffic_bw_match = re.search(r'traffic-(\d+)(tb|gb|mb)-(\d+)', default_value, re.IGNORECASE)
                                        if traffic_bw_match:
                                            size = traffic_bw_match.group(1)
                                            unit = traffic_bw_match.group(2).upper()
                                            bw_value = traffic_bw_match.group(3)
                                            server_info["bandwidth"] = f"{bw_value} Mbps / {size} {unit}流量"
                                            add_log("INFO", f"从addonFamilies默认选项提取带宽和流量: {server_info['bandwidth']} 给 {plan_code}")
                                        
                                        # 格式2: traffic-5tb (仅流量限制)
                                        elif re.search(r'traffic-(\d+)(tb|gb|mb)$', default_value, re.IGNORECASE):
                                            simple_traffic_match = re.search(r'traffic-(\d+)(tb|gb|mb)', default_value, re.IGNORECASE)
                                            size = simple_traffic_match.group(1)
                                            unit = simple_traffic_match.group(2).upper()
                                            server_info["bandwidth"] = f"{size} {unit}流量"
                                            add_log("INFO", f"从addonFamilies默认选项提取流量: {server_info['bandwidth']} 给 {plan_code}")
                                        
                                        # 格式3: bandwidth-100 (仅带宽限制)
                                        elif re.search(r'bandwidth-(\d+)', default_value, re.IGNORECASE):
                                            bandwidth_match = re.search(r'bandwidth-(\d+)', default_value, re.IGNORECASE)
                                            bw_value = int(bandwidth_match.group(1))
                                            if bw_value >= 1000:
                                                server_info["bandwidth"] = f"{bw_value/1000:.1f} Gbps".replace(".0 ", " ")
                                            else:
                                                server_info["bandwidth"] = f"{bw_value} Mbps"
                                            add_log("INFO", f"从addonFamilies默认选项提取带宽: {server_info['bandwidth']} 给 {plan_code}")
                                        
                                        # 格式4: traffic-unlimited (无限流量)
                                        elif "traffic-unlimited" in default_value.lower() or "unlimited" in default_value.lower():
                                            # 检查是否有带宽限制
                                            bw_match = re.search(r'(\d+)', default_value)
                                            if bw_match:
                                                bw_value = int(bw_match.group(1))
                                                server_info["bandwidth"] = f"{bw_value} Mbps / 无限流量"
                                            else:
                                                server_info["bandwidth"] = "无限流量"
                                            add_log("INFO", f"从addonFamilies默认选项提取带宽: {server_info['bandwidth']} 给 {plan_code}")
                                        
                                        # 格式5: bandwidth-guarantee (保证带宽)
                                        elif "guarantee" in default_value.lower() or "guaranteed" in default_value.lower():
                                            bw_guarantee_match = re.search(r'(\d+)', default_value)
                                            if bw_guarantee_match:
                                                bw_value = int(bw_guarantee_match.group(1))
                                                server_info["bandwidth"] = f"{bw_value} Mbps (保证带宽)"
                                                add_log("INFO", f"从addonFamilies默认选项提取保证带宽: {server_info['bandwidth']} 给 {plan_code}")
                                            else:
                                                server_info["bandwidth"] = "保证带宽"
                                                add_log("INFO", f"从addonFamilies默认选项提取保证带宽(无具体值) 给 {plan_code}")
                                        
                                        # 格式6: vrack-bandwidth (内部网络带宽)
                                        elif "vrack" in default_value.lower():
                                            vrack_bw_match = re.search(r'vrack-bandwidth-(\d+)', default_value, re.IGNORECASE)
                                            if vrack_bw_match:
                                                bw_value = int(vrack_bw_match.group(1))
                                                if bw_value >= 1000:
                                                    server_info["vrackBandwidth"] = f"{bw_value/1000:.1f} Gbps".replace(".0 ", " ")
                                                else:
                                                    server_info["vrackBandwidth"] = f"{bw_value} Mbps"
                                                add_log("INFO", f"从addonFamilies默认选项提取内部网络带宽: {server_info['vrackBandwidth']} 给 {plan_code}")
                                        
                                        # 无法识别的格式，使用原始值
                                        else:
                                            server_info["bandwidth"] = default_value
                                            add_log("INFO", f"从addonFamilies默认选项提取带宽(原始值): {default_value} 给 {plan_code}")
                        
                        # 将处理好的可选配置添加到服务器信息中
                        if temp_available_options:
                            available_options = temp_available_options
                
                except Exception as e:
                    add_log("ERROR", f"解析addonFamilies时出错: {str(e)}")
                    add_log("ERROR", f"错误详情: {traceback.format_exc()}")
                
                # 方法 5: 检查plan.pricings中的配置项
                if plan.get("pricings") and isinstance(plan.get("pricings"), dict):
                    for pricing_key, pricing_value in plan.get("pricings").items():
                        if isinstance(pricing_value, dict) and pricing_value.get("options"):
                            for option_code, option_details in pricing_value.get("options").items():
                                # 跳过已经在其他列表中的项目
                                if any(opt["value"] == option_code for opt in default_options) or any(opt["value"] == option_code for opt in available_options):
                                    continue
                                
                                option_label = option_code
                                if isinstance(option_details, dict) and option_details.get("description"):
                                    option_label = option_details.get("description")
                                
                                available_options.append({
                                    "label": option_label,
                                    "value": option_code
                                })
                
                # 记录找到的选项数量
                add_log("INFO", f"找到 {len(default_options)} 个默认选项和 {len(available_options)} 个可选配置用于 {plan_code}")
                
            except Exception as e:
                add_log("WARNING", f"解析 {plan_code} 选项时出错: {str(e)}")
            
            # 解析方法 1: 尝试从properties中提取硬件详情
            try:
                if plan.get("details") and plan.get("details").get("properties"):
                    for prop in plan.get("details").get("properties"):
                        # 添加类型检查，确保prop是字典类型
                        if not isinstance(prop, dict):
                            add_log("WARNING", f"属性项不是字典类型: {prop}")
                            continue
                            
                        prop_name = prop.get("name", "").lower()
                        value = prop.get("value", "N/A")
                        
                        if value and value != "N/A":
                            if any(cpu_term in prop_name for cpu_term in ["cpu", "processor"]):
                                server_info["cpu"] = value
                                add_log("INFO", f"从properties提取CPU: {value} 给 {plan_code}")
                            elif any(mem_term in prop_name for mem_term in ["memory", "ram"]):
                                server_info["memory"] = value
                                add_log("INFO", f"从properties提取内存: {value} 给 {plan_code}")
                            elif any(storage_term in prop_name for storage_term in ["storage", "disk", "hdd", "ssd"]):
                                server_info["storage"] = value
                                add_log("INFO", f"从properties提取存储: {value} 给 {plan_code}")
                            elif "bandwidth" in prop_name:
                                if any(private_term in prop_name for private_term in ["vrack", "private", "internal"]):
                                    server_info["vrackBandwidth"] = value
                                    add_log("INFO", f"从properties提取vRack带宽: {value} 给 {plan_code}")
                                else:
                                    server_info["bandwidth"] = value
                                    add_log("INFO", f"从properties提取带宽: {value} 给 {plan_code}")
            except Exception as e:
                add_log("WARNING", f"解析 {plan_code} 属性时出错: {str(e)}")
            
            # 解析方法 2: 尝试从名称中提取信息
            try:
                server_name = server_info["name"]
                server_desc = server_info["description"] if server_info["description"] else ""
                
                # 保存原始数据用于调试
                try:
                    with open(f"server_details_{plan_code}.json", "w") as f:
                        json.dump({
                            "name": server_name,
                            "description": server_desc,
                            "planCode": plan_code
                        }, f, indent=2)
                except Exception as e:
                    add_log("WARNING", f"保存服务器详情时出错: {str(e)}")
                
                # 检查是否为KS/RISE系列服务器，它们通常使用 "KS-XX | CPU信息" 格式
                if "|" in server_name:
                    parts = server_name.split("|")
                    if len(parts) > 1 and server_info["cpu"] == "N/A":
                        cpu_part = parts[1].strip()
                        server_info["cpu"] = cpu_part
                        add_log("INFO", f"从服务器名称提取CPU: {cpu_part} 给 {plan_code}")
                        
                        # 尝试从CPU部分提取更多信息
                        if "core" in cpu_part.lower():
                            # 例如: "4 Core, 8 Thread, xxxx"
                            core_parts = cpu_part.split(",")
                            if len(core_parts) > 1:
                                server_info["cpu"] = core_parts[0].strip()
                
                # 提取CPU型号信息
                if server_info["cpu"] == "N/A":
                    # 尝试匹配常见的CPU关键词
                    cpu_keywords = ["i7-", "i9-", "ryzen", "xeon", "epyc", "cpu", "intel", "amd", "processor"]
                    full_text = f"{server_name} {server_desc}".lower()
                    
                    for keyword in cpu_keywords:
                        if keyword in full_text.lower():
                            # 找到关键词的位置
                            pos = full_text.lower().find(keyword)
                            if pos >= 0:
                                # 提取关键词周围的文本
                                start = max(0, pos - 5)
                                end = min(len(full_text), pos + 25)
                                cpu_text = full_text[start:end]
                                
                                # 尝试清理提取的文本
                                cpu_text = re.sub(r'[^\w\s\-,.]', ' ', cpu_text)
                                cpu_text = ' '.join(cpu_text.split())
                                
                                if cpu_text:
                                    server_info["cpu"] = cpu_text
                                    add_log("INFO", f"从文本中提取CPU关键字: {cpu_text} 给 {plan_code}")
                                    break
                
                # 从服务器名称中提取内存信息
                if server_info["memory"] == "N/A":
                    # 寻找内存关键词
                    mem_match = None
                    mem_patterns = [
                        r'(\d+)\s*GB\s*RAM', 
                        r'RAM\s*(\d+)\s*GB',
                        r'(\d+)\s*G\s*RAM',
                        r'RAM\s*(\d+)\s*G',
                        r'(\d+)\s*GB'
                    ]
                    
                    full_text = f"{server_name} {server_desc}"
                    for pattern in mem_patterns:
                        match = re.search(pattern, full_text, re.IGNORECASE)
                        if match:
                            mem_match = match
                            break
                    
                    if mem_match:
                        memory_size = mem_match.group(1)
                        server_info["memory"] = f"{memory_size} GB"
                        add_log("INFO", f"从文本中提取内存: {server_info['memory']} 给 {plan_code}")
                
                # 从服务器名称中提取存储信息
                if server_info["storage"] == "N/A":
                    # 寻找存储关键词
                    storage_patterns = [
                        r'(\d+)\s*[xX]\s*(\d+)\s*GB\s*(SSD|HDD|NVMe)',
                        r'(\d+)\s*(SSD|HDD|NVMe)\s*(\d+)\s*GB',
                        r'(\d+)\s*TB\s*(SSD|HDD|NVMe)',
                        r'(\d+)\s*(SSD|HDD|NVMe)'
                    ]
                    
                    full_text = f"{server_name} {server_desc}"
                    for pattern in storage_patterns:
                        match = re.search(pattern, full_text, re.IGNORECASE)
                        if match:
                            if match.lastindex == 3:  # 匹配了第一种模式
                                count = match.group(1)
                                size = match.group(2)
                                disk_type = match.group(3).upper()
                                server_info["storage"] = f"{count}x {size}GB {disk_type}"
                            elif match.lastindex == 2:  # 匹配了最后一种模式
                                size = match.group(1)
                                disk_type = match.group(2).upper()
                                server_info["storage"] = f"{size} {disk_type}"
                            
                            add_log("INFO", f"从文本中提取存储: {server_info['storage']} 给 {plan_code}")
                            break
            except Exception as e:
                add_log("WARNING", f"解析 {plan_code} 服务器名称时出错: {str(e)}")
                add_log("WARNING", f"错误详情: {traceback.format_exc()}")
            
            # 解析方法 3: 尝试从产品配置中提取信息
            try:
                if plan.get("product") and isinstance(plan.get("product"), dict) and plan.get("product").get("configurations"):
                    configs = plan.get("product").get("configurations")
                    if not isinstance(configs, list):
                        add_log("WARNING", f"产品配置不是列表类型: {configs}")
                        configs = []
                        
                    for config in configs:
                        # 添加类型检查，确保config是字典类型
                        if not isinstance(config, dict):
                            add_log("WARNING", f"产品配置项不是字典类型: {config}")
                            continue
                            
                        config_name = config.get("name", "").lower()
                        value = config.get("value")
                        
                        if value:
                            if any(cpu_term in config_name for cpu_term in ["cpu", "processor"]):
                                server_info["cpu"] = value
                                add_log("INFO", f"从产品配置提取CPU: {value} 给 {plan_code}")
                            elif any(mem_term in config_name for mem_term in ["memory", "ram"]):
                                server_info["memory"] = value
                                add_log("INFO", f"从产品配置提取内存: {value} 给 {plan_code}")
                            elif any(storage_term in config_name for storage_term in ["storage", "disk", "hdd", "ssd"]):
                                server_info["storage"] = value
                                add_log("INFO", f"从产品配置提取存储: {value} 给 {plan_code}")
                            elif "bandwidth" in config_name:
                                server_info["bandwidth"] = value
                                add_log("INFO", f"从产品配置提取带宽: {value} 给 {plan_code}")
            except Exception as e:
                add_log("WARNING", f"解析 {plan_code} 产品配置时出错: {str(e)}")
                add_log("WARNING", f"错误详情: {traceback.format_exc()}")
            
            # 解析方法 4: 尝试从description解析信息
            try:
                description = plan.get("description", "")
                if description:
                    parts = description.split(",")
                    for part in parts:
                        part = part.strip().lower()
                        
                        # 检查每个部分是否包含硬件信息
                        if server_info["cpu"] == "N/A" and any(cpu_term in part for cpu_term in ["cpu", "core", "i7", "i9", "xeon", "epyc", "ryzen"]):
                            server_info["cpu"] = part
                            add_log("INFO", f"从描述提取CPU: {part} 给 {plan_code}")
                            
                        if server_info["memory"] == "N/A" and any(mem_term in part for mem_term in ["ram", "gb", "memory"]):
                            server_info["memory"] = part
                            add_log("INFO", f"从描述提取内存: {part} 给 {plan_code}")
                            
                        if server_info["storage"] == "N/A" and any(storage_term in part for storage_term in ["hdd", "ssd", "nvme", "storage", "disk"]):
                            server_info["storage"] = part
                            add_log("INFO", f"从描述提取存储: {part} 给 {plan_code}")
                            
                        if server_info["bandwidth"] == "N/A" and "bandwidth" in part:
                            server_info["bandwidth"] = part
                            add_log("INFO", f"从描述提取带宽: {part} 给 {plan_code}")
            except Exception as e:
                add_log("WARNING", f"解析 {plan_code} 描述时出错: {str(e)}")
            
            # 解析方法 5: 从pricing获取信息
            try:
                if plan.get("pricing") and isinstance(plan.get("pricing"), dict) and plan.get("pricing").get("configurations"):
                    pricing_configs = plan.get("pricing").get("configurations")
                    if not isinstance(pricing_configs, list):
                        add_log("WARNING", f"价格配置不是列表类型: {pricing_configs}")
                        pricing_configs = []
                        
                    for price_config in pricing_configs:
                        # 添加类型检查，确保price_config是字典类型
                        if not isinstance(price_config, dict):
                            add_log("WARNING", f"价格配置项不是字典类型: {price_config}")
                            continue
                            
                        config_name = price_config.get("name", "").lower()
                        value = price_config.get("value")
                        
                        if value:
                            if "processor" in config_name and server_info["cpu"] == "N/A":
                                server_info["cpu"] = value
                                add_log("INFO", f"从pricing配置提取CPU: {value} 给 {plan_code}")
                            elif "memory" in config_name and server_info["memory"] == "N/A":
                                server_info["memory"] = value
                                add_log("INFO", f"从pricing配置提取内存: {value} 给 {plan_code}")
                            elif "storage" in config_name and server_info["storage"] == "N/A":
                                server_info["storage"] = value
                                add_log("INFO", f"从pricing配置提取存储: {value} 给 {plan_code}")
            except Exception as e:
                add_log("WARNING", f"解析 {plan_code} pricing配置时出错: {str(e)}")
                add_log("WARNING", f"错误详情: {traceback.format_exc()}")
            
            # 清理提取的数据以确保格式一致
            # 对于CPU，添加一些基本信息如果只有核心数
            if server_info["cpu"] != "N/A" and server_info["cpu"].isdigit():
                server_info["cpu"] = f"{server_info['cpu']} 核心"
            
            # 更新服务器信息中的配置选项
            server_info["defaultOptions"] = default_options
            server_info["availableOptions"] = available_options
            
            # 更新硬件信息计数器
            if server_info["cpu"] != "N/A":
                hardware_info_counter["cpu_success"] += 1
            if server_info["memory"] != "N/A":
                hardware_info_counter["memory_success"] += 1
            if server_info["storage"] != "N/A":
                hardware_info_counter["storage_success"] += 1
            if server_info["bandwidth"] != "N/A":
                hardware_info_counter["bandwidth_success"] += 1
            
            plans.append(server_info)
        
        # 记录硬件信息提取的成功率
        total = hardware_info_counter["total"]
        if total > 0:
            cpu_rate = (hardware_info_counter["cpu_success"] / total) * 100
            memory_rate = (hardware_info_counter["memory_success"] / total) * 100
            storage_rate = (hardware_info_counter["storage_success"] / total) * 100
            bandwidth_rate = (hardware_info_counter["bandwidth_success"] / total) * 100
            
            add_log("INFO", f"服务器硬件信息提取成功率: CPU={cpu_rate:.1f}%, 内存={memory_rate:.1f}%, "
                           f"存储={storage_rate:.1f}%, 带宽={bandwidth_rate:.1f}%")
        
        return plans
    except Exception as e:
        add_log("ERROR", f"Failed to load server list: {str(e)}")
        add_log("ERROR", f"错误详情: {traceback.format_exc()}")
        return []

# 保存完整的API原始响应用于调试分析
def save_raw_api_response(client, zone):
    try:
        # 创建目录用于存储API响应
        if not os.path.exists("api_responses"):
            os.makedirs("api_responses")
        
        # 获取目录并保存
        catalog = client.get(f'/order/catalog/public/eco?ovhSubsidiary={zone}')
        with open(os.path.join("api_responses", "catalog_response.json"), "w") as f:
            json.dump(catalog, f, indent=2)
        
        add_log("INFO", "已保存目录API原始响应")
        
        # 获取可用的服务器列表
        available_servers = client.get('/dedicated/server/datacenter/availabilities')
        with open(os.path.join("api_responses", "availability_response.json"), "w") as f:
            json.dump(available_servers, f, indent=2)
        
        add_log("INFO", "已保存可用性API原始响应")
        
        # 尝试获取一些具体服务器的详细信息
        if available_servers and len(available_servers) > 0:
            for i, server in enumerate(available_servers[:5]):  # 只获取前5个服务器的信息
                server_code = server.get("planCode")
                if server_code:
                    try:
                        server_details = client.get(f'/order/catalog/formatted/eco?planCode={server_code}&ovhSubsidiary={zone}')
                        with open(os.path.join("api_responses", f"server_details_{server_code}.json"), "w") as f:
                            json.dump(server_details, f, indent=2)
                        add_log("INFO", f"已保存服务器{server_code}的详细API响应")
                    except Exception as e:
                        add_log("WARNING", f"获取服务器{server_code}详细信息时出错: {str(e)}")
        
    except Exception as e:
        add_log("WARNING", f"保存API原始响应时出错: {str(e)}")

#移植过来的 send_telegram_msg 函数，适配 app.py 的 config
def send_telegram_msg(message: str):
    # 使用 app.py 的全局 config 字典
    tg_token = config.get("tgToken")
    tg_chat_id = config.get("tgChatId")

    if not tg_token:
        add_log("WARNING", "Telegram消息未发送: Bot Token未在config中设置")
        return False
    
    if not tg_chat_id:
        add_log("WARNING", "Telegram消息未发送: Chat ID未在config中设置")
        return False
    
    add_log("INFO", f"准备发送Telegram消息，ChatID: {tg_chat_id}, TokenLength: {len(tg_token)}")
    
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    payload = {
        "chat_id": tg_chat_id,
        "text": message
    }
    headers = {"Content-Type": "application/json"}

    try:
        add_log("INFO", f"发送HTTP请求到Telegram API: {url[:45]}...")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        add_log("INFO", f"Telegram API响应: 状态码={response.status_code}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                add_log("INFO", f"Telegram响应数据: {response_data}")
                add_log("INFO", "成功发送消息到Telegram")
                return True
            except Exception as json_error: # Changed from json.JSONDecodeError to generic Exception for wider catch, or could add 'import json'
                add_log("ERROR", f"解析Telegram响应JSON时出错: {str(json_error)}")
                return False # Explicitly return False here
        else:
            add_log("ERROR", f"发送消息到Telegram失败: 状态码={response.status_code}, 响应={response.text}")
            return False
    except requests.exceptions.Timeout:
        add_log("ERROR", "发送Telegram消息超时")
        return False
    except requests.exceptions.RequestException as e:
        add_log("ERROR", f"发送Telegram消息时发生网络错误: {str(e)}")
        return False
    except Exception as e:
        add_log("ERROR", f"发送Telegram消息时发生未预期错误: {str(e)}")
        add_log("ERROR", f"错误详情: {traceback.format_exc()}")
        return False

# Routes
@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify(config)

@app.route('/api/settings', methods=['POST'])
def save_settings():
    global config
    data = request.json
    
    # Store previous TG settings to check if they changed
    prev_tg_token = config.get("tgToken")
    prev_tg_chat_id = config.get("tgChatId")

    # Update config
    config = {
        "appKey": data.get("appKey", ""),
        "appSecret": data.get("appSecret", ""),
        "consumerKey": data.get("consumerKey", ""),
        "endpoint": data.get("endpoint", "ovh-eu"),
        "tgToken": data.get("tgToken", ""),
        "tgChatId": data.get("tgChatId", ""),
        "iam": data.get("iam", "go-ovh-ie"),
        "zone": data.get("zone", "IE")
    }
    
    # Auto-generate IAM if not set
    if not config["iam"]:
        config["iam"] = f"go-ovh-{config['zone'].lower()}"
    
    save_data()
    add_log("INFO", "API settings updated in config.json") # Clarified log message

    # Check if Telegram settings are present and if they have changed or were just set
    current_tg_token = config.get("tgToken")
    current_tg_chat_id = config.get("tgChatId")

    if current_tg_token and current_tg_chat_id:
        # Send test message if token or chat id is newly set or changed
        if (current_tg_token != prev_tg_token) or (current_tg_chat_id != prev_tg_chat_id) or not prev_tg_token or not prev_tg_chat_id :
            add_log("INFO", f"Telegram Token或Chat ID已更新/设置。尝试发送Telegram测试消息到 Chat ID: {current_tg_chat_id}")
            test_message_content = "OVH Phantom Sniper: Telegram 通知已成功配置 (来自 app.py 测试)"
            test_result = send_telegram_msg(test_message_content) # Call the移植过来的 function
            if test_result:
                add_log("INFO", "Telegram 测试消息发送成功。")
            else:
                add_log("WARNING", "Telegram 测试消息发送失败。请检查 Token 和 Chat ID 以及后端日志。")
        else:
            add_log("INFO", "Telegram 配置未更改，跳过测试消息。")
    else:
        add_log("INFO", "未配置 Telegram Token 或 Chat ID，跳过测试消息。")
    
    return jsonify({"status": "success"})

@app.route('/api/verify-auth', methods=['POST'])
def verify_auth():
    client = get_ovh_client()
    if not client:
        return jsonify({"valid": False})
    
    try:
        # Try a simple API call to check authentication
        client.get("/me")
        return jsonify({"valid": True})
    except Exception as e:
        add_log("ERROR", f"Authentication verification failed: {str(e)}")
        return jsonify({"valid": False})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify(logs)

@app.route('/api/logs', methods=['DELETE'])
def clear_logs():
    global logs
    logs = []
    save_data()
    add_log("INFO", "Logs cleared")
    return jsonify({"status": "success"})

@app.route('/api/queue', methods=['GET'])
def get_queue():
    return jsonify(queue)

@app.route('/api/queue', methods=['POST'])
def add_queue_item():
    data = request.json
    
    queue_item = {
        "id": str(uuid.uuid4()),
        "planCode": data.get("planCode", ""),
        "datacenter": data.get("datacenter", ""),
        "options": data.get("options", []),
        "status": "running",  # 直接设置为 running
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat(),
        "retryInterval": data.get("retryInterval", 30),
        "retryCount": 0, # 初始化为0, process_queue的首次检查会处理
        "lastCheckTime": 0 # 初始化为0, process_queue的首次检查会处理
    }
    
    queue.append(queue_item)
    save_data()
    update_stats()
    
    add_log("INFO", f"添加任务 {queue_item['id']} ({queue_item['planCode']} 在 {queue_item['datacenter']}) 到队列并立即启动 (状态: running)")
    return jsonify({"status": "success", "id": queue_item["id"]})

@app.route('/api/queue/<id>', methods=['DELETE'])
def remove_queue_item(id):
    global queue
    item = next((item for item in queue if item["id"] == id), None)
    if item:
        queue = [item for item in queue if item["id"] != id]
        save_data()
        update_stats()
        add_log("INFO", f"Removed {item['planCode']} from queue")
    
    return jsonify({"status": "success"})

@app.route('/api/queue/<id>/status', methods=['PUT'])
def update_queue_status(id):
    data = request.json
    item = next((item for item in queue if item["id"] == id), None)
    
    if item:
        item["status"] = data.get("status", "pending")
        item["updatedAt"] = datetime.now().isoformat()
        save_data()
        update_stats()
        
        add_log("INFO", f"Updated {item['planCode']} status to {item['status']}")
    
    return jsonify({"status": "success"})

@app.route('/api/purchase-history', methods=['GET'])
def get_purchase_history():
    return jsonify(purchase_history)

@app.route('/api/purchase-history', methods=['DELETE'])
def clear_purchase_history():
    global purchase_history
    purchase_history = []
    save_data()
    update_stats()
    add_log("INFO", "Purchase history cleared")
    return jsonify({"status": "success"})

@app.route('/api/servers', methods=['GET'])
def get_servers():
    show_api_servers = request.args.get('showApiServers', 'false').lower() == 'true'
    
    if show_api_servers and get_ovh_client():
        # Try to reload from API
        add_log("INFO", "正在从OVH API重新加载服务器列表...")
        api_servers = load_server_list()
        if api_servers:
            global server_plans
            server_plans = api_servers
            save_data()
            update_stats()
            add_log("INFO", f"从OVH API加载了 {len(server_plans)} 台服务器")
            
            # 记录硬件信息统计
            cpu_count = sum(1 for s in server_plans if s["cpu"] != "N/A")
            memory_count = sum(1 for s in server_plans if s["memory"] != "N/A")
            storage_count = sum(1 for s in server_plans if s["storage"] != "N/A")
            bandwidth_count = sum(1 for s in server_plans if s["bandwidth"] != "N/A")
            
            add_log("INFO", f"服务器硬件信息统计: CPU={cpu_count}/{len(server_plans)}, 内存={memory_count}/{len(server_plans)}, "
                   f"存储={storage_count}/{len(server_plans)}, 带宽={bandwidth_count}/{len(server_plans)}")
            
            # 记录几个示例服务器的详细信息，帮助排查
            if len(server_plans) > 0:
                sample_server = server_plans[0]
                add_log("INFO", f"示例服务器信息: {json.dumps(sample_server, indent=2)}")
        else:
            add_log("WARNING", "从OVH API加载服务器列表失败")
    
    # 确保返回的服务器对象具有所有必要字段
    validated_servers = []
    
    for server in server_plans:
        # 确保每个字段都有合理的默认值
        validated_server = {
            "planCode": server.get("planCode", "未知"),
            "name": server.get("name", "未命名服务器"),
            "description": server.get("description", ""),
            "cpu": server.get("cpu", "N/A"),
            "memory": server.get("memory", "N/A"),
            "storage": server.get("storage", "N/A"),
            "bandwidth": server.get("bandwidth", "N/A"),
            "vrackBandwidth": server.get("vrackBandwidth", "N/A"),
            "defaultOptions": server.get("defaultOptions", []),
            "availableOptions": server.get("availableOptions", []),
            "datacenters": server.get("datacenters", [])
        }
        
        # 确保数组类型的字段是有效的数组
        if not isinstance(validated_server["defaultOptions"], list):
            validated_server["defaultOptions"] = []
        
        if not isinstance(validated_server["availableOptions"], list):
            validated_server["availableOptions"] = []
        
        if not isinstance(validated_server["datacenters"], list):
            validated_server["datacenters"] = []
        
        validated_servers.append(validated_server)
    
    # 返回服务器列表数组，前端将直接处理这个数组
    return jsonify(validated_servers)

@app.route('/api/availability/<plan_code>', methods=['GET'])
def get_availability(plan_code):
    availability = check_server_availability(plan_code)
    if availability:
        return jsonify(availability)
    else:
        return jsonify({}), 404

@app.route('/api/stats', methods=['GET'])
def get_stats():
    update_stats()
    return jsonify(stats)

# 确保所有必要的文件都存在
def ensure_files_exist():
    # 检查并创建日志文件
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'w') as f:
            f.write('[]')
        print(f"已创建空的 {LOGS_FILE} 文件")
    
    # 检查并创建队列文件
    if not os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, 'w') as f:
            f.write('[]')
        print(f"已创建空的 {QUEUE_FILE} 文件")
    
    # 检查并创建历史记录文件
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w') as f:
            f.write('[]')
        print(f"已创建空的 {HISTORY_FILE} 文件")
    
    # 检查并创建服务器信息文件
    if not os.path.exists(SERVERS_FILE):
        with open(SERVERS_FILE, 'w') as f:
            f.write('[]')
        print(f"已创建空的 {SERVERS_FILE} 文件")
    
    # 检查并创建配置文件
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        print(f"已创建默认 {CONFIG_FILE} 文件")

if __name__ == '__main__':
    # 确保所有文件都存在
    ensure_files_exist()
    
    # Load data first
    load_data()
    
    # Start queue processor
    start_queue_processor()
    
    # Add initial log
    add_log("INFO", "Server started")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)

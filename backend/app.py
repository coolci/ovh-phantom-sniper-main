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
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'r') as f:
            logs = json.load(f)
    
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, 'r') as f:
            queue = json.load(f)
    
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            purchase_history = json.load(f)
    
    if os.path.exists(SERVERS_FILE):
        with open(SERVERS_FILE, 'r') as f:
            server_plans = json.load(f)
    
    # Update stats
    update_stats()
    
    logging.info("Data loaded from files")

# Save data to files
def save_data():
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
    
    try:
        # Check availability first
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
            add_log("INFO", f"Server {queue_item['planCode']} not available in {queue_item['datacenter']}", "purchase")
            return False
        
        # Create cart
        add_log("INFO", f"Creating cart for {config['zone']}", "purchase")
        cart_result = client.post('/order/cart', ovhSubsidiary=config["zone"])
        cart_id = cart_result["cartId"]
        add_log("INFO", f"Cart created with ID: {cart_id}", "purchase")
        
        # Assign cart
        add_log("INFO", f"Assigning cart {cart_id}", "purchase")
        client.post(f'/order/cart/{cart_id}/assign')
        
        # Add item to cart
        add_log("INFO", f"Adding {queue_item['planCode']} to cart", "purchase")
        item_payload = {
            "planCode": queue_item["planCode"],
            "pricingMode": "default",
            "duration": "P1M",  # 1 month
            "quantity": 1
        }
        item_result = client.post(f'/order/cart/{cart_id}/eco', **item_payload)
        item_id = item_result["itemId"]
        
        # Configure item
        required_config = client.get(f'/order/cart/{cart_id}/item/{item_id}/requiredConfiguration')
        
        configurations_to_set = {
            "dedicated_datacenter": queue_item["datacenter"],
            "dedicated_os": "none_64.en"
        }
        
        for label, value in configurations_to_set.items():
            add_log("INFO", f"Setting configuration {label}={value}", "purchase")
            client.post(f'/order/cart/{cart_id}/item/{item_id}/configuration',
                       label=label,
                       value=str(value))
        
        # Add options if any
        if queue_item["options"]:
            for option in queue_item["options"]:
                if not option:
                    continue
                
                try:
                    add_log("INFO", f"Adding option: {option}", "purchase")
                    option_payload = {
                        "planCode": option,
                        "pricingMode": "default",
                        "duration": "P1M",
                        "quantity": 1
                    }
                    client.post(f'/order/cart/{cart_id}/item/{item_id}/option', **option_payload)
                except Exception as option_error:
                    add_log("WARNING", f"Failed to add option {option}: {str(option_error)}", "purchase")
        
        # Checkout
        add_log("INFO", f"Checking out cart {cart_id}", "purchase")
        checkout_payload = {
            "autoPayWithPreferredPaymentMethod": False,
            "waiveRetractationPeriod": True
        }
        checkout_result = client.post(f'/order/cart/{cart_id}/checkout', **checkout_payload)
        
        # Create purchase history entry
        history_entry = {
            "id": str(uuid.uuid4()),
            "planCode": queue_item["planCode"],
            "datacenter": queue_item["datacenter"],
            "status": "success",
            "orderId": checkout_result.get("orderId", ""),
            "orderUrl": checkout_result.get("url", ""),
            "purchaseTime": datetime.now().isoformat()
        }
        purchase_history.append(history_entry)
        save_data()
        update_stats()
        
        add_log("INFO", f"Successfully purchased {queue_item['planCode']} in {queue_item['datacenter']}", "purchase")
        return True
    
    except Exception as e:
        # Create failed purchase history entry
        history_entry = {
            "id": str(uuid.uuid4()),
            "planCode": queue_item["planCode"],
            "datacenter": queue_item["datacenter"],
            "status": "failed",
            "errorMessage": str(e),
            "purchaseTime": datetime.now().isoformat()
        }
        purchase_history.append(history_entry)
        save_data()
        update_stats()
        
        add_log("ERROR", f"Failed to purchase {queue_item['planCode']}: {str(e)}", "purchase")
        return False

# Process queue items
def process_queue():
    while True:
        for item in queue:
            if item["status"] == "running":
                # Check if it's time to retry
                current_time = time.time()
                last_check_time = item.get("lastCheckTime", 0)
                
                if current_time - last_check_time >= item["retryInterval"]:
                    add_log("INFO", f"Checking availability for {item['planCode']} in {item['datacenter']}", "queue")
                    
                    # Update last check time
                    item["lastCheckTime"] = current_time
                    item["retryCount"] += 1
                    
                    # Try to purchase
                    if purchase_server(item):
                        item["status"] = "completed"
                        add_log("INFO", f"Purchase successful for {item['planCode']} in {item['datacenter']}", "queue")
                    else:
                        add_log("INFO", f"Server not available, retrying later", "queue")
                    
                    # Save queue state
                    save_data()
        
        # Sleep for a second before checking again
        time.sleep(1)

# Start queue processing thread
def start_queue_processor():
    thread = threading.Thread(target=process_queue)
    thread.daemon = True
    thread.start()

# Load server list from OVH API
def load_server_list():
    client = get_ovh_client()
    if not client:
        return []
    
    try:
        # Get server models
        catalog = client.get(f'/order/catalog/public/eco?ovhSubsidiary={config["zone"]}')
        plans = []
        
        for plan in catalog.get("plans", []):
            plan_code = plan.get("planCode")
            if not plan_code:
                continue
            
            # Get availability
            availabilities = client.get('/dedicated/server/datacenter/availabilities', planCode=plan_code)
            datacenters = []
            
            for item in availabilities:
                for dc in item.get("datacenters", []):
                    datacenters.append({
                        "datacenter": dc.get("datacenter"),
                        "availability": dc.get("availability", "unknown")
                    })
            
            # Extract server details
            default_options = []
            available_options = []
            
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
                
                # 方法 4: 检查plan.addonFamilies
                if plan.get("addonFamilies") and isinstance(plan.get("addonFamilies"), list):
                    for family in plan.get("addonFamilies"):
                        if not isinstance(family, dict) or not family.get("addons"):
                            continue
                            
                        for addon in family.get("addons"):
                            if not isinstance(addon, dict):
                                continue
                                
                            addon_plan_code = addon.get("planCode")
                            if not addon_plan_code:
                                continue
                            
                            # 跳过已经在默认选项或可选配置中的项目
                            if any(opt["value"] == addon_plan_code for opt in default_options) or any(opt["value"] == addon_plan_code for opt in available_options):
                                continue
                            
                            # 添加到可选配置列表
                            available_options.append({
                                "label": addon.get("description", addon_plan_code),
                                "value": addon_plan_code
                            })
                
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
                add_log("INFO", f"Found {len(default_options)} default options and {len(available_options)} available options for {plan_code}")
                
            except Exception as e:
                add_log("WARNING", f"Error parsing options for {plan_code}: {str(e)}")
            
            # 创建初始服务器信息对象
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
            
            # 获取服务器名称和描述，确保它们不为空
            if not server_info["name"] and plan.get("displayName"):
                server_info["name"] = plan.get("displayName")
            
            if not server_info["description"] and plan.get("displayName"):
                server_info["description"] = plan.get("displayName")
            
            # 解析方法 1: 尝试从properties中提取硬件详情
            try:
                if plan.get("details") and plan.get("details").get("properties"):
                    for prop in plan.get("details").get("properties"):
                        prop_name = prop.get("name", "").lower()
                        value = prop.get("value", "N/A")
                        
                        if value and value != "N/A":
                            if any(cpu_term in prop_name for cpu_term in ["cpu", "processor"]):
                                server_info["cpu"] = value
                            elif any(mem_term in prop_name for mem_term in ["memory", "ram"]):
                                server_info["memory"] = value
                            elif any(storage_term in prop_name for storage_term in ["storage", "disk", "hdd", "ssd"]):
                                server_info["storage"] = value
                            elif "bandwidth" in prop_name:
                                if any(private_term in prop_name for private_term in ["vrack", "private", "internal"]):
                                    server_info["vrackBandwidth"] = value
                                else:
                                    server_info["bandwidth"] = value
            except Exception as e:
                add_log("WARNING", f"Error parsing properties for {plan_code}: {str(e)}")
            
            # 解析方法 2: 尝试从名称中提取信息
            try:
                server_name = server_info["name"]
                
                # 检查是否为KS/RISE系列服务器，它们通常使用 "KS-XX | CPU信息" 格式
                if "|" in server_name:
                    parts = server_name.split("|")
                    if len(parts) > 1 and server_info["cpu"] == "N/A":
                        cpu_part = parts[1].strip()
                        server_info["cpu"] = cpu_part
                        
                        # 尝试从CPU部分提取更多信息
                        if "core" in cpu_part.lower():
                            # 例如: "4 Core, 8 Thread, xxxx"
                            core_parts = cpu_part.split(",")
                            if len(core_parts) > 1:
                                server_info["cpu"] = core_parts[0].strip()
                
                # 从服务器名称中提取内存信息
                if server_info["memory"] == "N/A":
                    ram_match = None
                    if "ram" in server_name.lower():
                        # 尝试匹配 "xxxGB RAM" 或 "RAM xxxGB" 格式
                        ram_parts = server_name.lower().split("ram")
                        for ram_part in ram_parts:
                            if "gb" in ram_part:
                                server_info["memory"] = ram_part.strip()
                                break
            except Exception as e:
                add_log("WARNING", f"Error parsing server name for {plan_code}: {str(e)}")
            
            # 解析方法 3: 尝试从产品配置中提取信息
            try:
                if plan.get("product") and plan.get("product").get("configurations"):
                    configs = plan.get("product").get("configurations")
                    for config in configs:
                        config_name = config.get("name", "").lower()
                        value = config.get("value")
                        
                        if value:
                            if any(cpu_term in config_name for cpu_term in ["cpu", "processor"]):
                                server_info["cpu"] = value
                            elif any(mem_term in config_name for mem_term in ["memory", "ram"]):
                                server_info["memory"] = value
                            elif any(storage_term in config_name for storage_term in ["storage", "disk", "hdd", "ssd"]):
                                server_info["storage"] = value
                            elif "bandwidth" in config_name:
                                server_info["bandwidth"] = value
            except Exception as e:
                add_log("WARNING", f"Error parsing product configurations for {plan_code}: {str(e)}")
            
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
                            
                        if server_info["memory"] == "N/A" and any(mem_term in part for mem_term in ["ram", "gb", "memory"]):
                            server_info["memory"] = part
                            
                        if server_info["storage"] == "N/A" and any(storage_term in part for storage_term in ["hdd", "ssd", "nvme", "storage", "disk"]):
                            server_info["storage"] = part
                            
                        if server_info["bandwidth"] == "N/A" and "bandwidth" in part:
                            server_info["bandwidth"] = part
            except Exception as e:
                add_log("WARNING", f"Error parsing description for {plan_code}: {str(e)}")
            
            # 解析方法 5: 从pricing获取信息
            try:
                if plan.get("pricing") and plan.get("pricing").get("configurations"):
                    pricing_configs = plan.get("pricing").get("configurations")
                    for price_config in pricing_configs:
                        config_name = price_config.get("name", "").lower()
                        value = price_config.get("value")
                        
                        if value:
                            if "processor" in config_name and server_info["cpu"] == "N/A":
                                server_info["cpu"] = value
                            elif "memory" in config_name and server_info["memory"] == "N/A":
                                server_info["memory"] = value
                            elif "storage" in config_name and server_info["storage"] == "N/A":
                                server_info["storage"] = value
            except Exception as e:
                add_log("WARNING", f"Error parsing pricing for {plan_code}: {str(e)}")
            
            # 清理提取的数据以确保格式一致
            # 对于CPU，添加一些基本信息如果只有核心数
            if server_info["cpu"] != "N/A" and server_info["cpu"].isdigit():
                server_info["cpu"] = f"{server_info['cpu']} 核心"
            
            plans.append(server_info)
        
        # 为所有服务器记录日志
        add_log("INFO", f"成功加载 {len(plans)} 台服务器信息")
        
        # 记录缺失信息的服务器
        missing_info_servers = [
            plan["planCode"] for plan in plans 
            if plan["cpu"] == "N/A" or plan["memory"] == "N/A" or plan["storage"] == "N/A"
        ]
        
        if missing_info_servers:
            add_log("WARNING", f"以下服务器缺少硬件信息: {', '.join(missing_info_servers)}")
        
        return plans
    except Exception as e:
        add_log("ERROR", f"Failed to load server list: {str(e)}")
        return []

# Routes
@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify(config)

@app.route('/api/settings', methods=['POST'])
def save_settings():
    global config
    data = request.json
    
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
    add_log("INFO", "API settings updated")
    
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
        "status": "pending",
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat(),
        "retryInterval": data.get("retryInterval", 30),
        "retryCount": 0,
        "lastCheckTime": 0
    }
    
    queue.append(queue_item)
    save_data()
    update_stats()
    
    add_log("INFO", f"Added {queue_item['planCode']} in {queue_item['datacenter']} to queue")
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
        api_servers = load_server_list()
        if api_servers:
            global server_plans
            server_plans = api_servers
            save_data()
            update_stats()
            add_log("INFO", f"Loaded {len(server_plans)} servers from OVH API")
    
    return jsonify(server_plans)

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

if __name__ == '__main__':
    # Load data first
    load_data()
    
    # Start queue processor
    start_queue_processor()
    
    # Add initial log
    add_log("INFO", "Server started")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)

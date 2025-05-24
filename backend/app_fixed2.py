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
            print(f"璀﹀憡: {CONFIG_FILE}鏂囦欢鏍煎紡涓嶆纭紝浣跨敤榛樿鍊?)
    
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, 'r') as f:
                content = f.read().strip()
                if content:  # 纭繚鏂囦欢涓嶆槸绌虹殑
                    logs = json.loads(content)
                else:
                    print(f"璀﹀憡: {LOGS_FILE}鏂囦欢涓虹┖锛屼娇鐢ㄧ┖鍒楄〃")
        except json.JSONDecodeError:
            print(f"璀﹀憡: {LOGS_FILE}鏂囦欢鏍煎紡涓嶆纭紝浣跨敤绌哄垪琛?)
    
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, 'r') as f:
                content = f.read().strip()
                if content:  # 纭繚鏂囦欢涓嶆槸绌虹殑
                    queue = json.loads(content)
                else:
                    print(f"璀﹀憡: {QUEUE_FILE}鏂囦欢涓虹┖锛屼娇鐢ㄧ┖鍒楄〃")
        except json.JSONDecodeError:
            print(f"璀﹀憡: {QUEUE_FILE}鏂囦欢鏍煎紡涓嶆纭紝浣跨敤绌哄垪琛?)
    
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                content = f.read().strip()
                if content:  # 纭繚鏂囦欢涓嶆槸绌虹殑
                    purchase_history = json.loads(content)
                else:
                    print(f"璀﹀憡: {HISTORY_FILE}鏂囦欢涓虹┖锛屼娇鐢ㄧ┖鍒楄〃")
        except json.JSONDecodeError:
            print(f"璀﹀憡: {HISTORY_FILE}鏂囦欢鏍煎紡涓嶆纭紝浣跨敤绌哄垪琛?)
    
    if os.path.exists(SERVERS_FILE):
        try:
            with open(SERVERS_FILE, 'r') as f:
                content = f.read().strip()
                if content:  # 纭繚鏂囦欢涓嶆槸绌虹殑
                    server_plans = json.loads(content)
                else:
                    print(f"璀﹀憡: {SERVERS_FILE}鏂囦欢涓虹┖锛屼娇鐢ㄧ┖鍒楄〃")
        except json.JSONDecodeError:
            print(f"璀﹀憡: {SERVERS_FILE}鏂囦欢鏍煎紡涓嶆纭紝浣跨敤绌哄垪琛?)
    
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
        logging.error(f"淇濆瓨鏁版嵁鏃跺嚭閿? {str(e)}")
        print(f"淇濆瓨鏁版嵁鏃跺嚭閿? {str(e)}")
        # 灏濊瘯鍗曠嫭淇濆瓨姣忎釜鏂囦欢
        try_save_file(CONFIG_FILE, config)
        try_save_file(LOGS_FILE, logs)
        try_save_file(QUEUE_FILE, queue)
        try_save_file(HISTORY_FILE, purchase_history)
        try_save_file(SERVERS_FILE, server_plans)

# 灏濊瘯淇濆瓨鍗曚釜鏂囦欢
def try_save_file(filename, data):
    try:
        with open(filename, 'w') as f:
            json.dump(data, f)
        print(f"鎴愬姛淇濆瓨 {filename}")
    except Exception as e:
        print(f"淇濆瓨 {filename} 鏃跺嚭閿? {str(e)}")

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
                
                # 纭繚鍙敤鎬х姸鎬佹湁姝ｇ‘鐨勫€?                if not availability or availability == "unknown":
                    result[datacenter_name] = "unknown"
                elif availability == "unavailable":
                    result[datacenter_name] = "unavailable"
                else:
                    # 浠讳綍闈?unavailable"鎴?unknown"鐨勭姸鎬侀兘琚涓?available"
                    result[datacenter_name] = availability
                
        add_log("INFO", f"鎴愬姛妫€鏌?{plan_code} 鐨勫彲鐢ㄦ€? {result}")
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
            # 杩囨护閫夐」锛屽彧淇濈暀纭欢鐩稿叧閫夐」
            filtered_options = []
            for option in queue_item["options"]:
                if not option:
                    continue
                
                option_lower = option.lower()
                # 鎺掗櫎璁稿彲璇佺浉鍏抽€夐」
                if (
                    # Windows璁稿彲璇?                    "windows-server" in option_lower or
                    # SQL Server璁稿彲璇?                    "sql-server" in option_lower or
                    # cPanel璁稿彲璇?                    "cpanel-license" in option_lower or
                    # Plesk璁稿彲璇?                    "plesk-" in option_lower or
                    # 鍏朵粬甯歌璁稿彲璇?                    "-license-" in option_lower or
                    # 鎿嶄綔绯荤粺閫夐」
                    option_lower.startswith("os-") or
                    # 鎺у埗闈㈡澘
                    "control-panel" in option_lower or
                    "panel" in option_lower
                ):
                    add_log("INFO", f"璺宠繃璁稿彲璇侀€夐」: {option}", "purchase")
                    continue
                
                filtered_options.append(option)
            
            add_log("INFO", f"杩囨护鍚庣殑纭欢閫夐」: {filtered_options}", "purchase")
            
            for option in filtered_options:
                try:
                    add_log("INFO", f"娣诲姞閫夐」: {option}", "purchase")
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
    global config
    client = get_ovh_client()
    if not client:
        return []
    
    try:
        # 璁板綍瀹屾暣鐨凙PI鍝嶅簲鐢ㄤ簬璋冭瘯
        try:
            add_log("INFO", f"姝ｅ湪浠嶰VH API鑾峰彇鏈嶅姟鍣ㄦ暟鎹?..")
            raw_response = client.get(f'/order/catalog/public/eco?ovhSubsidiary={config["zone"]}')
            with open("ovh_api_raw_response.json", "w") as f:
                json.dump(raw_response, f, indent=2)
            add_log("INFO", f"宸蹭繚瀛極VH API鍘熷鏁版嵁鍒皁vh_api_raw_response.json")
        except Exception as e:
            add_log("ERROR", f"淇濆瓨OVH API鍘熷鏁版嵁澶辫触: {str(e)}")
        
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
            
            # 娣诲姞鏁版嵁涓績鐨勫悕绉板拰鍖哄煙淇℃伅
            for dc in datacenters:
                dc_code = dc.get("datacenter", "").lower()[:3]  # 鍙栧墠涓変釜瀛楃浣滀负鏁版嵁涓績浠ｇ爜
                
                # 鏍规嵁浠ｇ爜璁剧疆鍚嶇О鍜屽尯鍩?                if dc_code == "gra":
                    dc["dcName"] = "鏍兼媺澶凹鑼?
                    dc["region"] = "娉曞浗"
                elif dc_code == "sbg":
                    dc["dcName"] = "鏂壒鎷夋柉鍫?
                    dc["region"] = "娉曞浗"
                elif dc_code == "rbx":
                    dc["dcName"] = "椴佽礉"
                    dc["region"] = "娉曞浗"
                elif dc_code == "bhs":
                    dc["dcName"] = "鍗氶樋灏旇"
                    dc["region"] = "鍔犳嬁澶?
                elif dc_code == "hil":
                    dc["dcName"] = "甯屽皵鏂集鍕?
                    dc["region"] = "缇庡浗"
                elif dc_code == "vin":
                    dc["dcName"] = "缁翠篃绾?
                    dc["region"] = "缇庡浗"
                elif dc_code == "lim":
                    dc["dcName"] = "鍒╅┈绱㈠皵"
                    dc["region"] = "濉炴郸璺柉"
                elif dc_code == "sgp":
                    dc["dcName"] = "鏂板姞鍧?
                    dc["region"] = "鏂板姞鍧?
                elif dc_code == "syd":
                    dc["dcName"] = "鎮夊凹"
                    dc["region"] = "婢冲ぇ鍒╀簹"
                elif dc_code == "waw":
                    dc["dcName"] = "鍗庢矙"
                    dc["region"] = "娉㈠叞"
                elif dc_code == "fra":
                    dc["dcName"] = "娉曞叞鍏嬬"
                    dc["region"] = "寰峰浗"
                elif dc_code == "lon":
                    dc["dcName"] = "浼︽暒"
                    dc["region"] = "鑻卞浗"
                elif dc_code == "eri":
                    dc["dcName"] = "鍘勬柉娌冨皵"
                    dc["region"] = "鑻卞浗"
                else:
                    dc["dcName"] = dc.get("datacenter", "鏈煡")
                    dc["region"] = "鏈煡"
            
            # Extract server details
            default_options = []
            available_options = []
            
            # 鍒涘缓鍒濆鏈嶅姟鍣ㄤ俊鎭璞?- 纭繚鍦ㄨВ鏋愮壒瀹氬瓧娈靛墠灏卞凡鍒涘缓
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
            
            # 鑾峰彇鏈嶅姟鍣ㄥ悕绉板拰鎻忚堪锛岀‘淇濆畠浠笉涓虹┖
            if not server_info["name"] and plan.get("displayName"):
                server_info["name"] = plan.get("displayName")
            
            if not server_info["description"] and plan.get("displayName"):
                server_info["description"] = plan.get("displayName")
            
            # 鑾峰彇鎺ㄨ崘閰嶇疆鍜屽彲閫夐厤缃?- 浣跨敤澶氱鏂规硶澶勭悊涓嶅悓鏍煎紡
            try:
                # 鏂规硶 1: 妫€鏌lan.default.options
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
                
                # 鏂规硶 2: 妫€鏌lan.addons
                if plan.get("addons") and isinstance(plan.get("addons"), list):
                    for addon in plan.get("addons"):
                        if not isinstance(addon, dict):
                            continue
                            
                        addon_plan_code = addon.get("planCode")
                        if not addon_plan_code:
                            continue
                        
                        # 璺宠繃宸茬粡鍦ㄩ粯璁ら€夐」涓殑閰嶇疆
                        if any(opt["value"] == addon_plan_code for opt in default_options):
                            continue
                        
                        # 娣诲姞鍒板彲閫夐厤缃垪琛?                        available_options.append({
                            "label": addon.get("description", addon_plan_code),
                            "value": addon_plan_code
                        })
                
                # 鏂规硶 3: 妫€鏌lan.product.options
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
                
                # 鏂规硶 4: 灏濊瘯浠巔lan.addonFamilies涓彁鍙栫‖浠朵俊鎭?                printed_example = False
                try:
                    if plan.get("addonFamilies") and isinstance(plan.get("addonFamilies"), list):
                        # 鎵撳嵃涓€涓畬鏁寸殑addonFamilies绀轰緥鐢ㄤ簬璋冭瘯
                        if len(plan.get("addonFamilies")) > 0 and not printed_example:
                            add_log("INFO", f"addonFamilies绀轰緥: {json.dumps(plan.get('addonFamilies')[0], indent=2)}")
                            printed_example = True
                        
                        # 灏濊瘯淇濆瓨鎵€鏈夊甫瀹界浉鍏崇殑閫夐」鐢ㄤ簬璋冭瘯
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
                                add_log("INFO", f"宸蹭繚瀛榹plan_code}鐨勫甫瀹介€夐」鍒癰andwidth_options_{plan_code}.json")
                        except Exception as e:
                            add_log("WARNING", f"淇濆瓨甯﹀閫夐」鏃跺嚭閿? {str(e)}")
                        
                        # 閲嶇疆鍙€夐厤缃垪琛?                        temp_available_options = []
                        
                        # 鎻愬彇addonFamilies淇℃伅
                        for family in plan.get("addonFamilies"):
                            family_name = family.get("name", "").lower()  # 娉ㄦ剰: 鍦ˋPI鍝嶅簲涓槸'name'鑰屼笉鏄?family'
                            default_addon = family.get("default")  # 鑾峰彇榛樿閫夐」
                            
                            # 鎻愬彇鍙€夐厤缃?                            if family.get("addons") and isinstance(family.get("addons"), list):
                                for addon_code in family.get("addons"):
                                    # 鍦ˋPI鍝嶅簲涓紝addons鏄瓧绗︿覆鏁扮粍鑰屼笉鏄璞℃暟缁?                                    if not isinstance(addon_code, str):
                                        continue
                                    
                                    # 鏍囪鏄惁涓洪粯璁ら€夐」
                                    is_default = (addon_code == default_addon)
                                    
                                    # 浠巃ddon_code瑙ｆ瀽鎻忚堪淇℃伅
                                    addon_desc = addon_code
                                    
                                    # 杩囨护鎺夎鍙瘉鐩稿叧閫夐」
                                    if (
                                        # Windows璁稿彲璇?                                        "windows-server" in addon_code.lower() or
                                        # SQL Server璁稿彲璇?                                        "sql-server" in addon_code.lower() or
                                        # cPanel璁稿彲璇?                                        "cpanel-license" in addon_code.lower() or
                                        # Plesk璁稿彲璇?                                        "plesk-" in addon_code.lower() or
                                        # 鍏朵粬甯歌璁稿彲璇?                                        "-license-" in addon_code.lower() or
                                        # 鎿嶄綔绯荤粺閫夐」
                                        addon_code.lower().startswith("os-") or
                                        # 鎺у埗闈㈡澘
                                        "control-panel" in addon_code.lower() or
                                        "panel" in addon_code.lower()
                                    ):
                                        # 璺宠繃璁稿彲璇佺被閫夐」
                                        continue
                                    
                                    if addon_code:
                                        temp_available_options.append({
                                            "label": addon_desc,
                                            "value": addon_code,
                                            "family": family_name,
                                            "isDefault": is_default
                                        })
                                        
                                        # 濡傛灉鏄粯璁ら€夐」锛屾坊鍔犲埌榛樿閫夐」鍒楄〃
                                        if is_default:
                                            default_options.append({
                                                "label": addon_desc,
                                                "value": addon_code
                                            })
                            
                            # 鏍规嵁family鍚嶇О璁剧疆瀵瑰簲鐨勭‖浠朵俊鎭?                            if family_name and family.get("addons") and isinstance(family.get("addons"), list):
                                # 鑾峰彇榛樿閫夐」鐨勫€?                                default_value = family.get("default")
                                
                                # CPU淇℃伅
                                if ("cpu" in family_name or "processor" in family_name) and server_info["cpu"] == "N/A":
                                    if default_value:
                                        server_info["cpu"] = default_value
                                        add_log("INFO", f"浠巃ddonFamilies榛樿閫夐」鎻愬彇CPU: {default_value} 缁?{plan_code}")
                                
                                # 鍐呭瓨淇℃伅
                                elif ("memory" in family_name or "ram" in family_name) and server_info["memory"] == "N/A":
                                    if default_value:
                                        # 灏濊瘯鎻愬彇鍐呭瓨澶у皬
                                        ram_size = ""
                                        ram_match = re.search(r'ram-(\d+)g', default_value, re.IGNORECASE)
                                        if ram_match:
                                            ram_size = f"{ram_match.group(1)} GB"
                                            server_info["memory"] = ram_size
                                            add_log("INFO", f"浠巃ddonFamilies榛樿閫夐」鎻愬彇鍐呭瓨: {ram_size} 缁?{plan_code}")
                                        else:
                                            server_info["memory"] = default_value
                                            add_log("INFO", f"浠巃ddonFamilies榛樿閫夐」鎻愬彇鍐呭瓨(鍘熷鍊?: {default_value} 缁?{plan_code}")
                                
                                # 瀛樺偍淇℃伅
                                elif ("storage" in family_name or "disk" in family_name or "drive" in family_name or "ssd" in family_name or "hdd" in family_name) and server_info["storage"] == "N/A":
                                    if default_value:
                                        # 灏濊瘯浠庡瓨鍌ㄤ唬鐮佷腑鎻愬彇淇℃伅
                                        storage_match = re.search(r'(\d+)x(\d+)(ssd|hdd|nvme)', default_value, re.IGNORECASE)
                                        if storage_match:
                                            count = storage_match.group(1)
                                            size = storage_match.group(2)
                                            type_str = storage_match.group(3).upper()
                                            server_info["storage"] = f"{count}x {size}GB {type_str}"
                                            add_log("INFO", f"浠巃ddonFamilies榛樿閫夐」鎻愬彇瀛樺偍: {server_info['storage']} 缁?{plan_code}")
                                        else:
                                            server_info["storage"] = default_value
                                            add_log("INFO", f"浠巃ddonFamilies榛樿閫夐」鎻愬彇瀛樺偍(鍘熷鍊?: {default_value} 缁?{plan_code}")
                                
                                # 甯﹀淇℃伅
                                elif ("bandwidth" in family_name or "traffic" in family_name or "network" in family_name) and server_info["bandwidth"] == "N/A":
                                    if default_value:
                                        add_log("DEBUG", f"澶勭悊甯﹀閫夐」: {default_value}")
                                        
                                        # 鏍煎紡1: traffic-5tb-100-24sk-apac (甯﹀闄愬埗鍜屾祦閲忛檺鍒?
                                        traffic_bw_match = re.search(r'traffic-(\d+)(tb|gb|mb)-(\d+)', default_value, re.IGNORECASE)
                                        if traffic_bw_match:
                                            size = traffic_bw_match.group(1)
                                            unit = traffic_bw_match.group(2).upper()
                                            bw_value = traffic_bw_match.group(3)
                                            server_info["bandwidth"] = f"{bw_value} Mbps / {size} {unit}娴侀噺"
                                            add_log("INFO", f"浠巃ddonFamilies榛樿閫夐」鎻愬彇甯﹀鍜屾祦閲? {server_info['bandwidth']} 缁?{plan_code}")
                                        
                                        # 鏍煎紡2: traffic-5tb (浠呮祦閲忛檺鍒?
                                        elif re.search(r'traffic-(\d+)(tb|gb|mb)$', default_value, re.IGNORECASE):
                                            simple_traffic_match = re.search(r'traffic-(\d+)(tb|gb|mb)', default_value, re.IGNORECASE)
                                            size = simple_traffic_match.group(1)
                                            unit = simple_traffic_match.group(2).upper()
                                            server_info["bandwidth"] = f"{size} {unit}娴侀噺"
                                            add_log("INFO", f"浠巃ddonFamilies榛樿閫夐」鎻愬彇娴侀噺: {server_info['bandwidth']} 缁?{plan_code}")
                                        
                                        # 鏍煎紡3: bandwidth-100 (浠呭甫瀹介檺鍒?
                                        elif re.search(r'bandwidth-(\d+)', default_value, re.IGNORECASE):
                                            bandwidth_match = re.search(r'bandwidth-(\d+)', default_value, re.IGNORECASE)
                                            bw_value = int(bandwidth_match.group(1))
                                            if bw_value >= 1000:
                                                server_info["bandwidth"] = f"{bw_value/1000:.1f} Gbps".replace(".0 ", " ")
                                            else:
                                                server_info["bandwidth"] = f"{bw_value} Mbps"
                                            add_log("INFO", f"浠巃ddonFamilies榛樿閫夐」鎻愬彇甯﹀: {server_info['bandwidth']} 缁?{plan_code}")
                                        
                                        # 鏍煎紡4: traffic-unlimited (鏃犻檺娴侀噺)
                                        elif "traffic-unlimited" in default_value.lower():
                                            server_info["bandwidth"] = "鏃犻檺娴侀噺"
                                            add_log("INFO", f"浠巃ddonFamilies榛樿閫夐」鎻愬彇甯﹀: 鏃犻檺娴侀噺 缁?{plan_code}")
                                        
                                        # 鏍煎紡5: bandwidth-guarantee (淇濊瘉甯﹀)
                                        elif "guarantee" in default_value.lower() or "guaranteed" in default_value.lower():
                                            bw_guarantee_match = re.search(r'(\d+)', default_value)
                                            if bw_guarantee_match:
                                                bw_value = int(bw_guarantee_match.group(1))
                                                server_info["bandwidth"] = f"{bw_value} Mbps (淇濊瘉甯﹀)"
                                                add_log("INFO", f"浠巃ddonFamilies榛樿閫夐」鎻愬彇淇濊瘉甯﹀: {server_info['bandwidth']} 缁?{plan_code}")
                                            else:
                                                server_info["bandwidth"] = "淇濊瘉甯﹀"
                                                add_log("INFO", f"浠巃ddonFamilies榛樿閫夐」鎻愬彇淇濊瘉甯﹀(鏃犲叿浣撳€? 缁?{plan_code}")
                                        
                                        # 鏃犳硶璇嗗埆鐨勬牸寮忥紝浣跨敤鍘熷鍊?                                        else:
                                            server_info["bandwidth"] = default_value
                                            add_log("INFO", f"浠巃ddonFamilies榛樿閫夐」鎻愬彇甯﹀(鍘熷鍊?: {default_value} 缁?{plan_code}")
                        
                        # 灏嗗鐞嗗ソ鐨勫彲閫夐厤缃坊鍔犲埌鏈嶅姟鍣ㄤ俊鎭腑
                        if temp_available_options:
                            available_options = temp_available_options
                
                except Exception as e:
                    add_log("ERROR", f"瑙ｆ瀽addonFamilies鏃跺嚭閿? {str(e)}")
                    add_log("ERROR", f"閿欒璇︽儏: {traceback.format_exc()}")
                
                # 鏂规硶 5: 妫€鏌lan.pricings涓殑閰嶇疆椤?                if plan.get("pricings") and isinstance(plan.get("pricings"), dict):
                    for pricing_key, pricing_value in plan.get("pricings").items():
                        if isinstance(pricing_value, dict) and pricing_value.get("options"):
                            for option_code, option_details in pricing_value.get("options").items():
                                # 璺宠繃宸茬粡鍦ㄥ叾浠栧垪琛ㄤ腑鐨勯」鐩?                                if any(opt["value"] == option_code for opt in default_options) or any(opt["value"] == option_code for opt in available_options):
                                    continue
                                
                                option_label = option_code
                                if isinstance(option_details, dict) and option_details.get("description"):
                                    option_label = option_details.get("description")
                                
                                available_options.append({
                                    "label": option_label,
                                    "value": option_code
                                })
                
                # 璁板綍鎵惧埌鐨勯€夐」鏁伴噺
                add_log("INFO", f"鎵惧埌 {len(default_options)} 涓粯璁ら€夐」鍜?{len(available_options)} 涓彲閫夐厤缃敤浜?{plan_code}")
                
            except Exception as e:
                add_log("WARNING", f"瑙ｆ瀽 {plan_code} 閫夐」鏃跺嚭閿? {str(e)}")
            
            # 瑙ｆ瀽鏂规硶 1: 灏濊瘯浠巔roperties涓彁鍙栫‖浠惰鎯?            try:
                if plan.get("details") and plan.get("details").get("properties"):
                    for prop in plan.get("details").get("properties"):
                        prop_name = prop.get("name", "").lower()
                        value = prop.get("value", "N/A")
                        
                        if value and value != "N/A":
                            if any(cpu_term in prop_name for cpu_term in ["cpu", "processor"]):
                                server_info["cpu"] = value
                                add_log("INFO", f"浠巔roperties鎻愬彇CPU: {value} 缁?{plan_code}")
                            elif any(mem_term in prop_name for mem_term in ["memory", "ram"]):
                                server_info["memory"] = value
                                add_log("INFO", f"浠巔roperties鎻愬彇鍐呭瓨: {value} 缁?{plan_code}")
                            elif any(storage_term in prop_name for storage_term in ["storage", "disk", "hdd", "ssd"]):
                                server_info["storage"] = value
                                add_log("INFO", f"浠巔roperties鎻愬彇瀛樺偍: {value} 缁?{plan_code}")
                            elif "bandwidth" in prop_name:
                                if any(private_term in prop_name for private_term in ["vrack", "private", "internal"]):
                                    server_info["vrackBandwidth"] = value
                                    add_log("INFO", f"浠巔roperties鎻愬彇vRack甯﹀: {value} 缁?{plan_code}")
                                else:
                                    server_info["bandwidth"] = value
                                    add_log("INFO", f"浠巔roperties鎻愬彇甯﹀: {value} 缁?{plan_code}")
            except Exception as e:
                add_log("WARNING", f"瑙ｆ瀽 {plan_code} 灞炴€ф椂鍑洪敊: {str(e)}")
            
            # 瑙ｆ瀽鏂规硶 2: 灏濊瘯浠庡悕绉颁腑鎻愬彇淇℃伅
            try:
                server_name = server_info["name"]
                server_desc = server_info["description"] if server_info["description"] else ""
                
                # 淇濆瓨鍘熷鏁版嵁鐢ㄤ簬璋冭瘯
                try:
                    with open(f"server_details_{plan_code}.json", "w") as f:
                        json.dump({
                            "name": server_name,
                            "description": server_desc,
                            "planCode": plan_code
                        }, f, indent=2)
                except Exception as e:
                    add_log("WARNING", f"淇濆瓨鏈嶅姟鍣ㄨ鎯呮椂鍑洪敊: {str(e)}")
                
                # 妫€鏌ユ槸鍚︿负KS/RISE绯诲垪鏈嶅姟鍣紝瀹冧滑閫氬父浣跨敤 "KS-XX | CPU淇℃伅" 鏍煎紡
                if "|" in server_name:
                    parts = server_name.split("|")
                    if len(parts) > 1 and server_info["cpu"] == "N/A":
                        cpu_part = parts[1].strip()
                        server_info["cpu"] = cpu_part
                        add_log("INFO", f"浠庢湇鍔″櫒鍚嶇О鎻愬彇CPU: {cpu_part} 缁?{plan_code}")
                        
                        # 灏濊瘯浠嶤PU閮ㄥ垎鎻愬彇鏇村淇℃伅
                        if "core" in cpu_part.lower():
                            # 渚嬪: "4 Core, 8 Thread, xxxx"
                            core_parts = cpu_part.split(",")
                            if len(core_parts) > 1:
                                server_info["cpu"] = core_parts[0].strip()
                
                # 鎻愬彇CPU鍨嬪彿淇℃伅
                if server_info["cpu"] == "N/A":
                    # 灏濊瘯鍖归厤甯歌鐨凜PU鍏抽敭璇?                    cpu_keywords = ["i7-", "i9-", "ryzen", "xeon", "epyc", "cpu", "intel", "amd", "processor"]
                    full_text = f"{server_name} {server_desc}".lower()
                    
                    for keyword in cpu_keywords:
                        if keyword in full_text.lower():
                            # 鎵惧埌鍏抽敭璇嶇殑浣嶇疆
                            pos = full_text.lower().find(keyword)
                            if pos >= 0:
                                # 鎻愬彇鍏抽敭璇嶅懆鍥寸殑鏂囨湰
                                start = max(0, pos - 5)
                                end = min(len(full_text), pos + 25)
                                cpu_text = full_text[start:end]
                                
                                # 灏濊瘯娓呯悊鎻愬彇鐨勬枃鏈?                                cpu_text = re.sub(r'[^\w\s\-,.]', ' ', cpu_text)
                                cpu_text = ' '.join(cpu_text.split())
                                
                                if cpu_text:
                                    server_info["cpu"] = cpu_text
                                    add_log("INFO", f"浠庢枃鏈腑鎻愬彇CPU鍏抽敭瀛? {cpu_text} 缁?{plan_code}")
                                    break
                
                # 浠庢湇鍔″櫒鍚嶇О涓彁鍙栧唴瀛樹俊鎭?                if server_info["memory"] == "N/A":
                    # 瀵绘壘鍐呭瓨鍏抽敭璇?                    mem_match = None
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
                        add_log("INFO", f"浠庢枃鏈腑鎻愬彇鍐呭瓨: {server_info['memory']} 缁?{plan_code}")
                
                # 浠庢湇鍔″櫒鍚嶇О涓彁鍙栧瓨鍌ㄤ俊鎭?                if server_info["storage"] == "N/A":
                    # 瀵绘壘瀛樺偍鍏抽敭璇?                    storage_patterns = [
                        r'(\d+)\s*[xX]\s*(\d+)\s*GB\s*(SSD|HDD|NVMe)',
                        r'(\d+)\s*(SSD|HDD|NVMe)\s*(\d+)\s*GB',
                        r'(\d+)\s*TB\s*(SSD|HDD|NVMe)',
                        r'(\d+)\s*(SSD|HDD|NVMe)'
                    ]
                    
                    full_text = f"{server_name} {server_desc}"
                    for pattern in storage_patterns:
                        match = re.search(pattern, full_text, re.IGNORECASE)
                        if match:
                            if match.lastindex == 3:  # 鍖归厤浜嗙涓€绉嶆ā寮?                                count = match.group(1)
                                size = match.group(2)
                                disk_type = match.group(3).upper()
                                server_info["storage"] = f"{count}x {size}GB {disk_type}"
                            elif match.lastindex == 2:  # 鍖归厤浜嗘渶鍚庝竴绉嶆ā寮?                                size = match.group(1)
                                disk_type = match.group(2).upper()
                                server_info["storage"] = f"{size} {disk_type}"
                            
                            add_log("INFO", f"浠庢枃鏈腑鎻愬彇瀛樺偍: {server_info['storage']} 缁?{plan_code}")
                            break
            except Exception as e:
                add_log("WARNING", f"瑙ｆ瀽 {plan_code} 鏈嶅姟鍣ㄥ悕绉版椂鍑洪敊: {str(e)}")
                add_log("WARNING", f"閿欒璇︽儏: {traceback.format_exc()}")
            
            # 瑙ｆ瀽鏂规硶 3: 灏濊瘯浠庝骇鍝侀厤缃腑鎻愬彇淇℃伅
            try:
                if plan.get("product") and plan.get("product").get("configurations"):
                    configs = plan.get("product").get("configurations")
                    for config in configs:
                        config_name = config.get("name", "").lower()
                        value = config.get("value")
                        
                        if value:
                            if any(cpu_term in config_name for cpu_term in ["cpu", "processor"]):
                                server_info["cpu"] = value
                                add_log("INFO", f"浠庝骇鍝侀厤缃彁鍙朇PU: {value} 缁?{plan_code}")
                            elif any(mem_term in config_name for mem_term in ["memory", "ram"]):
                                server_info["memory"] = value
                                add_log("INFO", f"浠庝骇鍝侀厤缃彁鍙栧唴瀛? {value} 缁?{plan_code}")
                            elif any(storage_term in config_name for storage_term in ["storage", "disk", "hdd", "ssd"]):
                                server_info["storage"] = value
                                add_log("INFO", f"浠庝骇鍝侀厤缃彁鍙栧瓨鍌? {value} 缁?{plan_code}")
                            elif "bandwidth" in config_name:
                                server_info["bandwidth"] = value
                                add_log("INFO", f"浠庝骇鍝侀厤缃彁鍙栧甫瀹? {value} 缁?{plan_code}")
            except Exception as e:
                add_log("WARNING", f"瑙ｆ瀽 {plan_code} 浜у搧閰嶇疆鏃跺嚭閿? {str(e)}")
            
            # 瑙ｆ瀽鏂规硶 4: 灏濊瘯浠巇escription瑙ｆ瀽淇℃伅
            try:
                description = plan.get("description", "")
                if description:
                    parts = description.split(",")
                    for part in parts:
                        part = part.strip().lower()
                        
                        # 妫€鏌ユ瘡涓儴鍒嗘槸鍚﹀寘鍚‖浠朵俊鎭?                        if server_info["cpu"] == "N/A" and any(cpu_term in part for cpu_term in ["cpu", "core", "i7", "i9", "xeon", "epyc", "ryzen"]):
                            server_info["cpu"] = part
                            add_log("INFO", f"浠庢弿杩版彁鍙朇PU: {part} 缁?{plan_code}")
                            
                        if server_info["memory"] == "N/A" and any(mem_term in part for mem_term in ["ram", "gb", "memory"]):
                            server_info["memory"] = part
                            add_log("INFO", f"浠庢弿杩版彁鍙栧唴瀛? {part} 缁?{plan_code}")
                            
                        if server_info["storage"] == "N/A" and any(storage_term in part for storage_term in ["hdd", "ssd", "nvme", "storage", "disk"]):
                            server_info["storage"] = part
                            add_log("INFO", f"浠庢弿杩版彁鍙栧瓨鍌? {part} 缁?{plan_code}")
                            
                        if server_info["bandwidth"] == "N/A" and "bandwidth" in part:
                            server_info["bandwidth"] = part
                            add_log("INFO", f"浠庢弿杩版彁鍙栧甫瀹? {part} 缁?{plan_code}")
            except Exception as e:
                add_log("WARNING", f"瑙ｆ瀽 {plan_code} 鎻忚堪鏃跺嚭閿? {str(e)}")
            
            # 瑙ｆ瀽鏂规硶 5: 浠巔ricing鑾峰彇淇℃伅
            try:
                if plan.get("pricing") and plan.get("pricing").get("configurations"):
                    pricing_configs = plan.get("pricing").get("configurations")
                    for price_config in pricing_configs:
                        config_name = price_config.get("name", "").lower()
                        value = price_config.get("value")
                        
                        if value:
                            if "processor" in config_name and server_info["cpu"] == "N/A":
                                server_info["cpu"] = value
                                add_log("INFO", f"浠巔ricing閰嶇疆鎻愬彇CPU: {value} 缁?{plan_code}")
                            elif "memory" in config_name and server_info["memory"] == "N/A":
                                server_info["memory"] = value
                                add_log("INFO", f"浠巔ricing閰嶇疆鎻愬彇鍐呭瓨: {value} 缁?{plan_code}")
                            elif "storage" in config_name and server_info["storage"] == "N/A":
                                server_info["storage"] = value
                                add_log("INFO", f"浠巔ricing閰嶇疆鎻愬彇瀛樺偍: {value} 缁?{plan_code}")
            except Exception as e:
                add_log("WARNING", f"瑙ｆ瀽 {plan_code} pricing閰嶇疆鏃跺嚭閿? {str(e)}")
            
            # 娓呯悊鎻愬彇鐨勬暟鎹互纭繚鏍煎紡涓€鑷?            # 瀵逛簬CPU锛屾坊鍔犱竴浜涘熀鏈俊鎭鏋滃彧鏈夋牳蹇冩暟
            if server_info["cpu"] != "N/A" and server_info["cpu"].isdigit():
                server_info["cpu"] = f"{server_info['cpu']} 鏍稿績"
            
            # 鏇存柊鏈嶅姟鍣ㄤ俊鎭腑鐨勯厤缃€夐」
            server_info["defaultOptions"] = default_options
            server_info["availableOptions"] = available_options
            
            plans.append(server_info)
        
        # 涓烘墍鏈夋湇鍔″櫒璁板綍鏃ュ織
        add_log("INFO", f"鎴愬姛鍔犺浇 {len(plans)} 鍙版湇鍔″櫒淇℃伅")
        
        # 璁板綍缂哄け淇℃伅鐨勬湇鍔″櫒
        missing_info_servers = [
            plan["planCode"] for plan in plans 
            if plan["cpu"] == "N/A" or plan["memory"] == "N/A" or plan["storage"] == "N/A"
        ]
        
        if missing_info_servers:
            add_log("WARNING", f"浠ヤ笅鏈嶅姟鍣ㄧ己灏戠‖浠朵俊鎭? {', '.join(missing_info_servers)}")
        
        return plans
    except Exception as e:
        add_log("ERROR", f"鍔犺浇鏈嶅姟鍣ㄥ垪琛ㄥけ璐? {str(e)}")
        add_log("ERROR", f"閿欒璇︽儏: {traceback.format_exc()}")
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
        add_log("INFO", "姝ｅ湪浠嶰VH API閲嶆柊鍔犺浇鏈嶅姟鍣ㄥ垪琛?..")
        api_servers = load_server_list()
        if api_servers:
            global server_plans
            server_plans = api_servers
            save_data()
            update_stats()
            add_log("INFO", f"浠嶰VH API鍔犺浇浜?{len(server_plans)} 鍙版湇鍔″櫒")
            
            # 璁板綍纭欢淇℃伅缁熻
            cpu_count = sum(1 for s in server_plans if s["cpu"] != "N/A")
            memory_count = sum(1 for s in server_plans if s["memory"] != "N/A")
            storage_count = sum(1 for s in server_plans if s["storage"] != "N/A")
            bandwidth_count = sum(1 for s in server_plans if s["bandwidth"] != "N/A")
            
            add_log("INFO", f"鏈嶅姟鍣ㄧ‖浠朵俊鎭粺璁? CPU={cpu_count}/{len(server_plans)}, 鍐呭瓨={memory_count}/{len(server_plans)}, "
                   f"瀛樺偍={storage_count}/{len(server_plans)}, 甯﹀={bandwidth_count}/{len(server_plans)}")
            
            # 璁板綍鍑犱釜绀轰緥鏈嶅姟鍣ㄧ殑璇︾粏淇℃伅锛屽府鍔╂帓鏌?            if len(server_plans) > 0:
                sample_server = server_plans[0]
                add_log("INFO", f"绀轰緥鏈嶅姟鍣ㄤ俊鎭? {json.dumps(sample_server, indent=2)}")
        else:
            add_log("WARNING", "浠嶰VH API鍔犺浇鏈嶅姟鍣ㄥ垪琛ㄥけ璐?)
    
    # 杩斿洖鍖呰鐨勬暟鎹粨鏋勶紝浠ヤ究鍓嶇鍙互姝ｇ‘澶勭悊
    response = {"servers": server_plans}
    return jsonify(response)

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

# 纭繚鎵€鏈夊繀瑕佺殑鏂囦欢閮藉瓨鍦?def ensure_files_exist():
    # 妫€鏌ュ苟鍒涘缓鏃ュ織鏂囦欢
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'w') as f:
            f.write('[]')
        print(f"宸插垱寤虹┖鐨?{LOGS_FILE} 鏂囦欢")
    
    # 妫€鏌ュ苟鍒涘缓闃熷垪鏂囦欢
    if not os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, 'w') as f:
            f.write('[]')
        print(f"宸插垱寤虹┖鐨?{QUEUE_FILE} 鏂囦欢")
    
    # 妫€鏌ュ苟鍒涘缓鍘嗗彶璁板綍鏂囦欢
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w') as f:
            f.write('[]')
        print(f"宸插垱寤虹┖鐨?{HISTORY_FILE} 鏂囦欢")
    
    # 妫€鏌ュ苟鍒涘缓鏈嶅姟鍣ㄤ俊鎭枃浠?    if not os.path.exists(SERVERS_FILE):
        with open(SERVERS_FILE, 'w') as f:
            f.write('[]')
        print(f"宸插垱寤虹┖鐨?{SERVERS_FILE} 鏂囦欢")
    
    # 妫€鏌ュ苟鍒涘缓閰嶇疆鏂囦欢
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        print(f"宸插垱寤洪粯璁?{CONFIG_FILE} 鏂囦欢")

if __name__ == '__main__':
    # 纭繚鎵€鏈夋枃浠堕兘瀛樺湪
    ensure_files_exist()
    
    # Load data first
    load_data()
    
    # Start queue processor
    start_queue_processor()
    
    # Add initial log
    add_log("INFO", "Server started")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)


import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useAPI } from "@/context/APIContext";
import axios from "axios";
import { toast } from "sonner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Cpu, Database, Wifi, HardDrive, CheckSquare, Square, Settings, ArrowRightLeft } from "lucide-react";
import { apiEvents } from "@/context/APIContext";

// Backend API URL (update this to match your backend)
const API_URL = 'http://localhost:5000/api';

// OVH数据中心常量
const OVH_DATACENTERS = [
  { code: "gra", name: "格拉夫尼茨", region: "法国" },
  { code: "sbg", name: "斯特拉斯堡", region: "法国" },
  { code: "rbx", name: "鲁贝", region: "法国" },
  { code: "bhs", name: "博阿尔诺", region: "加拿大" },
  { code: "hil", name: "希尔斯伯勒", region: "美国" },
  { code: "vin", name: "维也纳", region: "美国" },
  { code: "lim", name: "利马索尔", region: "塞浦路斯" },
  { code: "sgp", name: "新加坡", region: "新加坡" },
  { code: "syd", name: "悉尼", region: "澳大利亚" },
  { code: "waw", name: "华沙", region: "波兰" },
  { code: "fra", name: "法兰克福", region: "德国" },
  { code: "lon", name: "伦敦", region: "英国" },
  { code: "eri", name: "厄斯沃尔", region: "英国" }
];

interface ServerOption {
  label: string;
  value: string;
  family?: string;
  isDefault?: boolean;
}

interface ServerPlan {
  planCode: string;
  name: string;
  description?: string;
  cpu: string;
  memory: string;
  storage: string;
  bandwidth: string;
  vrackBandwidth: string;
  defaultOptions: ServerOption[];
  availableOptions: ServerOption[];
  datacenters: {
    datacenter: string;
    dcName: string;
    region: string;
    availability: string;
  }[];
}

const ServersPage = () => {
  const { isAuthenticated } = useAPI();
  const [servers, setServers] = useState<ServerPlan[]>([]);
  const [filteredServers, setFilteredServers] = useState<ServerPlan[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDatacenter, setSelectedDatacenter] = useState<string>("all");
  const [datacenters, setDatacenters] = useState<string[]>([]);
  const [isCheckingAvailability, setIsCheckingAvailability] = useState(false);
  const [availability, setAvailability] = useState<Record<string, Record<string, string>>>({});
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
  // 为每个服务器的数据中心选择状态设置映射
  const [selectedDatacenters, setSelectedDatacenters] = useState<Record<string, Record<string, boolean>>>({});
  // 用于跟踪当前选中的服务器
  const [selectedServer, setSelectedServer] = useState<string | null>(null);
  // 保存每个服务器的选中选项
  const [selectedOptions, setSelectedOptions] = useState<Record<string, string[]>>({});

  // Fetch servers from the backend
  const fetchServers = async () => {
    setIsLoading(true);
    try {
      console.log("开始获取服务器数据...");
      const response = await axios.get(`${API_URL}/servers`, {
        params: { showApiServers: isAuthenticated }
      });
      
      // 调试输出查看原始服务器数据
      console.log("原始服务器数据:", response.data);
      
      // 确保我们从正确的数据结构中获取服务器列表
      let serversList = [];
      
      if (response.data && typeof response.data === 'object') {
        if (Array.isArray(response.data)) {
          serversList = response.data;
        } else if (response.data.servers && Array.isArray(response.data.servers)) {
          serversList = response.data.servers;
        }
      }
      
      // 进一步校验服务器列表的有效性
      if (!Array.isArray(serversList)) {
        console.error("无效的服务器列表格式:", serversList);
        toast.error("获取服务器列表失败: 数据格式错误");
        setIsLoading(false);
        return;
      }
      
      console.log("解析后的服务器列表:", serversList);
      console.log(`获取到 ${serversList.length} 台服务器`);
      
      // 确保每个服务器都有正确的数据结构
      const formattedServers = serversList.map((server: ServerPlan) => {
        // 验证必要字段是否存在
        const formattedServer = {
          ...server,
          planCode: server.planCode || "未知",
          name: server.name || "未命名服务器",
          description: server.description || "",
          cpu: server.cpu || "N/A",
          memory: server.memory || "N/A", 
          storage: server.storage || "N/A",
          bandwidth: server.bandwidth || "N/A",
          vrackBandwidth: server.vrackBandwidth || "N/A",
          defaultOptions: Array.isArray(server.defaultOptions) ? server.defaultOptions : [],
          availableOptions: Array.isArray(server.availableOptions) ? server.availableOptions : [],
          datacenters: Array.isArray(server.datacenters) ? server.datacenters : []
        };
        
        // 显示额外调试信息
        console.log(`服务器 ${formattedServer.planCode} 硬件信息:`, {
          cpu: formattedServer.cpu,
          memory: formattedServer.memory,
          storage: formattedServer.storage,
          bandwidth: formattedServer.bandwidth
        });
        
        return formattedServer;
      });
      
      console.log("格式化后的服务器列表:", formattedServers);
      
      // 初始化数据中心选择状态
      const dcSelections: Record<string, Record<string, boolean>> = {};
      formattedServers.forEach(server => {
        dcSelections[server.planCode] = {};
        server.datacenters.forEach(dc => {
          dcSelections[server.planCode][dc.datacenter] = false;
        });
      });
      
      // 收集所有数据中心
      const allDatacenters = new Set<string>();
      formattedServers.forEach(server => {
        server.datacenters.forEach(dc => {
          allDatacenters.add(dc.datacenter);
        });
      });
      setDatacenters(Array.from(allDatacenters));
      
      setSelectedDatacenters(dcSelections);
      setServers(formattedServers);
      setIsLoading(false);
      
      // 检查是否有服务器缺少硬件信息
      const missingInfoServers = formattedServers.filter(
        server => server.cpu === "N/A" || server.memory === "N/A" || server.storage === "N/A"
      );
      
      if (missingInfoServers.length > 0) {
        console.warn("以下服务器缺少硬件信息:", missingInfoServers.map(s => s.planCode).join(", "));
      }
      
    } catch (error) {
      console.error("获取服务器列表时出错:", error);
      toast.error("获取服务器列表失败");
      setIsLoading(false);
    }
  };

  // Format server specifications for better display
  const formatServerSpec = (value: string, type: string): string => {
    if (!value || value === "N/A") return "暂无数据";
    
    // 清理值
    value = value.trim();
    
    // 对于CPU，尝试格式化
    if (type === "CPU") {
      // 已经有完整描述的情况
      if (value.toLowerCase().includes("intel") || 
          value.toLowerCase().includes("amd") || 
          value.toLowerCase().includes("ryzen") || 
          value.toLowerCase().includes("xeon") || 
          value.toLowerCase().includes("epyc")) {
        return value;
      }
      
      // 处理OVH API返回的CPU值格式 (通常是planCode)
      const cpuNameMatch = value.match(/cpu-([a-z0-9-]+)/i);
      if (cpuNameMatch) {
        // 尝试从planCode中提取CPU型号
        const cpuName = cpuNameMatch[1]
          .replace(/-/g, ' ')
          .replace(/(\d+)c(\d+)t/i, '$1核$2线程')
          .replace(/(\d+)c/i, '$1核')
          .replace(/i(\d+)/i, 'Intel Core i$1');
        
        return cpuName.charAt(0).toUpperCase() + cpuName.slice(1);
      }
      
      // 尝试从不同格式中提取信息
      if (value.includes("x")) {
        // 已经是格式 "4 x Intel Xeon"
        return value;
      } else if (!isNaN(Number(value))) {
        return `${value} 核心`;
      }
      
      // 专门处理core关键词
      if (value.toLowerCase().includes("core")) {
        return value;
      }
      
      return value;
    }
    
    // 对于内存，转换为GB表示
    if (type === "内存") {
      // 已经包含单位
      if (value.toLowerCase().includes("gb") || 
          value.toLowerCase().includes("mb") || 
          value.toLowerCase().includes("tb")) {
        return value;
      } 
      
      // 处理OVH API返回的内存值格式
      const ramMatch = value.match(/ram-(\d+)g/i);
      if (ramMatch) {
        return `${ramMatch[1]} GB`;
      }
      
      // 尝试处理纯数字
      if (!isNaN(Number(value))) {
        const num = Number(value);
        // 大于1000的可能是MB为单位
        if (num > 1000) {
          return `${(num/1024).toFixed(0)} GB`;
        }
        return `${num} GB`;
      }
      
      // 尝试提取数字部分
      const numMatch = value.match(/(\d+)/);
      if (numMatch && numMatch[1]) {
        const num = parseInt(numMatch[1]);
        if (num > 0) {
          if (num > 1000) {
            return `${(num/1024).toFixed(0)} GB`;
          }
          return `${num} GB`;
        }
      }
      
      return value;
    }
    
    // 对于存储
    if (type === "存储") {
      // 已经包含单位
      if (value.toLowerCase().includes("gb") || 
          value.toLowerCase().includes("tb") || 
          value.toLowerCase().includes("ssd") || 
          value.toLowerCase().includes("hdd") || 
          value.toLowerCase().includes("nvme")) {
        return value;
      }
      
      // 处理OVH API返回的存储值格式
      const storageMatch = value.match(/(raid|softraid)-(\d+)x(\d+)(ssd|hdd|nvme)/i);
      if (storageMatch) {
        const raidType = storageMatch[1].toUpperCase();
        const count = storageMatch[2];
        const size = storageMatch[3];
        const diskType = storageMatch[4].toUpperCase();
        return `${raidType} ${count}x ${size}GB ${diskType}`;
      }
      
      // 尝试处理纯数字
      if (!isNaN(Number(value))) {
        const num = Number(value);
        if (num >= 1000) {
          return `${(num/1000).toFixed(1)} TB`;
        }
        return `${num} GB`;
      }
      
      // 尝试匹配常见的存储格式，如 "2x500GB SSD"
      const simpleStorageMatch = value.match(/(\d+)x(\d+)(GB|TB|G|T)?/i);
      if (simpleStorageMatch) {
        const count = parseInt(simpleStorageMatch[1]);
        const size = parseInt(simpleStorageMatch[2]);
        const unit = simpleStorageMatch[3]?.toUpperCase() || "GB";
        const sizeStr = unit.includes("T") ? `${size}TB` : `${size}GB`;
        return `${count}x ${sizeStr}`;
      }
      
      return value;
    }
    
    // 对于带宽
    if (type.includes("带宽")) {
      // 已经包含单位或特殊格式
      if (value.toLowerCase().includes("gbps") || 
          value.toLowerCase().includes("mbps") || 
          value.toLowerCase().includes("gbit") || 
          value.toLowerCase().includes("mbit") ||
          value.toLowerCase().includes("流量") ||
          value.toLowerCase().includes("无限") ||
          value.toLowerCase().includes("保证")) {
        return value;
      }
      
      // 处理带宽和流量组合格式 "traffic-5tb-100-24sk-apac"
      const combinedTrafficMatch = value.match(/traffic-(\d+)(tb|gb|mb)-(\d+)/i);
      if (combinedTrafficMatch) {
        const trafficSize = combinedTrafficMatch[1];
        const trafficUnit = combinedTrafficMatch[2].toUpperCase();
        const bandwidth = combinedTrafficMatch[3];
        return `${bandwidth} Mbps / ${trafficSize} ${trafficUnit}流量`;
      }
      
      // 处理无限流量
      if (value.toLowerCase().includes("unlimited")) {
        return "无限流量";
      }
      
      // 处理保证带宽
      if (value.toLowerCase().includes("guarantee")) {
        const bwMatch = value.match(/(\d+)/);
        if (bwMatch) {
          return `${bwMatch[1]} Mbps (保证带宽)`;
        }
        return "保证带宽";
      }
      
      // 处理OVH API返回的带宽值格式
      const trafficMatch = value.match(/traffic-(\d+)(tb|gb|mb|m|g)/i);
      if (trafficMatch) {
        const size = trafficMatch[1];
        const unit = trafficMatch[2].toLowerCase();
        if (unit === 'tb' || unit === 't') {
          return `${size} TB流量`;
        } else if (unit === 'gb' || unit === 'g') {
          return `${size} GB流量`;
        } else {
          return `${size} MB流量`;
        }
      }
      
      // 处理bandwidth格式
      const bandwidthMatch = value.match(/bandwidth-(\d+)/i);
      if (bandwidthMatch) {
        const bwValue = parseInt(bandwidthMatch[1]);
        if (bwValue >= 1000) {
          return `${bwValue/1000} Gbps`.replace(".0 ", " ");
        }
        return `${bwValue} Mbps`;
      }
      
      // 尝试处理纯数字
      if (!isNaN(Number(value))) {
        const num = Number(value);
        if (num >= 1000) {
          return `${(num/1000).toFixed(1)} Gbps`;
        }
        return `${num} Mbps`;
      }
      
      // 尝试匹配带宽格式
      const bwMatch = value.match(/(\d+)([mg])/i);
      if (bwMatch) {
        const size = parseInt(bwMatch[1]);
        const unit = bwMatch[2].toLowerCase();
        if (unit === 'g') {
          return `${size} Gbps`;
        } else if (unit === 'm') {
          return `${size} Mbps`;
        }
      }
      
      return value;
    }
    
    return value;
  };

  // Check availability for a specific server plan
  const checkAvailability = async (planCode: string) => {
    if (!isAuthenticated) {
      toast.error("请先配置 API 设置");
      return;
    }
    
    setIsCheckingAvailability(true);
    try {
      const response = await axios.get(`${API_URL}/availability/${planCode}`);
      console.log(`获取到 ${planCode} 的可用性数据:`, response.data);
      
      setAvailability(prev => ({
        ...prev,
        [planCode]: response.data
      }));
      
      toast.success(`已更新 ${planCode} 可用性信息`);
    } catch (error) {
      console.error(`Error checking availability for ${planCode}:`, error);
      toast.error(`获取 ${planCode} 可用性失败`);
    } finally {
      setIsCheckingAvailability(false);
    }
  };

  // 切换特定服务器的数据中心选择状态
  const toggleDatacenterSelection = (serverPlanCode: string, datacenter: string) => {
    setSelectedDatacenters(prev => ({
      ...prev,
      [serverPlanCode]: {
        ...prev[serverPlanCode],
        [datacenter]: !prev[serverPlanCode]?.[datacenter]
      }
    }));
  };

  // 全选或取消全选特定服务器的所有数据中心
  const toggleAllDatacenters = (serverPlanCode: string, selected: boolean) => {
    setSelectedDatacenters(prev => {
      const newServerState = { ...prev };
      if (newServerState[serverPlanCode]) {
        Object.keys(newServerState[serverPlanCode]).forEach(dc => {
          newServerState[serverPlanCode][dc] = selected;
        });
      }
      return newServerState;
    });
  };

  // 获取特定服务器已选中的数据中心列表
  const getSelectedDatacentersList = (serverPlanCode: string): string[] => {
    if (!selectedDatacenters[serverPlanCode]) return [];
    
    return Object.entries(selectedDatacenters[serverPlanCode])
      .filter(([_, selected]) => selected)
      .map(([dc]) => dc.toLowerCase());
  };

  // 切换选项，支持单选逻辑
  const toggleOption = (serverPlanCode: string, optionValue: string, groupName?: string) => {
    setSelectedOptions(prev => {
      let currentOptions = [...(prev[serverPlanCode] || [])];
      const index = currentOptions.indexOf(optionValue);
      
      if (index >= 0) {
        // 如果选项已经选中，则移除它
        currentOptions.splice(index, 1);
      } else {
        // 如果选项未选中，并且提供了组名，则实现单选逻辑
        if (groupName) {
          // 获取服务器的所有可用选项
          const serverOptions = servers.find(s => s.planCode === serverPlanCode)?.availableOptions || [];
          
          // 找出同组中的其他选项，并从当前选中列表中移除
          serverOptions.forEach(option => {
            const optionFamily = option.family?.toLowerCase() || "";
            const optionLabel = option.label.toLowerCase();
            
            // 检查此选项是否属于同一组
            let isInSameGroup = false;
            
            if (groupName === "CPU/处理器" && 
                (optionFamily.includes("cpu") || optionFamily.includes("processor") || 
                 optionLabel.includes("cpu") || optionLabel.includes("processor"))) {
              isInSameGroup = true;
            } else if (groupName === "内存" && 
                      (optionFamily.includes("memory") || optionFamily.includes("ram") || 
                       optionLabel.includes("ram") || optionLabel.includes("memory"))) {
              isInSameGroup = true;
            } else if (groupName === "存储" && 
                      (optionFamily.includes("storage") || optionFamily.includes("disk") || 
                       optionLabel.includes("ssd") || optionLabel.includes("hdd"))) {
              isInSameGroup = true;
            } else if (groupName === "带宽/网络" && 
                      (optionFamily.includes("bandwidth") || optionFamily.includes("traffic") || 
                       optionLabel.includes("bandwidth") || optionLabel.includes("network"))) {
              isInSameGroup = true;
            }
            
            // 如果是同组选项且不是当前选择的选项，则从选中列表中移除
            if (isInSameGroup && option.value !== optionValue) {
              const idx = currentOptions.indexOf(option.value);
              if (idx >= 0) {
                currentOptions.splice(idx, 1);
              }
            }
          });
        }
        
        // 添加当前选择的选项
        currentOptions.push(optionValue);
      }
      
      return {
        ...prev,
        [serverPlanCode]: currentOptions
      };
    });
  };

  // 判断选项是否已选中
  const isOptionSelected = (serverPlanCode: string, optionValue: string): boolean => {
    return selectedOptions[serverPlanCode]?.includes(optionValue) || false;
  };

  // 添加到抢购队列的函数，支持多数据中心
  const addToQueue = async (server: ServerPlan, datacenters: string[]) => {
    if (!isAuthenticated) {
      toast.error("请先配置 API 设置");
      return;
    }

    if (datacenters.length === 0) {
      toast.error("请至少选择一个数据中心");
      return;
    }
    
    try {
      // 过滤选项，只保留硬件相关的
      const filterHardwareOptions = (options: string[]) => {
        return options.filter(option => {
          const optionLower = option.toLowerCase();
          
          // 排除许可证相关选项
          if (
            // Windows许可证
            optionLower.includes("windows-server") ||
            // SQL Server许可证
            optionLower.includes("sql-server") ||
            // cPanel许可证
            optionLower.includes("cpanel-license") ||
            // Plesk许可证
            optionLower.includes("plesk-") ||
            // 其他常见许可证
            optionLower.includes("-license-") ||
            // 操作系统选项
            optionLower.startsWith("os-") ||
            // 控制面板
            optionLower.includes("control-panel") ||
            optionLower.includes("panel") ||
            // 安全产品
            optionLower.includes("security") ||
            optionLower.includes("antivirus") ||
            optionLower.includes("firewall")
          ) {
            return false;
          }
          
          return true;
        });
      };
      
      // 获取最终选项，如果用户选择了自定义选项则使用那些，否则使用默认选项
      let options = selectedOptions[server.planCode]?.length > 0 
        ? selectedOptions[server.planCode] 
        : server.defaultOptions.map(opt => opt.value);
      
      // 过滤掉非硬件相关选项
      options = filterHardwareOptions(options);
      
      console.log("提交的硬件选项:", options);

      // 为每个选中的数据中心创建一个抢购请求
      const promises = datacenters.map(datacenter => 
        axios.post(`${API_URL}/queue`, {
          planCode: server.planCode,
          datacenter,
          options: options,
        })
      );
      
      await Promise.all(promises);
      toast.success(`已将 ${server.planCode} 添加到 ${datacenters.length} 个数据中心的抢购队列`);
    } catch (error) {
      console.error("Error adding to queue:", error);
      toast.error("添加到抢购队列失败");
    }
  };

  // Subscribe to API auth changes to reload servers when auth status changes
  useEffect(() => {
    // Initial fetch
    fetchServers();
    
    // Subscribe to auth change events
    const unsubscribe = apiEvents.onAuthChanged(() => {
      fetchServers();
    });
    
    return () => {
      unsubscribe();
    };
  }, []);

  // Apply filters when search term or datacenter changes
  useEffect(() => {
    if (servers.length === 0) return;
    
    let filtered = [...servers];
    
    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        server => 
          server.planCode.toLowerCase().includes(term) ||
          server.name.toLowerCase().includes(term) ||
          server.cpu.toLowerCase().includes(term) ||
          server.memory.toLowerCase().includes(term)
      );
    }
    
    // Apply datacenter filter
    if (selectedDatacenter !== "all") {
      filtered = filtered.filter(server => 
        server.datacenters.some(dc => dc.datacenter === selectedDatacenter)
      );
    }
    
    setFilteredServers(filtered);
  }, [searchTerm, selectedDatacenter, servers]);

  // 初始化选项
  useEffect(() => {
    // 如果服务器数据加载完成，初始化默认选项
    if (servers.length > 0) {
      const defaultServerOptions: Record<string, string[]> = {};
      servers.forEach(server => {
        defaultServerOptions[server.planCode] = server.defaultOptions.map(opt => opt.value);
      });
      setSelectedOptions(defaultServerOptions);
    }
  }, [servers]);

  // 分类并显示服务器配置选项
  const renderServerOptions = (server: ServerPlan) => {
    // 过滤掉许可证相关的选项，只保留硬件相关选项
    const filteredOptions = server.availableOptions ? server.availableOptions.filter(option => {
      const optionValue = option.value.toLowerCase();
      const optionLabel = option.label.toLowerCase();
      
      // 排除许可证相关选项
      if (
        // Windows许可证
        optionValue.includes("windows-server") ||
        // SQL Server许可证
        optionValue.includes("sql-server") ||
        // cPanel许可证
        optionValue.includes("cpanel-license") ||
        // Plesk许可证
        optionValue.includes("plesk-") ||
        // 其他常见许可证
        optionValue.includes("-license-") ||
        // 操作系统选项
        optionValue.startsWith("os-") ||
        // 控制面板
        optionValue.includes("control-panel") ||
        optionValue.includes("panel") ||
        // 其他软件许可
        optionLabel.includes("license") ||
        optionLabel.includes("许可证") ||
        optionLabel.includes("许可") ||
        // 安全产品
        optionValue.includes("security") ||
        optionValue.includes("antivirus") ||
        optionValue.includes("firewall")
      ) {
        return false;
      }
      
      return true;
    }) : [];
    
    const filteredDefaultOptions = server.defaultOptions ? server.defaultOptions.filter(option => {
      const optionValue = option.value.toLowerCase();
      const optionLabel = option.label.toLowerCase();
      
      // 排除许可证相关选项
      if (
        // Windows许可证
        optionValue.includes("windows-server") ||
        // SQL Server许可证
        optionValue.includes("sql-server") ||
        // cPanel许可证
        optionValue.includes("cpanel-license") ||
        // Plesk许可证
        optionValue.includes("plesk-") ||
        // 其他常见许可证
        optionValue.includes("-license-") ||
        // 操作系统选项
        optionValue.startsWith("os-") ||
        // 控制面板
        optionValue.includes("control-panel") ||
        optionValue.includes("panel") ||
        // 其他软件许可
        optionLabel.includes("license") ||
        optionLabel.includes("许可证") ||
        optionLabel.includes("许可") ||
        // 安全产品
        optionValue.includes("security") ||
        optionValue.includes("antivirus") ||
        optionValue.includes("firewall")
      ) {
        return false;
      }
      
      return true;
    }) : [];
    
    // 如果没有任何硬件相关的可选和默认配置，则不显示任何内容
    if (filteredOptions.length === 0 && filteredDefaultOptions.length === 0) {
      return null;
    }
    
    // 判断可选配置和默认配置内容是否完全一致
    const defaultSet = new Set(filteredDefaultOptions.map(opt => opt.value));
    const optionSet = new Set(filteredOptions.map(opt => opt.value));
    let optionsIdentical = false;
    if (defaultSet.size === optionSet.size && [...defaultSet].every(v => optionSet.has(v))) {
      optionsIdentical = true;
    }

    // 尝试根据选项分类将选项分组
    const optionGroups: Record<string, ServerOption[]> = {
      "CPU/处理器": [],
      "内存": [],
      "存储": [],
      "带宽/网络": [],
      "其他": []
    };
    
    // 根据family或描述关键字分配选项到不同分组
    filteredOptions.forEach(option => {
      const family = option.family?.toLowerCase() || "";
      const desc = option.label.toLowerCase();
      
      if (family.includes("cpu") || family.includes("processor") || 
          desc.includes("cpu") || desc.includes("processor") || 
          desc.includes("intel") || desc.includes("amd") || 
          desc.includes("xeon") || desc.includes("epyc") || 
          desc.includes("ryzen") || desc.includes("core")) {
        optionGroups["CPU/处理器"].push(option);
      }
      else if (family.includes("memory") || family.includes("ram") || 
               desc.includes("ram") || desc.includes("memory") || 
               desc.includes("gb") || desc.includes("ddr")) {
        optionGroups["内存"].push(option);
      }
      else if (family.includes("storage") || family.includes("disk") || 
               desc.includes("ssd") || desc.includes("hdd") || 
               desc.includes("nvme") || desc.includes("storage") || 
               desc.includes("disk") || desc.includes("raid")) {
        optionGroups["存储"].push(option);
      }
      else if (family.includes("bandwidth") || family.includes("traffic") || 
               desc.includes("bandwidth") || desc.includes("network") || 
               desc.includes("ip") || desc.includes("带宽") || 
               desc.includes("mbps") || desc.includes("gbps")) {
        optionGroups["带宽/网络"].push(option);
      }
      else {
        optionGroups["其他"].push(option);
      }
    });
    
    // 检查是否有任何选项被分组（确保至少有一个组有内容）
    const hasGroupedOptions = Object.values(optionGroups).some(group => group.length > 0);
    
    // 渲染分组选项
    return (
      <div className="space-y-3">
        {filteredDefaultOptions.length > 0 && (
          <div>
            <div className="font-medium text-cyber-accent mb-1">默认配置</div>
            <div className="flex flex-wrap gap-1 mb-3">
              {filteredDefaultOptions.map(option => (
                <div
                  key={option.value}
                  className="bg-cyber-accent/10 px-2 py-1 rounded text-xs border border-cyber-accent/20 text-cyber-accent"
                >
                  {option.label}
                </div>
              ))}
            </div>
          </div>
        )}
        {/* 只有当可选配置和默认配置不一致时才显示可选配置区域 */}
        {!optionsIdentical && hasGroupedOptions && (
          <div className="mt-2">
            <div className="font-medium text-cyber-blue mb-1">可选配置</div>
            {Object.entries(optionGroups).map(([groupName, options]) => {
              if (options.length === 0) return null;
              return (
                <div key={groupName} className="mb-3">
                  <div className="font-medium text-cyber-blue mb-1">{groupName}</div>
                  <div className="space-y-1 mb-2">
                    {options.map(option => {
                      // 格式化显示值，添加友好值+原始值双重显示
                      let displayLabel = option.label;
                      
                      // 对于RAM，尝试提取内存大小
                      if (groupName === "内存" && option.value.includes("ram-")) {
                        const ramMatch = option.value.match(/ram-(\d+)g/i);
                        if (ramMatch) {
                          displayLabel = `${ramMatch[1]}GB (${option.value})`;
                        }
                      }
                      
                      // 对于存储，尝试提取容量和类型
                      if ((groupName === "存储" && option.value.includes("raid")) || option.value.includes("ssd") || option.value.includes("hdd") || option.value.includes("nvme")) {
                        // 匹配 hybridsoftraid-2x6000sa-2x512nvme-24rise 这样的格式
                        const hybridRaidMatch = option.value.match(/hybridsoftraid-(\d+)x(\d+)(sa|ssd|hdd)-(\d+)x(\d+)(nvme|ssd|hdd)/i);
                        if (hybridRaidMatch) {
                          const count1 = hybridRaidMatch[1];
                          const size1 = hybridRaidMatch[2];
                          const type1 = hybridRaidMatch[3].toUpperCase();
                          const count2 = hybridRaidMatch[4];
                          const size2 = hybridRaidMatch[5];
                          const type2 = hybridRaidMatch[6].toUpperCase();
                          displayLabel = `混合RAID ${count1}x ${size1}GB ${type1} + ${count2}x ${size2}GB ${type2} (${option.value})`;
                        } else {
                          // 标准RAID格式
                          const storageMatch = option.value.match(/(raid|softraid)-(\d+)x(\d+)(sa|ssd|hdd|nvme)/i);
                          if (storageMatch) {
                            const raidType = storageMatch[1].toUpperCase();
                            const count = storageMatch[2];
                            const size = storageMatch[3];
                            const diskType = storageMatch[4].toUpperCase();
                            displayLabel = `${raidType} ${count}x ${size}GB ${diskType} (${option.value})`;
                          }
                        }
                      }
                      
                      // 对于带宽，尝试提取速率
                      if (groupName === "带宽/网络" && (option.value.includes("bandwidth") || option.value.includes("traffic"))) {
                        const bwMatch = option.value.match(/bandwidth-(\d+)/i);
                        if (bwMatch) {
                          const speed = parseInt(bwMatch[1]);
                          displayLabel = speed >= 1000 
                            ? `${speed/1000} Gbps (${option.value})` 
                            : `${speed} Mbps (${option.value})`;
                        }
                        
                        // 匹配格式如 traffic-25tb-1000-24rise-apac
                        const combinedTrafficMatch = option.value.match(/traffic-(\d+)(tb|gb|mb)-(\d+)/i);
                        if (combinedTrafficMatch) {
                          const trafficSize = combinedTrafficMatch[1];
                          const trafficUnit = combinedTrafficMatch[2].toUpperCase();
                          const bandwidth = combinedTrafficMatch[3];
                          displayLabel = `${bandwidth} Mbps / ${trafficSize} ${trafficUnit}流量 (${option.value})`;
                        } else {
                          // 匹配仅有流量限制的格式 traffic-25tb
                          const trafficMatch = option.value.match(/traffic-(\d+)(tb|gb)/i);
                          if (trafficMatch) {
                            displayLabel = `${trafficMatch[1]} ${trafficMatch[2].toUpperCase()} 流量 (${option.value})`;
                          }
                        }

                        // 匹配无限流量
                        if (option.value.toLowerCase().includes("unlimited")) {
                          displayLabel = `无限流量 (${option.value})`;
                        }
                      }
                      
                      return (
                        <div key={option.value} className="flex items-center">
                          <label className="cyber-radio-container flex items-center cursor-pointer">
                            <input
                              type="radio"
                              name={`${server.planCode}-${groupName}`}
                              checked={isOptionSelected(server.planCode, option.value)}
                              onChange={() => toggleOption(server.planCode, option.value, groupName)}
                              className="mr-2"
                            />
                            <span className="text-sm">{displayLabel}</span>
                          </label>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { 
      opacity: 1,
      transition: { 
        staggerChildren: 0.05
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  };

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h1 className="text-3xl font-bold mb-1 cyber-glow-text">服务器列表</h1>
        <p className="text-cyber-muted mb-6">浏览可用服务器与实时可用性检测</p>
      </motion.div>

      {/* Filters and controls */}
      <div className="cyber-panel p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-cyber-muted">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
            </div>
            <input
              type="text"
              placeholder="搜索服务器..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="cyber-input pl-10 w-full"
            />
          </div>
          
          <div>
            <select
              value={selectedDatacenter}
              onChange={(e) => setSelectedDatacenter(e.target.value)}
              className="cyber-input w-full"
            >
              <option value="all">所有数据中心</option>
              {datacenters.map((dc) => {
                // 查找对应的数据中心完整信息
                const dcInfo = OVH_DATACENTERS.find(item => item.code.toUpperCase() === dc);
                return (
                  <option key={dc} value={dc}>
                    {dc} - {dcInfo ? `${dcInfo.name} (${dcInfo.region})` : dc}
                  </option>
                );
              })}
            </select>
          </div>
          
          <div className="flex items-center justify-end space-x-4">
            <div className="flex items-center space-x-2">
              <Button
                onClick={() => setViewMode("grid")}
                variant="cyber"
                size="sm"
                className={viewMode === "grid" ? "bg-cyber-accent/20" : ""}
                title="网格视图"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="7" height="7"></rect>
                  <rect x="14" y="3" width="7" height="7"></rect>
                  <rect x="14" y="14" width="7" height="7"></rect>
                  <rect x="3" y="14" width="7" height="7"></rect>
                </svg>
              </Button>
              <Button
                onClick={() => setViewMode("table")}
                variant="cyber"
                size="sm"
                className={viewMode === "table" ? "bg-cyber-accent/20" : ""}
                title="表格视图"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="3" y1="12" x2="21" y2="12"></line>
                  <line x1="3" y1="6" x2="21" y2="6"></line>
                  <line x1="3" y1="18" x2="21" y2="18"></line>
                </svg>
              </Button>
            </div>
            
            <Button
              onClick={() => fetchServers()}
              variant="cyber"
              size="sm"
              className="text-xs"
              disabled={isLoading}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
                <polyline points="1 4 1 10 7 10"></polyline>
                <polyline points="23 20 23 14 17 14"></polyline>
                <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"></path>
              </svg>
              刷新
            </Button>
          </div>
        </div>
      </div>

      {/* Loading state */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse border-cyber-accent/30">
              <CardHeader className="bg-cyber-grid/10">
                <div className="h-6 bg-cyber-grid/30 rounded w-1/3"></div>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-3">
                  <div className="h-5 bg-cyber-grid/20 rounded"></div>
                  <div className="h-5 bg-cyber-grid/20 rounded w-5/6"></div>
                  <div className="h-5 bg-cyber-grid/20 rounded w-4/6"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredServers.length === 0 ? (
        <Card className="border-cyber-accent/30 py-10">
          <CardContent className="flex flex-col items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-cyber-muted mx-auto mb-4">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
              <line x1="6" y1="6" x2="6.01" y2="6"></line>
              <line x1="6" y1="18" x2="6.01" y2="18"></line>
            </svg>
            <p className="text-cyber-muted mb-4">没有找到匹配的服务器</p>
            <Button 
              onClick={() => {
                setSearchTerm("");
                setSelectedDatacenter("all");
              }}
              variant="cyber"
              size="sm"
            >
              清除筛选
            </Button>
          </CardContent>
        </Card>
      ) : viewMode === "grid" ? (
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"
        >
          {filteredServers.map((server) => (
            <motion.div 
              key={server.planCode}
              variants={itemVariants}
            >
              <Card className="border-cyber-accent/30 overflow-hidden h-full">
                {/* Header with server code and name */}
                <CardHeader className="px-4 py-3 bg-cyber-grid/20 border-b border-cyber-accent/20">
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-lg">{server.planCode}</CardTitle>
                    <div className="bg-cyber-accent/10 px-2 py-1 rounded text-xs border border-cyber-accent/20 text-cyber-accent">
                      {server.name}
                    </div>
                  </div>
                </CardHeader>
                
                <CardContent className="p-4">
                  {/* Server specs in a grid */}
                  <div className="grid grid-cols-2 gap-2 mb-4">
                    <div className="flex items-center space-x-2 p-2 bg-cyber-grid/10 rounded border border-cyber-accent/10">
                      <Cpu size={18} className="text-cyber-accent" />
                      <div>
                        <div className="text-xs text-cyber-muted">CPU</div>
                        <div className="font-medium text-sm">{formatServerSpec(server.cpu, "CPU")}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 p-2 bg-cyber-grid/10 rounded border border-cyber-accent/10">
                      <Database size={18} className="text-cyber-accent" />
                      <div>
                        <div className="text-xs text-cyber-muted">内存</div>
                        <div className="font-medium text-sm">{formatServerSpec(server.memory, "内存")}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 p-2 bg-cyber-grid/10 rounded border border-cyber-accent/10">
                      <HardDrive size={18} className="text-cyber-accent" />
                      <div>
                        <div className="text-xs text-cyber-muted">存储</div>
                        <div className="font-medium text-sm">{formatServerSpec(server.storage, "存储")}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 p-2 bg-cyber-grid/10 rounded border border-cyber-accent/10">
                      <Wifi size={18} className="text-cyber-accent" />
                      <div>
                        <div className="text-xs text-cyber-muted">带宽</div>
                        <div className="font-medium text-sm">{formatServerSpec(server.bandwidth, "带宽")}</div>
                      </div>
                    </div>
                  </div>
                  
                  {/* 服务器配置选项 */}
                  {renderServerOptions(server)}
                  
                  {/* Datacenters availability section */}
                  <div className="rounded border border-cyber-accent/20 overflow-hidden">
                    <div className="flex justify-between items-center bg-cyber-grid/20 px-3 py-2 border-b border-cyber-accent/20">
                      <span className="text-xs font-medium">数据中心</span>
                      <div className="flex space-x-2">
                        <Button
                          onClick={() => checkAvailability(server.planCode)}
                          disabled={isCheckingAvailability || !isAuthenticated}
                          variant="cyber"
                          size="sm"
                          className="h-7 text-xs"
                        >
                          {isCheckingAvailability ? (
                            <span className="inline-flex items-center">
                              <svg className="animate-spin -ml-1 mr-2 h-3 w-3 text-cyber-accent" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              检查中
                            </span>
                          ) : (
                            <span className="inline-flex items-center">
                              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
                                <circle cx="12" cy="12" r="10"></circle>
                                <line x1="12" y1="16" x2="12" y2="12"></line>
                                <line x1="12" y1="8" x2="12.01" y2="8"></line>
                              </svg>
                              检查可用性
                            </span>
                          )}
                        </Button>
                        <Button
                          onClick={() => {
                            setSelectedServer(server.planCode);
                            const selectedDcs = getSelectedDatacentersList(server.planCode);
                            if (selectedDcs.length > 0) {
                              addToQueue(server, selectedDcs);
                            } else {
                              toast.error("请至少选择一个数据中心");
                            }
                          }}
                          disabled={!isAuthenticated || getSelectedDatacentersList(server.planCode).length === 0}
                          variant="cyber-filled"
                          size="sm"
                          className="h-7 text-xs"
                        >
                          抢购
                        </Button>
                      </div>
                    </div>
                    
                    <div className="p-2 bg-cyber-grid/5 border-b border-cyber-accent/10">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-cyber-muted">选择数据中心:</span>
                        <div className="flex space-x-2">
                          <Button
                            onClick={() => toggleAllDatacenters(server.planCode, true)}
                            variant="cyber"
                            size="sm"
                            className="h-6 text-xs"
                          >
                            全选
                          </Button>
                          <Button
                            onClick={() => toggleAllDatacenters(server.planCode, false)}
                            variant="cyber"
                            size="sm"
                            className="h-6 text-xs"
                          >
                            取消全选
                          </Button>
                        </div>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-px bg-cyber-accent/10 p-px">
                      {server.datacenters.map((dc) => {
                        // Get availability from our availability state, or use the default from the server
                        const availStatus = availability[server.planCode]?.[dc.datacenter.toLowerCase()] || dc.availability;
                        
                        let statusText = "未知";
                        let statusClass = "text-yellow-400";
                        let bgClass = "bg-cyber-grid/10";
                        
                        // 根据不同的可用性状态设置样式和文本
                        if (availStatus === "unavailable") {
                          statusText = "不可用";
                          statusClass = "text-red-400";
                        } else if (availStatus && availStatus !== "unknown") {
                          // 如果有值且不是"unknown"，则显示为可用
                          statusText = availStatus.includes("1H") ? 
                                     `可用(${availStatus})` : "可用";
                          statusClass = "text-green-400";
                          bgClass = "bg-green-500/10";
                        }
                        
                        return (
                          <div 
                            key={dc.datacenter}
                            className={`p-2 text-center ${bgClass} cursor-pointer hover:bg-cyber-accent/10`}
                            onClick={() => toggleDatacenterSelection(server.planCode, dc.datacenter)}
                          >
                            <div className="flex justify-center items-center mb-1">
                              {selectedDatacenters[server.planCode]?.[dc.datacenter] ? (
                                <CheckSquare size={14} className="text-cyber-accent mr-1" />
                              ) : (
                                <Square size={14} className="text-cyber-muted mr-1" />
                              )}
                              <span className="text-xs font-medium">{dc.datacenter}</span>
                            </div>
                            <div className="text-xs text-cyber-muted mb-1">{dc.dcName} ({dc.region})</div>
                            <div className={`text-xs ${statusClass} mb-1`}>
                              {statusText}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      ) : (
        <Card className="border-cyber-accent/30">
          <Table>
            <TableHeader>
              <TableRow className="border-cyber-accent/20">
                <TableHead className="text-cyber-accent">型号</TableHead>
                <TableHead>名称</TableHead>
                <TableHead>CPU</TableHead>
                <TableHead>内存</TableHead>
                <TableHead>存储</TableHead>
                <TableHead>带宽</TableHead>
                <TableHead>选项</TableHead>
                <TableHead>数据中心</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredServers.map((server) => (
                <TableRow key={server.planCode} className="border-cyber-accent/10 hover:bg-cyber-grid/20">
                  <TableCell className="font-mono text-cyber-accent">{server.planCode}</TableCell>
                  <TableCell>{server.name}</TableCell>
                  <TableCell className="whitespace-nowrap">
                    <div className="flex items-center">
                      <Cpu size={14} className="mr-1.5 text-cyber-accent" />
                      {formatServerSpec(server.cpu, "CPU")}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <div className="flex items-center">
                      <Database size={14} className="mr-1.5 text-cyber-accent" />
                      {formatServerSpec(server.memory, "内存")}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <div className="flex items-center">
                      <HardDrive size={14} className="mr-1.5 text-cyber-accent" />
                      {formatServerSpec(server.storage, "存储")}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <div className="flex items-center">
                      <Wifi size={14} className="mr-1.5 text-cyber-accent" />
                      {formatServerSpec(server.bandwidth, "带宽")}
                    </div>
                  </TableCell>
                  <TableCell>
                    {renderServerOptions(server)}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {server.datacenters.map((dc) => {
                        const availStatus = availability[server.planCode]?.[dc.datacenter.toLowerCase()] || dc.availability;
                        let statusColor = "bg-yellow-500/20 border-yellow-500/30 text-yellow-400";
                        
                        // 根据不同的可用性状态设置样式
                        if (availStatus === "unavailable") {
                          statusColor = "bg-red-500/20 border-red-500/30 text-red-400";
                        } else if (availStatus && availStatus !== "unknown") {
                          statusColor = "bg-green-500/20 border-green-500/30 text-green-400";
                        }
                        
                        return (
                          <div 
                            key={dc.datacenter} 
                            className={`text-xs px-1.5 py-0.5 rounded border ${statusColor} mr-1 mb-1 flex items-center cursor-pointer hover:bg-cyber-accent/10`}
                            title={`${dc.dcName} (${dc.region})`}
                            onClick={() => toggleDatacenterSelection(server.planCode, dc.datacenter)}
                          >
                            {selectedDatacenters[server.planCode]?.[dc.datacenter] ? (
                              <CheckSquare size={10} className="text-cyber-accent mr-1" />
                            ) : (
                              <Square size={10} className="text-cyber-muted mr-1" />
                            )}
                            <span className="font-medium">{dc.datacenter}</span>
                            {availStatus === "unavailable" && 
                              <span className="ml-1">不可用</span>
                            }
                            {availStatus === "unknown" && 
                              <span className="ml-1">未知</span>
                            }
                            {availStatus && availStatus !== "unavailable" && availStatus !== "unknown" && (
                              <span className="ml-1">
                                {availStatus.includes("1H") ? `(${availStatus})` : "可用"}
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex space-x-2">
                      <Button
                        onClick={() => {
                          const selectedDcs = getSelectedDatacentersList(server.planCode);
                          if (selectedDcs.length > 0) {
                            addToQueue(server, selectedDcs);
                          } else {
                            toast.error("请至少选择一个数据中心");
                          }
                        }}
                        disabled={!isAuthenticated || getSelectedDatacentersList(server.planCode).length === 0}
                        variant="cyber-filled"
                        size="sm"
                        className="h-7 text-xs"
                      >
                        抢购
                      </Button>
                      <Button
                        onClick={() => checkAvailability(server.planCode)}
                        disabled={isCheckingAvailability || !isAuthenticated}
                        variant="cyber"
                        size="sm"
                        className="h-7 text-xs whitespace-nowrap"
                      >
                        检查可用性
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
};

export default ServersPage;

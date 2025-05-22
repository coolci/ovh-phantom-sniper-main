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

// Fixed list of datacenters for display purposes
const DISPLAY_DATACENTERS = [
  { code: "gra", name: "Gravelines", region: "Europe (France)" },
  { code: "sbg", name: "Strasbourg", region: "Europe (France)" },
  { code: "rbx", name: "Roubaix", region: "Europe (France)" },
  { code: "lim", name: "Limburg", region: "Europe (Germany)" }, // Assuming this was meant for Germany (often confused with LIM in Cyprus)
  { code: "fra", name: "Frankfurt", region: "Europe (Germany)" },
  { code: "waw", name: "Warsaw", region: "Europe (Poland)" },
  { code: "lon", name: "London", region: "Europe (UK)" },
  { code: "hil", name: "Hillsboro", region: "North America (USA)" },
  { code: "vin", name: "Vint Hill", region: "North America (USA)" }, // Corrected from Vienna
  { code: "bhs", name: "Beauharnois", region: "North America (Canada)" },
  { code: "sgp", name: "Singapore", region: "Asia (Singapore)" },
  { code: "syd", name: "Sydney", region: "Oceania (Australia)" },
  // Add any other datacenters you want to consistently display
  // { code: "eri", name: "Erith", region: "Europe (UK)" }, // Example if needed
];

interface ServerOption {
  label: string;
  value: string;
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
  price: number | null;
  currency: string | null;
  billingCycle: string | null;
  setupFee?: number | null; // Optional setup fee
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
      const response = await axios.get(`${API_URL}/servers`, {
        params: { showApiServers: isAuthenticated }
      });
      
      // 调试输出查看原始服务器数据
      console.log("原始服务器数据:", response.data);
      
      const rawServers: ServerPlan[] = response.data;

      // Process servers to align with DISPLAY_DATACENTERS
      const processedServers = rawServers.map((server: ServerPlan) => {
        const apiDatacentersMap = new Map(
          server.datacenters.map(dc => [dc.datacenter.toLowerCase(), dc.availability])
        );

        const newServerDatacenters = DISPLAY_DATACENTERS.map(displayDc => {
          const availability = apiDatacentersMap.get(displayDc.code.toLowerCase()) || "unknown";
          return {
            datacenter: displayDc.code.toUpperCase(),
            dcName: displayDc.name,
            region: displayDc.region,
            availability: availability,
          };
        });

        return {
          ...server,
          cpu: formatServerSpec(server.cpu, "CPU"),
          memory: formatServerSpec(server.memory, "内存"),
          storage: formatServerSpec(server.storage, "存储"),
          bandwidth: formatServerSpec(server.bandwidth, "带宽"),
          vrackBandwidth: formatServerSpec(server.vrackBandwidth, "内部带宽"),
          datacenters: newServerDatacenters,
          // Map new pricing fields, providing defaults if missing from API
          price: server.price ?? null,
          currency: server.currency ?? null,
          billingCycle: server.billingCycle ?? null,
          setupFee: server.setupFee ?? undefined, // Use undefined for optional fields if not present
        };
      });
      
      // 调试输出查看格式化后的服务器数据
      console.log("格式化后的服务器数据:", processedServers);
      
      setServers(processedServers);
      setFilteredServers(processedServers);
      
      // Populate datacenters state for the filter dropdown from DISPLAY_DATACENTERS
      setDatacenters(DISPLAY_DATACENTERS.map(dc => dc.code.toUpperCase()));

      // 初始化每个服务器的数据中心选择状态 based on DISPLAY_DATACENTERS
      const newSelectedDatacenters: Record<string, Record<string, boolean>> = {};
      processedServers.forEach(server => {
        const dcState: Record<string, boolean> = {};
        DISPLAY_DATACENTERS.forEach(displayDc => {
          dcState[displayDc.code.toUpperCase()] = false;
        });
        newSelectedDatacenters[server.planCode] = dcState;
      });
      setSelectedDatacenters(newSelectedDatacenters);
      
    } catch (error) {
      console.error("Error fetching servers:", error);
      toast.error("获取服务器列表失败");
    } finally {
      setIsLoading(false);
    }
  };

  // Format server specifications for better display
  const formatServerSpec = (rawValue: string | number, type: string): string => {
    if (rawValue === null || rawValue === undefined || String(rawValue).toUpperCase() === "N/A" || String(rawValue).trim() === "") {
      return "暂无数据";
    }

    let value = String(rawValue).trim();
    const lowerValue = value.toLowerCase();

    if (type === "CPU") {
      // Prioritize full model names
      if (/\b(intel|amd|xeon|epyc|ryzen|i\d-\d{4,}|atom)\b/i.test(lowerValue)) {
        return value.replace(/\s+/g, ' '); // Normalize spacing
      }

      // Regex for patterns like "8c/16t @ 3.0GHz", "8c @ 3.0GHz", "4 cores", "8 vCores"
      const cpuPattern = /(\d+)\s*(?:c(?:ores)?|\s*vcpu|\s*vcore[s]?)(?:\s*\/s*(\d+)\s*t(?:hreads)?)?(?:\s*@\s*([\d.]+)\s*GHz)?/i;
      const match = lowerValue.match(cpuPattern);

      if (match) {
        const cores = match[1];
        const threads = match[2];
        const freq = match[3];
        let result = `${cores} Cores`;
        if (threads) result += ` / ${threads} Threads`;
        if (freq) result += ` @ ${freq} GHz`;
        return result;
      }
      
      // Handle "2x Intel Xeon ..." or "1x AMD EPYC ..."
      const multiCpuPattern = /^(\d+)\s*x\s*(.*)/i;
      const multiMatch = value.match(multiCpuPattern);
      if (multiMatch) {
          return `${multiMatch[1]} x ${multiMatch[2]}`;
      }

      // If it's just a number, assume cores
      if (/^\d+$/.test(value)) {
        return `${value} Cores`;
      }
      
      // Fallback for "X x Y" or "N x Something" which might be CPU descriptions
      if (lowerValue.includes('x') && lowerValue.length < 30) { // Heuristic for short "N x CPU_TYPE"
        return value;
      }

      return value; // Return original if no specific pattern matches
    }

    if (type === "内存") {
      const ramPattern = /(\d+(?:\.\d+)?)\s*(TB|GB|MB|T|G|M|To|Go|Mo)/i;
      const match = lowerValue.match(ramPattern);
      if (match) {
        let amount = parseFloat(match[1]);
        const unit = match[2].toUpperCase();
        if (unit.startsWith("T")) return `${amount} TB RAM`;
        if (unit.startsWith("M")) return `${amount} MB RAM`;
        // Default to GB for G, GO
        return `${amount} GB RAM`;
      }
      // If just a number, assume GB, if very large, assume MB and convert
      if (/^\d+$/.test(value)) {
        const num = parseInt(value, 10);
        if (num > 1024*4) { // Heuristic: if > 4096, likely MB for very large RAM amounts not specified in GB
             return `${(num / 1024).toFixed(0)} GB RAM`;
        }
        return `${num} GB RAM`;
      }
      return value.toUpperCase().endsWith("RAM") ? value : `${value} RAM`;
    }

    if (type === "存储") {
      // Normalize common terms
      let normValue = lowerValue
        .replace(/\s*x\s*/g, 'x') // 2 x 1TB -> 2x1TB
        .replace(/(\d+)\s*(tb|gb|mb|go|to|mo)/ig, '$1$2') // 1 TB -> 1TB
        .replace(/sata|sas/ig, 'HDD') // Treat SATA/SAS as HDD for simplicity unless SSD is mentioned
        .replace(/hard drive/ig, 'HDD');

      const parts = normValue.split(/\s*\+\s*|\s*,\s*/); // Split by + or ,
      const formattedParts: string[] = [];

      for (const part of parts) {
        const diskPattern = /(\d*x)?(\d+(?:\.\d+)?)?\s*(tb|gb|mb|go|to|mo)?\s*(nvme|ssd|hdd|flash)?/i;
        const match = part.match(diskPattern);
        
        if (match) {
          let count = match[1] ? match[1].toLowerCase().replace('x', '') : '1';
          if (count === '') count = '1';
          
          let size = match[2] ? parseFloat(match[2]) : null;
          let unit = match[3] ? match[3].toUpperCase() : null;
          let diskType = match[4] ? match[4].toUpperCase() : null;

          let currentPart = "";
          if (count !== '1') currentPart += `${count}x`;
          
          if (size && unit) {
            if (unit.startsWith("T")) currentPart += `${size}TB`;
            else if (unit.startsWith("M")) currentPart += `${size}MB`;
            else currentPart += `${size}GB`; // Default GB
          } else if (size) {
             currentPart += `${size}GB`; // Assume GB if no unit but size is present
          }


          if (diskType) {
            currentPart += ` ${diskType}`;
          } else if (part.includes("ssd")) {
            currentPart += ` SSD`;
          } else if (part.includes("nvme")) {
            currentPart += ` NVMe`;
          } else if (part.includes("hdd")) {
            currentPart += ` HDD`;
          } else {
            currentPart += ` Storage`; // Generic if type unknown
          }
          formattedParts.push(currentPart.trim());
        } else if (part.trim()) {
            // Fallback for complex strings or unparsable parts
            let currentPart = part.trim();
            if (/\d/.test(currentPart) && !/(tb|gb|mb|ssd|hdd|nvme)/i.test(currentPart)) {
                 // If it has numbers but no units/types, assume GB and generic storage
                 currentPart = currentPart.replace(/(\d+)/, '$1GB');
                 currentPart += ' Storage';
            }
            formattedParts.push(currentPart);
        }
      }

      if (formattedParts.length > 0) {
        return formattedParts.join(" + ").replace(/\s+/g, ' '); // Normalize spacing
      }
      
      // Fallback if original value was complex
      if (value.length > 0 && /\d/.test(value)) return value; // Return original if it had numbers and was not parsed
      return "暂无数据"; // Final fallback
    }

    if (type.includes("带宽")) { // Handles "带宽" and "内部带宽"
      const bwPattern = /(\d+(?:\.\d+)?)\s*(TBPS|GBPS|MBPS|TBIT|GBIT|MBIT|T|G|M)/i;
      const match = lowerValue.match(bwPattern);
      if (match) {
        const amount = parseFloat(match[1]);
        const unit = match[2].toUpperCase();
        if (unit.startsWith("T")) return `${amount} Tbps`;
        if (unit.startsWith("M")) return `${amount} Mbps`;
        // Default to Gbps for G, GBIT
        return `${amount} Gbps`;
      }
      // If just a number
      if (/^\d+$/.test(value)) {
        const num = parseInt(value, 10);
        if (num >= 1000 && num % 1000 === 0 && type === "带宽") return `${num / 1000} Gbps`; // e.g. 1000 -> 1 Gbps for public
        if (num >= 1000 && num % 1000 === 0 && type === "内部带宽") return `${num / 1000} Gbps`;// e.g. 10000 -> 10 Gbps for vRack
        if (num < 100 && num > 5 && type === "带宽") return `${num} Gbps`; // Heuristic: 1, 2, 10 are usually Gbps for public
        return `${num} Mbps`; // Default to Mbps for smaller numbers or vRack if not clearly Gbps
      }
      // Handle "Standard", "High" etc. if API provides them
      if (["standard", "high", "premium", "unlimited", "illimité"].includes(lowerValue)) {
        return value.charAt(0).toUpperCase() + value.slice(1);
      }
      return value;
    }

    return value; // Fallback for unknown types
  };

  // Check availability for a specific server plan
  const checkAvailability = async (planCode: string) => {
    if (!isAuthenticated) {
      toast.error("请先配置 API 设置");
      return;
    }
    
    setIsCheckingAvailability(true);
    try {
      const currentPlanOptions = selectedOptions[planCode];
      const apiParams: Record<string, string> = {};

      if (currentPlanOptions && currentPlanOptions.length > 0) {
        currentPlanOptions.forEach(optionString => {
          if (optionString.includes('=')) {
            const [key, ...valueParts] = optionString.split('=');
            apiParams[key] = valueParts.join('=');
          } else {
            apiParams[optionString] = 'true';
          }
        });
      }

      let response;
      if (Object.keys(apiParams).length > 0) {
        response = await axios.get(`${API_URL}/availability/${planCode}`, { params: apiParams });
      } else {
        response = await axios.get(`${API_URL}/availability/${planCode}`);
      }
      
      console.log(`获取到 ${planCode} 的可用性数据 (选项: ${JSON.stringify(apiParams)}):`, response.data);
      
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

  // 切换选项
  const toggleOption = (serverPlanCode: string, optionValue: string) => {
    setSelectedOptions(prev => {
      const currentOptions = [...(prev[serverPlanCode] || [])];
      const index = currentOptions.indexOf(optionValue);
      
      if (index >= 0) {
        // 如果选项已经选中，则移除它
        currentOptions.splice(index, 1);
      } else {
        // 如果选项未选中，则添加它
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
      // 获取最终选项，如果用户选择了自定义选项则使用那些，否则使用默认选项
      const options = selectedOptions[server.planCode]?.length > 0 
        ? selectedOptions[server.planCode] 
        : server.defaultOptions.map(opt => opt.value);

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
              {DISPLAY_DATACENTERS.map((dc) => (
                <option key={dc.code} value={dc.code.toUpperCase()}>
                  {dc.code.toUpperCase()} - {dc.name} ({dc.region})
                </option>
              ))}
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
                        <div className="font-medium text-sm">{server.cpu || "暂无数据"}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 p-2 bg-cyber-grid/10 rounded border border-cyber-accent/10">
                      <Database size={18} className="text-cyber-accent" />
                      <div>
                        <div className="text-xs text-cyber-muted">内存</div>
                        <div className="font-medium text-sm">{server.memory || "暂无数据"}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 p-2 bg-cyber-grid/10 rounded border border-cyber-accent/10">
                      <HardDrive size={18} className="text-cyber-accent" />
                      <div>
                        <div className="text-xs text-cyber-muted">存储</div>
                        <div className="font-medium text-sm">{server.storage || "暂无数据"}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 p-2 bg-cyber-grid/10 rounded border border-cyber-accent/10">
                      <Wifi size={18} className="text-cyber-accent" />
                      <div>
                        <div className="text-xs text-cyber-muted">带宽</div>
                        <div className="font-medium text-sm">{server.bandwidth || "暂无数据"}</div>
                      </div>
                    </div>
                  </div>
                  
                  {/* 服务器配置选项 */}
                  {(server.defaultOptions.length > 0 || server.availableOptions.length > 0) && (
                    <div className="rounded border border-cyber-accent/20 overflow-hidden mb-4">
                      <div className="bg-cyber-grid/20 px-3 py-2 border-b border-cyber-accent/20">
                        <span className="text-xs font-medium flex items-center">
                          <Settings size={14} className="mr-1.5 text-cyber-accent" />
                          配置选项
                        </span>
                      </div>
                      <div className="p-3">
                        {server.defaultOptions.length > 0 && (
                          <div className="mb-3">
                            <div className="text-xs text-cyber-muted mb-1">默认选项:</div>
                            <div className="flex flex-wrap gap-1">
                              {server.defaultOptions.map(option => (
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
                        
                        {server.availableOptions.length > 0 && (
                          <div>
                            <div className="text-xs text-cyber-muted mb-1">可选配置:</div>
                            <div className="flex flex-wrap gap-1">
                              {server.availableOptions.map(option => (
                                <div 
                                  key={option.value} 
                                  className={`px-2 py-1 rounded text-xs border cursor-pointer transition-colors
                                    ${isOptionSelected(server.planCode, option.value) 
                                      ? "bg-cyber-accent/30 border-cyber-accent text-white" 
                                      : "bg-cyber-grid/10 border-cyber-accent/10 text-cyber-muted hover:bg-cyber-accent/10"}`}
                                  onClick={() => toggleOption(server.planCode, option.value)}
                                >
                                  <div className="flex items-center">
                                    {isOptionSelected(server.planCode, option.value) ? (
                                      <CheckSquare size={10} className="mr-1" />
                                    ) : (
                                      <Square size={10} className="mr-1" />
                                    )}
                                    {option.label}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  
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
                      {server.cpu || "暂无数据"}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <div className="flex items-center">
                      <Database size={14} className="mr-1.5 text-cyber-accent" />
                      {server.memory || "暂无数据"}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <div className="flex items-center">
                      <HardDrive size={14} className="mr-1.5 text-cyber-accent" />
                      {server.storage || "暂无数据"}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <div className="flex items-center">
                      <Wifi size={14} className="mr-1.5 text-cyber-accent" />
                      {server.bandwidth || "暂无数据"}
                    </div>
                  </TableCell>
                  <TableCell>
                    {(server.defaultOptions.length > 0 || server.availableOptions.length > 0) && (
                      <div>
                        {server.defaultOptions.length > 0 && (
                          <div className="mb-2">
                            <div className="text-xs text-cyber-muted mb-1">默认选项:</div>
                            <div className="flex flex-wrap gap-1">
                              {server.defaultOptions.map(option => (
                                <div key={option.value} className="bg-cyber-accent/10 px-1.5 py-0.5 rounded text-xs border border-cyber-accent/20 text-cyber-accent">
                                  {option.label}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {server.availableOptions.length > 0 && (
                          <div>
                            <div className="text-xs text-cyber-muted mb-1">可选配置:</div>
                            <div className="flex flex-wrap gap-1">
                              {server.availableOptions.map(option => (
                                <div 
                                  key={option.value} 
                                  className={`px-1.5 py-0.5 rounded text-xs border cursor-pointer transition-colors
                                    ${isOptionSelected(server.planCode, option.value) 
                                      ? "bg-cyber-accent/30 border-cyber-accent text-white" 
                                      : "bg-cyber-grid/10 border-cyber-accent/10 text-cyber-muted hover:bg-cyber-accent/10"}`}
                                  onClick={() => toggleOption(server.planCode, option.value)}
                                >
                                  <div className="flex items-center">
                                    {isOptionSelected(server.planCode, option.value) ? (
                                      <CheckSquare size={10} className="mr-1" />
                                    ) : (
                                      <Square size={10} className="mr-1" />
                                    )}
                                    {option.label}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
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

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
import { Cpu, Database, Wifi, HardDrive } from "lucide-react";
import { apiEvents } from "@/context/APIContext";

// Backend API URL (update this to match your backend)
const API_URL = 'http://localhost:5000/api';

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
  datacenters: {
    datacenter: string;
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

  // Fetch servers from the backend
  const fetchServers = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get(`${API_URL}/servers`, {
        params: { showApiServers: isAuthenticated }
      });
      
      // Ensure server information is properly formatted
      const formattedServers = response.data.map((server: ServerPlan) => ({
        ...server,
        cpu: formatServerSpec(server.cpu, "CPU"),
        memory: formatServerSpec(server.memory, "内存"),
        storage: formatServerSpec(server.storage, "存储"),
        bandwidth: formatServerSpec(server.bandwidth, "带宽"),
        vrackBandwidth: formatServerSpec(server.vrackBandwidth, "内部带宽")
      }));
      
      setServers(formattedServers);
      setFilteredServers(formattedServers);
      
      // Extract unique datacenters and deduplicate them
      const dcSet = new Set<string>();
      formattedServers.forEach((server: ServerPlan) => {
        const uniqueDcs = new Set<string>();
        server.datacenters.forEach(dc => {
          uniqueDcs.add(dc.datacenter);
        });
        // 更新全局数据中心集合
        uniqueDcs.forEach(dc => dcSet.add(dc));
        
        // 用去重后的数据中心替换原数据
        const uniqueDatacenters = Array.from(uniqueDcs).map(dcName => {
          // 查找相同数据中心的最佳可用性
          const allMatches = server.datacenters.filter(d => d.datacenter === dcName);
          let bestAvailability = "unavailable";
          
          // 优先选择非不可用状态
          allMatches.forEach(match => {
            if (match.availability !== "unavailable") {
              if (bestAvailability === "unavailable" || 
                  match.availability.includes("1H-high") || 
                  (match.availability.includes("1H-low") && !bestAvailability.includes("1H-high"))) {
                bestAvailability = match.availability;
              }
            }
          });
          
          return {
            datacenter: dcName,
            availability: bestAvailability
          };
        });
        
        // 这里我们不直接修改原对象，而是在处理后将结果赋值
        server.datacenters = uniqueDatacenters;
      });
      
      setDatacenters(Array.from(dcSet));
      
    } catch (error) {
      console.error("Error fetching servers:", error);
      toast.error("获取服务器列表失败");
    } finally {
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
      
      // 尝试从不同格式中提取信息
      if (value.includes("x")) {
        // 已经是格式 "4 x Intel Xeon"
        return value;
      } else if (!isNaN(Number(value))) {
        return `${value} 核心`;
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
      
      // 尝试处理纯数字
      if (!isNaN(Number(value))) {
        const num = Number(value);
        if (num > 1000) {
          return `${(num/1024).toFixed(0)} GB`;
        }
        return `${num} GB`;
      }
      
      // KS/RISE系列可能用文本描述内存大小
      if (value.match(/\d+/)) {
        return value;
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
      
      // 尝试处理纯数字
      if (!isNaN(Number(value))) {
        const num = Number(value);
        if (num >= 1000) {
          return `${(num/1000).toFixed(1)} TB`;
        }
        return `${num} GB`;
      }
      
      return value;
    }
    
    // 对于带宽
    if (type.includes("带宽")) {
      // 已经包含单位
      if (value.toLowerCase().includes("gbps") || 
          value.toLowerCase().includes("mbps") || 
          value.toLowerCase().includes("gbit") || 
          value.toLowerCase().includes("mbit")) {
        return value;
      }
      
      // 尝试处理纯数字
      if (!isNaN(Number(value))) {
        const num = Number(value);
        if (num >= 1000) {
          return `${(num/1000).toFixed(1)} Gbps`;
        }
        return `${num} Mbps`;
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

  // Add server to purchase queue
  const addToQueue = async (server: ServerPlan, datacenter: string) => {
    if (!isAuthenticated) {
      toast.error("请先配置 API 设置");
      return;
    }
    
    try {
      await axios.post(`${API_URL}/queue`, {
        planCode: server.planCode,
        datacenter,
        options: server.defaultOptions.map(opt => opt.value),
      });
      
      toast.success("已添加到抢购队列");
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
              {datacenters.map((dc) => (
                <option key={dc} value={dc}>{dc}</option>
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
                        <div className="font-medium text-sm">{server.cpu}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 p-2 bg-cyber-grid/10 rounded border border-cyber-accent/10">
                      <Database size={18} className="text-cyber-accent" />
                      <div>
                        <div className="text-xs text-cyber-muted">内存</div>
                        <div className="font-medium text-sm">{server.memory}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 p-2 bg-cyber-grid/10 rounded border border-cyber-accent/10">
                      <HardDrive size={18} className="text-cyber-accent" />
                      <div>
                        <div className="text-xs text-cyber-muted">存储</div>
                        <div className="font-medium text-sm">{server.storage}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 p-2 bg-cyber-grid/10 rounded border border-cyber-accent/10">
                      <Wifi size={18} className="text-cyber-accent" />
                      <div>
                        <div className="text-xs text-cyber-muted">带宽</div>
                        <div className="font-medium text-sm">{server.bandwidth}</div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Datacenters availability section */}
                  <div className="rounded border border-cyber-accent/20 overflow-hidden">
                    <div className="flex justify-between items-center bg-cyber-grid/20 px-3 py-2 border-b border-cyber-accent/20">
                      <span className="text-xs font-medium">数据中心可用性</span>
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
                    </div>
                    
                    <div className="grid grid-cols-3 gap-px bg-cyber-accent/10 p-px">
                      {server.datacenters.map((dc) => {
                        // Get availability from our availability state, or use the default from the server
                        const availStatus = availability[server.planCode]?.[dc.datacenter] || dc.availability;
                        
                        let statusClass = "text-yellow-400";
                        let bgClass = "bg-cyber-grid/10";
                        
                        if (availStatus === "available") {
                          statusClass = "text-green-400";
                          bgClass = "bg-green-500/10";
                        } else if (availStatus === "unavailable") {
                          statusClass = "text-red-400";
                        }
                        
                        return (
                          <div 
                            key={dc.datacenter}
                            className={`p-2 text-center ${bgClass}`}
                          >
                            <div className="text-xs font-medium mb-1">{dc.datacenter}</div>
                            <div className={`text-xs ${statusClass} mb-1`}>
                              {availStatus === "available" ? "可用" : 
                              availStatus === "unavailable" ? "不可用" : "未知"}
                            </div>
                            
                            {availStatus === "available" && (
                              <Button
                                onClick={() => addToQueue(server, dc.datacenter)}
                                disabled={!isAuthenticated}
                                variant="cyber-filled"
                                size="sm"
                                className="w-full h-6 text-xs"
                              >
                                抢购
                              </Button>
                            )}
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
                      {server.cpu}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <div className="flex items-center">
                      <Database size={14} className="mr-1.5 text-cyber-accent" />
                      {server.memory}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <div className="flex items-center">
                      <HardDrive size={14} className="mr-1.5 text-cyber-accent" />
                      {server.storage}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <div className="flex items-center">
                      <Wifi size={14} className="mr-1.5 text-cyber-accent" />
                      {server.bandwidth}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {server.datacenters.map((dc) => {
                        const availStatus = availability[server.planCode]?.[dc.datacenter] || dc.availability;
                        let statusColor = "bg-yellow-500/20 border-yellow-500/30 text-yellow-400";
                        
                        if (availStatus === "available") {
                          statusColor = "bg-green-500/20 border-green-500/30 text-green-400";
                        } else if (availStatus === "unavailable") {
                          statusColor = "bg-red-500/20 border-red-500/30 text-red-400";
                        }
                        
                        return (
                          <span key={dc.datacenter} className={`text-xs px-1.5 py-0.5 rounded border ${statusColor}`}>
                            {dc.datacenter}
                          </span>
                        );
                      })}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex space-x-2">
                      <Button
                        onClick={() => checkAvailability(server.planCode)}
                        disabled={isCheckingAvailability || !isAuthenticated}
                        variant="cyber"
                        size="sm"
                        className="h-7 text-xs whitespace-nowrap"
                      >
                        检查可用性
                      </Button>
                      {server.datacenters.some(dc => availability[server.planCode]?.[dc.datacenter] === "available" || dc.availability === "available") && (
                        <Button
                          onClick={() => {
                            const availableDc = server.datacenters.find(
                              dc => availability[server.planCode]?.[dc.datacenter] === "available" || dc.availability === "available"
                            );
                            if (availableDc) addToQueue(server, availableDc.datacenter);
                          }}
                          disabled={!isAuthenticated}
                          variant="cyber-filled"
                          size="sm"
                          className="h-7 text-xs"
                        >
                          抢购
                        </Button>
                      )}
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

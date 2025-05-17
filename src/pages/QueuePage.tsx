
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useAPI } from "@/context/APIContext";
import axios from "axios";
import { toast } from "sonner";

// Backend API URL (update this to match your backend)
const API_URL = 'http://localhost:5000/api';

interface QueueItem {
  id: string;
  planCode: string;
  datacenter: string;
  options: string[];
  status: "pending" | "running" | "completed" | "failed";
  createdAt: string;
  updatedAt: string;
  retryInterval: number;
  retryCount: number;
}

interface ServerOption {
  label: string;
  value: string;
}

interface ServerPlan {
  planCode: string;
  name: string;
  cpu: string;
  memory: string;
  storage: string;
  datacenters: {
    datacenter: string;
    availability: string;
  }[];
  defaultOptions: ServerOption[];
  availableOptions: ServerOption[];
}

const QueuePage = () => {
  const { isAuthenticated } = useAPI();
  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [servers, setServers] = useState<ServerPlan[]>([]);
  const [selectedServer, setSelectedServer] = useState<ServerPlan | null>(null);
  const [selectedDatacenter, setSelectedDatacenter] = useState<string>("");
  const [retryInterval, setRetryInterval] = useState<number>(30);
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);

  // Fetch queue items
  const fetchQueueItems = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get(`${API_URL}/queue`);
      setQueueItems(response.data);
    } catch (error) {
      console.error("Error fetching queue items:", error);
      toast.error("获取队列失败");
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch servers for the add form
  const fetchServers = async () => {
    try {
      const response = await axios.get(`${API_URL}/servers`, {
        params: { showApiServers: isAuthenticated },
      });
      setServers(response.data);
    } catch (error) {
      console.error("Error fetching servers:", error);
      toast.error("获取服务器列表失败");
    }
  };

  // Add new queue item
  const addQueueItem = async () => {
    if (!selectedServer || !selectedDatacenter) {
      toast.error("请选择服务器和数据中心");
      return;
    }

    try {
      await axios.post(`${API_URL}/queue`, {
        planCode: selectedServer.planCode,
        datacenter: selectedDatacenter,
        options: selectedOptions,
        retryInterval: retryInterval,
      });
      
      toast.success("已添加到抢购队列");
      setShowAddForm(false);
      fetchQueueItems();
      
      // Reset form
      setSelectedServer(null);
      setSelectedDatacenter("");
      setSelectedOptions([]);
      setRetryInterval(30);
    } catch (error) {
      console.error("Error adding to queue:", error);
      toast.error("添加到抢购队列失败");
    }
  };

  // Remove queue item
  const removeQueueItem = async (id: string) => {
    try {
      await axios.delete(`${API_URL}/queue/${id}`);
      toast.success("已从队列中移除");
      fetchQueueItems();
    } catch (error) {
      console.error("Error removing queue item:", error);
      toast.error("从队列中移除失败");
    }
  };

  // Start/stop queue item
  const toggleQueueItemStatus = async (id: string, currentStatus: string) => {
    const newStatus = currentStatus === "running" ? "pending" : "running";
    
    try {
      await axios.put(`${API_URL}/queue/${id}/status`, {
        status: newStatus,
      });
      
      toast.success(`已${newStatus === "running" ? "启动" : "暂停"}队列项`);
      fetchQueueItems();
    } catch (error) {
      console.error("Error updating queue item status:", error);
      toast.error("更新队列项状态失败");
    }
  };

  // Initial fetch
  useEffect(() => {
    fetchQueueItems();
    fetchServers();
    
    // Set up polling interval
    const interval = setInterval(fetchQueueItems, 10000);
    
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  // Update options when server changes
  useEffect(() => {
    if (selectedServer) {
      setSelectedOptions(selectedServer.defaultOptions.map(opt => opt.value));
    } else {
      setSelectedOptions([]);
    }
  }, [selectedServer]);

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
        <h1 className="text-3xl font-bold mb-1 cyber-glow-text">抢购队列</h1>
        <p className="text-cyber-muted mb-6">管理自动抢购服务器的队列</p>
      </motion.div>

      {/* Controls */}
      <div className="flex justify-between items-center mb-6">
        <button
          onClick={() => fetchQueueItems()}
          className="cyber-button text-xs flex items-center"
          disabled={isLoading}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
            <polyline points="1 4 1 10 7 10"></polyline>
            <polyline points="23 20 23 14 17 14"></polyline>
            <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"></path>
          </svg>
          刷新
        </button>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="cyber-button text-xs flex items-center"
          disabled={!isAuthenticated}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          添加新任务
        </button>
      </div>

      {/* Add Form */}
      {showAddForm && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.3 }}
          className="cyber-panel mb-6 overflow-hidden"
        >
          <div className="p-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">添加抢购任务</h2>
              <button onClick={() => setShowAddForm(false)} className="text-cyber-muted hover:text-cyber-accent">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-cyber-muted text-sm mb-1">选择服务器</label>
                <select
                  value={selectedServer?.planCode || ""}
                  onChange={(e) => {
                    const server = servers.find(s => s.planCode === e.target.value);
                    setSelectedServer(server || null);
                    setSelectedDatacenter("");
                  }}
                  className="cyber-input w-full"
                >
                  <option value="">选择服务器</option>
                  {servers.map((server) => (
                    <option key={server.planCode} value={server.planCode}>
                      {server.planCode} - {server.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-cyber-muted text-sm mb-1">选择数据中心</label>
                <select
                  value={selectedDatacenter}
                  onChange={(e) => setSelectedDatacenter(e.target.value)}
                  className="cyber-input w-full"
                  disabled={!selectedServer}
                >
                  <option value="">选择数据中心</option>
                  {selectedServer?.datacenters.map((dc) => (
                    <option key={dc.datacenter} value={dc.datacenter}>{dc.datacenter}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-cyber-muted text-sm mb-1">重试间隔（秒）</label>
              <input
                type="number"
                min="10"
                max="600"
                value={retryInterval}
                onChange={(e) => setRetryInterval(Number(e.target.value))}
                className="cyber-input w-full"
              />
              <p className="text-xs text-cyber-muted mt-1">设置检查服务器可用性的间隔时间</p>
            </div>

            {selectedServer && (
              <div className="mb-4">
                <label className="block text-cyber-muted text-sm mb-1">选择配置选项</label>
                <div className="cyber-panel p-3 bg-cyber-grid/20">
                  {selectedServer.availableOptions.length === 0 ? (
                    <p className="text-cyber-muted text-sm">没有可选配置</p>
                  ) : (
                    <div className="grid grid-cols-2 gap-2">
                      {selectedServer.availableOptions.map((option) => (
                        <label key={option.value} className="flex items-center space-x-2 text-sm cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedOptions.includes(option.value)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedOptions([...selectedOptions, option.value]);
                              } else {
                                setSelectedOptions(selectedOptions.filter(o => o !== option.value));
                              }
                            }}
                            className="form-checkbox cyber-input h-4 w-4"
                          />
                          <span>{option.label}</span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="flex justify-end">
              <button
                onClick={addQueueItem}
                className="cyber-button"
                disabled={!selectedServer || !selectedDatacenter}
              >
                添加到队列
              </button>
            </div>
          </div>
        </motion.div>
      )}

      {/* Queue List */}
      {isLoading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="cyber-panel h-24 animate-pulse">
              <div className="h-full bg-cyber-grid/30"></div>
            </div>
          ))}
        </div>
      ) : queueItems.length === 0 ? (
        <div className="cyber-panel p-8 text-center">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-cyber-muted mx-auto mb-4">
            <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
            <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
            <path d="M9 12h6"></path>
            <path d="M9 16h6"></path>
            <path d="M9 8h6"></path>
          </svg>
          <p className="text-cyber-muted">队列为空</p>
          <button 
            onClick={() => setShowAddForm(true)}
            className="cyber-button mt-4 text-xs"
            disabled={!isAuthenticated}
          >
            添加任务
          </button>
        </div>
      ) : (
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="space-y-4"
        >
          {queueItems.map((item) => (
            <motion.div 
              key={item.id}
              variants={itemVariants}
              className="cyber-panel"
            >
              <div className="p-4 flex flex-col md:flex-row md:items-center md:justify-between">
                <div className="md:flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="text-lg font-cyber font-bold text-cyber-accent">
                      {item.planCode}
                    </h3>
                    <div className="bg-cyber-grid/50 px-2 py-0.5 rounded text-xs">
                      {item.datacenter}
                    </div>
                    <div className={`px-2 py-0.5 rounded text-xs ${
                      item.status === "running" ? "bg-green-500/20 text-green-400" :
                      item.status === "completed" ? "bg-blue-500/20 text-blue-400" :
                      item.status === "failed" ? "bg-red-500/20 text-red-400" :
                      "bg-yellow-500/20 text-yellow-400"
                    }`}>
                      {item.status === "running" ? "运行中" :
                       item.status === "completed" ? "已完成" :
                       item.status === "failed" ? "失败" :
                       "等待中"}
                    </div>
                  </div>
                  
                  <div className="text-cyber-muted text-sm mb-3">
                    <div className="flex items-center gap-4">
                      <span>
                        创建时间: {new Date(item.createdAt).toLocaleString()}
                      </span>
                      <span>
                        重试间隔: {item.retryInterval}秒
                      </span>
                      <span>
                        重试次数: {item.retryCount}
                      </span>
                    </div>
                  </div>
                  
                  {item.options.length > 0 && (
                    <div className="mb-3">
                      <span className="text-cyber-muted text-xs block mb-1">选项:</span>
                      <div className="flex flex-wrap gap-1">
                        {item.options.map((option, index) => (
                          <span key={index} className="bg-cyber-grid/30 px-2 py-0.5 rounded text-xs">
                            {option}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                
                <div className="flex items-center space-x-2 mt-3 md:mt-0">
                  {(item.status === "pending" || item.status === "running") && (
                    <button
                      onClick={() => toggleQueueItemStatus(item.id, item.status)}
                      className={`cyber-button text-xs ${
                        item.status === "running" ? "bg-yellow-500/10 border-yellow-500/30 hover:border-yellow-500/50" : 
                        "bg-green-500/10 border-green-500/30 hover:border-green-500/50"
                      }`}
                    >
                      {item.status === "running" ? (
                        <span className="flex items-center">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
                            <rect x="6" y="4" width="4" height="16"></rect>
                            <rect x="14" y="4" width="4" height="16"></rect>
                          </svg>
                          暂停
                        </span>
                      ) : (
                        <span className="flex items-center">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
                            <polygon points="5 3 19 12 5 21 5 3"></polygon>
                          </svg>
                          启动
                        </span>
                      )}
                    </button>
                  )}
                  
                  <button
                    onClick={() => removeQueueItem(item.id)}
                    className="cyber-button text-xs bg-red-500/10 border-red-500/30 hover:border-red-500/50"
                  >
                    <span className="flex items-center">
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
                        <path d="M3 6h18"></path>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                      </svg>
                      删除
                    </span>
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
};

export default QueuePage;

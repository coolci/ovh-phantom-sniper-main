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
    dcName: string;
    region: string;
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
  const [planCodeInput, setPlanCodeInput] = useState<string>("");
  const [selectedServer, setSelectedServer] = useState<ServerPlan | null>(null);
  const [selectedDatacenters, setSelectedDatacenters] = useState<string[]>([]);
  const [retryInterval, setRetryInterval] = useState<number>(30);
  const [allAvailableDatacenters, setAllAvailableDatacenters] = useState<{ datacenter: string; dcName: string; }[]>([]);

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
      
      const serversList = response.data.servers || response.data || [];
      setServers(serversList);

      // Populate allAvailableDatacenters
      const uniqueDcs = new Map<string, { datacenter: string; dcName: string }>();
      serversList.forEach(server => {
        if (server.datacenters) {
          server.datacenters.forEach(dc => {
            if (!uniqueDcs.has(dc.datacenter)) {
              uniqueDcs.set(dc.datacenter, { datacenter: dc.datacenter, dcName: dc.dcName });
            }
          });
        }
      });
      const sortedDcs = Array.from(uniqueDcs.values()).sort((a, b) => a.dcName.localeCompare(b.dcName));
      setAllAvailableDatacenters(sortedDcs);

    } catch (error) {
      console.error("Error fetching servers:", error);
      toast.error("获取服务器列表失败");
    }
  };

  // Add new queue item
  const addQueueItem = async () => {
    if (!planCodeInput.trim() || selectedDatacenters.length === 0) {
      toast.error("请输入服务器计划代码并至少选择一个数据中心");
      return;
    }

    let successCount = 0;
    let errorCount = 0;

    for (const dc of selectedDatacenters) {
      try {
        await axios.post(`${API_URL}/queue`, {
          planCode: planCodeInput.trim(),
          datacenter: dc,
          retryInterval: retryInterval,
        });
        successCount++;
      } catch (error) {
        console.error(`Error adding ${planCodeInput.trim()} in ${dc} to queue:`, error);
        errorCount++;
      }
    }

    if (successCount > 0) {
      toast.success(`${successCount}个任务已成功添加到抢购队列`);
    }
    if (errorCount > 0) {
      toast.error(`${errorCount}个任务添加到抢购队列失败`);
    }

    if (successCount > 0 || errorCount === 0) {
      fetchQueueItems();
      setShowAddForm(false);
      setPlanCodeInput("");
      setSelectedDatacenters([]);
      setRetryInterval(30);
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

  // Update selectedServer when planCodeInput or servers list changes
  useEffect(() => {
    if (planCodeInput.trim()) {
      const server = servers.find(s => s.planCode === planCodeInput.trim());
      setSelectedServer(server || null);
    } else {
      setSelectedServer(null);
    }
  }, [planCodeInput, servers]);

  // Reset selectedDatacenters when planCodeInput changes
  useEffect(() => {
    setSelectedDatacenters([]);
  }, [planCodeInput]);

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
                <label className="block text-cyber-muted text-sm mb-1">服务器计划代码</label>
                <input
                  type="text"
                  value={planCodeInput}
                  onChange={(e) => setPlanCodeInput(e.target.value)}
                  placeholder="例如: 24sk40"
                  className="cyber-input w-full"
                />
                {selectedServer && planCodeInput.trim() && (
                  <p className="text-xs text-cyber-muted mt-1">匹配到: {selectedServer.name}</p>
                )}
              </div>
              <div>
                <label className="block text-cyber-muted text-sm mb-1">选择数据中心 (可多选)</label>
                {planCodeInput.trim() ? (
                  allAvailableDatacenters.length > 0 ? (
                    <div className="max-h-48 overflow-y-auto space-y-2 cyber-panel p-3 bg-cyber-grid/20 rounded border border-cyber-border">
                      {allAvailableDatacenters.map((dc) => (
                        <label key={dc.datacenter} className="flex items-center cyber-checkbox-label text-sm cursor-pointer hover:bg-cyber-hover p-1 rounded">
                          <input
                            type="checkbox"
                            value={dc.datacenter}
                            checked={selectedDatacenters.includes(dc.datacenter)}
                            onChange={(e) => {
                              const dcValue = e.target.value;
                              setSelectedDatacenters(prev =>
                                e.target.checked
                                  ? [...prev, dcValue]
                                  : prev.filter(d => d !== dcValue)
                              );
                            }}
                            className="cyber-checkbox"
                          />
                          <span className="ml-2">{dc.dcName} ({dc.datacenter})</span>
                        </label>
                      ))}
                    </div>
                  ) : (
                    <p className="text-cyber-muted text-sm p-3 bg-cyber-grid/10 rounded border border-cyber-border">
                      {isLoading ? "正在加载数据中心列表..." : "暂无可用数据中心信息。"}
                    </p>
                  )
                ) : (
                  <p className="text-cyber-muted text-sm p-3 bg-cyber-grid/10 rounded border border-cyber-border">
                    请输入服务器计划代码以查看数据中心。
                  </p>
                )}
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-cyber-muted text-sm mb-1">抢购失败后重试间隔 (秒)</label>
              <input
                type="number"
                value={retryInterval}
                onChange={(e) => setRetryInterval(parseInt(e.target.value, 10))}
                min="5"
                className="cyber-input w-full"
              />
            </div>

            <div className="flex justify-end">
              <button
                onClick={addQueueItem}
                className="cyber-button"
                disabled={!planCodeInput.trim() || selectedDatacenters.length === 0}
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

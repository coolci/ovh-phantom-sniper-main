import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useAPI } from "@/context/APIContext";
import axios from "axios";
import { toast } from "sonner";
import { XIcon, RefreshCwIcon, PlusIcon, SearchIcon, PlayIcon, PauseIcon, Trash2Icon, ArrowUpDownIcon, HeartIcon } from 'lucide-react';
import { OVH_DATACENTERS, DatacenterInfo } from "@/config/ovhConstants";

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
  const [showAddForm, setShowAddForm] = useState(true);
  const [servers, setServers] = useState<ServerPlan[]>([]);
  const [planCodeInput, setPlanCodeInput] = useState<string>("123");
  const [selectedServer, setSelectedServer] = useState<ServerPlan | null>(null);
  const [selectedDatacenters, setSelectedDatacenters] = useState<string[]>([]);
  const [retryInterval, setRetryInterval] = useState<number>(29);

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

  const handleDatacenterChange = (dcCode: string) => {
    setSelectedDatacenters(prev => 
      prev.includes(dcCode) ? prev.filter(d => d !== dcCode) : [...prev, dcCode]
    );
  };

  return (
    <div className="space-y-6 p-4 md:p-6 bg-cyber-background text-cyber-text min-h-screen">
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
          <RefreshCwIcon size={12} className="mr-1" />
          刷新
        </button>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="cyber-button text-xs flex items-center bg-cyber-primary hover:bg-cyber-primary-dark text-white"
        >
          <PlusIcon size={14} className="mr-1" />
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
          className="bg-cyber-surface-dark p-6 rounded-lg shadow-xl border border-cyber-border relative"
        >
          <button 
            onClick={() => setShowAddForm(false)} 
            className="absolute top-3 right-3 text-cyber-muted hover:text-cyber-text transition-colors"
          >
            <XIcon size={20} />
          </button>
          <h2 className="text-xl font-semibold mb-6 text-cyber-primary-accent">添加抢购任务</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            {/* Left Column: Plan Code & Retry Interval */}
            <div className="md:col-span-1 space-y-6">
              <div>
                <label htmlFor="planCode" className="block text-sm font-medium text-cyber-secondary mb-1">服务器计划代码</label>
                <input
                  type="text"
                  id="planCode"
                  value={planCodeInput}
                  onChange={(e) => setPlanCodeInput(e.target.value)}
                  placeholder="例如: advance-1"
                  className="w-full cyber-input bg-cyber-surface text-cyber-text border-cyber-border focus:ring-cyber-primary focus:border-cyber-primary"
                />
              </div>
              <div>
                <label htmlFor="retryInterval" className="block text-sm font-medium text-cyber-secondary mb-1">抢购失败后重试间隔 (秒)</label>
                <input
                  type="number"
                  id="retryInterval"
                  value={retryInterval}
                  onChange={(e) => setRetryInterval(Number(e.target.value))}
                  min="5"
                  className="w-full cyber-input bg-cyber-surface text-cyber-text border-cyber-border focus:ring-cyber-primary focus:border-cyber-primary"
                />
              </div>
            </div>

            {/* Right Column: Datacenter Selection */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-cyber-secondary mb-2">选择数据中心 (可选)</label>
              <div className="h-48 p-3 bg-cyber-surface border border-cyber-border rounded-md overflow-y-auto grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2 custom-scrollbar">
                {OVH_DATACENTERS.sort((a, b) => a.name.localeCompare(b.name)).map(dc => (
                  <div key={dc.code} className="flex items-center">
                    <input
                      type="checkbox"
                      id={`dc-${dc.code}`}
                      checked={selectedDatacenters.includes(dc.code)}
                      onChange={() => handleDatacenterChange(dc.code)}
                      className="cyber-checkbox h-4 w-4 text-cyber-primary bg-cyber-surface border-cyber-border focus:ring-cyber-primary"
                    />
                    <label htmlFor={`dc-${dc.code}`} className="ml-2 text-sm text-cyber-text-dimmed truncate" title={`${dc.name} (${dc.code})`}>
                      {dc.name} ({dc.code})
                    </label>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <button
            onClick={addQueueItem}
            className="w-full cyber-button bg-cyber-primary hover:bg-cyber-primary-dark text-white font-semibold py-2.5"
            disabled={!planCodeInput.trim()}
          >
            添加到队列
          </button>
        </motion.div>
      )}

      {/* Queue List */}
      <motion.div variants={containerVariants} initial="hidden" animate="visible">
        {isLoading && queueItems.length === 0 && (
          <div className="text-center py-10">
            <RefreshCwIcon className="mx-auto animate-spin text-cyber-primary mb-2" size={24} />
            <p className="text-cyber-secondary">正在加载队列...</p>
          </div>
        )}

        {!isLoading && queueItems.length === 0 && (
          <div className="text-center py-10 border border-dashed border-cyber-border rounded-lg">
            <SearchIcon className="mx-auto text-cyber-secondary mb-2" size={32} />
            <p className="text-cyber-secondary font-medium">队列为空</p>
            <p className="text-xs text-cyber-muted">通过上方的表单添加新的抢购任务。</p>
          </div>
        )}

        {queueItems.length > 0 && (
          <div className="space-y-3">
            {queueItems.map(item => (
              <motion.div 
                key={item.id} 
                variants={itemVariants}
                className="bg-cyber-surface p-4 rounded-lg shadow-md border border-cyber-border flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3"
              >
                <div className="flex-grow">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="px-2 py-0.5 text-xs bg-cyber-primary-accent/20 text-cyber-primary-accent rounded-full font-mono">
                      {item.planCode}
                    </span>
                    <span className="text-sm text-cyber-text-dimmed">DC: {item.datacenter.toUpperCase()}</span>
                  </div>
                  <p className="text-xs text-cyber-muted">
                    下次尝试: {item.retryCount > 0 ? `${item.retryInterval}秒后 (第${item.retryCount + 1}次)` : `即将开始` } | 创建于: {new Date(item.createdAt).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2 mt-2 sm:mt-0 flex-shrink-0">
                  <span 
                    className={`text-xs px-2 py-1 rounded-full font-medium
                      ${item.status === 'pending' ? 'bg-yellow-500/20 text-yellow-400' :
                        item.status === 'running' ? 'bg-green-500/20 text-green-400' :
                        item.status === 'completed' ? 'bg-blue-500/20 text-blue-400' :
                        item.status === 'failed' ? 'bg-red-500/20 text-red-400' : 'bg-gray-500/20 text-gray-400'}
                    `}
                  >
                    {item.status === "pending" && "待命中"}
                    {item.status === "running" && "运行中"}
                    {item.status === "completed" && "已完成"}
                    {item.status === "failed" && "失败"}
                  </span>
                  <button 
                    onClick={() => toggleQueueItemStatus(item.id, item.status)}
                    className="p-1.5 hover:bg-cyber-hover rounded text-cyber-secondary hover:text-cyber-primary transition-colors"
                    title={item.status === 'running' ? "暂停" : "启动"}
                  >
                    {item.status === 'running' ? <PauseIcon size={16} /> : <PlayIcon size={16} />}
                  </button>
                  <button 
                    onClick={() => removeQueueItem(item.id)}
                    className="p-1.5 hover:bg-cyber-hover rounded text-cyber-secondary hover:text-red-500 transition-colors"
                    title="移除"
                  >
                    <Trash2Icon size={16} />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
};

export default QueuePage;

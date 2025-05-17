
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import axios from "axios";
import { toast } from "sonner";

// Backend API URL (update this to match your backend)
const API_URL = 'http://localhost:5000/api';

interface PurchaseHistory {
  id: string;
  planCode: string;
  datacenter: string;
  status: "success" | "failed";
  orderId?: string;
  orderUrl?: string;
  errorMessage?: string;
  purchaseTime: string;
}

const HistoryPage = () => {
  const [history, setHistory] = useState<PurchaseHistory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<"all" | "success" | "failed">("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [filteredHistory, setFilteredHistory] = useState<PurchaseHistory[]>([]);

  // Fetch purchase history
  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get(`${API_URL}/purchase-history`);
      setHistory(response.data);
      setFilteredHistory(response.data);
    } catch (error) {
      console.error("Error fetching purchase history:", error);
      toast.error("获取购买历史记录失败");
    } finally {
      setIsLoading(false);
    }
  };

  // Clear history
  const clearHistory = async () => {
    if (!confirm("确定要清空购买历史记录吗？此操作不可撤销。")) {
      return;
    }
    
    try {
      await axios.delete(`${API_URL}/purchase-history`);
      toast.success("已清空购买历史记录");
      fetchHistory();
    } catch (error) {
      console.error("Error clearing purchase history:", error);
      toast.error("清空购买历史记录失败");
    }
  };

  // Initial fetch
  useEffect(() => {
    fetchHistory();
  }, []);

  // Apply filters
  useEffect(() => {
    if (history.length === 0) return;
    
    let filtered = [...history];
    
    // Apply status filter
    if (filterStatus !== "all") {
      filtered = filtered.filter(item => item.status === filterStatus);
    }
    
    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        item => 
          item.planCode.toLowerCase().includes(term) ||
          item.datacenter.toLowerCase().includes(term) ||
          (item.orderId && item.orderId.toLowerCase().includes(term))
      );
    }
    
    setFilteredHistory(filtered);
  }, [history, filterStatus, searchTerm]);

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h1 className="text-3xl font-bold mb-1 cyber-glow-text">抢购历史</h1>
        <p className="text-cyber-muted mb-6">查看服务器购买历史记录</p>
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
              placeholder="搜索..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="cyber-input pl-10 w-full"
            />
          </div>
          
          <div>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as "all" | "success" | "failed")}
              className="cyber-input w-full"
            >
              <option value="all">所有状态</option>
              <option value="success">成功</option>
              <option value="failed">失败</option>
            </select>
          </div>
          
          <div className="flex items-center justify-end space-x-2">
            <button
              onClick={() => fetchHistory()}
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
              onClick={clearHistory}
              className="cyber-button text-xs flex items-center bg-red-500/10 border-red-500/30 hover:border-red-500/50"
              disabled={isLoading || history.length === 0}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
                <path d="M3 6h18"></path>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
              清空
            </button>
          </div>
        </div>
      </div>

      {/* History List */}
      <div className="cyber-panel overflow-hidden">
        {isLoading ? (
          <div className="animate-pulse p-4">
            <div className="h-8 bg-cyber-grid/30 rounded mb-4"></div>
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-16 bg-cyber-grid/50 rounded"></div>
              ))}
            </div>
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="p-8 text-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-cyber-muted mx-auto mb-4">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            <p className="text-cyber-muted">没有找到购买历史记录</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-cyber-grid/30 text-cyber-muted text-left text-sm">
                  <th className="p-4">服务器</th>
                  <th className="p-4">数据中心</th>
                  <th className="p-4">状态</th>
                  <th className="p-4">订单 ID</th>
                  <th className="p-4">购买时间</th>
                  <th className="p-4">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-cyber-grid/20">
                {filteredHistory.map((item) => (
                  <motion.tr 
                    key={item.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="hover:bg-cyber-grid/10 transition-colors"
                  >
                    <td className="p-4 font-medium text-cyber-accent">{item.planCode}</td>
                    <td className="p-4">{item.datacenter}</td>
                    <td className="p-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs ${
                        item.status === "success" 
                          ? "bg-green-500/20 text-green-400" 
                          : "bg-red-500/20 text-red-400"
                      }`}>
                        {item.status === "success" ? "成功" : "失败"}
                      </span>
                    </td>
                    <td className="p-4 text-cyber-muted">
                      {item.orderId || "-"}
                    </td>
                    <td className="p-4 text-cyber-muted">
                      {new Date(item.purchaseTime).toLocaleString()}
                    </td>
                    <td className="p-4">
                      {item.status === "success" && item.orderUrl ? (
                        <a 
                          href={item.orderUrl} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-cyber-accent hover:text-cyber-accent/80 transition-colors text-sm"
                        >
                          查看订单
                        </a>
                      ) : item.status === "failed" && item.errorMessage ? (
                        <button
                          onClick={() => toast.info(item.errorMessage)}
                          className="text-red-400 hover:text-red-400/80 transition-colors text-sm"
                        >
                          查看错误
                        </button>
                      ) : (
                        "-"
                      )}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default HistoryPage;

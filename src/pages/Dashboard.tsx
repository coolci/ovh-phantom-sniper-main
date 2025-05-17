
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { useAPI } from "@/context/APIContext";
import axios from "axios";

// Backend API URL (update this to match your backend)
const API_URL = 'http://localhost:5000/api';

interface StatsType {
  activeQueues: number;
  totalServers: number;
  availableServers: number;
  purchaseSuccess: number;
  purchaseFailed: number;
}

const Dashboard = () => {
  const { isAuthenticated } = useAPI();
  const [stats, setStats] = useState<StatsType>({
    activeQueues: 0,
    totalServers: 0,
    availableServers: 0,
    purchaseSuccess: 0,
    purchaseFailed: 0,
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get(`${API_URL}/stats`);
        setStats(response.data);
      } catch (error) {
        console.error("Error fetching stats:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
    
    // Set up polling interval
    const interval = setInterval(fetchStats, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: { y: 0, opacity: 1 }
  };

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h1 className="text-3xl font-bold mb-1 cyber-glow-text">仪表盘</h1>
        <p className="text-cyber-muted mb-6">OVH 服务器抢购平台状态概览</p>
      </motion.div>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
      >
        {/* 活跃队列 */}
        <motion.div variants={itemVariants} className="cyber-card relative overflow-hidden">
          <div className="absolute top-0 right-0 w-16 h-16 -mr-6 -mt-6 bg-cyber-accent/10 rounded-full blur-xl"></div>
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-cyber-muted text-sm mb-1">活跃队列</h3>
              {isLoading ? (
                <div className="h-8 w-16 bg-cyber-grid animate-pulse rounded"></div>
              ) : (
                <p className="text-3xl font-cyber font-bold text-cyber-accent">{stats.activeQueues}</p>
              )}
            </div>
            <div className="p-2 bg-cyber-accent/10 rounded-full">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-cyber-accent">
                <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
                <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
                <path d="M9 12h6"></path>
                <path d="M9 16h6"></path>
                <path d="M9 8h6"></path>
              </svg>
            </div>
          </div>
          <div className="mt-4 text-cyber-muted text-xs">
            <Link to="/queue" className="inline-flex items-center hover:text-cyber-accent transition-colors">
              查看队列 
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="ml-1">
                <path d="m9 18 6-6-6-6"/>
              </svg>
            </Link>
          </div>
        </motion.div>

        {/* 服务器总数 */}
        <motion.div variants={itemVariants} className="cyber-card relative overflow-hidden">
          <div className="absolute top-0 right-0 w-16 h-16 -mr-6 -mt-6 bg-cyber-neon/10 rounded-full blur-xl"></div>
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-cyber-muted text-sm mb-1">服务器总数</h3>
              {isLoading ? (
                <div className="h-8 w-16 bg-cyber-grid animate-pulse rounded"></div>
              ) : (
                <p className="text-3xl font-cyber font-bold text-cyber-neon">{stats.totalServers}</p>
              )}
            </div>
            <div className="p-2 bg-cyber-neon/10 rounded-full">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-cyber-neon">
                <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
                <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
                <line x1="6" y1="6" x2="6.01" y2="6"></line>
                <line x1="6" y1="18" x2="6.01" y2="18"></line>
              </svg>
            </div>
          </div>
          <div className="mt-1 flex items-center text-xs">
            <span className={`inline-flex items-center px-2 py-0.5 rounded ${
              stats.availableServers > 0 
                ? 'text-green-400 bg-green-400/10' 
                : 'text-cyber-muted bg-cyber-grid/30'
            }`}>
              <span className={`w-1.5 h-1.5 mr-1 rounded-full ${
                stats.availableServers > 0 ? 'bg-green-400 animate-pulse' : 'bg-cyber-muted'
              }`}></span>
              可用: {isLoading ? '-' : stats.availableServers}
            </span>
          </div>
          <div className="mt-2 text-cyber-muted text-xs">
            <Link to="/servers" className="inline-flex items-center hover:text-cyber-neon transition-colors">
              查看服务器 
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="ml-1">
                <path d="m9 18 6-6-6-6"/>
              </svg>
            </Link>
          </div>
        </motion.div>

        {/* 抢购成功 */}
        <motion.div variants={itemVariants} className="cyber-card relative overflow-hidden">
          <div className="absolute top-0 right-0 w-16 h-16 -mr-6 -mt-6 bg-green-500/10 rounded-full blur-xl"></div>
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-cyber-muted text-sm mb-1">抢购成功</h3>
              {isLoading ? (
                <div className="h-8 w-16 bg-cyber-grid animate-pulse rounded"></div>
              ) : (
                <p className="text-3xl font-cyber font-bold text-green-400">{stats.purchaseSuccess}</p>
              )}
            </div>
            <div className="p-2 bg-green-500/10 rounded-full">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-green-400">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
            </div>
          </div>
          <div className="mt-4 text-cyber-muted text-xs">
            <Link to="/history" className="inline-flex items-center hover:text-green-400 transition-colors">
              查看历史 
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="ml-1">
                <path d="m9 18 6-6-6-6"/>
              </svg>
            </Link>
          </div>
        </motion.div>

        {/* 抢购失败 */}
        <motion.div variants={itemVariants} className="cyber-card relative overflow-hidden">
          <div className="absolute top-0 right-0 w-16 h-16 -mr-6 -mt-6 bg-red-500/10 rounded-full blur-xl"></div>
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-cyber-muted text-sm mb-1">抢购失败</h3>
              {isLoading ? (
                <div className="h-8 w-16 bg-cyber-grid animate-pulse rounded"></div>
              ) : (
                <p className="text-3xl font-cyber font-bold text-red-400">{stats.purchaseFailed}</p>
              )}
            </div>
            <div className="p-2 bg-red-500/10 rounded-full">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-red-400">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </div>
          </div>
          <div className="mt-4 text-cyber-muted text-xs">
            <Link to="/logs" className="inline-flex items-center hover:text-red-400 transition-colors">
              查看日志 
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="ml-1">
                <path d="m9 18 6-6-6-6"/>
              </svg>
            </Link>
          </div>
        </motion.div>
      </motion.div>

      {/* 最近活动和队列状态 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* 活跃队列详情 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.3 }}
          className="cyber-card lg:col-span-2"
        >
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-bold text-cyber-text">活跃队列</h2>
            <Link 
              to="/queue" 
              className="text-cyber-muted text-xs hover:text-cyber-accent transition-colors"
            >
              查看全部
            </Link>
          </div>

          {isLoading ? (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-16 bg-cyber-grid/50 animate-pulse rounded"></div>
              ))}
            </div>
          ) : stats.activeQueues === 0 ? (
            <div className="cyber-panel bg-cyber-grid/30 p-4 text-center text-cyber-muted">
              <p>没有活跃队列</p>
              <Link 
                to="/queue" 
                className="mt-2 cyber-button text-xs inline-block px-3 py-1"
              >
                创建队列
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {/* 这里可以显示队列详情，但因为我们没有实际数据，所以先用占位符 */}
              <div className="cyber-panel p-3 bg-cyber-grid/30 flex justify-between items-center">
                <div className="flex-1">
                  <p className="font-medium">25skmystery01</p>
                  <div className="flex items-center gap-2 text-xs text-cyber-muted mt-1">
                    <span>RBX</span>
                    <span>•</span>
                    <span>内存: 32GB</span>
                    <span>•</span>
                    <span>硬盘: 2TB</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="animate-pulse text-green-400 text-xs flex items-center">
                    <span className="w-1.5 h-1.5 mr-1 rounded-full bg-green-400"></span>
                    运行中
                  </span>
                  <button className="p-1 hover:text-cyber-accent transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                      <line x1="9" y1="9" x2="15" y2="15"></line>
                      <line x1="15" y1="9" x2="9" y2="15"></line>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          )}
        </motion.div>

        {/* API 状态 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.3 }}
          className="cyber-card"
        >
          <h2 className="text-lg font-bold mb-4">系统状态</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-2 border-b border-cyber-grid">
              <span className="text-cyber-muted">API 连接</span>
              <span className={`flex items-center ${isAuthenticated ? 'text-green-400' : 'text-red-400'}`}>
                <span className={`w-2 h-2 rounded-full mr-2 ${isAuthenticated ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`}></span>
                {isAuthenticated ? '已连接' : '未连接'}
              </span>
            </div>
            <div className="flex justify-between items-center p-2 border-b border-cyber-grid">
              <span className="text-cyber-muted">后端服务</span>
              <span className="flex items-center text-green-400">
                <span className="w-2 h-2 rounded-full mr-2 bg-green-400 animate-pulse"></span>
                运行中
              </span>
            </div>
            <div className="flex justify-between items-center p-2 border-b border-cyber-grid">
              <span className="text-cyber-muted">自动抢购</span>
              <span className="flex items-center text-green-400">
                <span className="w-2 h-2 rounded-full mr-2 bg-green-400 animate-pulse"></span>
                已启用
              </span>
            </div>
            <div className="flex justify-between items-center p-2">
              <span className="text-cyber-muted">版本</span>
              <span className="text-cyber-text">v1.0.0</span>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Dashboard;

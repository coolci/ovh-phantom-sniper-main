import { useState, useEffect, useRef } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useIsMobile } from "@/hooks/use-mobile";
import Sidebar from "./Sidebar";
import { useAPI } from "@/context/APIContext";
import APINotice from "./APINotice";

const Layout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const isMobile = useIsMobile();
  const { isAuthenticated, isLoading } = useAPI();
  const location = useLocation();
  const touchStartX = useRef(0);
  const touchEndX = useRef(0);
  
  // 监听触摸事件以实现从左向右划出侧边栏
  useEffect(() => {
    if (isMobile) {
      const handleTouchStart = (e: TouchEvent) => {
        touchStartX.current = e.touches[0].clientX;
      };
      
      const handleTouchEnd = (e: TouchEvent) => {
        touchEndX.current = e.changedTouches[0].clientX;
        const distance = touchEndX.current - touchStartX.current;
        
        // 如果从屏幕左边缘开始向右划动超过30px，打开侧边栏
        if (touchStartX.current < 20 && distance > 30 && !sidebarOpen) {
          setSidebarOpen(true);
        }
        
        // 如果侧边栏打开，从右向左划动超过50px，关闭侧边栏
        if (distance < -50 && sidebarOpen) {
          setSidebarOpen(false);
        }
      };
      
      document.addEventListener('touchstart', handleTouchStart);
      document.addEventListener('touchend', handleTouchEnd);
      
      return () => {
        document.removeEventListener('touchstart', handleTouchStart);
        document.removeEventListener('touchend', handleTouchEnd);
      };
    }
  }, [isMobile, sidebarOpen]);

  useEffect(() => {
    // 仅在移动端时关闭边栏，桌面端始终保持显示
    if (isMobile) {
      setSidebarOpen(false);
    } else {
      setSidebarOpen(true);
    }
  }, [isMobile]);

  useEffect(() => {
    // 移动端切换页面时关闭侧边栏
    if (isMobile) {
      setSidebarOpen(false);
    }
  }, [location.pathname, isMobile]);

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <div className="min-h-screen flex flex-col bg-cyber-bg cyber-grid-bg text-cyber-text">
      {/* Animated top border */}
      <div className="fixed top-0 left-0 right-0 h-1 bg-gradient-to-r from-cyber-accent via-cyber-neon to-cyber-neon-alt animate-gradient-x z-50"></div>
      
      <div className="flex-1 flex relative">
        {/* 桌面端始终显示侧边栏 */}
        <div className={`hidden lg:block fixed inset-y-0 left-0 z-40`}>
          <Sidebar onToggle={toggleSidebar} isOpen={true} />
        </div>

        {/* 移动端可滑出的侧边栏 */}
        <AnimatePresence mode="wait">
          {isMobile && sidebarOpen && (
            <>
              {/* 背景遮罩，点击关闭侧边栏 */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.5 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black z-30"
                onClick={() => setSidebarOpen(false)}
                style={{ pointerEvents: 'auto' }}
              />
              
              {/* 侧边栏 */}
              <motion.div
                initial={{ x: -280 }}
                animate={{ x: 0 }}
                exit={{ x: -280 }}
                transition={{ duration: 0.3, ease: "easeInOut" }}
                className="fixed inset-y-0 left-0 z-40"
              >
                <Sidebar onToggle={toggleSidebar} isOpen={sidebarOpen} />
                
                {/* 添加关闭按钮 */}
                <button 
                  onClick={() => setSidebarOpen(false)}
                  className="absolute top-4 right-4 w-8 h-8 bg-cyber-bg border border-cyber-accent/30 rounded-md flex items-center justify-center text-cyber-text hover:bg-cyber-accent/10 transition-colors"
                  aria-label="关闭侧边栏"
                >
                  <svg 
                    xmlns="http://www.w3.org/2000/svg" 
                    width="16" 
                    height="16" 
                    viewBox="0 0 24 24" 
                    fill="none" 
                    stroke="currentColor" 
                    strokeWidth="2" 
                    strokeLinecap="round" 
                    strokeLinejoin="round"
                  >
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </motion.div>
            </>
          )}
        </AnimatePresence>

        {/* 移动端贴边呼出按钮 */}
        {isMobile && !sidebarOpen && (
          <div 
            onClick={toggleSidebar}
            className="fixed right-0 top-1/3 z-40 cursor-pointer"
          >
            <div className="flex items-center">
              <div className="h-16 w-4 bg-cyber-bg/80 border border-r-0 border-cyber-accent/50 rounded-l-md flex items-center justify-center">
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  width="16" 
                  height="16" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  strokeWidth="2" 
                  strokeLinecap="round" 
                  strokeLinejoin="round"
                  className="text-cyber-accent"
                >
                  <polyline points="15 18 9 12 15 6"></polyline>
                </svg>
              </div>
              <div className="h-24 w-1.5 bg-cyber-accent/80 rounded-l-sm shadow-neon"></div>
            </div>
          </div>
        )}

        <main 
          className={`flex-1 py-6 px-4 sm:px-6 transition-all duration-300 ${
            !isMobile ? "lg:ml-72" : "ml-0"
          } relative`}
        >
          {!isLoading && !isAuthenticated && <APINotice />}
          
          <div className="container mx-auto max-w-7xl">
            {/* 移除面包屑部分，直接显示页面内容 */}
            <Outlet />
          </div>
          
          {/* 移除移动端菜单按钮，只依赖左侧滑动手势显示菜单 */}
        </main>
      </div>
      
      {/* 移除移动端底部导航栏 */}
    </div>
  );
};

export default Layout;

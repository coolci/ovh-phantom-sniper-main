
import { useState, useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useIsMobile } from "@/hooks/use-mobile";
import Sidebar from "./Sidebar";
import { useAPI } from "@/context/APIContext";
import APINotice from "./APINotice";
import { Menu } from "lucide-react";

const Layout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const isMobile = useIsMobile();
  const { isAuthenticated, isLoading } = useAPI();
  const location = useLocation();

  useEffect(() => {
    if (isMobile) {
      setSidebarOpen(false);
    } else {
      setSidebarOpen(true);
    }
  }, [isMobile]);

  useEffect(() => {
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
        <AnimatePresence mode="wait">
          {sidebarOpen && (
            <motion.div
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="fixed inset-y-0 left-0 z-40"
            >
              <Sidebar onToggle={toggleSidebar} isOpen={sidebarOpen} />
            </motion.div>
          )}
        </AnimatePresence>

        <main 
          className={`flex-1 py-6 px-4 sm:px-6 transition-all duration-300 ${
            sidebarOpen ? "lg:ml-72" : "ml-0"
          } relative`}
        >
          {!isLoading && !isAuthenticated && <APINotice />}
          
          <div className="container mx-auto max-w-7xl">
            <div className="flex items-center mb-6">
              {!sidebarOpen && !isMobile && (
                <motion.button
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.3 }}
                  onClick={toggleSidebar}
                  className="mr-4 p-2 bg-cyber-grid rounded-md border border-cyber-accent/30 text-cyber-accent hover:bg-cyber-accent/20 hover:shadow-neon transition-all"
                  aria-label="打开菜单"
                >
                  <Menu size={24} />
                </motion.button>
              )}
            </div>
            <Outlet />
          </div>
          
          {/* Mobile menu button - positioned in the top-left corner */}
          {isMobile && !sidebarOpen && (
            <motion.button
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.3 }}
              onClick={toggleSidebar}
              className="fixed top-6 left-6 z-50 p-3.5 bg-cyber-bg/80 backdrop-blur-sm rounded-md border border-cyber-accent text-cyber-accent shadow-sm hover:bg-cyber-accent/10 transition-all"
              aria-label="菜单"
            >
              <div className="flex flex-col space-y-1.5">
                <div className="w-6 h-1 bg-cyber-accent rounded-full"></div>
                <div className="w-6 h-1 bg-cyber-accent rounded-full"></div>
                <div className="w-6 h-1 bg-cyber-accent rounded-full"></div>
              </div>
            </motion.button>
          )}
          
          {isMobile && (
            <div className="fixed bottom-0 left-0 right-0 h-16 bg-cyber-bg/80 backdrop-blur-md border-t border-cyber-accent/20 flex justify-around items-center z-30 px-2 mobile-bottom-safe-area">
              <a href="/" className={`flex flex-col items-center p-2 ${location.pathname === '/' ? 'text-cyber-accent' : 'text-cyber-muted'}`}>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="20" x2="18" y2="10"></line>
                  <line x1="12" y1="20" x2="12" y2="4"></line>
                  <line x1="6" y1="20" x2="6" y2="14"></line>
                </svg>
                <span className="text-xs mt-1">仪表盘</span>
              </a>
              <a href="/servers" className={`flex flex-col items-center p-2 ${location.pathname.startsWith('/servers') ? 'text-cyber-accent' : 'text-cyber-muted'}`}>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
                  <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
                  <line x1="6" y1="6" x2="6.01" y2="6"></line>
                  <line x1="6" y1="18" x2="6.01" y2="18"></line>
                </svg>
                <span className="text-xs mt-1">服务器</span>
              </a>
              <a href="/queue" className={`flex flex-col items-center p-2 ${location.pathname.startsWith('/queue') ? 'text-cyber-accent' : 'text-cyber-muted'}`}>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
                  <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
                  <path d="M9 12h6"></path>
                  <path d="M9 16h6"></path>
                  <path d="M9 8h6"></path>
                </svg>
                <span className="text-xs mt-1">队列</span>
              </a>
            </div>
          )}
        </main>
      </div>
      
      {isMobile && <div className="h-16"></div>}
    </div>
  );
};

export default Layout;

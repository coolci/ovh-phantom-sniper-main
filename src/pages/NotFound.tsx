
import { useLocation } from "react-router-dom";
import { useEffect } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";

const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    console.error(
      "404 Error: User attempted to access non-existent route:",
      location.pathname
    );
  }, [location.pathname]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <motion.div 
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="cyber-panel p-12 text-center max-w-lg"
      >
        <h1 className="text-6xl font-bold mb-4 text-cyber-accent animate-pulse-glow">404</h1>
        <div className="cyber-grid-line my-4"></div>
        <p className="text-xl mb-4">页面未找到</p>
        <p className="text-cyber-muted mb-8">您请求的页面不存在或已被移除</p>
        
        <Link to="/" className="cyber-button px-6 py-3">
          返回首页
        </Link>
      </motion.div>
    </div>
  );
};

export default NotFound;

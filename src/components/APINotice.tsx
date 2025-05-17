
import { Link } from "react-router-dom";
import { motion } from "framer-motion";

const APINotice = () => {
  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mb-6 cyber-panel p-4 text-center"
    >
      <div className="flex flex-col md:flex-row items-center justify-center gap-4">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-yellow-400"
        >
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
          <line x1="12" y1="9" x2="12" y2="13"></line>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
        <div className="text-cyber-muted">
          您尚未配置 OVH API，某些功能将无法正常使用。
        </div>
        <Link
          to="/settings"
          className="cyber-button text-xs px-3 py-1"
        >
          配置 API
        </Link>
      </div>
    </motion.div>
  );
};

export default APINotice;

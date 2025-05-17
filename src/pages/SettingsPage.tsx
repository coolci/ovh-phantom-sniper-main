import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useAPI } from "@/context/APIContext";
import { toast } from "sonner";

const SettingsPage = () => {
  const { 
    appKey, 
    appSecret, 
    consumerKey, 
    endpoint,
    tgToken,
    tgChatId,
    iam,
    zone,
    isLoading,
    isAuthenticated,
    setAPIKeys,
    checkAuthentication
  } = useAPI();

  const [formValues, setFormValues] = useState({
    appKey: "",
    appSecret: "",
    consumerKey: "",
    endpoint: "ovh-eu",
    tgToken: "",
    tgChatId: "",
    iam: "go-ovh-ie",
    zone: "IE"
  });
  const [isSaving, setIsSaving] = useState(false);
  const [showValues, setShowValues] = useState({
    appKey: false,
    appSecret: false,
    consumerKey: false,
    tgToken: false
  });

  // Load current values when component mounts
  useEffect(() => {
    setFormValues({
      appKey: appKey || "",
      appSecret: appSecret || "",
      consumerKey: consumerKey || "",
      endpoint: endpoint || "ovh-eu",
      tgToken: tgToken || "",
      tgChatId: tgChatId || "",
      iam: iam || "go-ovh-ie",
      zone: zone || "IE"
    });
  }, [appKey, appSecret, consumerKey, endpoint, tgToken, tgChatId, iam, zone]);

  // Auto-update IAM when zone changes
  useEffect(() => {
    if (formValues.zone) {
      setFormValues(prev => ({
        ...prev,
        iam: `go-ovh-${formValues.zone.toLowerCase()}`
      }));
    }
  }, [formValues.zone]);

  // Handle input changes
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormValues({
      ...formValues,
      [name]: value
    });
  };

  // Toggle password visibility
  const toggleShowValue = (field: keyof typeof showValues) => {
    setShowValues({
      ...showValues,
      [field]: !showValues[field]
    });
  };

  // Save settings
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate required fields
    if (!formValues.appKey || !formValues.appSecret || !formValues.consumerKey) {
      toast.error("请填写所有必填字段");
      return;
    }
    
    setIsSaving(true);
    try {
      await setAPIKeys(formValues);
      const isValid = await checkAuthentication();
      
      if (isValid) {
        toast.success("API设置已保存并验证");
      } else {
        toast.warning("API设置已保存，但验证失败");
      }
    } catch (error) {
      console.error("Error saving settings:", error);
      toast.error("保存设置失败");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h1 className="text-3xl font-bold mb-1 cyber-glow-text">API设置</h1>
        <p className="text-cyber-muted mb-6">配置OVH API和通知设置</p>
      </motion.div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin w-10 h-10 border-4 border-cyber-accent border-t-transparent rounded-full"></div>
          <span className="ml-3 text-cyber-muted">加载中...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2">
            <form onSubmit={handleSubmit} className="cyber-panel p-6 space-y-6">
              <div>
                <h2 className="text-xl font-bold mb-4">OVH API 凭据</h2>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-cyber-muted mb-1">
                      应用密钥 (APP KEY) <span className="text-red-400">*</span>
                    </label>
                    <div className="relative">
                      <input
                        type={showValues.appKey ? "text" : "password"}
                        name="appKey"
                        value={formValues.appKey}
                        onChange={handleChange}
                        className="cyber-input w-full pr-10"
                        placeholder="xxxxxxxxxxxxxxxx"
                        required
                      />
                      <button
                        type="button"
                        onClick={() => toggleShowValue("appKey")}
                        className="absolute inset-y-0 right-0 px-3 text-cyber-muted hover:text-cyber-accent"
                      >
                        {showValues.appKey ? (
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                            <line x1="1" y1="1" x2="23" y2="23"></line>
                          </svg>
                        ) : (
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-cyber-muted mb-1">
                      应用密钥 (APP SECRET) <span className="text-red-400">*</span>
                    </label>
                    <div className="relative">
                      <input
                        type={showValues.appSecret ? "text" : "password"}
                        name="appSecret"
                        value={formValues.appSecret}
                        onChange={handleChange}
                        className="cyber-input w-full pr-10"
                        placeholder="xxxxxxxxxxxxxxxx"
                        required
                      />
                      <button
                        type="button"
                        onClick={() => toggleShowValue("appSecret")}
                        className="absolute inset-y-0 right-0 px-3 text-cyber-muted hover:text-cyber-accent"
                      >
                        {showValues.appSecret ? (
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                            <line x1="1" y1="1" x2="23" y2="23"></line>
                          </svg>
                        ) : (
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-cyber-muted mb-1">
                      消费者密钥 (CONSUMER KEY) <span className="text-red-400">*</span>
                    </label>
                    <div className="relative">
                      <input
                        type={showValues.consumerKey ? "text" : "password"}
                        name="consumerKey"
                        value={formValues.consumerKey}
                        onChange={handleChange}
                        className="cyber-input w-full pr-10"
                        placeholder="xxxxxxxxxxxxxxxx"
                        required
                      />
                      <button
                        type="button"
                        onClick={() => toggleShowValue("consumerKey")}
                        className="absolute inset-y-0 right-0 px-3 text-cyber-muted hover:text-cyber-accent"
                      >
                        {showValues.consumerKey ? (
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                            <line x1="1" y1="1" x2="23" y2="23"></line>
                          </svg>
                        ) : (
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-cyber-muted mb-1">
                      API 节点 (ENDPOINT)
                    </label>
                    <select
                      name="endpoint"
                      value={formValues.endpoint}
                      onChange={handleChange}
                      className="cyber-input w-full"
                    >
                      <option value="ovh-eu">欧洲 (ovh-eu)</option>
                      <option value="ovh-us">美国 (ovh-us)</option>
                      <option value="ovh-ca">加拿大 (ovh-ca)</option>
                    </select>
                    <p className="text-xs text-cyber-muted mt-1">默认: ovh-eu</p>
                  </div>
                </div>
              </div>
              
              <div className="cyber-grid-line pt-4">
                <h2 className="text-xl font-bold mb-4">区域设置</h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-cyber-muted mb-1">
                      OVH 子公司 (ZONE)
                    </label>
                    <select
                      name="zone"
                      value={formValues.zone}
                      onChange={handleChange}
                      className="cyber-input w-full"
                    >
                      <option value="IE">爱尔兰 (IE)</option>
                      <option value="FR">法国 (FR)</option>
                      <option value="GB">英国 (GB)</option>
                      <option value="DE">德国 (DE)</option>
                      <option value="ES">西班牙 (ES)</option>
                      <option value="PT">葡萄牙 (PT)</option>
                      <option value="IT">意大利 (IT)</option>
                      <option value="PL">波兰 (PL)</option>
                      <option value="FI">芬兰 (FI)</option>
                      <option value="LT">立陶宛 (LT)</option>
                      <option value="CZ">捷克 (CZ)</option>
                      <option value="NL">荷兰 (NL)</option>
                    </select>
                    <p className="text-xs text-cyber-muted mt-1">默认: IE</p>
                  </div>
                  
                  <div>
                    <label className="block text-cyber-muted mb-1">
                      标识 (IAM)
                    </label>
                    <input
                      type="text"
                      name="iam"
                      value={formValues.iam}
                      onChange={handleChange}
                      className="cyber-input w-full"
                      placeholder="go-ovh-ie"
                    />
                    <p className="text-xs text-cyber-muted mt-1">默认会根据 ZONE 设置自动生成，例如: go-ovh-ie</p>
                  </div>
                </div>
              </div>
              
              <div className="cyber-grid-line pt-4">
                <h2 className="text-xl font-bold mb-4">Telegram 通知设置 (可选)</h2>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-cyber-muted mb-1">
                      Telegram Bot Token
                    </label>
                    <div className="relative">
                      <input
                        type={showValues.tgToken ? "text" : "password"}
                        name="tgToken"
                        value={formValues.tgToken}
                        onChange={handleChange}
                        className="cyber-input w-full pr-10"
                        placeholder="123456789:ABCDEFGH..."
                      />
                      <button
                        type="button"
                        onClick={() => toggleShowValue("tgToken")}
                        className="absolute inset-y-0 right-0 px-3 text-cyber-muted hover:text-cyber-accent"
                      >
                        {showValues.tgToken ? (
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                            <line x1="1" y1="1" x2="23" y2="23"></line>
                          </svg>
                        ) : (
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-cyber-muted mb-1">
                      Telegram Chat ID
                    </label>
                    <input
                      type="text"
                      name="tgChatId"
                      value={formValues.tgChatId}
                      onChange={handleChange}
                      className="cyber-input w-full"
                      placeholder="-100123456789"
                    />
                  </div>
                </div>
              </div>
              
              <div className="flex justify-end pt-4">
                <button
                  type="submit"
                  className="cyber-button px-6"
                  disabled={isSaving}
                >
                  {isSaving ? (
                    <span className="flex items-center">
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-cyber-text" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      保存中...
                    </span>
                  ) : "保存设置"}
                </button>
              </div>
            </form>
          </div>
          
          <div>
            <div className="cyber-panel p-6">
              <h2 className="text-lg font-bold mb-4">连接状态</h2>
              
              <div className="space-y-4">
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${isAuthenticated ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`}></div>
                  <span className={isAuthenticated ? 'text-green-400' : 'text-red-400'}>
                    {isAuthenticated ? 'API 已连接' : 'API 未连接'}
                  </span>
                </div>
                
                <div className="cyber-grid-line pt-4">
                  <h3 className="font-medium mb-2">获取 OVH API 密钥</h3>
                  <p className="text-cyber-muted text-sm mb-2">
                    您需要从 OVH API 获取 APP KEY、APP SECRET 和 CONSUMER KEY 才能使用本服务。
                  </p>
                  <a 
                    href="https://api.ovh.com/createToken/" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="cyber-button text-xs mt-2 inline-flex items-center"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
                      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                      <polyline points="15 3 21 3 21 9"></polyline>
                      <line x1="10" y1="14" x2="21" y2="3"></line>
                    </svg>
                    获取 API 密钥
                  </a>
                </div>
                
                <div className="cyber-grid-line pt-4">
                  <h3 className="font-medium mb-2">所需权限</h3>
                  <ul className="text-cyber-muted text-sm list-disc pl-5 space-y-1">
                    <li>/dedicated/server/*</li>
                    <li>/order/*</li>
                    <li>/me/*</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SettingsPage;

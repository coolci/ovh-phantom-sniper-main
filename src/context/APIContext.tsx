import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';
import { toast } from 'sonner';

// Backend API URL (update this to match your backend)
const API_URL = 'http://localhost:5000/api';

// 创建一个事件总线，用于在API认证状态变化时通知其他组件
export const apiEvents = {
  onAuthChanged: (callback: (isAuthenticated: boolean) => void) => {
    window.addEventListener('api-auth-changed', ((e: CustomEvent) => callback(e.detail)) as EventListener);
    return () => window.removeEventListener('api-auth-changed', ((e: CustomEvent) => callback(e.detail)) as EventListener);
  },
  emitAuthChanged: (isAuthenticated: boolean) => {
    window.dispatchEvent(new CustomEvent('api-auth-changed', { detail: isAuthenticated }));
  }
};

// Define API Context structure
interface APIContextType {
  appKey: string;
  appSecret: string;
  consumerKey: string;
  endpoint: string;
  tgToken: string;
  tgChatId: string;
  iam: string;
  zone: string;
  isLoading: boolean;
  isAuthenticated: boolean;
  setAPIKeys: (keys: APIKeysType) => Promise<void>;
  checkAuthentication: () => Promise<boolean>;
}

interface APIKeysType {
  appKey: string;
  appSecret: string;
  consumerKey: string;
  endpoint?: string;
  tgToken?: string;
  tgChatId?: string;
  iam?: string;
  zone?: string;
}

// Create the API Context
const APIContext = createContext<APIContextType | undefined>(undefined);

// Context Provider Component
export const API_Provider = ({ children }: { children: ReactNode }) => {
  const [appKey, setAppKey] = useState<string>('');
  const [appSecret, setAppSecret] = useState<string>('');
  const [consumerKey, setConsumerKey] = useState<string>('');
  const [endpoint, setEndpoint] = useState<string>('ovh-eu');
  const [tgToken, setTgToken] = useState<string>('');
  const [tgChatId, setTgChatId] = useState<string>('');
  const [iam, setIam] = useState<string>('go-ovh-ie');
  const [zone, setZone] = useState<string>('IE');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  // Load API keys from backend on mount
  useEffect(() => {
    const loadAPIKeys = async () => {
      try {
        const response = await axios.get(`${API_URL}/settings`);
        const data = response.data;
        
        if (data && data.appKey) {
          setAppKey(data.appKey);
          setAppSecret(data.appSecret);
          setConsumerKey(data.consumerKey);
          setEndpoint(data.endpoint || 'ovh-eu');
          setTgToken(data.tgToken || '');
          setTgChatId(data.tgChatId || '');
          setIam(data.iam || 'go-ovh-ie');
          setZone(data.zone || 'IE');
          
          setIsAuthenticated(true);
          apiEvents.emitAuthChanged(true);
        }
      } catch (error) {
        console.error('Failed to load API keys:', error);
        setIsAuthenticated(false);
        apiEvents.emitAuthChanged(false);
      } finally {
        setIsLoading(false);
      }
    };

    loadAPIKeys();
  }, []);

  // Save API keys to backend
  const setAPIKeys = async (keys: APIKeysType): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await axios.post(`${API_URL}/settings`, {
        appKey: keys.appKey,
        appSecret: keys.appSecret,
        consumerKey: keys.consumerKey,
        endpoint: keys.endpoint || 'ovh-eu',
        tgToken: keys.tgToken || '',
        tgChatId: keys.tgChatId || '',
        iam: keys.iam || 'go-ovh-ie',
        zone: keys.zone || 'IE'
      });
      
      setAppKey(keys.appKey);
      setAppSecret(keys.appSecret);
      setConsumerKey(keys.consumerKey);
      setEndpoint(keys.endpoint || 'ovh-eu');
      setTgToken(keys.tgToken || '');
      setTgChatId(keys.tgChatId || '');
      setIam(keys.iam || 'go-ovh-ie');
      setZone(keys.zone || 'IE');
      
      setIsAuthenticated(true);
      apiEvents.emitAuthChanged(true);
      toast.success('API设置已保存');
    } catch (error) {
      console.error('Failed to save API keys:', error);
      toast.error('保存API设置失败');
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // Check authentication status with backend
  const checkAuthentication = async (): Promise<boolean> => {
    try {
      const response = await axios.post(`${API_URL}/verify-auth`, {
        appKey,
        appSecret,
        consumerKey,
        endpoint
      });
      
      const isValid = response.data.valid;
      setIsAuthenticated(isValid);
      apiEvents.emitAuthChanged(isValid);
      return isValid;
    } catch (error) {
      console.error('Authentication check failed:', error);
      setIsAuthenticated(false);
      apiEvents.emitAuthChanged(false);
      return false;
    }
  };

  const value = {
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
  };

  return <APIContext.Provider value={value}>{children}</APIContext.Provider>;
};

// Custom hook to use the API context
export const useAPI = (): APIContextType => {
  const context = useContext(APIContext);
  if (context === undefined) {
    throw new Error('useAPI must be used within an APIProvider');
  }
  return context;
};

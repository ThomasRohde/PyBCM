import React, { createContext, useContext, useState, useEffect } from 'react';
import { ApiClient } from '../api/client';
import type { UserSession, Capability } from '../types/api';

interface AppContextType {
  userSession: UserSession | null;
  capabilities: Capability[];
  activeUsers: UserSession[];
  login: (nickname: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshCapabilities: () => Promise<void>;
  moveCapability: (
    capabilityId: number,
    newParentId: number | null,
    newOrder: number
  ) => Promise<void>;
  createCapability: (
    name: string,
    parentId?: number | null
  ) => Promise<void>;
  deleteCapability: (capabilityId: number) => Promise<void>;
  updateCapability: (
    capabilityId: number,
    name: string,
    description?: string | null
  ) => Promise<void>;
}

const AppContext = createContext<AppContextType | null>(null);

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [userSession, setUserSession] = useState<UserSession | null>(null);
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [activeUsers, setActiveUsers] = useState<UserSession[]>([]);

  // Fetch active users periodically
  useEffect(() => {
    const fetchActiveUsers = async () => {
      try {
        const users = await ApiClient.getActiveUsers();
        setActiveUsers(users);
      } catch (error) {
        console.error('Failed to fetch active users:', error);
      }
    };

    const interval = setInterval(fetchActiveUsers, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch capabilities when user session changes
  useEffect(() => {
    if (userSession) {
      refreshCapabilities();
    }
  }, [userSession]);

  const login = async (nickname: string) => {
    try {
      const session = await ApiClient.createUserSession({ nickname });
      setUserSession(session);
    } catch (error) {
      console.error('Failed to create user session:', error);
      throw error;
    }
  };

  const logout = async () => {
    if (userSession) {
      try {
        await ApiClient.removeUserSession(userSession.session_id);
        setUserSession(null);
        setCapabilities([]);
      } catch (error) {
        console.error('Failed to remove user session:', error);
        throw error;
      }
    }
  };

  const refreshCapabilities = async () => {
    try {
      const caps = await ApiClient.getCapabilities(null, true);
      setCapabilities(caps);
    } catch (error) {
      console.error('Failed to fetch capabilities:', error);
      throw error;
    }
  };

  const moveCapability = async (
    capabilityId: number,
    newParentId: number | null,
    newOrder: number
  ) => {
    if (!userSession) return;

    try {
      await ApiClient.moveCapability(
        capabilityId,
        { new_parent_id: newParentId, new_order: newOrder },
        userSession.session_id
      );
      await refreshCapabilities();
    } catch (error) {
      console.error('Failed to move capability:', error);
      throw error;
    }
  };

  const createCapability = async (name: string, parentId?: number | null) => {
    if (!userSession) return;

    try {
      await ApiClient.createCapability(
        { name, parent_id: parentId },
        userSession.session_id
      );
      await refreshCapabilities();
    } catch (error) {
      console.error('Failed to create capability:', error);
      throw error;
    }
  };

  const deleteCapability = async (capabilityId: number) => {
    if (!userSession) return;

    try {
      await ApiClient.deleteCapability(capabilityId, userSession.session_id);
      await refreshCapabilities();
    } catch (error) {
      console.error('Failed to delete capability:', error);
      throw error;
    }
  };

  const updateCapability = async (
    capabilityId: number,
    name: string,
    description?: string | null
  ) => {
    if (!userSession) return;

    try {
      await ApiClient.updateCapability(
        capabilityId,
        { name, description },
        userSession.session_id
      );
      await refreshCapabilities();
    } catch (error) {
      console.error('Failed to update capability:', error);
      throw error;
    }
  };

  const value = {
    userSession,
    capabilities,
    activeUsers,
    login,
    logout,
    refreshCapabilities,
    moveCapability,
    createCapability,
    deleteCapability,
    updateCapability,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

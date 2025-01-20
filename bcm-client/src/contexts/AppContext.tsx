import React, { createContext, useContext, useState, useEffect } from 'react';
import { ApiClient, wsManager } from '../api/client';
import type { UserSession, Capability } from '../types/api';
import toast from 'react-hot-toast';

interface DropTarget {
  capabilityId: number;
  type: 'sibling' | 'child' | 'between';
  position?: number;
}

interface AppContextType {
  userSession: UserSession | null;
  capabilities: Capability[];
  activeUsers: UserSession[];
  currentDropTarget: DropTarget | null;
  setCurrentDropTarget: (target: DropTarget | null) => void;
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
  const [currentDropTarget, setCurrentDropTarget] = useState<DropTarget | null>(null);

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

      // Set up WebSocket connection and capabilities refresh when user session changes
      useEffect(() => {
        if (userSession) {
          // Connect WebSocket
          wsManager.connect();
          
          // Set up model change handler
          const unsubscribeModel = wsManager.onModelChange((user, action) => {
            refreshCapabilities();
            // Don't show toast for own actions
            if (user !== userSession.nickname) {
              toast(`${user} ${action}`, {
                duration: 3000,
                position: 'bottom-right',
                style: {
                  background: '#4B5563',
                  color: '#fff',
                  padding: '12px 24px',
                  borderRadius: '8px',
                },
              });
            }
          });

          // Set up user event handler
          const unsubscribeUser = wsManager.onUserEvent((user, event) => {
            // Don't show toast for own events
            if (user !== userSession.nickname) {
              toast(`${user} has ${event}`, {
                duration: 3000,
                position: 'bottom-right',
                style: {
                  background: event === 'joined' ? '#10B981' : '#EF4444',
                  color: '#fff',
                  padding: '12px 24px',
                  borderRadius: '8px',
                },
              });
            }
          });

          // Initial capabilities fetch
          refreshCapabilities();

          // Cleanup
          return () => {
            unsubscribeModel();
            unsubscribeUser();
            wsManager.disconnect();
          };
        }
      }, [userSession]);

  const login = async (nickname: string) => {
    try {
      const session = await ApiClient.createUserSession({ nickname });
      setUserSession(session);
    } catch (error: unknown) {
      console.error('Failed to create user session:', error);
      if (error && typeof error === 'object' && 'response' in error) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        const axiosError = error as { 
          response: { 
            data: unknown; 
            status: number; 
            headers: unknown; 
          } 
        };
        console.error('Error response:', {
          data: axiosError.response.data,
          status: axiosError.response.status,
          headers: axiosError.response.headers
        });
      } else if (error && typeof error === 'object' && 'request' in error) {
        // The request was made but no response was received
        console.error('No response received:', (error as { request: unknown }).request);
      } else if (error instanceof Error) {
        // Something happened in setting up the request that triggered an Error
        console.error('Error setting up request:', error.message);
      }
      throw error;
    }
  };

  const logout = async () => {
    if (userSession) {
      try {
        await ApiClient.removeUserSession(userSession.session_id);
        wsManager.disconnect();
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
      if (Array.isArray(caps)) {
        setCapabilities(caps);
      } else {
        console.error('Invalid capabilities response:', caps);
        setCapabilities([]);
      }
    } catch (error) {
      console.error('Failed to fetch capabilities:', error);
      setCapabilities([]);
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
    currentDropTarget,
    setCurrentDropTarget,
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

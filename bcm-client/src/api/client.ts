import axios from 'axios';
import type { 
  User, 
  UserSession, 
  Capability, 
  CapabilityCreate, 
  CapabilityUpdate,
  CapabilityMove,
  PromptUpdate,
  CapabilityContextResponse,
  Settings,
  LayoutModel
} from '../types/api';

// In development, use the Vite dev server port
const isDev = import.meta.env.DEV;
const WS_URL = isDev 
  ? 'ws://127.0.0.1:8080/api/ws'
  : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws`;

const api = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
  baseURL: isDev ? 'http://127.0.0.1:8080' : undefined,
});

// WebSocket connection manager
class WebSocketManager {
  private ws: WebSocket | null = null;
  private onModelChangeCallbacks: Set<(user: string, action: string) => void> = new Set();
  private onUserEventCallbacks: Set<(user: string, event: string) => void> = new Set();

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(WS_URL);
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'model_changed') {
        this.notifyModelChange(data.user, data.action);
      } else if (data.type === 'user_event') {
        this.notifyUserEvent(data.user, data.event);
      }
    };

    this.ws.onclose = () => {
      // Attempt to reconnect after a delay
      setTimeout(() => this.connect(), 5000);
    };

    // Send periodic ping to keep connection alive
    setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
      }
    }, 30000);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  onModelChange(callback: (user: string, action: string) => void) {
    this.onModelChangeCallbacks.add(callback);
    return () => this.onModelChangeCallbacks.delete(callback);
  }

  onUserEvent(callback: (user: string, event: string) => void) {
    this.onUserEventCallbacks.add(callback);
    return () => this.onUserEventCallbacks.delete(callback);
  }

  private notifyModelChange(user: string, action: string) {
    this.onModelChangeCallbacks.forEach(callback => callback(user, action));
  }

  private notifyUserEvent(user: string, event: string) {
    this.onUserEventCallbacks.forEach(callback => callback(user, event));
  }
}

export const wsManager = new WebSocketManager();

export const ApiClient = {
  // User session management
  createUserSession: async (user: User): Promise<UserSession> => {
    const response = await api.post<UserSession>('/api/users', user);
    return response.data;
  },

  getActiveUsers: async (): Promise<UserSession[]> => {
    const response = await api.get<UserSession[]>('/api/users');
    return response.data;
  },

  removeUserSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/api/users/${sessionId}`);
  },

  // Capability locking
  lockCapability: async (capabilityId: number, nickname: string): Promise<void> => {
    await api.post(`/api/capabilities/lock/${capabilityId}?nickname=${nickname}`);
  },

  unlockCapability: async (capabilityId: number, nickname: string): Promise<void> => {
    await api.post(`/api/capabilities/unlock/${capabilityId}?nickname=${nickname}`);
  },

  // Capability CRUD operations
  createCapability: async (capability: CapabilityCreate, sessionId: string): Promise<Capability> => {
    const response = await api.post<Capability>(`/api/capabilities?session_id=${sessionId}`, capability);
    return response.data;
  },

  getCapability: async (capabilityId: number): Promise<Capability> => {
    const response = await api.get<Capability>(`/api/capabilities/${capabilityId}`);
    return response.data;
  },

  getCapabilityContext: async (capabilityId: number): Promise<CapabilityContextResponse> => {
    const response = await api.get<CapabilityContextResponse>(`/api/capabilities/${capabilityId}/context`);
    return response.data;
  },

  updateCapability: async (
    capabilityId: number, 
    capability: CapabilityUpdate, 
    sessionId: string
  ): Promise<Capability> => {
    const response = await api.put<Capability>(
      `/api/capabilities/${capabilityId}?session_id=${sessionId}`, 
      capability
    );
    return response.data;
  },

  deleteCapability: async (capabilityId: number, sessionId: string): Promise<void> => {
    await api.delete(`/api/capabilities/${capabilityId}?session_id=${sessionId}`);
  },

  // Capability movement and organization
  moveCapability: async (
    capabilityId: number, 
    move: CapabilityMove, 
    sessionId: string
  ): Promise<void> => {
    await api.post(
      `/api/capabilities/${capabilityId}/move?session_id=${sessionId}`, 
      move
    );
  },

  // Capability description and prompts
  updateDescription: async (
    capabilityId: number, 
    description: string, 
    sessionId: string
  ): Promise<void> => {
    await api.put(
      `/api/capabilities/${capabilityId}/description?session_id=${sessionId}&description=${encodeURIComponent(description)}`
    );
  },

  updatePrompt: async (
    capabilityId: number, 
    promptUpdate: PromptUpdate, 
    sessionId: string
  ): Promise<void> => {
    await api.put(
      `/api/capabilities/${capabilityId}/prompt?session_id=${sessionId}`, 
      promptUpdate
    );
  },

  // Get capabilities tree or list
  getCapabilities: async (
    parentId?: number | null, 
    hierarchical: boolean = false
  ): Promise<Capability[]> => {
    const params = new URLSearchParams();
    if (parentId !== undefined && parentId !== null) {
      params.append('parent_id', parentId.toString());
    }
    params.append('hierarchical', hierarchical.toString());
    
    const response = await api.get<Capability[]>(`/api/capabilities?${params.toString()}`);
    return response.data;
  },

  // Export/Import operations
  exportCapabilities: async (sessionId: string): Promise<Capability[]> => {
    const response = await api.get<Capability[]>(`/api/capabilities/export?session_id=${sessionId}`);
    return response.data;
  },

  importCapabilities: async (data: Capability[], sessionId: string): Promise<void> => {
    await api.post(`/api/capabilities/import?session_id=${sessionId}`, {
      data: data
    });
  },

  // Settings operations
  getSettings: async (): Promise<Settings> => {
    const response = await api.get<Settings>('/api/settings');
    return response.data;
  },

  updateSettings: async (settings: Settings): Promise<Settings> => {
    const response = await api.put<Settings>('/api/settings', settings);
    return response.data;
  },

  // Layout operations
  getLayout: async (nodeId: number): Promise<LayoutModel> => {
    const response = await api.get<LayoutModel>(`/api/layout/${nodeId}`);
    return response.data;
  },

  // Format operations
  formatNode: async (nodeId: number, format: string): Promise<Blob> => {
    const response = await api.post(`/api/format/${nodeId}`, { format }, { responseType: 'blob' });
    return response.data;
  }
};

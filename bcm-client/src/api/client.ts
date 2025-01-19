import axios from 'axios';
import type { 
  User, 
  UserSession, 
  Capability, 
  CapabilityCreate, 
  CapabilityUpdate,
  CapabilityMove,
  PromptUpdate,
  CapabilityContextResponse
} from '../types/api';

const BASE_URL = 'http://127.0.0.1:8080'; // We'll make this configurable later
const WS_URL = 'ws://127.0.0.1:8080/ws';

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// WebSocket connection manager
class WebSocketManager {
  private ws: WebSocket | null = null;
  private onModelChangeCallbacks: Set<(user: string, action: string) => void> = new Set();

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(WS_URL);
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'model_changed') {
        this.notifyModelChange(data.user, data.action);
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

  private notifyModelChange(user: string, action: string) {
    this.onModelChangeCallbacks.forEach(callback => callback(user, action));
  }
}

export const wsManager = new WebSocketManager();

export const ApiClient = {
  // User session management
  createUserSession: async (user: User): Promise<UserSession> => {
    const response = await api.post<UserSession>('/users', user);
    return response.data;
  },

  getActiveUsers: async (): Promise<UserSession[]> => {
    const response = await api.get<UserSession[]>('/users');
    return response.data;
  },

  removeUserSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/users/${sessionId}`);
  },

  // Capability locking
  lockCapability: async (capabilityId: number, sessionId: string): Promise<void> => {
    await api.post(`/capabilities/lock/${capabilityId}?session_id=${sessionId}`);
  },

  unlockCapability: async (capabilityId: number, sessionId: string): Promise<void> => {
    await api.post(`/capabilities/unlock/${capabilityId}?session_id=${sessionId}`);
  },

  // Capability CRUD operations
  createCapability: async (capability: CapabilityCreate, sessionId: string): Promise<Capability> => {
    const response = await api.post<Capability>(`/capabilities?session_id=${sessionId}`, capability);
    return response.data;
  },

  getCapability: async (capabilityId: number): Promise<Capability> => {
    const response = await api.get<Capability>(`/capabilities/${capabilityId}`);
    return response.data;
  },

  getCapabilityContext: async (capabilityId: number): Promise<CapabilityContextResponse> => {
    const response = await api.get<CapabilityContextResponse>(`/capabilities/${capabilityId}/context`);
    return response.data;
  },

  updateCapability: async (
    capabilityId: number, 
    capability: CapabilityUpdate, 
    sessionId: string
  ): Promise<Capability> => {
    const response = await api.put<Capability>(
      `/capabilities/${capabilityId}?session_id=${sessionId}`, 
      capability
    );
    return response.data;
  },

  deleteCapability: async (capabilityId: number, sessionId: string): Promise<void> => {
    await api.delete(`/capabilities/${capabilityId}?session_id=${sessionId}`);
  },

  // Capability movement and organization
  moveCapability: async (
    capabilityId: number, 
    move: CapabilityMove, 
    sessionId: string
  ): Promise<void> => {
    await api.post(
      `/capabilities/${capabilityId}/move?session_id=${sessionId}`, 
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
      `/capabilities/${capabilityId}/description?session_id=${sessionId}&description=${encodeURIComponent(description)}`
    );
  },

  updatePrompt: async (
    capabilityId: number, 
    promptUpdate: PromptUpdate, 
    sessionId: string
  ): Promise<void> => {
    await api.put(
      `/capabilities/${capabilityId}/prompt?session_id=${sessionId}`, 
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
    
    const response = await api.get<Capability[]>(`/capabilities?${params.toString()}`);
    return response.data;
  },
};

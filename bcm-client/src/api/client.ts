import axios from 'axios';
import type { 
  User, 
  UserSession, 
  Capability, 
  CapabilityCreate, 
  CapabilityUpdate,
  CapabilityMove,
  CapabilityPaste,
  PromptUpdate 
} from '../types/api';

const BASE_URL = 'http://127.0.0.1:8080'; // We'll make this configurable later

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

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

  getCapabilityContext: async (capabilityId: number): Promise<Capability> => {
    const response = await api.get<Capability>(`/capabilities/${capabilityId}/context`);
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

  pasteCapability: async (paste: CapabilityPaste, sessionId: string): Promise<void> => {
    await api.post(`/capabilities/paste?session_id=${sessionId}`, paste);
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
    if (parentId !== undefined) {
      params.append('parent_id', parentId?.toString() || '');
    }
    params.append('hierarchical', hierarchical.toString());
    
    const response = await api.get<Capability[]>(`/capabilities?${params.toString()}`);
    return response.data;
  },
};

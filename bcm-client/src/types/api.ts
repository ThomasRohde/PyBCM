export interface User {
  nickname: string;
}

export interface UserSession {
  session_id: string;
  nickname: string;
  locked_capabilities: number[];
}

export interface Capability {
  id: number;
  name: string;
  description: string | null;
  parent_id: number | null;
  order_position?: number;
  children?: Capability[];
}

export interface CapabilityCreate {
  name: string;
  description?: string | null;
  parent_id?: number | null;
}

export interface CapabilityUpdate {
  name?: string;
  description?: string | null;
  parent_id?: number | null;
}

export interface CapabilityMove {
  new_parent_id?: number | null;
  new_order: number;
}

export interface CapabilityPaste {
  source_id: number;
  target_id?: number | null;
  position?: number | null;
}

export interface PromptUpdate {
  prompt: string;
  capability_id: number;
  prompt_type: 'first-level' | 'expansion';
}

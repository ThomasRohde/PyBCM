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
  locked_by?: string | null;  // Nickname of user who locked the capability
  is_locked?: boolean;        // Whether the capability is locked
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

export interface PromptUpdate {
  prompt: string;
  capability_id: number;
  prompt_type: 'first-level' | 'expansion';
}

export interface CapabilityContextResponse {
  rendered_context: string;
}

export interface LayoutModel {
  id: number;
  name: string;
  description?: string;
  x: number;
  y: number;
  width: number;
  height: number;
  level: number;
  children?: LayoutModel[];
}

export interface TemplateSettings {
  selected: string;
  available: string[];
}

export interface Settings {
  theme: string;
  max_ai_capabilities: number;
  first_level_range: string;
  first_level_template: string | TemplateSettings;
  normal_template: string | TemplateSettings;
  font_size: number;
  model: string;
  context_include_parents: boolean;
  context_include_siblings: boolean;
  context_first_level: boolean;
  context_tree: boolean;
  layout_algorithm: string;
  root_font_size: number;
  box_min_width: number;
  box_min_height: number;
  horizontal_gap: number;
  vertical_gap: number;
  padding: number;
  top_padding: number;
  target_aspect_ratio: number;
  max_level: number;
  color_0: string;
  color_1: string;
  color_2: string;
  color_3: string;
  color_4: string;
  color_5: string;
  color_6: string;
  color_leaf: string;
}

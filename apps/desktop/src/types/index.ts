export interface Experiment {
  exp_number: number;
  title: string;
  category: string;
  software: string;
  aim: string;
  procedure?: string;
  result?: string;
  page_start: number;
  page_end: number;
  pages: string;
  tags: string[];
  diagram_images: string[];
  code_sample?: string;
  viva_questions?: VivaQuestion[];
  manual_pages?: { page: number; content: string }[];
}

export interface VivaQuestion {
  question: string;
  expected_answer: string;
  key_concepts: string[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  experiment_id?: number;
  citations?: string[];
}

export interface HardwareInfo {
  cpu_cores: number;
  cpu_percent: number;
  ram_total_gb: number;
  ram_available_gb: number;
  ram_used_percent: number;
  platform: string;
}

export interface ModelInfo {
  name: string;
  exists: boolean;
  size_gb: number;
  path: string;
  loaded: boolean;
  backend: string;
  port: number;
}

export interface SystemStatus {
  status: 'READY' | 'CONFIG_REQUIRED' | 'OFFLINE_ONLY';
  offline_mode: boolean;
  cloud_api_disabled: boolean;
  telemetry_disabled: boolean;
  hardware: HardwareInfo;
  model: ModelInfo;
  knowledge_base: {
    database_ready: boolean;
    experiments_indexed: number;
    manual_title: string;
    db_path: string;
  };
  simulation_engines: {
    pyspice: boolean;
    digital_logic: boolean;
    numerical_simulink_equiv: boolean;
  };
  app_root: string;
}

export interface SearchResult {
  exp_number: number;
  section: string;
  page_start: number;
  page_end: number;
  citation: string;
  snippet: string;
  content: string;
}

// Database abstraction types for multi-provider support

export type DatabaseProvider = 'supabase' | 'neon' | 'postgres' | 'mock';

export interface Workflow {
  id: string;
  name: string;
  description: string | null;
  status: 'draft' | 'active' | 'paused' | 'archived';
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  created_at: string;
  updated_at: string;
  user_id: string;
  settings: WorkflowSettings;
}

export interface WorkflowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: AgentNodeData;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
  animated?: boolean;
  style?: Record<string, unknown>;
}

export interface AgentNodeData {
  label: string;
  agentType: string;
  status: 'idle' | 'running' | 'success' | 'error';
  config: AgentConfig;
}

export interface AgentConfig {
  model: string;
  temperature: number;
  maxTokens: number;
  systemPrompt: string;
  tools: string[];
  ragSources: string[];
  retryPolicy: {
    maxRetries: number;
    backoffMultiplier: number;
  };
  timeout: number;
  outputSchema?: Record<string, unknown>;
}

export interface WorkflowSettings {
  maxConcurrentAgents: number;
  globalTimeout: number;
  errorHandling: 'stop' | 'continue' | 'retry';
  loggingLevel: 'minimal' | 'standard' | 'verbose';
}

export interface Execution {
  id: string;
  workflow_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  error: string | null;
  tokens_used: number;
  cost_usd: number;
  agent_executions: AgentExecution[];
}

export interface AgentExecution {
  id: string;
  execution_id: string;
  agent_id: string;
  agent_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  error: string | null;
  tokens_used: number;
  tool_calls: ToolCall[];
  trace: TraceEntry[];
}

export interface ToolCall {
  id: string;
  tool_name: string;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  started_at: string;
  completed_at: string | null;
  status: 'success' | 'error';
  error: string | null;
}

export interface TraceEntry {
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error';
  message: string;
  metadata?: Record<string, unknown>;
}

export interface ActivityLog {
  id: string;
  timestamp: string;
  user_id: string;
  user_email: string;
  action: string;
  resource_type: 'workflow' | 'agent' | 'tool' | 'rag_source' | 'execution' | 'settings';
  resource_id: string | null;
  resource_name: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
}

export interface Tool {
  id: string;
  name: string;
  description: string;
  type: 'api' | 'function' | 'webhook' | 'mcp';
  schema: {
    input: Record<string, unknown>;
    output: Record<string, unknown>;
  };
  config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  user_id: string;
}

export interface RAGSource {
  id: string;
  name: string;
  type: 'document' | 'website' | 'api' | 'database';
  status: 'indexing' | 'ready' | 'error' | 'stale';
  document_count: number;
  chunk_count: number;
  last_synced: string | null;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  user_id: string;
}

export interface UsageRecord {
  id: string;
  user_id: string;
  date: string;
  workflow_id: string | null;
  tokens_input: number;
  tokens_output: number;
  cost_usd: number;
  execution_count: number;
}

// Database adapter interface
export interface DatabaseAdapter {
  // Connection
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  isConnected(): boolean;

  // Workflows
  getWorkflows(userId: string): Promise<Workflow[]>;
  getWorkflow(id: string): Promise<Workflow | null>;
  createWorkflow(workflow: Omit<Workflow, 'id' | 'created_at' | 'updated_at'>): Promise<Workflow>;
  updateWorkflow(id: string, updates: Partial<Workflow>): Promise<Workflow>;
  deleteWorkflow(id: string): Promise<void>;

  // Executions
  getExecutions(workflowId: string, limit?: number): Promise<Execution[]>;
  getExecution(id: string): Promise<Execution | null>;
  createExecution(execution: Omit<Execution, 'id'>): Promise<Execution>;
  updateExecution(id: string, updates: Partial<Execution>): Promise<Execution>;

  // Activity Logs
  getActivityLogs(userId: string, limit?: number, offset?: number): Promise<ActivityLog[]>;
  createActivityLog(log: Omit<ActivityLog, 'id'>): Promise<ActivityLog>;

  // Tools
  getTools(userId: string): Promise<Tool[]>;
  getTool(id: string): Promise<Tool | null>;
  createTool(tool: Omit<Tool, 'id' | 'created_at' | 'updated_at'>): Promise<Tool>;
  updateTool(id: string, updates: Partial<Tool>): Promise<Tool>;
  deleteTool(id: string): Promise<void>;

  // RAG Sources
  getRAGSources(userId: string): Promise<RAGSource[]>;
  getRAGSource(id: string): Promise<RAGSource | null>;
  createRAGSource(source: Omit<RAGSource, 'id' | 'created_at' | 'updated_at'>): Promise<RAGSource>;
  updateRAGSource(id: string, updates: Partial<RAGSource>): Promise<RAGSource>;
  deleteRAGSource(id: string): Promise<void>;

  // Usage
  getUsage(userId: string, startDate: string, endDate: string): Promise<UsageRecord[]>;
  recordUsage(usage: Omit<UsageRecord, 'id'>): Promise<UsageRecord>;
}

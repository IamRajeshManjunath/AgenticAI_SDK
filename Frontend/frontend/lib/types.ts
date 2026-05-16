// Workflow Schema Types based on the API specification

export interface ToolConfig {
  id: string
  name: string
  description: string
  type: 'api' | 'function' | 'mcp'
  api_endpoint?: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  api_key_env_var?: string
  mcp_endpoint?: string
  code_snippet?: string
}

export interface RAGSourceConfig {
  id: string
  provider: 'pinecone' | 'weaviate' | 'qdrant' | 'chroma' | 'milvus' | 'file'
  name?: string
  uri?: string
  api_key_env_var?: string
  embedding_model: string
  top_k: number
  similarity_threshold: number
  hybrid_search: boolean
  file_path?: string
}

export interface LLMConfig {
  provider: 'openai' | 'anthropic' | 'google' | 'azure' | 'local'
  model_name: string
  temperature: number
  max_tokens: number
  api_key_env_var: string
}

export interface BudgetGuardrails {
  max_tokens?: number
  max_cost?: number
  max_iterations?: number
}

export interface PIIGuardrails {
  enabled: boolean
  masking_level: 'hash' | 'partial' | 'full'
}

export interface FirewallGuardrails {
  prompt_injection_protection: boolean
}

export interface ConsensusConfig {
  enabled: boolean
  num_instances: number
  agreement_threshold: number
}

export interface FallbackConfig {
  llm_config: LLMConfig
  priority: number
}

export interface PromptTemplate {
  template_string: string
  input_variables: string[]
}

export interface ReasoningStep {
  id: string
  description: string
  order: number
}

export interface AgentNodeConfig {
  agent_id: string
  role: string
  prompt_template: PromptTemplate
  llm_config: LLMConfig
  orchestration_mode: 'model-driven' | 'agent-driven'
  reasoning_steps?: ReasoningStep[]
  tools: string[]
  rag_sources: string[]
  sub_agents: string[]
  budget_guardrails?: BudgetGuardrails
  pii_guardrails?: PIIGuardrails
  firewall_guardrails?: FirewallGuardrails
  consensus_config?: ConsensusConfig
  fallback_configs?: FallbackConfig[]
  interruption_point?: boolean
}

export interface EdgeCondition {
  id: string
  source: string
  target: string
  condition?: string // Python expression like: state["next_step"] == "review"
}

export interface WorkflowSchema {
  id: string
  name: string
  description: string
  entry_point: string
  agents: AgentNodeConfig[]
  edges: EdgeCondition[]
  global_tools: ToolConfig[]
  global_rag_sources: RAGSourceConfig[]
  created_at: string
  updated_at: string
}

// Observability Types
export interface TraceSpan {
  id: string
  name: string
  agent_id?: string
  start_time: number
  end_time?: number
  duration_ms?: number
  status: 'running' | 'completed' | 'failed'
  children: TraceSpan[]
  metadata?: Record<string, unknown>
}

export interface ExecutionMessage {
  id: string
  timestamp: number
  type: 'thought' | 'tool_call' | 'tool_result' | 'message' | 'error' | 'hitl'
  agent_id: string
  content: string
  metadata?: Record<string, unknown>
}

export interface WorkflowMetrics {
  total_cost: number
  budget_limit: number
  total_tokens: number
  prompt_tokens: number
  completion_tokens: number
  avg_latency_ms: number
  consensus_score?: number
}

export interface HITLRequest {
  id: string
  agent_id: string
  proposed_action: string
  proposed_output: string
  timestamp: number
  status: 'pending' | 'approved' | 'rejected'
}

export interface WorkflowState {
  scratchpad: Record<string, unknown>
  messages: ExecutionMessage[]
  current_agent?: string
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed'
}

// UI State Types
export interface Workspace {
  id: string
  name: string
  workflows: string[]
  created_at: string
}

export interface NodePosition {
  x: number
  y: number
}

export interface CanvasNode {
  id: string
  type: 'agent'
  position: NodePosition
  data: AgentNodeConfig
}

export interface CanvasEdge {
  id: string
  source: string
  target: string
  data?: EdgeCondition
}

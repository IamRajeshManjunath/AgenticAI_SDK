import { RAG_VECTOR_PROVIDER_OPTIONS, type AgentNodeConfig, type EdgeCondition, type RAGVectorProvider, type ToolConfig, type WorkflowSchema } from './types'

type DataObject = Record<string, unknown>

function asObject(value: unknown): DataObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as DataObject
    : {}
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function asNumber(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function asStringArray(value: unknown): string[] {
  return asArray(value).filter((item): item is string => typeof item === 'string')
}

function optionalObject(value: unknown): DataObject | undefined {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as DataObject
    : undefined
}

function normalizeTool(value: unknown, index: number): ToolConfig {
  const tool = asObject(value)
  const config = asObject(tool.config)
  const rawType = asString(tool.type ?? tool.tool_type)
  const method = asString(tool.method ?? config.method)
  return {
    id: asString(tool.id ?? tool.tool_id, `tool_${index + 1}`),
    name: asString(tool.name, `Tool ${index + 1}`),
    description: asString(tool.description),
    type: rawType === 'rest_api' || rawType === 'api'
      ? 'api'
      : rawType === 'mcp' ? 'mcp' : 'function',
    api_endpoint: asString(tool.api_endpoint ?? config.endpoint) || undefined,
    method: ['GET', 'POST', 'PUT', 'DELETE'].includes(method)
      ? method as ToolConfig['method']
      : undefined,
    api_key_env_var: asString(tool.api_key_env_var ?? config.api_key_env_var) || undefined,
    mcp_endpoint: asString(tool.mcp_endpoint ?? config.connection_string) || undefined,
    code_snippet: asString(tool.code_snippet ?? config.code) || undefined,
  }
}

function normalizeAgent(value: unknown, index: number): AgentNodeConfig {
  const agent = asObject(value)
  const template = asObject(agent.prompt_template)
  const llm = asObject(agent.llm_config ?? agent.llm)
  const topology = asObject(agent.topology)
  const consensus = optionalObject(agent.consensus_config)
  const mode = asString(agent.orchestration_mode ?? topology.orchestration_mode)
  return {
    agent_id: asString(agent.agent_id, `agent_${index + 1}`),
    role: asString(agent.role, 'Assistant'),
    prompt_template: {
      template_string: asString(template.template_string, 'Process the input.'),
      input_variables: asStringArray(template.input_variables),
    },
    llm_config: {
      provider: asString(llm.provider, 'openai'),
      model_name: asString(llm.model_name ?? llm.model, 'gpt-4o'),
      temperature: asNumber(llm.temperature, 0.7),
      max_tokens: asNumber(llm.max_tokens, 4096),
      api_key_env_var: asString(llm.api_key_env_var, 'OPENAI_API_KEY'),
    },
    orchestration_mode: mode === 'agent-driven' || mode === 'agent_driven'
      ? 'agent-driven'
      : 'model-driven',
    reasoning_steps: asArray(agent.reasoning_steps).map((step, stepIndex) => {
      const item = asObject(step)
      return {
        id: asString(item.id, `step_${stepIndex + 1}`),
        description: asString(item.description),
        order: asNumber(item.order, stepIndex + 1),
      }
    }),
    tools: asStringArray(agent.tools),
    rag_sources: asStringArray(agent.rag_sources),
    sub_agents: asStringArray(agent.sub_agents),
    budget_guardrails: optionalObject(agent.budget_guardrails),
    pii_guardrails: optionalObject(agent.pii_guardrails) as AgentNodeConfig['pii_guardrails'],
    firewall_guardrails: optionalObject(agent.firewall_guardrails) as AgentNodeConfig['firewall_guardrails'],
    consensus_config: consensus
      ? {
          enabled: typeof consensus.enabled === 'boolean' ? consensus.enabled : false,
          num_instances: asNumber(consensus.num_instances ?? consensus.instances, 3),
          agreement_threshold: asNumber(consensus.agreement_threshold ?? consensus.threshold, 0.7),
        }
      : undefined,
    fallback_configs: asArray(agent.fallback_configs) as AgentNodeConfig['fallback_configs'],
    interruption_point: typeof agent.interruption_point === 'boolean'
      ? agent.interruption_point
      : undefined,
    input_schema: optionalObject(agent.input_schema),
    output_schema: optionalObject(agent.output_schema),
  }
}

function normalizeEdge(value: unknown, index: number): EdgeCondition {
  const edge = asObject(value)
  const condition = edge.condition
  let normalizedCondition: string | undefined
  if (typeof condition === 'string') {
    normalizedCondition = condition
  } else {
    const conditionObject = asObject(condition)
    if (conditionObject.value !== undefined) {
      normalizedCondition = `state["${asString(conditionObject.field)}"] ${asString(conditionObject.operator, '==')} "${String(conditionObject.value)}"`
    }
  }
  return {
    id: asString(edge.id, `edge_${index + 1}`),
    source: asString(edge.source),
    target: asString(edge.target),
    condition: normalizedCondition,
  }
}

function normalizeRagSource(value: unknown, index: number): WorkflowSchema['global_rag_sources'][number] {
  const source = asObject(value)
  const providerValue = asString(source.provider ?? source.vector_db, 'qdrant')
  const provider = RAG_VECTOR_PROVIDER_OPTIONS.find((option) => option.value === providerValue)?.value
    ?? ('qdrant' satisfies RAGVectorProvider)
  return {
    id: asString(source.id ?? source.rag_id, `rag_${index + 1}`),
    provider,
    name: asString(source.name ?? source.collection_name) || undefined,
    uri: asString(source.uri ?? source.connection_uri) || undefined,
    api_key_env_var: asString(source.api_key_env_var) || undefined,
    embedding_model: asString(source.embedding_model, 'text-embedding-3-small'),
    top_k: asNumber(source.top_k, 3),
    similarity_threshold: asNumber(source.similarity_threshold, 0.7),
    hybrid_search: typeof source.hybrid_search === 'boolean' ? source.hybrid_search : true,
    file_path: asString(source.file_path) || undefined,
  }
}

export function normalizeWorkflowConfig(value: unknown, fallbackId?: string): WorkflowSchema | null {
  const workflow = asObject(value)
  const id = asString(workflow.id ?? workflow.workflow_id, fallbackId ?? '')
  const agents = asArray(workflow.agents).map(normalizeAgent)
  if (!id || agents.length === 0) return null

  const entryPoint = asString(workflow.entry_point, agents[0].agent_id)
  const edges = asArray(workflow.edges).map(normalizeEdge)
  const workflowTools = workflow.global_tools ?? workflow.tools
  const workflowRagSources = workflow.global_rag_sources ?? workflow.rag_sources

  return {
    id,
    name: asString(workflow.name, 'Untitled workflow'),
    description: asString(workflow.description),
    entry_point: entryPoint,
    agents,
    edges,
    global_tools: asArray(workflowTools).map(normalizeTool),
    global_rag_sources: asArray(workflowRagSources).map(normalizeRagSource),
    created_at: asString(workflow.created_at, new Date().toISOString()),
    updated_at: asString(workflow.updated_at, new Date().toISOString()),
  }
}

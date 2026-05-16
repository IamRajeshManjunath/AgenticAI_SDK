// Mock database adapter for development and testing

import type {
  DatabaseAdapter,
  Workflow,
  Execution,
  ActivityLog,
  Tool,
  RAGSource,
  UsageRecord,
} from './types';

// In-memory storage
const store = {
  workflows: new Map<string, Workflow>(),
  executions: new Map<string, Execution>(),
  activityLogs: new Map<string, ActivityLog>(),
  tools: new Map<string, Tool>(),
  ragSources: new Map<string, RAGSource>(),
  usage: new Map<string, UsageRecord>(),
};

// Generate unique IDs
const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// Initialize with sample data
function initializeSampleData() {
  // Sample workflows
  const sampleWorkflows: Workflow[] = [
    {
      id: 'wf-1',
      name: 'Customer Support Pipeline',
      description: 'Automated customer inquiry handling with sentiment analysis and routing',
      status: 'active',
      nodes: [
        {
          id: 'node-1',
          type: 'agentNode',
          position: { x: 100, y: 100 },
          data: {
            label: 'Intent Classifier',
            agentType: 'classifier',
            status: 'idle',
            config: {
              model: 'gpt-4o',
              temperature: 0.3,
              maxTokens: 500,
              systemPrompt: 'Classify customer intents...',
              tools: [],
              ragSources: [],
              retryPolicy: { maxRetries: 3, backoffMultiplier: 2 },
              timeout: 30000,
            },
          },
        },
        {
          id: 'node-2',
          type: 'agentNode',
          position: { x: 400, y: 100 },
          data: {
            label: 'Response Generator',
            agentType: 'generator',
            status: 'idle',
            config: {
              model: 'gpt-4o',
              temperature: 0.7,
              maxTokens: 1000,
              systemPrompt: 'Generate helpful responses...',
              tools: ['knowledge-base-search'],
              ragSources: ['company-docs'],
              retryPolicy: { maxRetries: 3, backoffMultiplier: 2 },
              timeout: 60000,
            },
          },
        },
      ],
      edges: [
        { id: 'edge-1', source: 'node-1', target: 'node-2', animated: true },
      ],
      created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date().toISOString(),
      user_id: 'user-1',
      settings: {
        maxConcurrentAgents: 5,
        globalTimeout: 300000,
        errorHandling: 'retry',
        loggingLevel: 'standard',
      },
    },
    {
      id: 'wf-2',
      name: 'Document Processing',
      description: 'Extract, analyze, and summarize document content',
      status: 'active',
      nodes: [],
      edges: [],
      created_at: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
      user_id: 'user-1',
      settings: {
        maxConcurrentAgents: 3,
        globalTimeout: 600000,
        errorHandling: 'continue',
        loggingLevel: 'verbose',
      },
    },
    {
      id: 'wf-3',
      name: 'Lead Qualification',
      description: 'Score and qualify inbound leads automatically',
      status: 'draft',
      nodes: [],
      edges: [],
      created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
      user_id: 'user-1',
      settings: {
        maxConcurrentAgents: 2,
        globalTimeout: 120000,
        errorHandling: 'stop',
        loggingLevel: 'minimal',
      },
    },
  ];

  sampleWorkflows.forEach((wf) => store.workflows.set(wf.id, wf));

  // Sample executions
  const sampleExecutions: Execution[] = [
    {
      id: 'exec-1',
      workflow_id: 'wf-1',
      status: 'completed',
      started_at: new Date(Date.now() - 60000).toISOString(),
      completed_at: new Date(Date.now() - 45000).toISOString(),
      duration_ms: 15000,
      input: { message: 'How do I reset my password?' },
      output: { response: 'To reset your password, please visit...' },
      error: null,
      tokens_used: 850,
      cost_usd: 0.0025,
      agent_executions: [],
    },
    {
      id: 'exec-2',
      workflow_id: 'wf-1',
      status: 'completed',
      started_at: new Date(Date.now() - 120000).toISOString(),
      completed_at: new Date(Date.now() - 95000).toISOString(),
      duration_ms: 25000,
      input: { message: 'I want to cancel my subscription' },
      output: { response: 'I understand you want to cancel...' },
      error: null,
      tokens_used: 1200,
      cost_usd: 0.0036,
      agent_executions: [],
    },
    {
      id: 'exec-3',
      workflow_id: 'wf-1',
      status: 'failed',
      started_at: new Date(Date.now() - 180000).toISOString(),
      completed_at: new Date(Date.now() - 175000).toISOString(),
      duration_ms: 5000,
      input: { message: 'Test message' },
      output: null,
      error: 'Rate limit exceeded',
      tokens_used: 100,
      cost_usd: 0.0003,
      agent_executions: [],
    },
  ];

  sampleExecutions.forEach((exec) => store.executions.set(exec.id, exec));

  // Sample activity logs
  const sampleLogs: ActivityLog[] = [
    {
      id: 'log-1',
      timestamp: new Date().toISOString(),
      user_id: 'user-1',
      user_email: 'admin@harpy.ai',
      action: 'workflow.updated',
      resource_type: 'workflow',
      resource_id: 'wf-1',
      resource_name: 'Customer Support Pipeline',
      details: { field: 'nodes', action: 'added' },
      ip_address: '192.168.1.1',
      user_agent: 'Mozilla/5.0...',
    },
    {
      id: 'log-2',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      user_id: 'user-1',
      user_email: 'admin@harpy.ai',
      action: 'workflow.executed',
      resource_type: 'execution',
      resource_id: 'exec-1',
      resource_name: 'Customer Support Pipeline',
      details: { status: 'completed', duration_ms: 15000 },
      ip_address: '192.168.1.1',
      user_agent: 'Mozilla/5.0...',
    },
    {
      id: 'log-3',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      user_id: 'user-1',
      user_email: 'admin@harpy.ai',
      action: 'tool.created',
      resource_type: 'tool',
      resource_id: 'tool-1',
      resource_name: 'Slack Notifier',
      details: { type: 'webhook' },
      ip_address: '192.168.1.1',
      user_agent: 'Mozilla/5.0...',
    },
  ];

  sampleLogs.forEach((log) => store.activityLogs.set(log.id, log));

  // Sample tools
  const sampleTools: Tool[] = [
    {
      id: 'tool-1',
      name: 'Slack Notifier',
      description: 'Send notifications to Slack channels',
      type: 'webhook',
      schema: {
        input: { channel: 'string', message: 'string' },
        output: { success: 'boolean' },
      },
      config: { webhook_url: 'https://hooks.slack.com/...' },
      is_active: true,
      created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date().toISOString(),
      user_id: 'user-1',
    },
    {
      id: 'tool-2',
      name: 'Knowledge Base Search',
      description: 'Search company knowledge base',
      type: 'function',
      schema: {
        input: { query: 'string', limit: 'number' },
        output: { results: 'array' },
      },
      config: { index_name: 'company-docs' },
      is_active: true,
      created_at: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
      user_id: 'user-1',
    },
  ];

  sampleTools.forEach((tool) => store.tools.set(tool.id, tool));

  // Sample RAG sources
  const sampleRAGSources: RAGSource[] = [
    {
      id: 'rag-1',
      name: 'Company Documentation',
      type: 'document',
      status: 'ready',
      document_count: 156,
      chunk_count: 2340,
      last_synced: new Date(Date.now() - 3600000).toISOString(),
      config: { folder_path: '/docs' },
      created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date().toISOString(),
      user_id: 'user-1',
    },
    {
      id: 'rag-2',
      name: 'Product Website',
      type: 'website',
      status: 'indexing',
      document_count: 45,
      chunk_count: 890,
      last_synced: null,
      config: { url: 'https://example.com', depth: 3 },
      created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date().toISOString(),
      user_id: 'user-1',
    },
  ];

  sampleRAGSources.forEach((source) => store.ragSources.set(source.id, source));
}

// Initialize on load
initializeSampleData();

export class MockDatabaseAdapter implements DatabaseAdapter {
  private connected = false;

  async connect(): Promise<void> {
    this.connected = true;
  }

  async disconnect(): Promise<void> {
    this.connected = false;
  }

  isConnected(): boolean {
    return this.connected;
  }

  // Workflows
  async getWorkflows(userId: string): Promise<Workflow[]> {
    return Array.from(store.workflows.values()).filter((w) => w.user_id === userId);
  }

  async getWorkflow(id: string): Promise<Workflow | null> {
    return store.workflows.get(id) || null;
  }

  async createWorkflow(workflow: Omit<Workflow, 'id' | 'created_at' | 'updated_at'>): Promise<Workflow> {
    const newWorkflow: Workflow = {
      ...workflow,
      id: generateId(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    store.workflows.set(newWorkflow.id, newWorkflow);
    return newWorkflow;
  }

  async updateWorkflow(id: string, updates: Partial<Workflow>): Promise<Workflow> {
    const existing = store.workflows.get(id);
    if (!existing) throw new Error('Workflow not found');
    const updated: Workflow = { ...existing, ...updates, updated_at: new Date().toISOString() };
    store.workflows.set(id, updated);
    return updated;
  }

  async deleteWorkflow(id: string): Promise<void> {
    store.workflows.delete(id);
  }

  // Executions
  async getExecutions(workflowId: string, limit = 50): Promise<Execution[]> {
    return Array.from(store.executions.values())
      .filter((e) => e.workflow_id === workflowId)
      .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())
      .slice(0, limit);
  }

  async getExecution(id: string): Promise<Execution | null> {
    return store.executions.get(id) || null;
  }

  async createExecution(execution: Omit<Execution, 'id'>): Promise<Execution> {
    const newExecution: Execution = { ...execution, id: generateId() };
    store.executions.set(newExecution.id, newExecution);
    return newExecution;
  }

  async updateExecution(id: string, updates: Partial<Execution>): Promise<Execution> {
    const existing = store.executions.get(id);
    if (!existing) throw new Error('Execution not found');
    const updated: Execution = { ...existing, ...updates };
    store.executions.set(id, updated);
    return updated;
  }

  // Activity Logs
  async getActivityLogs(userId: string, limit = 50, offset = 0): Promise<ActivityLog[]> {
    return Array.from(store.activityLogs.values())
      .filter((l) => l.user_id === userId)
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(offset, offset + limit);
  }

  async createActivityLog(log: Omit<ActivityLog, 'id'>): Promise<ActivityLog> {
    const newLog: ActivityLog = { ...log, id: generateId() };
    store.activityLogs.set(newLog.id, newLog);
    return newLog;
  }

  // Tools
  async getTools(userId: string): Promise<Tool[]> {
    return Array.from(store.tools.values()).filter((t) => t.user_id === userId);
  }

  async getTool(id: string): Promise<Tool | null> {
    return store.tools.get(id) || null;
  }

  async createTool(tool: Omit<Tool, 'id' | 'created_at' | 'updated_at'>): Promise<Tool> {
    const newTool: Tool = {
      ...tool,
      id: generateId(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    store.tools.set(newTool.id, newTool);
    return newTool;
  }

  async updateTool(id: string, updates: Partial<Tool>): Promise<Tool> {
    const existing = store.tools.get(id);
    if (!existing) throw new Error('Tool not found');
    const updated: Tool = { ...existing, ...updates, updated_at: new Date().toISOString() };
    store.tools.set(id, updated);
    return updated;
  }

  async deleteTool(id: string): Promise<void> {
    store.tools.delete(id);
  }

  // RAG Sources
  async getRAGSources(userId: string): Promise<RAGSource[]> {
    return Array.from(store.ragSources.values()).filter((r) => r.user_id === userId);
  }

  async getRAGSource(id: string): Promise<RAGSource | null> {
    return store.ragSources.get(id) || null;
  }

  async createRAGSource(source: Omit<RAGSource, 'id' | 'created_at' | 'updated_at'>): Promise<RAGSource> {
    const newSource: RAGSource = {
      ...source,
      id: generateId(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    store.ragSources.set(newSource.id, newSource);
    return newSource;
  }

  async updateRAGSource(id: string, updates: Partial<RAGSource>): Promise<RAGSource> {
    const existing = store.ragSources.get(id);
    if (!existing) throw new Error('RAG source not found');
    const updated: RAGSource = { ...existing, ...updates, updated_at: new Date().toISOString() };
    store.ragSources.set(id, updated);
    return updated;
  }

  async deleteRAGSource(id: string): Promise<void> {
    store.ragSources.delete(id);
  }

  // Usage
  async getUsage(userId: string, startDate: string, endDate: string): Promise<UsageRecord[]> {
    return Array.from(store.usage.values()).filter(
      (u) => u.user_id === userId && u.date >= startDate && u.date <= endDate
    );
  }

  async recordUsage(usage: Omit<UsageRecord, 'id'>): Promise<UsageRecord> {
    const newUsage: UsageRecord = { ...usage, id: generateId() };
    store.usage.set(newUsage.id, newUsage);
    return newUsage;
  }
}

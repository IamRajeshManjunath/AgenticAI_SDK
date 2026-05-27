import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type {
  WorkflowSchema,
  Workspace,
  ToolConfig,
  RAGSourceConfig,
  AgentNodeConfig,
  EdgeCondition,
  WorkflowState,
  WorkflowMetrics,
  TraceSpan,
  ExecutionMessage,
  HITLRequest,
} from './types'

// Generate unique IDs
const generateId = () => Math.random().toString(36).substring(2, 15)

// Default LLM Config
const defaultLLMConfig = {
  provider: 'openai' as const,
  model_name: 'gpt-4-turbo',
  temperature: 0.7,
  max_tokens: 4096,
  api_key_env_var: 'OPENAI_API_KEY',
}

// Default Agent Config
const createDefaultAgent = (id?: string): AgentNodeConfig => ({
  agent_id: id || `agent_${generateId()}`,
  role: 'Assistant',
  prompt_template: {
    template_string: 'You are a helpful assistant. {{input}}',
    input_variables: ['input'],
  },
  llm_config: { ...defaultLLMConfig },
  orchestration_mode: 'model-driven',
  tools: [],
  rag_sources: [],
  sub_agents: [],
})

// Default Workflow
const createDefaultWorkflow = (name: string): WorkflowSchema => {
  const id = generateId()
  const defaultAgent = createDefaultAgent('coordinator')
  return {
    id,
    name,
    description: '',
    entry_point: defaultAgent.agent_id,
    agents: [defaultAgent],
    edges: [],
    global_tools: [],
    global_rag_sources: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }
}

// Workflow Store
interface WorkflowStore {
  // Workspaces
  workspaces: Workspace[]
  activeWorkspaceId: string | null
  
  // Workflows
  workflows: Record<string, WorkflowSchema>
  activeWorkflowId: string | null
  
  // Global Registry
  globalTools: ToolConfig[]
  globalRAGSources: RAGSourceConfig[]
  
  // Canvas State
  selectedNodeId: string | null
  selectedEdgeId: string | null
  
  // Execution State
  executionStates: Record<string, WorkflowState>
  metrics: Record<string, WorkflowMetrics>
  traces: Record<string, TraceSpan>
  hitlRequests: HITLRequest[]
  
  // UI State
  sidebarOpen: boolean
  configPanelOpen: boolean
  registryDrawerOpen: boolean
  
  // Workspace Actions
  createWorkspace: (name: string) => void
  setActiveWorkspace: (id: string) => void
  updateWorkspace: (id: string, updates: Partial<Workspace>) => void
  deleteWorkspace: (id: string) => void
  
  // Workflow Actions
  createWorkflow: (name: string, workspaceId?: string) => string
  setActiveWorkflow: (id: string) => void
  updateWorkflow: (id: string, updates: Partial<WorkflowSchema>) => void
  deleteWorkflow: (id: string) => void
  duplicateWorkflow: (id: string) => string
  importWorkflow: (json: string) => string | null
  exportWorkflow: (id: string) => string | null
  
  // Agent Actions
  addAgent: (workflowId: string, position?: { x: number; y: number }) => string
  updateAgent: (workflowId: string, agentId: string, updates: Partial<AgentNodeConfig>) => void
  deleteAgent: (workflowId: string, agentId: string) => void
  
  // Edge Actions
  addEdge: (workflowId: string, edge: Omit<EdgeCondition, 'id'>) => void
  updateEdge: (workflowId: string, edgeId: string, updates: Partial<EdgeCondition>) => void
  deleteEdge: (workflowId: string, edgeId: string) => void
  
  // Global Registry Actions
  addGlobalTool: (tool: Omit<ToolConfig, 'id'>) => void
  updateGlobalTool: (id: string, updates: Partial<ToolConfig>) => void
  deleteGlobalTool: (id: string) => void
  addGlobalRAGSource: (source: Omit<RAGSourceConfig, 'id'>) => string
  updateGlobalRAGSource: (id: string, updates: Partial<RAGSourceConfig>) => void
  deleteGlobalRAGSource: (id: string) => void
  
  // Selection Actions
  setSelectedNode: (id: string | null) => void
  setSelectedEdge: (id: string | null) => void
  
  // Execution Actions
  setExecutionState: (workflowId: string, state: WorkflowState) => void
  addExecutionMessage: (workflowId: string, message: ExecutionMessage) => void
  setMetrics: (workflowId: string, metrics: WorkflowMetrics) => void
  setTrace: (workflowId: string, trace: TraceSpan) => void
  addHITLRequest: (request: HITLRequest) => void
  resolveHITLRequest: (id: string, action: 'approve' | 'reject', feedback?: string) => void
  
  // UI Actions
  toggleSidebar: () => void
  toggleConfigPanel: () => void
  toggleRegistryDrawer: () => void
}

export const useWorkflowStore = create<WorkflowStore>()(
  persist(
    (set, get) => ({
      // Initial State
      workspaces: [],
      activeWorkspaceId: null,
      workflows: {},
      activeWorkflowId: null,
      globalTools: [],
      globalRAGSources: [],
      selectedNodeId: null,
      selectedEdgeId: null,
      executionStates: {},
      metrics: {},
      traces: {},
      hitlRequests: [],
      sidebarOpen: true,
      configPanelOpen: false,
      registryDrawerOpen: false,

      // Workspace Actions
      createWorkspace: (name) => {
        const workspace: Workspace = {
          id: generateId(),
          name,
          workflows: [],
          created_at: new Date().toISOString(),
        }
        set((state) => ({
          workspaces: [...state.workspaces, workspace],
          activeWorkspaceId: workspace.id,
        }))
      },

      setActiveWorkspace: (id) => set({ activeWorkspaceId: id }),
      
      updateWorkspace: (id, updates) => {
        set((state) => ({
          workspaces: state.workspaces.map((w) =>
            w.id === id ? { ...w, ...updates } : w
          ),
        }))
      },

      deleteWorkspace: (id) => {
        set((state) => {
          const workspace = state.workspaces.find((w) => w.id === id)
          const newWorkflows = { ...state.workflows }
          workspace?.workflows.forEach((wId) => delete newWorkflows[wId])
          return {
            workspaces: state.workspaces.filter((w) => w.id !== id),
            workflows: newWorkflows,
            activeWorkspaceId: state.activeWorkspaceId === id ? null : state.activeWorkspaceId,
          }
        })
      },

      // Workflow Actions
      createWorkflow: (name, workspaceId) => {
        const store = get()
        const wsId = workspaceId || store.activeWorkspaceId
        let targetWorkspaceId = wsId

        if (!wsId || !store.workspaces.find(w => w.id === wsId)) {
          const firstWs = store.workspaces[0]
          if (firstWs) {
            targetWorkspaceId = firstWs.id
          } else {
            const newWsId = crypto.randomUUID()
            const now = new Date().toISOString()
            const newWs: Workspace = { id: newWsId, name: 'Default Workspace', workflows: [], created_at: now }
            set({ workspaces: [...store.workspaces, newWs], activeWorkspaceId: newWsId })
            targetWorkspaceId = newWsId
          }
        }

        const workflow = createDefaultWorkflow(name)
        
        set((state) => ({
          workflows: { ...state.workflows, [workflow.id]: workflow },
          activeWorkflowId: workflow.id,
          workspaces: state.workspaces.map((w) =>
            w.id === targetWorkspaceId
              ? { ...w, workflows: [...w.workflows, workflow.id] }
              : w
          ),
        }))
        return workflow.id
      },

      setActiveWorkflow: (id) => set({ activeWorkflowId: id, selectedNodeId: null, selectedEdgeId: null }),

      updateWorkflow: (id, updates) => {
        set((state) => ({
          workflows: {
            ...state.workflows,
            [id]: {
              ...state.workflows[id],
              ...updates,
              updated_at: new Date().toISOString(),
            },
          },
        }))
      },

      deleteWorkflow: (id) => {
        set((state) => {
          const newWorkflows = { ...state.workflows }
          delete newWorkflows[id]
          return {
            workflows: newWorkflows,
            workspaces: state.workspaces.map((w) => ({
              ...w,
              workflows: w.workflows.filter((wId) => wId !== id),
            })),
            activeWorkflowId: state.activeWorkflowId === id ? null : state.activeWorkflowId,
          }
        })
      },

      duplicateWorkflow: (id) => {
        const workflow = get().workflows[id]
        if (!workflow) return ''
        
        const newWorkflow: WorkflowSchema = {
          ...JSON.parse(JSON.stringify(workflow)),
          id: generateId(),
          name: `${workflow.name} (Copy)`,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }
        
        set((state) => ({
          workflows: { ...state.workflows, [newWorkflow.id]: newWorkflow },
          workspaces: state.workspaces.map((w) =>
            w.workflows.includes(id)
              ? { ...w, workflows: [...w.workflows, newWorkflow.id] }
              : w
          ),
        }))
        return newWorkflow.id
      },

      importWorkflow: (json) => {
        try {
          const workflow = JSON.parse(json) as WorkflowSchema
          workflow.id = generateId()
          workflow.created_at = new Date().toISOString()
          workflow.updated_at = new Date().toISOString()
          
          const activeWorkspaceId = get().activeWorkspaceId
          set((state) => ({
            workflows: { ...state.workflows, [workflow.id]: workflow },
            activeWorkflowId: workflow.id,
            workspaces: state.workspaces.map((w) =>
              w.id === activeWorkspaceId
                ? { ...w, workflows: [...w.workflows, workflow.id] }
                : w
            ),
          }))
          return workflow.id
        } catch {
          return null
        }
      },

      exportWorkflow: (id) => {
        const workflow = get().workflows[id]
        if (!workflow) return null
        return JSON.stringify(workflow, null, 2)
      },

      // Agent Actions
      addAgent: (workflowId, position) => {
        const agent = createDefaultAgent()
        set((state) => ({
          workflows: {
            ...state.workflows,
            [workflowId]: {
              ...state.workflows[workflowId],
              agents: [...state.workflows[workflowId].agents, agent],
              updated_at: new Date().toISOString(),
            },
          },
          selectedNodeId: agent.agent_id,
        }))
        return agent.agent_id
      },

      updateAgent: (workflowId, agentId, updates) => {
        set((state) => ({
          workflows: {
            ...state.workflows,
            [workflowId]: {
              ...state.workflows[workflowId],
              agents: state.workflows[workflowId].agents.map((a) =>
                a.agent_id === agentId ? { ...a, ...updates } : a
              ),
              updated_at: new Date().toISOString(),
            },
          },
        }))
      },

      deleteAgent: (workflowId, agentId) => {
        set((state) => {
          const workflow = state.workflows[workflowId]
          return {
            workflows: {
              ...state.workflows,
              [workflowId]: {
                ...workflow,
                agents: workflow.agents.filter((a) => a.agent_id !== agentId),
                edges: workflow.edges.filter(
                  (e) => e.source !== agentId && e.target !== agentId
                ),
                entry_point: workflow.entry_point === agentId ? '' : workflow.entry_point,
                updated_at: new Date().toISOString(),
              },
            },
            selectedNodeId: state.selectedNodeId === agentId ? null : state.selectedNodeId,
          }
        })
      },

      // Edge Actions
      addEdge: (workflowId, edge) => {
        const newEdge: EdgeCondition = { ...edge, id: generateId() }
        set((state) => ({
          workflows: {
            ...state.workflows,
            [workflowId]: {
              ...state.workflows[workflowId],
              edges: [...state.workflows[workflowId].edges, newEdge],
              updated_at: new Date().toISOString(),
            },
          },
        }))
      },

      updateEdge: (workflowId, edgeId, updates) => {
        set((state) => ({
          workflows: {
            ...state.workflows,
            [workflowId]: {
              ...state.workflows[workflowId],
              edges: state.workflows[workflowId].edges.map((e) =>
                e.id === edgeId ? { ...e, ...updates } : e
              ),
              updated_at: new Date().toISOString(),
            },
          },
        }))
      },

      deleteEdge: (workflowId, edgeId) => {
        set((state) => ({
          workflows: {
            ...state.workflows,
            [workflowId]: {
              ...state.workflows[workflowId],
              edges: state.workflows[workflowId].edges.filter((e) => e.id !== edgeId),
              updated_at: new Date().toISOString(),
            },
          },
          selectedEdgeId: state.selectedEdgeId === edgeId ? null : state.selectedEdgeId,
        }))
      },

      // Global Registry Actions
      addGlobalTool: (tool) => {
        set((state) => ({
          globalTools: [...state.globalTools, { ...tool, id: generateId() }],
        }))
      },

      updateGlobalTool: (id, updates) => {
        set((state) => ({
          globalTools: state.globalTools.map((t) =>
            t.id === id ? { ...t, ...updates } : t
          ),
        }))
      },

      deleteGlobalTool: (id) => {
        set((state) => ({
          globalTools: state.globalTools.filter((t) => t.id !== id),
        }))
      },

      addGlobalRAGSource: (source) => {
        const id = generateId()
        set((state) => ({
          globalRAGSources: [...state.globalRAGSources, { ...source, id }],
        }))
        return id
      },

      updateGlobalRAGSource: (id, updates) => {
        set((state) => ({
          globalRAGSources: state.globalRAGSources.map((s) =>
            s.id === id ? { ...s, ...updates } : s
          ),
        }))
      },

      deleteGlobalRAGSource: (id) => {
        set((state) => ({
          globalRAGSources: state.globalRAGSources.filter((s) => s.id !== id),
        }))
      },

      // Selection Actions
      setSelectedNode: (id) => set({ selectedNodeId: id, selectedEdgeId: null }),
      setSelectedEdge: (id) => set({ selectedEdgeId: id, selectedNodeId: null }),

      // Execution Actions
      setExecutionState: (workflowId, state) => {
        set((s) => ({
          executionStates: { ...s.executionStates, [workflowId]: state },
        }))
      },

      addExecutionMessage: (workflowId, message) => {
        set((state) => {
          const currentState = state.executionStates[workflowId] || {
            scratchpad: {},
            messages: [],
            status: 'idle' as const,
          }
          return {
            executionStates: {
              ...state.executionStates,
              [workflowId]: {
                ...currentState,
                messages: [...currentState.messages, message],
              },
            },
          }
        })
      },

      setMetrics: (workflowId, metrics) => {
        set((state) => ({
          metrics: { ...state.metrics, [workflowId]: metrics },
        }))
      },

      setTrace: (workflowId, trace) => {
        set((state) => ({
          traces: { ...state.traces, [workflowId]: trace },
        }))
      },

      addHITLRequest: (request) => {
        set((state) => ({
          hitlRequests: [...state.hitlRequests, request],
        }))
      },

      resolveHITLRequest: (id, action, feedback) => {
        set((state) => ({
          hitlRequests: state.hitlRequests.map((r) =>
            r.id === id ? { ...r, status: action === 'approve' ? 'approved' : 'rejected' } : r
          ),
        }))
      },

      // UI Actions
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      toggleConfigPanel: () => set((state) => ({ configPanelOpen: !state.configPanelOpen })),
      toggleRegistryDrawer: () => set((state) => ({ registryDrawerOpen: !state.registryDrawerOpen })),
    }),
    {
      name: 'harpy-workflow-store',
      partialize: (state) => ({
        workspaces: state.workspaces,
        workflows: state.workflows,
        globalTools: state.globalTools,
        globalRAGSources: state.globalRAGSources,
      }),
    }
  )
)

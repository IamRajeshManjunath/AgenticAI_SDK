'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  Bot,
  Crown,
  Cpu,
  FileText,
  Wrench,
  Database,
  Users,
  Shield,
  AlertTriangle,
  Zap,
  RefreshCw,
  Plus,
  Trash2,
  ChevronDown,
  ChevronRight,
  Grip,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useWorkflowStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Slider } from '@/components/ui/slider'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import type { AgentNodeConfig, ReasoningStep, FallbackConfig, LLMConfig } from '@/lib/types'

interface AgentConfigSidebarProps {
  workflowId: string
  agentId: string | null
  onClose: () => void
}

export function AgentConfigSidebar({
  workflowId,
  agentId,
  onClose,
}: AgentConfigSidebarProps) {
  const { workflows, globalTools, globalRAGSources, updateAgent, updateWorkflow } =
    useWorkflowStore()
  const workflow = workflows[workflowId]
  const agent = workflow?.agents.find((a) => a.agent_id === agentId)

  const otherAgents = workflow?.agents.filter((a) => a.agent_id !== agentId) || []

  const handleUpdate = (updates: Partial<AgentNodeConfig>) => {
    if (!agentId) return
    updateAgent(workflowId, agentId, updates)
  }

  const handleSetEntryPoint = () => {
    if (!agentId) return
    updateWorkflow(workflowId, { entry_point: agentId })
  }

  if (!agent) {
    return (
      <AnimatePresence>
        {agentId && (
          <motion.div
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            className="fixed right-0 top-0 h-full w-96 bg-card border-l border-border z-40 flex items-center justify-center"
          >
            <p className="text-muted-foreground">Agent not found</p>
          </motion.div>
        )}
      </AnimatePresence>
    )
  }

  const isEntryPoint = workflow?.entry_point === agentId
  const isCoordinator = agent.sub_agents && agent.sub_agents.length > 0

  return (
    <AnimatePresence>
      <motion.div
        initial={{ x: 400, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: 400, opacity: 0 }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className="fixed right-0 top-0 h-full w-[420px] bg-card border-l border-border z-40 flex flex-col"
      >
        {/* Header */}
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'p-2 rounded-lg',
                isCoordinator ? 'bg-warning/20' : 'bg-primary/20'
              )}
            >
              {isCoordinator ? (
                <Crown className="w-5 h-5 text-warning" />
              ) : (
                <Bot className="w-5 h-5 text-primary" />
              )}
            </div>
            <div>
              <h2 className="font-semibold">Agent Configuration</h2>
              <p className="text-sm text-muted-foreground">{agent.agent_id}</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0">
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-6">
          {/* Identity Section */}
          <Section title="Identity" icon={<Bot className="w-4 h-4" />}>
            <div className="space-y-4">
              <div>
                <Label htmlFor="agent_id">Agent ID</Label>
                <Input
                  id="agent_id"
                  value={agent.agent_id}
                  onChange={(e) => handleUpdate({ agent_id: e.target.value })}
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label htmlFor="role">Role</Label>
                <Input
                  id="role"
                  value={agent.role}
                  onChange={(e) => handleUpdate({ role: e.target.value })}
                  className="mt-1.5"
                  placeholder="e.g., Research Assistant"
                />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Entry Point</Label>
                  <p className="text-xs text-muted-foreground">
                    Set as workflow entry point
                  </p>
                </div>
                {isEntryPoint ? (
                  <Badge variant="secondary" className="bg-success/20 text-success">
                    Entry Point
                  </Badge>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSetEntryPoint}
                  >
                    Set as Entry
                  </Button>
                )}
              </div>
            </div>
          </Section>

          {/* Prompt Template Section */}
          <Section title="Prompt Template" icon={<FileText className="w-4 h-4" />}>
            <div className="space-y-4">
              <div>
                <Label htmlFor="template_string">Template String</Label>
                <Textarea
                  id="template_string"
                  value={agent.prompt_template?.template_string || ''}
                  onChange={(e) =>
                    handleUpdate({
                      prompt_template: {
                        ...agent.prompt_template,
                        template_string: e.target.value,
                      },
                    })
                  }
                  className="mt-1.5 h-32 font-mono text-sm"
                  placeholder="You are a helpful assistant. {{input}}"
                />
              </div>
              <div>
                <Label>Input Variables</Label>
                <div className="flex flex-wrap gap-2 mt-1.5">
                  {agent.prompt_template?.input_variables?.map((variable, i) => (
                    <Badge key={i} variant="secondary" className="gap-1">
                      {`{{${variable}}}`}
                      <button
                        onClick={() => {
                          const newVars =
                            agent.prompt_template?.input_variables?.filter(
                              (_, idx) => idx !== i
                            ) || []
                          handleUpdate({
                            prompt_template: {
                              ...agent.prompt_template,
                              input_variables: newVars,
                            },
                          })
                        }}
                        className="ml-1 hover:text-destructive"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </Badge>
                  ))}
                  <Input
                    placeholder="Add variable..."
                    className="w-32 h-7 text-xs"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && e.currentTarget.value) {
                        const newVar = e.currentTarget.value.trim()
                        const currentVars =
                          agent.prompt_template?.input_variables || []
                        if (!currentVars.includes(newVar)) {
                          handleUpdate({
                            prompt_template: {
                              ...agent.prompt_template,
                              input_variables: [...currentVars, newVar],
                            },
                          })
                        }
                        e.currentTarget.value = ''
                      }
                    }}
                  />
                </div>
              </div>
            </div>
          </Section>

          {/* LLM Settings Section */}
          <Section title="LLM Settings" icon={<Cpu className="w-4 h-4" />}>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Provider</Label>
                  <Select
                    value={agent.llm_config?.provider || 'openai'}
                    onValueChange={(value) =>
                      handleUpdate({
                        llm_config: {
                          ...agent.llm_config,
                          provider: value as LLMConfig['provider'],
                        },
                      })
                    }
                  >
                    <SelectTrigger className="mt-1.5">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="openai">OpenAI</SelectItem>
                      <SelectItem value="anthropic">Anthropic</SelectItem>
                      <SelectItem value="google">Google</SelectItem>
                      <SelectItem value="azure">Azure</SelectItem>
                      <SelectItem value="local">Local</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Model Name</Label>
                  <Input
                    value={agent.llm_config?.model_name || ''}
                    onChange={(e) =>
                      handleUpdate({
                        llm_config: {
                          ...agent.llm_config,
                          model_name: e.target.value,
                        },
                      })
                    }
                    className="mt-1.5"
                    placeholder="gpt-4-turbo"
                  />
                </div>
              </div>
              <div>
                <Label>
                  Temperature: {(agent.llm_config?.temperature || 0.7).toFixed(2)}
                </Label>
                <Slider
                  value={[(agent.llm_config?.temperature || 0.7) * 100]}
                  onValueChange={([value]) =>
                    handleUpdate({
                      llm_config: {
                        ...agent.llm_config,
                        temperature: value / 100,
                      },
                    })
                  }
                  min={0}
                  max={200}
                  step={1}
                  className="mt-2"
                />
              </div>
              <div>
                <Label>Max Tokens</Label>
                <Input
                  type="number"
                  value={agent.llm_config?.max_tokens || 4096}
                  onChange={(e) =>
                    handleUpdate({
                      llm_config: {
                        ...agent.llm_config,
                        max_tokens: parseInt(e.target.value) || 4096,
                      },
                    })
                  }
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label>API Key Env Var</Label>
                <Input
                  value={agent.llm_config?.api_key_env_var || ''}
                  onChange={(e) =>
                    handleUpdate({
                      llm_config: {
                        ...agent.llm_config,
                        api_key_env_var: e.target.value,
                      },
                    })
                  }
                  className="mt-1.5"
                  placeholder="OPENAI_API_KEY"
                />
              </div>
            </div>
          </Section>

          {/* Topology Section */}
          <Section title="Topology" icon={<Users className="w-4 h-4" />}>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Orchestration Mode</Label>
                  <p className="text-xs text-muted-foreground">
                    {agent.orchestration_mode === 'agent-driven'
                      ? 'Agent controls execution flow'
                      : 'Model determines next steps'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      'text-xs',
                      agent.orchestration_mode === 'model-driven'
                        ? 'text-foreground'
                        : 'text-muted-foreground'
                    )}
                  >
                    Model
                  </span>
                  <Switch
                    checked={agent.orchestration_mode === 'agent-driven'}
                    onCheckedChange={(checked) =>
                      handleUpdate({
                        orchestration_mode: checked ? 'agent-driven' : 'model-driven',
                      })
                    }
                  />
                  <span
                    className={cn(
                      'text-xs',
                      agent.orchestration_mode === 'agent-driven'
                        ? 'text-foreground'
                        : 'text-muted-foreground'
                    )}
                  >
                    Agent
                  </span>
                </div>
              </div>

              {agent.orchestration_mode === 'agent-driven' && (
                <ReasoningStepsEditor
                  steps={agent.reasoning_steps || []}
                  onChange={(steps) => handleUpdate({ reasoning_steps: steps })}
                />
              )}
            </div>
          </Section>

          {/* Tool & Data Bindings Section */}
          <Section title="Tool & Data Bindings" icon={<Wrench className="w-4 h-4" />}>
            <div className="space-y-4">
              <div>
                <Label>Tools</Label>
                <div className="flex flex-wrap gap-2 mt-1.5">
                  {globalTools.map((tool) => (
                    <Badge
                      key={tool.id}
                      variant={
                        agent.tools?.includes(tool.id) ? 'default' : 'outline'
                      }
                      className={cn(
                        'cursor-pointer transition-colors',
                        agent.tools?.includes(tool.id)
                          ? 'bg-success hover:bg-success/80'
                          : 'hover:bg-secondary'
                      )}
                      onClick={() => {
                        const currentTools = agent.tools || []
                        const newTools = currentTools.includes(tool.id)
                          ? currentTools.filter((id) => id !== tool.id)
                          : [...currentTools, tool.id]
                        handleUpdate({ tools: newTools })
                      }}
                    >
                      <Wrench className="w-3 h-3 mr-1" />
                      {tool.name}
                    </Badge>
                  ))}
                  {globalTools.length === 0 && (
                    <p className="text-xs text-muted-foreground">
                      No tools available. Add tools in the Global Registry.
                    </p>
                  )}
                </div>
              </div>
              <div>
                <Label>RAG Sources</Label>
                <div className="flex flex-wrap gap-2 mt-1.5">
                  {globalRAGSources.map((source) => (
                    <Badge
                      key={source.id}
                      variant={
                        agent.rag_sources?.includes(source.id) ? 'default' : 'outline'
                      }
                      className={cn(
                        'cursor-pointer transition-colors',
                        agent.rag_sources?.includes(source.id)
                          ? 'bg-chart-2 hover:bg-chart-2/80'
                          : 'hover:bg-secondary'
                      )}
                      onClick={() => {
                        const currentSources = agent.rag_sources || []
                        const newSources = currentSources.includes(source.id)
                          ? currentSources.filter((id) => id !== source.id)
                          : [...currentSources, source.id]
                        handleUpdate({ rag_sources: newSources })
                      }}
                    >
                      <Database className="w-3 h-3 mr-1" />
                      {source.provider}
                    </Badge>
                  ))}
                  {globalRAGSources.length === 0 && (
                    <p className="text-xs text-muted-foreground">
                      No RAG sources available. Add sources in the Global Registry.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </Section>

          {/* Delegation Section */}
          <Section title="Delegation" icon={<Crown className="w-4 h-4" />}>
            <div className="space-y-4">
              <div>
                <Label>Sub-Agents</Label>
                <p className="text-xs text-muted-foreground mb-2">
                  Select agents this coordinator can delegate to
                </p>
                <div className="flex flex-wrap gap-2">
                  {otherAgents.map((otherAgent) => (
                    <Badge
                      key={otherAgent.agent_id}
                      variant={
                        agent.sub_agents?.includes(otherAgent.agent_id)
                          ? 'default'
                          : 'outline'
                      }
                      className={cn(
                        'cursor-pointer transition-colors',
                        agent.sub_agents?.includes(otherAgent.agent_id)
                          ? 'bg-warning hover:bg-warning/80 text-warning-foreground'
                          : 'hover:bg-secondary'
                      )}
                      onClick={() => {
                        const currentSubs = agent.sub_agents || []
                        const newSubs = currentSubs.includes(otherAgent.agent_id)
                          ? currentSubs.filter((id) => id !== otherAgent.agent_id)
                          : [...currentSubs, otherAgent.agent_id]
                        handleUpdate({ sub_agents: newSubs })
                      }}
                    >
                      <Users className="w-3 h-3 mr-1" />
                      {otherAgent.agent_id}
                    </Badge>
                  ))}
                  {otherAgents.length === 0 && (
                    <p className="text-xs text-muted-foreground">
                      Add more agents to enable delegation.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </Section>

          {/* Middleware Guardrails Accordion */}
          <Accordion type="multiple" className="space-y-2">
            <AccordionItem value="budget" className="border rounded-lg px-4">
              <AccordionTrigger className="text-sm font-medium">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-warning" />
                  Budget Guardrails
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pb-4">
                <div>
                  <Label>Max Tokens</Label>
                  <Input
                    type="number"
                    value={agent.budget_guardrails?.max_tokens || ''}
                    onChange={(e) =>
                      handleUpdate({
                        budget_guardrails: {
                          ...agent.budget_guardrails,
                          max_tokens: parseInt(e.target.value) || undefined,
                        },
                      })
                    }
                    className="mt-1.5"
                    placeholder="Unlimited"
                  />
                </div>
                <div>
                  <Label>Max Cost ($)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={agent.budget_guardrails?.max_cost || ''}
                    onChange={(e) =>
                      handleUpdate({
                        budget_guardrails: {
                          ...agent.budget_guardrails,
                          max_cost: parseFloat(e.target.value) || undefined,
                        },
                      })
                    }
                    className="mt-1.5"
                    placeholder="Unlimited"
                  />
                </div>
                <div>
                  <Label>Max Iterations</Label>
                  <Input
                    type="number"
                    value={agent.budget_guardrails?.max_iterations || ''}
                    onChange={(e) =>
                      handleUpdate({
                        budget_guardrails: {
                          ...agent.budget_guardrails,
                          max_iterations: parseInt(e.target.value) || undefined,
                        },
                      })
                    }
                    className="mt-1.5"
                    placeholder="Unlimited"
                  />
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="pii" className="border rounded-lg px-4">
              <AccordionTrigger className="text-sm font-medium">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-chart-2" />
                  PII Protection
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pb-4">
                <div className="flex items-center justify-between">
                  <Label>Enable PII Masking</Label>
                  <Switch
                    checked={agent.pii_guardrails?.enabled || false}
                    onCheckedChange={(checked) =>
                      handleUpdate({
                        pii_guardrails: {
                          ...agent.pii_guardrails,
                          enabled: checked,
                          masking_level: agent.pii_guardrails?.masking_level || 'partial',
                        },
                      })
                    }
                  />
                </div>
                {agent.pii_guardrails?.enabled && (
                  <div>
                    <Label>Masking Level</Label>
                    <Select
                      value={agent.pii_guardrails?.masking_level || 'partial'}
                      onValueChange={(value) =>
                        handleUpdate({
                          pii_guardrails: {
                            enabled: agent.pii_guardrails?.enabled ?? false,
                            masking_level: value as 'hash' | 'partial' | 'full',
                          },
                        })
                      }
                    >
                      <SelectTrigger className="mt-1.5">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="hash">Hash</SelectItem>
                        <SelectItem value="partial">Partial</SelectItem>
                        <SelectItem value="full">Full</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="firewall" className="border rounded-lg px-4">
              <AccordionTrigger className="text-sm font-medium">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-destructive" />
                  Firewall Protection
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pb-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Prompt Injection Protection</Label>
                    <p className="text-xs text-muted-foreground">
                      Detect and block injection attempts
                    </p>
                  </div>
                  <Switch
                    checked={agent.firewall_guardrails?.prompt_injection_protection || false}
                    onCheckedChange={(checked) =>
                      handleUpdate({
                        firewall_guardrails: {
                          prompt_injection_protection: checked,
                        },
                      })
                    }
                  />
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="consensus" className="border rounded-lg px-4">
              <AccordionTrigger className="text-sm font-medium">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-primary" />
                  Consensus Voting
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pb-4">
                <div className="flex items-center justify-between">
                  <Label>Enable Consensus</Label>
                  <Switch
                    checked={agent.consensus_config?.enabled || false}
                    onCheckedChange={(checked) =>
                      handleUpdate({
                        consensus_config: {
                          enabled: checked,
                          num_instances: agent.consensus_config?.num_instances || 3,
                          agreement_threshold:
                            agent.consensus_config?.agreement_threshold || 0.7,
                        },
                      })
                    }
                  />
                </div>
                {agent.consensus_config?.enabled && (
                  <>
                    <div>
                      <Label>
                        Instances: {agent.consensus_config?.num_instances || 3}
                      </Label>
                      <Slider
                        value={[agent.consensus_config?.num_instances || 3]}
                        onValueChange={([value]) =>
                          handleUpdate({
                            consensus_config: {
                              enabled: agent.consensus_config?.enabled ?? false,
                              num_instances: value,
                              agreement_threshold: agent.consensus_config?.agreement_threshold ?? 0.7,
                            },
                          })
                        }
                        min={1}
                        max={5}
                        step={1}
                        className="mt-2"
                      />
                    </div>
                    <div>
                      <Label>
                        Agreement Threshold:{' '}
                        {(
                          (agent.consensus_config?.agreement_threshold || 0.7) * 100
                        ).toFixed(0)}
                        %
                      </Label>
                      <Slider
                        value={[
                          (agent.consensus_config?.agreement_threshold || 0.7) * 100,
                        ]}
                        onValueChange={([value]) =>
                          handleUpdate({
                            consensus_config: {
                              enabled: agent.consensus_config?.enabled ?? false,
                              num_instances: agent.consensus_config?.num_instances ?? 3,
                              agreement_threshold: value / 100,
                            },
                          })
                        }
                        min={10}
                        max={100}
                        step={5}
                        className="mt-2"
                      />
                    </div>
                  </>
                )}
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="hitl" className="border rounded-lg px-4">
              <AccordionTrigger className="text-sm font-medium">
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-success" />
                  Human-in-the-Loop
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pb-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Interruption Point</Label>
                    <p className="text-xs text-muted-foreground">
                      Pause for human approval before actions
                    </p>
                  </div>
                  <Switch
                    checked={agent.interruption_point || false}
                    onCheckedChange={(checked) =>
                      handleUpdate({ interruption_point: checked })
                    }
                  />
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="fallback" className="border rounded-lg px-4">
              <AccordionTrigger className="text-sm font-medium">
                <div className="flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 text-chart-4" />
                  Fallback Routing
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pb-4">
                <FallbackEditor
                  fallbacks={agent.fallback_configs || []}
                  onChange={(fallbacks) =>
                    handleUpdate({ fallback_configs: fallbacks })
                  }
                />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      </motion.div>
    </AnimatePresence>
  )
}

interface SectionProps {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
}

function Section({ title, icon, children }: SectionProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm font-medium">
        {icon}
        {title}
      </div>
      {children}
    </div>
  )
}

interface ReasoningStepsEditorProps {
  steps: ReasoningStep[]
  onChange: (steps: ReasoningStep[]) => void
}

function ReasoningStepsEditor({ steps, onChange }: ReasoningStepsEditorProps) {
  const handleAdd = () => {
    onChange([
      ...steps,
      {
        id: Math.random().toString(36).substring(2, 15),
        description: '',
        order: steps.length,
      },
    ])
  }

  const handleRemove = (id: string) => {
    onChange(
      steps
        .filter((s) => s.id !== id)
        .map((s, i) => ({ ...s, order: i }))
    )
  }

  const handleUpdate = (id: string, description: string) => {
    onChange(steps.map((s) => (s.id === id ? { ...s, description } : s)))
  }

  return (
    <div className="space-y-2">
      <Label>Reasoning Steps</Label>
      <div className="space-y-2">
        {steps.map((step, i) => (
          <div key={step.id} className="flex items-center gap-2">
            <Grip className="w-4 h-4 text-muted-foreground cursor-move" />
            <span className="text-xs text-muted-foreground w-6">{i + 1}.</span>
            <Input
              value={step.description}
              onChange={(e) => handleUpdate(step.id, e.target.value)}
              placeholder="Describe this step..."
              className="flex-1 h-8 text-sm"
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleRemove(step.id)}
              className="h-8 w-8 p-0 text-destructive"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        ))}
        <Button
          variant="outline"
          size="sm"
          onClick={handleAdd}
          className="w-full gap-2"
        >
          <Plus className="w-4 h-4" />
          Add Step
        </Button>
      </div>
    </div>
  )
}

interface FallbackEditorProps {
  fallbacks: FallbackConfig[]
  onChange: (fallbacks: FallbackConfig[]) => void
}

function FallbackEditor({ fallbacks, onChange }: FallbackEditorProps) {
  const handleAdd = () => {
    onChange([
      ...fallbacks,
      {
        llm_config: {
          provider: 'openai',
          model_name: 'gpt-3.5-turbo',
          temperature: 0.7,
          max_tokens: 4096,
          api_key_env_var: 'OPENAI_API_KEY',
        },
        priority: fallbacks.length + 1,
      },
    ])
  }

  const handleRemove = (index: number) => {
    onChange(
      fallbacks
        .filter((_, i) => i !== index)
        .map((f, i) => ({ ...f, priority: i + 1 }))
    )
  }

  const handleUpdate = (index: number, config: Partial<LLMConfig>) => {
    onChange(
      fallbacks.map((f, i) =>
        i === index ? { ...f, llm_config: { ...f.llm_config, ...config } } : f
      )
    )
  }

  return (
    <div className="space-y-3">
      {fallbacks.map((fallback, i) => (
        <div key={i} className="glass-card p-3 rounded-lg space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium">
              Fallback #{fallback.priority}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleRemove(i)}
              className="h-6 w-6 p-0 text-destructive"
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label className="text-xs">Provider</Label>
              <Select
                value={fallback.llm_config.provider}
                onValueChange={(value) =>
                  handleUpdate(i, { provider: value as LLMConfig['provider'] })
                }
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="openai">OpenAI</SelectItem>
                  <SelectItem value="anthropic">Anthropic</SelectItem>
                  <SelectItem value="google">Google</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Model</Label>
              <Input
                value={fallback.llm_config.model_name}
                onChange={(e) => handleUpdate(i, { model_name: e.target.value })}
                className="h-8 text-xs"
              />
            </div>
          </div>
        </div>
      ))}
      <Button
        variant="outline"
        size="sm"
        onClick={handleAdd}
        className="w-full gap-2"
      >
        <Plus className="w-4 h-4" />
        Add Fallback LLM
      </Button>
    </div>
  )
}

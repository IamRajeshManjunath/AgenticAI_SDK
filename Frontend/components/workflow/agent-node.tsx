'use client'

import { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { motion } from 'framer-motion'
import { Bot, Crown, Users, Wrench, Database, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { AgentNodeConfig } from '@/lib/types'

interface AgentNodeData extends AgentNodeConfig {
  isRunning?: boolean
  isEntryPoint?: boolean
}

export const AgentNode = memo(function AgentNode({
  data,
  selected,
}: NodeProps<AgentNodeData>) {
  const isCoordinator = data.sub_agents && data.sub_agents.length > 0
  const hasTools = data.tools && data.tools.length > 0
  const hasRAG = data.rag_sources && data.rag_sources.length > 0
  const hasHITL = data.interruption_point

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={cn(
        'relative px-4 py-3 rounded-xl min-w-[200px] max-w-[280px]',
        'bg-card/80 backdrop-blur-sm border-2 transition-all duration-200',
        selected
          ? 'border-primary shadow-lg glow-primary-sm'
          : 'border-border hover:border-primary/50',
        data.isRunning && 'pulse-glow border-primary',
        data.isEntryPoint && 'ring-2 ring-success/50 ring-offset-2 ring-offset-background'
      )}
    >
      {/* Entry Point Badge */}
      {data.isEntryPoint && (
        <div className="absolute -top-2 -left-2 px-2 py-0.5 bg-success text-success-foreground text-xs font-medium rounded-full">
          Entry
        </div>
      )}

      {/* Target Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-primary !border-2 !border-background"
      />

      {/* Header */}
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'p-2 rounded-lg shrink-0',
            isCoordinator ? 'bg-warning/20' : 'bg-primary/20'
          )}
        >
          {isCoordinator ? (
            <Crown className="w-5 h-5 text-warning" />
          ) : (
            <Bot className="w-5 h-5 text-primary" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-sm text-foreground truncate">
            {data.agent_id}
          </p>
          <p className="text-xs text-muted-foreground truncate">{data.role}</p>
        </div>
      </div>

      {/* Metadata */}
      <div className="flex items-center gap-2 mt-3 flex-wrap">
        {/* LLM Badge */}
        <span className="px-2 py-0.5 bg-secondary rounded text-xs text-secondary-foreground">
          {data.llm_config?.model_name || 'No Model'}
        </span>

        {/* Orchestration Mode */}
        <span
          className={cn(
            'px-2 py-0.5 rounded text-xs',
            data.orchestration_mode === 'agent-driven'
              ? 'bg-chart-4/20 text-chart-4'
              : 'bg-chart-2/20 text-chart-2'
          )}
        >
          {data.orchestration_mode === 'agent-driven' ? 'Agent' : 'Model'}
        </span>
      </div>

      {/* Feature Icons */}
      <div className="flex items-center gap-2 mt-2 pt-2 border-t border-border/50">
        {isCoordinator && (
          <div className="flex items-center gap-1 text-warning" title="Has sub-agents">
            <Users className="w-3.5 h-3.5" />
            <span className="text-xs">{data.sub_agents.length}</span>
          </div>
        )}
        {hasTools && (
          <div className="flex items-center gap-1 text-success" title="Has tools">
            <Wrench className="w-3.5 h-3.5" />
            <span className="text-xs">{data.tools.length}</span>
          </div>
        )}
        {hasRAG && (
          <div className="flex items-center gap-1 text-chart-2" title="Has RAG sources">
            <Database className="w-3.5 h-3.5" />
            <span className="text-xs">{data.rag_sources.length}</span>
          </div>
        )}
        {hasHITL && (
          <div className="flex items-center gap-1 text-destructive" title="HITL enabled">
            <AlertTriangle className="w-3.5 h-3.5" />
          </div>
        )}
      </div>

      {/* Source Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-primary !border-2 !border-background"
      />
    </motion.div>
  )
})

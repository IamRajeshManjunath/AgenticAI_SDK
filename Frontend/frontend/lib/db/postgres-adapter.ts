// PostgreSQL database adapter for Neon, Supabase, or standard Postgres

import type {
  DatabaseAdapter,
  Workflow,
  Execution,
  ActivityLog,
  Tool,
  RAGSource,
  UsageRecord,
} from './types';

// SQL schema for initialization
export const INIT_SCHEMA = `
-- Workflows table
CREATE TABLE IF NOT EXISTS workflows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  description TEXT,
  status VARCHAR(50) DEFAULT 'draft',
  nodes JSONB DEFAULT '[]',
  edges JSONB DEFAULT '[]',
  settings JSONB DEFAULT '{}',
  user_id VARCHAR(255) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Executions table
CREATE TABLE IF NOT EXISTS executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
  status VARCHAR(50) DEFAULT 'pending',
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE,
  duration_ms INTEGER,
  input JSONB DEFAULT '{}',
  output JSONB,
  error TEXT,
  tokens_used INTEGER DEFAULT 0,
  cost_usd DECIMAL(10, 6) DEFAULT 0,
  agent_executions JSONB DEFAULT '[]'
);

-- Activity logs table
CREATE TABLE IF NOT EXISTS activity_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  user_id VARCHAR(255) NOT NULL,
  user_email VARCHAR(255),
  action VARCHAR(255) NOT NULL,
  resource_type VARCHAR(100),
  resource_id VARCHAR(255),
  resource_name VARCHAR(255),
  details JSONB,
  ip_address VARCHAR(50),
  user_agent TEXT
);

-- Tools table
CREATE TABLE IF NOT EXISTS tools (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  description TEXT,
  type VARCHAR(50) NOT NULL,
  schema JSONB DEFAULT '{}',
  config JSONB DEFAULT '{}',
  is_active BOOLEAN DEFAULT true,
  user_id VARCHAR(255) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RAG sources table
CREATE TABLE IF NOT EXISTS rag_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  type VARCHAR(50) NOT NULL,
  status VARCHAR(50) DEFAULT 'indexing',
  document_count INTEGER DEFAULT 0,
  chunk_count INTEGER DEFAULT 0,
  last_synced TIMESTAMP WITH TIME ZONE,
  config JSONB DEFAULT '{}',
  user_id VARCHAR(255) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Usage records table
CREATE TABLE IF NOT EXISTS usage_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id VARCHAR(255) NOT NULL,
  date DATE NOT NULL,
  workflow_id UUID REFERENCES workflows(id) ON DELETE SET NULL,
  tokens_input INTEGER DEFAULT 0,
  tokens_output INTEGER DEFAULT 0,
  cost_usd DECIMAL(10, 6) DEFAULT 0,
  execution_count INTEGER DEFAULT 0
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_workflows_user_id ON workflows(user_id);
CREATE INDEX IF NOT EXISTS idx_executions_workflow_id ON executions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_executions_started_at ON executions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_tools_user_id ON tools(user_id);
CREATE INDEX IF NOT EXISTS idx_rag_sources_user_id ON rag_sources(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_records_user_date ON usage_records(user_id, date);
`;

// Type for the SQL client (compatible with pg, @neondatabase/serverless, @vercel/postgres)
interface SQLClient {
  query: <T = Record<string, unknown>>(
    text: string,
    params?: unknown[]
  ) => Promise<{ rows: T[]; rowCount: number }>;
}

export class PostgresAdapter implements DatabaseAdapter {
  private client: SQLClient | null = null;
  private connectionString: string;

  constructor(connectionString: string) {
    this.connectionString = connectionString;
  }

  async connect(): Promise<void> {
    // Dynamically import the appropriate driver based on connection string
    if (this.connectionString.includes('neon.tech')) {
      const { neon } = await import('@neondatabase/serverless');
      const sql = neon(this.connectionString);
      this.client = {
        query: async <T>(text: string, params?: unknown[]) => {
          const rows = await sql(text as unknown as TemplateStringsArray, ...(params ?? [])) as T[];
          return { rows, rowCount: rows.length };
        },
      };
    } else {
      // Use standard pg for Supabase or other Postgres
      // @ts-expect-error - @types/pg not installed
      const { Pool } = await import('pg');
      const pool = new Pool({ connectionString: this.connectionString });
      this.client = pool;
    }
  }

  async disconnect(): Promise<void> {
    this.client = null;
  }

  isConnected(): boolean {
    return this.client !== null;
  }

  async initializeSchema(): Promise<void> {
    if (!this.client) throw new Error('Not connected');
    await this.client.query(INIT_SCHEMA);
  }

  // Workflows
  async getWorkflows(userId: string): Promise<Workflow[]> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<Workflow>(
      'SELECT * FROM workflows WHERE user_id = $1 ORDER BY updated_at DESC',
      [userId]
    );
    return result.rows;
  }

  async getWorkflow(id: string): Promise<Workflow | null> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<Workflow>(
      'SELECT * FROM workflows WHERE id = $1',
      [id]
    );
    return result.rows[0] || null;
  }

  async createWorkflow(workflow: Omit<Workflow, 'id' | 'created_at' | 'updated_at'>): Promise<Workflow> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<Workflow>(
      `INSERT INTO workflows (name, description, status, nodes, edges, settings, user_id)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       RETURNING *`,
      [
        workflow.name,
        workflow.description,
        workflow.status,
        JSON.stringify(workflow.nodes),
        JSON.stringify(workflow.edges),
        JSON.stringify(workflow.settings),
        workflow.user_id,
      ]
    );
    return result.rows[0];
  }

  async updateWorkflow(id: string, updates: Partial<Workflow>): Promise<Workflow> {
    if (!this.client) throw new Error('Not connected');
    const setClauses: string[] = [];
    const values: unknown[] = [];
    let paramIndex = 1;

    if (updates.name !== undefined) {
      setClauses.push(`name = $${paramIndex++}`);
      values.push(updates.name);
    }
    if (updates.description !== undefined) {
      setClauses.push(`description = $${paramIndex++}`);
      values.push(updates.description);
    }
    if (updates.status !== undefined) {
      setClauses.push(`status = $${paramIndex++}`);
      values.push(updates.status);
    }
    if (updates.nodes !== undefined) {
      setClauses.push(`nodes = $${paramIndex++}`);
      values.push(JSON.stringify(updates.nodes));
    }
    if (updates.edges !== undefined) {
      setClauses.push(`edges = $${paramIndex++}`);
      values.push(JSON.stringify(updates.edges));
    }
    if (updates.settings !== undefined) {
      setClauses.push(`settings = $${paramIndex++}`);
      values.push(JSON.stringify(updates.settings));
    }

    setClauses.push(`updated_at = NOW()`);
    values.push(id);

    const result = await this.client.query<Workflow>(
      `UPDATE workflows SET ${setClauses.join(', ')} WHERE id = $${paramIndex} RETURNING *`,
      values
    );
    return result.rows[0];
  }

  async deleteWorkflow(id: string): Promise<void> {
    if (!this.client) throw new Error('Not connected');
    await this.client.query('DELETE FROM workflows WHERE id = $1', [id]);
  }

  // Executions
  async getExecutions(workflowId: string, limit = 50): Promise<Execution[]> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<Execution>(
      'SELECT * FROM executions WHERE workflow_id = $1 ORDER BY started_at DESC LIMIT $2',
      [workflowId, limit]
    );
    return result.rows;
  }

  async getExecution(id: string): Promise<Execution | null> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<Execution>(
      'SELECT * FROM executions WHERE id = $1',
      [id]
    );
    return result.rows[0] || null;
  }

  async createExecution(execution: Omit<Execution, 'id'>): Promise<Execution> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<Execution>(
      `INSERT INTO executions (workflow_id, status, started_at, completed_at, duration_ms, input, output, error, tokens_used, cost_usd, agent_executions)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
       RETURNING *`,
      [
        execution.workflow_id,
        execution.status,
        execution.started_at,
        execution.completed_at,
        execution.duration_ms,
        JSON.stringify(execution.input),
        execution.output ? JSON.stringify(execution.output) : null,
        execution.error,
        execution.tokens_used,
        execution.cost_usd,
        JSON.stringify(execution.agent_executions),
      ]
    );
    return result.rows[0];
  }

  async updateExecution(id: string, updates: Partial<Execution>): Promise<Execution> {
    if (!this.client) throw new Error('Not connected');
    const setClauses: string[] = [];
    const values: unknown[] = [];
    let paramIndex = 1;

    if (updates.status !== undefined) {
      setClauses.push(`status = $${paramIndex++}`);
      values.push(updates.status);
    }
    if (updates.completed_at !== undefined) {
      setClauses.push(`completed_at = $${paramIndex++}`);
      values.push(updates.completed_at);
    }
    if (updates.duration_ms !== undefined) {
      setClauses.push(`duration_ms = $${paramIndex++}`);
      values.push(updates.duration_ms);
    }
    if (updates.output !== undefined) {
      setClauses.push(`output = $${paramIndex++}`);
      values.push(JSON.stringify(updates.output));
    }
    if (updates.error !== undefined) {
      setClauses.push(`error = $${paramIndex++}`);
      values.push(updates.error);
    }
    if (updates.tokens_used !== undefined) {
      setClauses.push(`tokens_used = $${paramIndex++}`);
      values.push(updates.tokens_used);
    }
    if (updates.cost_usd !== undefined) {
      setClauses.push(`cost_usd = $${paramIndex++}`);
      values.push(updates.cost_usd);
    }

    values.push(id);

    const result = await this.client.query<Execution>(
      `UPDATE executions SET ${setClauses.join(', ')} WHERE id = $${paramIndex} RETURNING *`,
      values
    );
    return result.rows[0];
  }

  // Activity Logs
  async getActivityLogs(userId: string, limit = 50, offset = 0): Promise<ActivityLog[]> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<ActivityLog>(
      'SELECT * FROM activity_logs WHERE user_id = $1 ORDER BY timestamp DESC LIMIT $2 OFFSET $3',
      [userId, limit, offset]
    );
    return result.rows;
  }

  async createActivityLog(log: Omit<ActivityLog, 'id'>): Promise<ActivityLog> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<ActivityLog>(
      `INSERT INTO activity_logs (timestamp, user_id, user_email, action, resource_type, resource_id, resource_name, details, ip_address, user_agent)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       RETURNING *`,
      [
        log.timestamp,
        log.user_id,
        log.user_email,
        log.action,
        log.resource_type,
        log.resource_id,
        log.resource_name,
        log.details ? JSON.stringify(log.details) : null,
        log.ip_address,
        log.user_agent,
      ]
    );
    return result.rows[0];
  }

  // Tools
  async getTools(userId: string): Promise<Tool[]> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<Tool>(
      'SELECT * FROM tools WHERE user_id = $1 ORDER BY created_at DESC',
      [userId]
    );
    return result.rows;
  }

  async getTool(id: string): Promise<Tool | null> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<Tool>(
      'SELECT * FROM tools WHERE id = $1',
      [id]
    );
    return result.rows[0] || null;
  }

  async createTool(tool: Omit<Tool, 'id' | 'created_at' | 'updated_at'>): Promise<Tool> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<Tool>(
      `INSERT INTO tools (name, description, type, schema, config, is_active, user_id)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       RETURNING *`,
      [
        tool.name,
        tool.description,
        tool.type,
        JSON.stringify(tool.schema),
        JSON.stringify(tool.config),
        tool.is_active,
        tool.user_id,
      ]
    );
    return result.rows[0];
  }

  async updateTool(id: string, updates: Partial<Tool>): Promise<Tool> {
    if (!this.client) throw new Error('Not connected');
    const setClauses: string[] = [];
    const values: unknown[] = [];
    let paramIndex = 1;

    if (updates.name !== undefined) {
      setClauses.push(`name = $${paramIndex++}`);
      values.push(updates.name);
    }
    if (updates.description !== undefined) {
      setClauses.push(`description = $${paramIndex++}`);
      values.push(updates.description);
    }
    if (updates.type !== undefined) {
      setClauses.push(`type = $${paramIndex++}`);
      values.push(updates.type);
    }
    if (updates.schema !== undefined) {
      setClauses.push(`schema = $${paramIndex++}`);
      values.push(JSON.stringify(updates.schema));
    }
    if (updates.config !== undefined) {
      setClauses.push(`config = $${paramIndex++}`);
      values.push(JSON.stringify(updates.config));
    }
    if (updates.is_active !== undefined) {
      setClauses.push(`is_active = $${paramIndex++}`);
      values.push(updates.is_active);
    }

    setClauses.push(`updated_at = NOW()`);
    values.push(id);

    const result = await this.client.query<Tool>(
      `UPDATE tools SET ${setClauses.join(', ')} WHERE id = $${paramIndex} RETURNING *`,
      values
    );
    return result.rows[0];
  }

  async deleteTool(id: string): Promise<void> {
    if (!this.client) throw new Error('Not connected');
    await this.client.query('DELETE FROM tools WHERE id = $1', [id]);
  }

  // RAG Sources
  async getRAGSources(userId: string): Promise<RAGSource[]> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<RAGSource>(
      'SELECT * FROM rag_sources WHERE user_id = $1 ORDER BY created_at DESC',
      [userId]
    );
    return result.rows;
  }

  async getRAGSource(id: string): Promise<RAGSource | null> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<RAGSource>(
      'SELECT * FROM rag_sources WHERE id = $1',
      [id]
    );
    return result.rows[0] || null;
  }

  async createRAGSource(source: Omit<RAGSource, 'id' | 'created_at' | 'updated_at'>): Promise<RAGSource> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<RAGSource>(
      `INSERT INTO rag_sources (name, type, status, document_count, chunk_count, last_synced, config, user_id)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
       RETURNING *`,
      [
        source.name,
        source.type,
        source.status,
        source.document_count,
        source.chunk_count,
        source.last_synced,
        JSON.stringify(source.config),
        source.user_id,
      ]
    );
    return result.rows[0];
  }

  async updateRAGSource(id: string, updates: Partial<RAGSource>): Promise<RAGSource> {
    if (!this.client) throw new Error('Not connected');
    const setClauses: string[] = [];
    const values: unknown[] = [];
    let paramIndex = 1;

    if (updates.name !== undefined) {
      setClauses.push(`name = $${paramIndex++}`);
      values.push(updates.name);
    }
    if (updates.type !== undefined) {
      setClauses.push(`type = $${paramIndex++}`);
      values.push(updates.type);
    }
    if (updates.status !== undefined) {
      setClauses.push(`status = $${paramIndex++}`);
      values.push(updates.status);
    }
    if (updates.document_count !== undefined) {
      setClauses.push(`document_count = $${paramIndex++}`);
      values.push(updates.document_count);
    }
    if (updates.chunk_count !== undefined) {
      setClauses.push(`chunk_count = $${paramIndex++}`);
      values.push(updates.chunk_count);
    }
    if (updates.last_synced !== undefined) {
      setClauses.push(`last_synced = $${paramIndex++}`);
      values.push(updates.last_synced);
    }
    if (updates.config !== undefined) {
      setClauses.push(`config = $${paramIndex++}`);
      values.push(JSON.stringify(updates.config));
    }

    setClauses.push(`updated_at = NOW()`);
    values.push(id);

    const result = await this.client.query<RAGSource>(
      `UPDATE rag_sources SET ${setClauses.join(', ')} WHERE id = $${paramIndex} RETURNING *`,
      values
    );
    return result.rows[0];
  }

  async deleteRAGSource(id: string): Promise<void> {
    if (!this.client) throw new Error('Not connected');
    await this.client.query('DELETE FROM rag_sources WHERE id = $1', [id]);
  }

  // Usage
  async getUsage(userId: string, startDate: string, endDate: string): Promise<UsageRecord[]> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<UsageRecord>(
      'SELECT * FROM usage_records WHERE user_id = $1 AND date >= $2 AND date <= $3 ORDER BY date DESC',
      [userId, startDate, endDate]
    );
    return result.rows;
  }

  async recordUsage(usage: Omit<UsageRecord, 'id'>): Promise<UsageRecord> {
    if (!this.client) throw new Error('Not connected');
    const result = await this.client.query<UsageRecord>(
      `INSERT INTO usage_records (user_id, date, workflow_id, tokens_input, tokens_output, cost_usd, execution_count)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       RETURNING *`,
      [
        usage.user_id,
        usage.date,
        usage.workflow_id,
        usage.tokens_input,
        usage.tokens_output,
        usage.cost_usd,
        usage.execution_count,
      ]
    );
    return result.rows[0];
  }
}

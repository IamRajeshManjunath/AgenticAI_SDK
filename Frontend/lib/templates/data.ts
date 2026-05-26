export interface WorkflowTemplate {
  id: string
  name: string
  description: string
  category: string
  agentCount: number
  complexity: 'beginner' | 'intermediate' | 'advanced'
  workflow: Record<string, unknown>
}

const generateId = () => Math.random().toString(36).substring(2, 15)

export const templates: WorkflowTemplate[] = [
  {
    id: 'customer-support-bot',
    name: 'Customer Support Bot',
    description: 'A two-agent workflow that answers FAQs from a knowledge base and escalates complex issues to a human.',
    category: 'Customer Support',
    agentCount: 2,
    complexity: 'beginner',
    workflow: {
      workflow_id: generateId(),
      name: 'Customer Support Bot',
      description: 'Answers FAQs and escalates complex issues to human',
      entry_point: 'coordinator',
      agents: [
        { agent_id: 'coordinator', role: 'Support Coordinator', prompt_template: { template_string: 'You are a support coordinator. Route FAQ questions to the FAQ agent. Route complex issues to the escalation agent. {{input}}', input_variables: ['input'] }, llm: { provider: 'openai', model_name: 'gpt-4o', temperature: 0.3 }, topology: { orchestration_mode: 'model_driven' }, tools: [], rag_sources: [], sub_agents: ['faq_agent', 'escalation_agent'] },
        { agent_id: 'faq_agent', role: 'FAQ Assistant', prompt_template: { template_string: 'Answer the user question based on the knowledge base. If you cannot find the answer, respond with "ESCALATE". {{input}}', input_variables: ['input'] }, llm: { provider: 'openai', model_name: 'gpt-4o', temperature: 0.3 }, tools: [], rag_sources: ['kb_collection'], sub_agents: [] },
        { agent_id: 'escalation_agent', role: 'Escalation Handler', prompt_template: { template_string: 'A human agent will review this request. Prepare a clear summary of the issue. {{input}}', input_variables: ['input'] }, llm: { provider: 'openai', model_name: 'gpt-4o', temperature: 0.5 }, tools: [], rag_sources: [], sub_agents: [], interruption_point: true },
      ],
      edges: [
        { source: 'coordinator', target: 'faq_agent', condition: 'state["next_step"] == "faq"' },
        { source: 'coordinator', target: 'escalation_agent', condition: 'state["next_step"] == "escalate"' },
        { source: 'faq_agent', target: 'coordinator', condition: null },
        { source: 'escalation_agent', target: 'coordinator', condition: null },
      ],
      tools: [],
      rag_sources: [{ rag_id: 'kb_collection', provider: 'qdrant', collection_name: 'faq_knowledge_base', embedding_model: 'text-embedding-3-small', top_k: 3, similarity_threshold: 0.7, hybrid_search: true }],
    },
  },
  {
    id: 'research-pipeline',
    name: 'Research Pipeline',
    description: 'Searches the web, summarizes findings, and generates a structured report.',
    category: 'Research',
    agentCount: 3,
    complexity: 'intermediate',
    workflow: {
      workflow_id: generateId(),
      name: 'Research Pipeline',
      description: 'Web search → Summarization → Report generation',
      entry_point: 'researcher',
      agents: [
        { agent_id: 'researcher', role: 'Web Researcher', prompt_template: { template_string: 'Search for information about: {{input}}. Return key findings with sources.', input_variables: ['input'] }, llm: { provider: 'openai', model_name: 'gpt-4o', temperature: 0.5 }, tools: ['web_search'], rag_sources: [], sub_agents: [] },
        { agent_id: 'summarizer', role: 'Content Summarizer', prompt_template: { template_string: 'Summarize the following research findings into 3-5 key points: {{input}}', input_variables: ['input'] }, llm: { provider: 'openai', model_name: 'gpt-4o', temperature: 0.3 }, tools: [], rag_sources: [], sub_agents: [] },
        { agent_id: 'reporter', role: 'Report Generator', prompt_template: { template_string: 'Generate a well-structured report based on the summary. Include an executive summary, key findings, and recommendations. {{input}}', input_variables: ['input'] }, llm: { provider: 'openai', model_name: 'gpt-4o', temperature: 0.4 }, tools: [], rag_sources: [], sub_agents: [] },
      ],
      edges: [
        { source: 'researcher', target: 'summarizer', condition: null },
        { source: 'summarizer', target: 'reporter', condition: null },
      ],
      tools: [{ tool_id: 'web_search', name: 'Web Search', description: 'Search the web for current information', type: 'api' }],
      rag_sources: [],
    },
  },
  {
    id: 'content-review-workflow',
    name: 'Content Review with HITL',
    description: 'Generates content, checks for policy compliance, and requires human approval before publishing.',
    category: 'Content',
    agentCount: 3,
    complexity: 'advanced',
    workflow: {
      workflow_id: generateId(),
      name: 'Content Review Pipeline',
      description: 'Content generation → Policy check → Human approval → Publish',
      entry_point: 'writer',
      agents: [
        { agent_id: 'writer', role: 'Content Writer', prompt_template: { template_string: 'Write content based on: {{input}}. Follow brand guidelines and use a professional tone.', input_variables: ['input'] }, llm: { provider: 'openai', model_name: 'gpt-4o', temperature: 0.7 }, tools: [], rag_sources: ['brand_guidelines'], sub_agents: [] },
        { agent_id: 'reviewer', role: 'Policy Reviewer', prompt_template: { template_string: 'Check this content for policy compliance. Flag any issues: {{input}}', input_variables: ['input'] }, llm: { provider: 'openai', model_name: 'gpt-4o', temperature: 0.2 }, tools: [], rag_sources: ['policy_docs'], sub_agents: [] },
        { agent_id: 'approver', role: 'Human Approver', prompt_template: { template_string: 'Review the content and approve or reject. {{input}}', input_variables: ['input'] }, llm: { provider: 'openai', model_name: 'gpt-4o', temperature: 0.3 }, tools: [], rag_sources: [], sub_agents: [], interruption_point: true },
      ],
      edges: [
        { source: 'writer', target: 'reviewer', condition: null },
        { source: 'reviewer', target: 'approver', condition: 'state["next_step"] == "approve"' },
        { source: 'reviewer', target: 'writer', condition: 'state["next_step"] == "revise"' },
      ],
      tools: [],
      rag_sources: [
        { rag_id: 'brand_guidelines', provider: 'qdrant', collection_name: 'brand_guidelines', embedding_model: 'text-embedding-3-small', top_k: 5, similarity_threshold: 0.7, hybrid_search: true },
        { rag_id: 'policy_docs', provider: 'qdrant', collection_name: 'policy_documents', embedding_model: 'text-embedding-3-small', top_k: 5, similarity_threshold: 0.8, hybrid_search: true },
      ],
    },
  },
  {
    id: 'sentiment-monitor',
    name: 'Social Media Sentiment Monitor',
    description: 'Monitors social media mentions, analyzes sentiment, and generates weekly reports.',
    category: 'Monitoring',
    agentCount: 2,
    complexity: 'intermediate',
    workflow: {
      workflow_id: generateId(),
      name: 'Sentiment Monitor',
      description: 'Monitors social sentiment and generates reports',
      entry_point: 'monitor',
      agents: [
        { agent_id: 'monitor', role: 'Sentiment Analyzer', prompt_template: { template_string: 'Analyze the sentiment of these social media mentions. Classify each as positive, negative, or neutral. {{input}}', input_variables: ['input'] }, llm: { provider: 'openai', model_name: 'gpt-4o', temperature: 0.3 }, tools: ['social_listener'], rag_sources: [], sub_agents: [] },
        { agent_id: 'reporter', role: 'Report Generator', prompt_template: { template_string: 'Generate a weekly sentiment report with trends, top mentions, and recommendations. {{input}}', input_variables: ['input'] }, llm: { provider: 'openai', model_name: 'gpt-4o', temperature: 0.5 }, tools: [], rag_sources: [], sub_agents: [] },
      ],
      edges: [
        { source: 'monitor', target: 'reporter', condition: null },
      ],
      tools: [{ tool_id: 'social_listener', name: 'Social Media Listener', description: 'Fetch recent social media mentions', type: 'api' }],
      rag_sources: [],
    },
  },
]

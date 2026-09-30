import { NextRequest, NextResponse } from "next/server";

const MOCK_PLUGINS: Record<string, any> = {
  openai: {
    type: "chat_model",
    provider: "openai",
    name: "OpenAI",
    description: "OpenAI chat models (GPT-4o, GPT-4, GPT-3.5)",
    package_name: "langchain-openai",
    version: "0.3.0",
    features: { stream: true, tools: true, structured_output: true, multimodal: true },
    docs_url: "https://docs.langchain.com/oss/python/integrations/chat/openai",
    downloads_per_month: 64000000,
    tags: ["openai", "gpt", "chat", "multimodal"],
    installed: true,
    config_schema: {
      type: "object",
      properties: {
        api_key: { type: "string", format: "password", description: "OpenAI API Key" },
        model: { type: "string", enum: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"], default: "gpt-4o" },
        temperature: { type: "number", minimum: 0, maximum: 2, default: 0.7 },
        max_tokens: { type: "integer" },
        organization: { type: "string" },
      },
      required: ["api_key"],
    },
    current_config: {
      model: "gpt-4o",
      temperature: 0.7,
      organization: "org-123",
    },
  },
  anthropic: {
    type: "chat_model",
    provider: "anthropic",
    name: "Anthropic",
    description: "Anthropic chat models (Claude 3.5 Sonnet, Claude 3 Opus)",
    package_name: "langchain-anthropic",
    version: "0.3.0",
    features: { stream: true, tools: true, structured_output: true, multimodal: true },
    docs_url: "https://docs.langchain.com/oss/python/integrations/chat/anthropic",
    downloads_per_month: 22000000,
    tags: ["anthropic", "claude", "chat", "multimodal"],
    installed: true,
    config_schema: {
      type: "object",
      properties: {
        api_key: { type: "string", format: "password", description: "Anthropic API Key" },
        model: { type: "string", enum: ["claude-3.5-sonnet", "claude-3-opus", "claude-3-haiku"], default: "claude-3.5-sonnet" },
        temperature: { type: "number", minimum: 0, maximum: 1, default: 0.7 },
        max_tokens: { type: "integer" },
      },
      required: ["api_key"],
    },
    current_config: {
      model: "claude-3.5-sonnet",
      temperature: 0.7,
    },
  },
  tavily: {
    type: "tool",
    provider: "tavily",
    name: "Tavily Search",
    description: "Tavily AI-powered search API",
    package_name: "langchain-tavily",
    version: "0.3.0",
    features: { stream: false, tools: true, structured_output: true, multimodal: false },
    docs_url: "https://docs.langchain.com/oss/python/integrations/tools/tavily_search",
    downloads_per_month: 645000,
    tags: ["tavily", "search", "web", "research"],
    installed: true,
    config_schema: {
      type: "object",
      properties: {
        api_key: { type: "string", format: "password", description: "Tavily API Key" },
        max_results: { type: "integer", default: 5, minimum: 1, maximum: 20 },
        search_depth: { type: "string", enum: ["basic", "advanced"], default: "basic" },
        include_domains: { type: "array", items: { type: "string" } },
        exclude_domains: { type: "array", items: { type: "string" } },
      },
      required: ["api_key"],
    },
    current_config: {
      max_results: 5,
      search_depth: "basic",
    },
  },
};

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ provider: string }> }
) {
  const { provider } = await params;
  const plugin = MOCK_PLUGINS[provider];

  if (!plugin) {
    return NextResponse.json({ error: "Integration not found" }, { status: 404 });
  }

  return NextResponse.json(plugin);
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ provider: string }> }
) {
  const { provider } = await params;
  const plugin = MOCK_PLUGINS[provider];

  if (!plugin) {
    return NextResponse.json({ error: "Integration not found" }, { status: 404 });
  }

  try {
    const body = await request.json();
    const { config } = body;

    // In production, validate config against schema, encrypt credentials, update SDK
    plugin.current_config = { ...plugin.current_config, ...config };
    plugin.installed = true;

    return NextResponse.json({
      success: true,
      integration: plugin,
      updated_at: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ provider: string }> }
) {
  const { provider } = await params;
  const plugin = MOCK_PLUGINS[provider];

  if (!plugin) {
    return NextResponse.json({ error: "Integration not found" }, { status: 404 });
  }

  // In production, remove credentials, unregister from SDK
  plugin.installed = false;
  plugin.current_config = {};

  return NextResponse.json({
    success: true,
    message: `${plugin.name} uninstalled`,
    uninstalled_at: new Date().toISOString(),
  });
}
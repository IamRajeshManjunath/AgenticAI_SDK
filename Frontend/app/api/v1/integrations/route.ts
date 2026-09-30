import { NextRequest, NextResponse } from "next/server";

// Mock plugin registry - in production this would connect to the Python SDK
const MOCK_PLUGINS = [
  {
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
        api_key: { type: "string", format: "password" },
        model: { type: "string", enum: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"] },
        temperature: { type: "number", minimum: 0, maximum: 2, default: 0.7 },
        max_tokens: { type: "integer" },
      },
      required: ["api_key"],
    },
  },
  {
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
        api_key: { type: "string", format: "password" },
        model: { type: "string", enum: ["claude-3.5-sonnet", "claude-3-opus", "claude-3-haiku"] },
        temperature: { type: "number", minimum: 0, maximum: 1, default: 0.7 },
        max_tokens: { type: "integer" },
      },
      required: ["api_key"],
    },
  },
  {
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
        api_key: { type: "string", format: "password" },
        max_results: { type: "integer", default: 5 },
        search_depth: { type: "string", enum: ["basic", "advanced"], default: "basic" },
      },
      required: ["api_key"],
    },
  },
];

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get("type");
  const installed = searchParams.get("installed");
  const search = searchParams.get("search");

  let plugins = [...MOCK_PLUGINS];

  if (type && type !== "all") {
    plugins = plugins.filter(p => p.type === type);
  }

  if (installed === "true") {
    plugins = plugins.filter(p => p.installed);
  }

  if (search) {
    const query = search.toLowerCase();
    plugins = plugins.filter(p =>
      p.name.toLowerCase().includes(query) ||
      p.description.toLowerCase().includes(query) ||
      p.tags.some(t => t.toLowerCase().includes(query))
    );
  }

  return NextResponse.json({
    plugins,
    total: plugins.length,
    types: [...new Set(MOCK_PLUGINS.map(p => p.type))],
  });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { provider, config } = body;

    // In production, this would:
    // 1. Validate the config against the plugin's schema
    // 2. Store credentials securely (encrypted)
    // 3. Register the integration with the Python SDK
    // 4. Return the created integration config

    const plugin = MOCK_PLUGINS.find(p => p.provider === provider);
    if (!plugin) {
      return NextResponse.json({ error: "Plugin not found" }, { status: 404 });
    }

    // Mock installation
    plugin.installed = true;

    return NextResponse.json({
      success: true,
      integration: {
        provider,
        config,
        installed_at: new Date().toISOString(),
      },
    });
  } catch (error) {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }
}
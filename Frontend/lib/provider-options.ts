'use client'

import { useEffect, useState } from 'react'
import { providerApi, type ChatModelProviderOption } from '@/lib/api'

const LEGACY_CHAT_MODEL_PROVIDERS: ChatModelProviderOption[] = [
  { provider: 'openai', name: 'OpenAI', description: '', type: 'chat_model', features: { stream: true, tools: true, structured_output: true, multimodal: true }, docs_url: '' },
  { provider: 'anthropic', name: 'Anthropic', description: '', type: 'chat_model', features: { stream: true, tools: true, structured_output: true, multimodal: true }, docs_url: '' },
  { provider: 'ollama', name: 'Ollama', description: '', type: 'chat_model', features: { stream: true, tools: true, structured_output: true, multimodal: false }, docs_url: '' },
]

export function useChatModelProviders() {
  const [providers, setProviders] = useState(LEGACY_CHAT_MODEL_PROVIDERS)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void providerApi.getChatModelProviders().then((result) => {
      if (!active) return
      if (result.error) {
        setError(`Could not load installed providers: ${result.error}`)
        return
      }
      const discovered = result.data?.providers ?? []
      setProviders(discovered.length ? discovered : LEGACY_CHAT_MODEL_PROVIDERS)
    })
    return () => {
      active = false
    }
  }, [])

  return { providers, error }
}

export function providersWithCurrent(
  providers: ChatModelProviderOption[],
  currentProvider: string,
): ChatModelProviderOption[] {
  if (!currentProvider || providers.some(({ provider }) => provider === currentProvider)) return providers
  return [
    {
      provider: currentProvider,
      name: `${currentProvider} (not currently installed)`,
      description: '',
      type: 'chat_model',
      features: { stream: false, tools: false, structured_output: false, multimodal: false },
      docs_url: '',
    },
    ...providers,
  ]
}

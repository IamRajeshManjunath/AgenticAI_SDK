'use client'

import { useEffect, useRef, useState } from 'react'
import dynamic from 'next/dynamic'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Download, Save, RefreshCw, Eye, CheckCircle2, AlertCircle, AlertTriangle, Info, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { useWorkflowStore } from '@/lib/store'
import { cn } from '@/lib/utils'

// Dynamically import Monaco Editor to avoid SSR issues
const Editor = dynamic(() => import('@monaco-editor/react').then(mod => mod.Editor), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-[500px]">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )
})

interface ValidationError {
  path: string
  message: string
}

export default function ConfigEditor() {
  const [config, setConfig] = useState<string>('')
  const [schema, setSchema] = useState<any>(null)
  const [errors, setErrors] = useState<ValidationError[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isValidating, setIsValidating] = useState(false)
  const [activeTab, setActiveTab] = useState<'editor' | 'schema' | 'diff'>('editor')
  const [showDiff, setShowDiff] = useState(false)
  const [lastSaved, setLastSaved] = useState<string | null>(null)
  const editorRef = useRef<any>(null)
  const [originalConfig, setOriginalConfig] = useState<string>('')

  const { token } = useAuthStore()

  useEffect(() => {
    loadConfig()
    loadSchema()
  }, [])

  const loadConfig = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/config`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        const configStr = JSON.stringify(data, null, 2)
        setConfig(configStr)
        setOriginalConfig(configStr)
      }
    } catch (error) {
      console.error('Failed to load config:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const loadSchema = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/config/schema`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setSchema(data)
      }
    } catch (error) {
      console.error('Failed to load schema:', error)
    }
  }

  const validateConfig = async (configStr: string) => {
    setIsValidating(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/config/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify({ config: JSON.parse(configStr) }),
      })
      if (response.ok) {
        const data = await response.json()
        setErrors(data.errors || [])
      } else {
        const data = await response.json()
        setErrors(data.errors || [{ path: '', message: data.detail || 'Validation failed' }])
      }
    } catch (error) {
      setErrors([{ path: '', message: error instanceof Error ? error.message : 'Validation failed' }])
    } finally {
      setIsValidating(false)
    }
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      const configObj = JSON.parse(config)
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/config`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify(configObj),
      })
      if (response.ok) {
        const data = await response.json()
        setOriginalConfig(config)
        setLastSaved(new Date().toISOString())
        alert('Configuration saved successfully!')
      } else {
        const data = await response.json()
        alert(`Failed to save: ${data.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to save: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsSaving(false)
    }
  }

  const handleFormat = () => {
    try {
      const parsed = JSON.parse(config)
      const formatted = JSON.stringify(parsed, null, 2)
      setConfig(formatted)
    } catch (error) {
      alert(`Invalid JSON: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const handleDownload = () => {
    const blob = new Blob([config], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'agenticai-config.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string
        const parsed = JSON.parse(content)
        setConfig(JSON.stringify(parsed, null, 2))
      } catch (error) {
        alert(`Invalid JSON file: ${error instanceof Error ? error.message : 'Unknown error'}`)
      }
    }
    reader.readAsText(file)
  }

  const validateJson = (jsonStr: string): { valid: boolean; error?: string } => {
    try {
      JSON.parse(jsonStr)
      return { valid: true }
    } catch (error) {
      return { valid: false, error: error instanceof Error ? error.message : 'Invalid JSON' }
    }
  }

  const handleEditorChange = (value: string | undefined) => {
    if (value !== undefined) {
      setConfig(value)
      // Debounced validation
      const validation = validateJson(value)
      if (!validation.valid) {
        setErrors([{ path: '', message: validation.error || 'Invalid JSON' }])
      }
    }
  }

  const hasUnsavedChanges = config !== originalConfig
  const validation = validateJson(config)

  const configErrors = errors.filter(e => e.path !== '')
  const jsonError = validation.valid ? null : validation.error

  const errorCount = (jsonError ? 1 : 0) + configErrors.length
  const warningCount = 0 // Could add warnings later

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold">Configuration Editor</h1>
          <p className="text-muted-foreground mt-1">Edit and validate AgenticAI configuration with real-time JSON schema validation</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleFormat} disabled={isSaving}>
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V6a2 2 0 00-2-2h-2" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 2H6a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-2" />
            </svg>
            Format
          </Button>
          <Button variant="outline" onClick={handleDownload} disabled={isSaving}>
            <Download className="w-4 h-4 mr-2" />
            Download
          </Button>
          <input
            type="file"
            accept=".json"
            onChange={handleFileUpload}
            className="hidden"
            id="config-upload"
            ref={(el) => { if (el) el.style.display = 'none' }}
          />
          <Button variant="outline" onClick={() => document.getElementById('config-upload')?.click()}>
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Upload
          </Button>
          <Button
            onClick={handleSave}
            disabled={isSaving || isValidating || !validation.valid || errorCount > 0}
            className="glow-primary-sm"
          >
            <Save className="w-4 h-4 mr-2" />
            {isSaving ? (
              <>
                <span className="animate-spin mr-2">
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                </span>
                Saving...
              </> : (
                'Save'
              )}
          </Button>
        </div>
      </div>

      {/* Status Bar */}
      <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1">
            {jsonError ? (
              <AlertCircle className="w-4 h-4 text-destructive" />
            ) : validation.valid ? (
              <CheckCircle2 className="w-4 h-4 text-green-500" />
            ) : (
              <AlertCircle className="w-4 h-4 text-yellow-500" />
            )}
            <span className="text-sm font-medium">
              {jsonError ? 'Invalid JSON' : validation.valid ? 'Valid JSON' : 'Invalid JSON'}
            </span>
            {errorCount > 0 && (
              <>
                <AlertTriangle className="w-4 h-4 text-yellow-500 ml-2" />
                <span className="text-sm">{errorCount} schema error{errorCount > 1 ? 's' : ''}</span>
              </>
            )}
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            {lastSaved && <span>Last saved: {new Date(lastSaved).toLocaleTimeString()}</span>}
            {hasUnsavedChanges && (
              <span className="text-yellow-500">● Unsaved changes</span>
            )}
          </div>
        </div>

        {/* Validation Errors Panel */}
        {(jsonError || configErrors.length > 0) && (
          <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
            <h4 className="font-medium text-destructive mb-2 flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              Validation Errors ({errorCount})
            </h4>
            {jsonError && (
              <div className="mb-2 p-2 bg-destructive/5 rounded text-sm font-mono text-destructive">
                {jsonError}
              </div>
            )}
            {configErrors.map((error, index) => (
              <div key={index} className="p-2 bg-destructive/5 rounded text-sm font-mono text-destructive">
                <div className="text-xs text-muted-foreground">{error.path || 'root'}</div>
                <div>{error.message}</div>
              </div>
            ))}
          </div>
        )}

        {/* Tabs */}
        <Tabs defaultValue="editor" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="editor">Editor</TabsTrigger>
            <TabsTrigger value="schema">Schema</TabsTrigger>
            <TabsTrigger value="diff">Diff</TabsTrigger>
          </TabsList>

          <TabsContent value="editor" className="mt-4 h-[600px]">
            <div className="h-full border border-border rounded-lg overflow-hidden">
              <Editor
                ref={editorRef}
                height="100%"
                language="json"
                theme="vs-dark"
                value={config}
                onChange={handleEditorChange}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  lineNumbers: 'on',
                  wordWrap: 'on',
                  tabSize: 2,
                  formatOnPaste: true,
                  formatOnType: true,
                  autoIndent: 'full',
                  bracketPairColorization: { enabled: true },
                  guides: { bracketPairs: true },
                  renderLineHighlight: 'all',
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                }}
              />
            </div>
          </TabsContent>

          <TabsContent value="schema" className="mt-4 h-[600px]">
            <div className="h-[600px] border border-border rounded-lg overflow-hidden">
              {schema ? (
                <Editor
                  height="100%"
                  language="json"
                  theme="vs-dark"
                  value={JSON.stringify(schema, null, 2)}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 12,
                    lineNumbers: 'on',
                    wordWrap: 'on',
                    tabSize: 2,
                    readOnly: true,
                  }}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">
                  No schema loaded
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="diff" className="mt-4 h-[600px]">
            <div className="h-[600px] border border-border rounded-lg overflow-hidden">
              {hasUnsavedChanges ? (
                <div className="h-full flex">
                  <div className="flex-1 border-r border-border overflow-auto p-4 bg-destructive/5">
                    <h4 className="font-medium mb-2 text-destructive">Original</h4>
                    <pre className="font-mono text-sm text-muted-foreground whitespace-pre-wrap overflow-auto h-[calc(100%-40px)]">
                      {originalConfig}
                    </pre>
                  </div>
                  <div className="flex-1 overflow-auto p-4 bg-green-50/50">
                    <h4 className="font-medium mb-2 text-green-600">Modified</h4>
                    <pre className="font-mono text-sm whitespace-pre-wrap overflow-auto h-[calc(100%-40px)]">
                      {config}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">
                  No unsaved changes to diff
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

export default ConfigEditor
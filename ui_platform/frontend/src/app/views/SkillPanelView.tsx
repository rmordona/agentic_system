import React, { useState, useEffect } from 'react'
import ReactDOM from 'react-dom'
import { X, FileText, FileCode, Layers, Trash, Plus, Edit, Check } from 'lucide-react'
import SkillControlPanel from './SkillControlPanel'
import UIFormFactory from '../../components/form/UIFormFactory'
import { AgentSkillSchema } from '@/api/types/agent_skill'
import { AgentContextSchema } from '@/api/types/agent_context'

interface SkillPanelViewProps {
  skillName: string
  prompt: string
  skillJson: string | Record<string, any>
  contextJson: string | Record<string, any>
  onClose: () => void
  onSave: (updatedText: string, type: 'prompt' | 'skill' | 'context') => void
}

type PanelType = 'prompt' | 'skill' | 'context'

interface NestedEditorState {
  key: string
  data: Record<string, any>
  open: boolean
}

interface FloatingContextState {
  key: string
  data: Record<string, any>
  position: { top: number; left: number }
}

const SkillPanelView: React.FC<SkillPanelViewProps> = ({
  skillName,
  prompt,
  skillJson,
  contextJson,
  onClose,
  onSave,
}) => {
  const [activePanel, setActivePanel] = useState<PanelType>('prompt')
  const [text, setText] = useState('')
  const [formData, setFormData] = useState<any>(null)
  const [jsonError, setJsonError] = useState<string | null>(null)
  const [nestedEditor, setNestedEditor] = useState<NestedEditorState | null>(null)
  const [floatingContext, setFloatingContext] = useState<FloatingContextState | null>(null)
  const [isEditingPrompt, setIsEditingPrompt] = useState(false)

  const formatJson = (json: string | Record<string, any>) => {
    if (!json) return ''
    try {
      const obj = typeof json === 'string' ? JSON.parse(json) : json
      return JSON.stringify(obj, null, 2)
    } catch {
      return typeof json === 'string' ? json : JSON.stringify(json)
    }
  }

  const parseJsonToForm = (jsonStr: string | Record<string, any>, type?: PanelType) => {
    let obj: any
    try {
      obj = typeof jsonStr === 'string' ? JSON.parse(jsonStr) : jsonStr
    } catch {
      setJsonError('Invalid JSON')
      setFormData(null)
      return
    }

    if (Array.isArray(obj)) {
      setFormData({ __isArray: true, items: obj })
      setJsonError(null)
      return
    }

    try {
      if (type === 'skill') AgentSkillSchema.parse(obj)
      if (type === 'context') AgentContextSchema.parse(obj)
      setJsonError(null)
    } catch (err: any) {
      setJsonError(err.message)
    }

    setFormData({ ...obj })
  }

  const switchPanel = (panel: PanelType) => {
    setActivePanel(panel)
    setIsEditingPrompt(false)

    if (panel === 'prompt') {
      const promptText = prompt ? prompt.replace(/^["']|["']$/g, '').replace(/\\n/g, '\n') : ''
      setText(promptText)
      parseJsonToForm(contextJson, 'context')
    } else if (panel === 'skill') {
      const skillText = formatJson(skillJson)
      setText(skillText)
      parseJsonToForm(skillText, 'skill')
    } else if (panel === 'context') {
      const contextText = formatJson(contextJson)
      setText(contextText)
      parseJsonToForm(contextText, 'context')
    }
  }

  useEffect(() => {
    if (activePanel === 'skill' || activePanel === 'context') {
      parseJsonToForm(text, activePanel)
    } else if (activePanel === 'prompt') {
      parseJsonToForm(contextJson, 'context')
    }
  }, [text, activePanel])

  // -------------------------
  // Handle clickable {key} in prompt
  // -------------------------
  const renderPromptWithContext = () => {
    if (!text) return null
    const regex = /\{([^{}]+)\}/g
    const parts: React.ReactNode[] = []
    let lastIndex = 0
    let match: RegExpExecArray | null

    while ((match = regex.exec(text)) !== null) {
      const start = match.index
      const end = regex.lastIndex
      const key = match[1].trim()

      if (start > lastIndex) {
        parts.push(<span key={lastIndex}>{text.slice(lastIndex, start)}</span>)
      }

      parts.push(
        <span
          key={start}
          className="cursor-pointer text-green-400 hover:underline"
          onClick={(e) => {
            const obj = formData?.[key] || {}
            const rect = (e.target as HTMLElement).getBoundingClientRect()
            setFloatingContext({
              key,
              data: { ...obj },
              position: { top: rect.bottom + window.scrollY, left: rect.left + window.scrollX },
            })
          }}
        >
          {text.slice(start, end)}
        </span>
      )

      lastIndex = end
    }

    if (lastIndex < text.length) {
      parts.push(<span key={lastIndex}>{text.slice(lastIndex)}</span>)
    }

    return parts
  }

  return ReactDOM.createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="bg-gray-900 shadow-2xl w-full max-w-7xl h-[70vh] flex flex-col overflow-hidden border border-gray-1000 rounded-3xl">
        {/* Topbar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700 bg-gray-800 rounded-t-3xl">
          <h2 className="text-lg font-semibold text-gray-100">{skillName}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-100 transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="flex flex-1 overflow-hidden">
          <SkillControlPanel
            activePanel={activePanel}
            formData={formData}
            setFormData={setFormData}
            switchPanel={switchPanel}
            openNestedEditor={(key, data) => setNestedEditor({ key, data, open: true })}
            text={text}
            onSave={() => {
              onSave(text, activePanel)
              setIsEditingPrompt(false)
            }}
            jsonError={jsonError}
          />

          {activePanel === 'prompt' ? (
            <div className="flex-1 flex flex-col p-3 overflow-auto">
              <div className="flex items-center justify-between mb-2">
                <div className="flex space-x-2">
                  {['prompt.md', 'plan.md', 'spec.md'].map((file) => (
                    <button
                      key={file}
                      className="px-2 py-1 bg-gray-700 text-gray-200 rounded text-xs"
                    >
                      {file}
                    </button>
                  ))}
                </div>

                <button
                  onClick={() => setIsEditingPrompt((v) => !v)}
                  className="flex items-center space-x-1 px-2 py-1 bg-gray-700 hover:bg-green-600 text-xs rounded"
                >
                  {isEditingPrompt ? <Check size={14} /> : <Edit size={14} />}
                  <span>{isEditingPrompt ? 'Done' : 'Edit'}</span>
                </button>
              </div>

              {isEditingPrompt ? (
                <textarea
                  className="flex-1 resize-none bg-gray-900 p-2 text-gray-200 text-sm leading-relaxed outline-none"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                />
              ) : (
                <div className="flex-1 bg-gray-900 p-2 overflow-auto text-sm leading-relaxed text-gray-200 whitespace-pre-wrap break-words">
                  {renderPromptWithContext()}
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 p-3 overflow-hidden">
              <textarea
                className="w-full h-full resize-none bg-gray-900 text-gray-200 text-sm"
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
            </div>
          )}
        </div>

        {/* ✅ FLOATING CONTEXT PANEL (RESTORED) */}
        {floatingContext && (
          <div
            className="absolute z-50 bg-gray-800 p-3 rounded-lg shadow-lg"
            style={{
              top: floatingContext.position.top,
              left: floatingContext.position.left,
              minWidth: 300,
            }}
          >
            <div className="flex justify-between items-center mb-2">
              <span className="text-gray-200 text-sm">{floatingContext.key}</span>
              <button
                className="text-gray-400 hover:text-gray-200"
                onClick={() => setFloatingContext(null)}
              >
                <X size={16} />
              </button>
            </div>

            <UIFormFactory
              value={floatingContext.data}
              onChange={(updated) => {
                if (!formData) return
                setFormData({ ...formData, [floatingContext.key]: updated })
                setFloatingContext({ ...floatingContext, data: updated })
              }}
            />
          </div>
        )}
      </div>
    </div>,
    document.body
  )
}

export default SkillPanelView

import React, { useState, useEffect } from 'react'
import ReactDOM from 'react-dom'
import { X, FileText, FileCode, Layers, Plus, Trash } from 'lucide-react'
import { z } from 'zod'
import { AgentSkillSchema } from '@/api/types/agent_skill'
import { AgentContextSchema } from '@/api/types/agent_context'

interface SkillPromptPanelProps {
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

const SkillPromptPanel: React.FC<SkillPromptPanelProps> = ({
  skillName,
  prompt,
  skillJson,
  contextJson,
  onClose,
  onSave,
}) => {
  const [activePanel, setActivePanel] = useState<PanelType>('prompt')
  const [text, setText] = useState('')
  const [formData, setFormData] = useState<Record<string, any> | null>(null)
  const [jsonError, setJsonError] = useState<string | null>(null)
  const [nestedEditor, setNestedEditor] = useState<NestedEditorState | null>(null)

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

    // Handle root arrays as sections
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

    setFormData(obj)
  }

  const switchPanel = (panel: PanelType) => {
    setActivePanel(panel)

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

  const updateField = (key: string, value: any) => {
    if (!formData) return
    const updated = { ...formData, [key]: value }
    setFormData(updated)
  }

  const addArrayItem = (key: string) => {
    if (!formData) return
    const arr = formData[key] || []
    const updated = { ...formData, [key]: [...arr, ''] }
    setFormData(updated)
  }

  const updateArrayItem = (key: string, index: number, value: any) => {
    if (!formData) return
    const arr = [...(formData[key] || [])]
    arr[index] = value
    const updated = { ...formData, [key]: arr }
    setFormData(updated)
  }

  const removeArrayItem = (key: string, index: number) => {
    if (!formData) return
    const arr = [...(formData[key] || [])]
    arr.splice(index, 1)
    const updated = { ...formData, [key]: arr }
    setFormData(updated)
  }

  const openNestedEditor = (key: string, data: Record<string, any>) => {
    setNestedEditor({ key, data: { ...data }, open: true })
  }

  const updateNestedField = (nestedKey: string, value: any) => {
    if (!nestedEditor) return
    const updated = { ...nestedEditor.data, [nestedKey]: value }
    setNestedEditor({ ...nestedEditor, data: updated })
  }

  const addNestedArrayItem = (nestedKey: string) => {
    if (!nestedEditor) return
    const arr = nestedEditor.data[nestedKey] || []
    const updated = { ...nestedEditor.data, [nestedKey]: [...arr, ''] }
    setNestedEditor({ ...nestedEditor, data: updated })
  }

  const removeNestedArrayItem = (nestedKey: string, index: number) => {
    if (!nestedEditor) return
    const arr = [...(nestedEditor.data[nestedKey] || [])]
    arr.splice(index, 1)
    const updated = { ...nestedEditor.data, [nestedKey]: arr }
    setNestedEditor({ ...nestedEditor, data: updated })
  }

  const saveNestedEditor = () => {
    if (!nestedEditor || !formData) return

    // Handle editing of section titles
    const keyParts = nestedEditor.key.split('_')
    if ((formData as any).__isArray && !isNaN(Number(keyParts[0]))) {
      const idx = Number(keyParts[0])
      if (keyParts[1] === 'name') {
        const newItems = [...(formData as any).items]
        newItems[idx].name = nestedEditor.data.name
        setFormData({ ...formData, items: newItems })
      } else {
        const newItems = [...(formData as any).items]
        newItems[idx][keyParts[1]] = nestedEditor.data
        setFormData({ ...formData, items: newItems })
      }
    } else {
      const updated = { ...formData, [nestedEditor.key]: nestedEditor.data }
      setFormData(updated)
    }

    setNestedEditor(null)
  }

  const renderForm = () => {
    if (!formData) return <div className="text-red-400 text-xs">{jsonError || 'Invalid JSON'}</div>

    // Render array of sections
    if ((formData as any).__isArray) {
      return (
        <div className="flex-1 overflow-y-auto text-xs space-y-3">
          {(formData as any).items.map((item: any, idx: number) => (
            <div key={idx} className="border-b border-gray-700 pb-2">
              {/* Section title */}
              <div
                className="bg-gray-700 text-gray-200 px-2 py-1 rounded-sm mb-1 cursor-pointer"
                onClick={() => openNestedEditor(`${idx}_name`, { name: item.name || `Section ${idx + 1}` })}
              >
                {item.name || `Section ${idx + 1}`}
              </div>

              {/* Render fields */}
              {Object.keys(item).map((key) => {
                if (key === 'name') return null
                const value = item[key]
                if (Array.isArray(value)) {
                  return (
                    <div key={key} className="mb-2">
                      <label className="text-gray-300 font-semibold text-xs">{key}</label>
                      {value.map((v: any, i: number) => (
                        <div key={i} className="flex items-center space-x-1 mb-1">
                          <input
                            type="text"
                            className="flex-1 p-1 text-gray-200 bg-gray-700 rounded text-xs"
                            value={v}
                            onChange={(e) => {
                              const arr = [...value]
                              arr[i] = e.target.value
                              const newItems = [...(formData as any).items]
                              newItems[idx][key] = arr
                              setFormData({ ...formData, items: newItems })
                            }}
                          />
                          <button
                            onClick={() => {
                              const arr = [...value]
                              arr.splice(i, 1)
                              const newItems = [...(formData as any).items]
                              newItems[idx][key] = arr
                              setFormData({ ...formData, items: newItems })
                            }}
                          >
                            <Trash size={14} className="text-red-500" />
                          </button>
                        </div>
                      ))}
                      <button
                        onClick={() => {
                          const newItems = [...(formData as any).items]
                          newItems[idx][key] = [...value, '']
                          setFormData({ ...formData, items: newItems })
                        }}
                        className="flex items-center space-x-1 text-xs text-green-400"
                      >
                        <Plus size={12} /> Add
                      </button>
                    </div>
                  )
                } else if (typeof value === 'object' && value !== null) {
                  return (
                    <div key={key} className="mb-2">
                      <label className="text-gray-300 font-semibold text-xs">{key}</label>
                      <button
                        onClick={() => openNestedEditor(`${idx}_${key}`, value)}
                        className="px-1 py-1 text-xs bg-gray-700 rounded text-gray-200 mt-1"
                      >
                        Edit Nested
                      </button>
                    </div>
                  )
                }
                return (
                  <div key={key} className="mb-2">
                    <label className="text-gray-300 font-semibold text-xs">{key}</label>
                    <input
                      type="text"
                      className="w-full p-1 text-gray-200 bg-gray-700 rounded text-xs"
                      value={value}
                      onChange={(e) => {
                        const newItems = [...(formData as any).items]
                        newItems[idx][key] = e.target.value
                        setFormData({ ...formData, items: newItems })
                      }}
                    />
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      )
    }

    // Default object form rendering (skillJson or object context)
    return (
      <div className="flex-1 overflow-y-auto text-xs">
        {Object.keys(formData).map((key) => {
          const value = formData[key]
          if (Array.isArray(value)) {
            return (
              <div key={key} className="mb-2">
                <label className="text-gray-300 font-semibold text-xs">{key}</label>
                {value.map((item, idx) => (
                  <div key={idx} className="flex items-center space-x-1 mb-1">
                    <input
                      type="text"
                      className="flex-1 p-1 text-gray-200 bg-gray-700 rounded text-xs"
                      value={item}
                      onChange={(e) => updateArrayItem(key, idx, e.target.value)}
                    />
                    <button onClick={() => removeArrayItem(key, idx)}>
                      <Trash size={14} className="text-red-500" />
                    </button>
                  </div>
                ))}
                <button
                  onClick={() => addArrayItem(key)}
                  className="flex items-center space-x-1 text-xs text-green-400"
                >
                  <Plus size={12} /> Add
                </button>
              </div>
            )
          } else if (typeof value === 'object' && value !== null) {
            return (
              <div key={key} className="mb-2">
                <label className="text-gray-300 font-semibold text-xs">{key}</label>
                <button
                  onClick={() => openNestedEditor(key, value)}
                  className="px-1 py-1 text-xs bg-gray-700 rounded text-gray-200 mt-1"
                >
                  Edit Nested
                </button>
              </div>
            )
          }
          return (
            <div key={key} className="mb-2">
              <label className="text-gray-300 font-semibold text-xs">{key}</label>
              <input
                type="text"
                className="w-full p-1 text-gray-200 bg-gray-700 rounded text-xs"
                value={value}
                onChange={(e) => updateField(key, e.target.value)}
              />
            </div>
          )
        })}
      </div>
    )
  }

  return ReactDOM.createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="bg-gray-900 shadow-2xl w-full max-w-5xl h-[70vh] flex flex-col overflow-hidden border border-gray-800 rounded-3xl">
        {/* Topbar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700 bg-gray-800 rounded-t-3xl">
          <h2 className="text-lg font-semibold text-gray-100">{skillName}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-100 transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left: Control panel */}
          <div className="w-[250px] bg-gray-800 border-r border-gray-700 p-3 flex flex-col text-xs">
            <div className="flex justify-end space-x-2 mb-3">
              <button
                className={`p-1 ${activePanel === 'prompt' ? 'bg-gray-700 rounded' : ''}`}
                onClick={() => switchPanel('prompt')}
                title="Prompt.md"
              >
                <FileText size={14} className="text-gray-200" />
              </button>
              <button
                className={`p-1 ${activePanel === 'skill' ? 'bg-gray-700 rounded' : ''}`}
                onClick={() => switchPanel('skill')}
                title="Skill.json"
              >
                <FileCode size={14} className="text-gray-200" />
              </button>
              <button
                className={`p-1 ${activePanel === 'context' ? 'bg-gray-700 rounded' : ''}`}
                onClick={() => switchPanel('context')}
                title="Context.json"
              >
                <Layers size={14} className="text-gray-200" />
              </button>
            </div>

            {renderForm()}

            <div className="mt-auto">
              <button
                onClick={() => onSave(text, activePanel)}
                className="w-full py-1 bg-green-600 hover:bg-green-700 text-white rounded text-xs transition-colors"
              >
                Save
              </button>
            </div>
          </div>

          {/* Right: Editable textarea */}
          <div className="flex-1 p-3 overflow-y-auto">
            <textarea
              className="w-full h-full resize-none bg-gray-900 text-gray-200 leading-relaxed overflow-y-auto scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-900 outline-none text-sm"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </div>
        </div>

        {/* Nested floating editor */}
        {nestedEditor?.open && (
          <div className="absolute top-16 left-1/2 transform -translate-x-1/2 w-[400px] max-h-[60vh] bg-gray-800 p-3 rounded-2xl shadow-lg overflow-y-auto z-50 text-xs">
            <div className="flex justify-between mb-2">
              <h3 className="text-gray-100 font-semibold">{nestedEditor.key}</h3>
              <button
                onClick={() => setNestedEditor(null)}
                className="text-gray-400 hover:text-gray-100"
              >
                <X size={16} />
              </button>
            </div>
            {Object.keys(nestedEditor.data).map((k) => {
              const val = nestedEditor.data[k]
              if (Array.isArray(val)) {
                return (
                  <div key={k} className="mb-2">
                    <label className="text-gray-300 font-semibold">{k}</label>
                    {val.map((item, idx) => (
                      <div key={idx} className="flex items-center space-x-1 mb-1">
                        <input
                          type="text"
                          className="flex-1 p-1 text-gray-200 bg-gray-700 rounded text-xs"
                          value={item}
                          onChange={(e) => {
                            const arr = [...val]
                            arr[idx] = e.target.value
                            updateNestedField(k, arr)
                          }}
                        />
                        <button onClick={() => removeNestedArrayItem(k, idx)}>
                          <Trash size={14} className="text-red-500" />
                        </button>
                      </div>
                    ))}
                    <button
                      onClick={() => addNestedArrayItem(k)}
                      className="flex items-center space-x-1 text-xs text-green-400"
                    >
                      <Plus size={12} /> Add
                    </button>
                  </div>
                )
              }
              return (
                <div key={k} className="mb-2">
                  <label className="text-gray-300 font-semibold">{k}</label>
                  <input
                    type="text"
                    className="w-full p-1 text-gray-200 bg-gray-700 rounded text-xs"
                    value={val}
                    onChange={(e) => updateNestedField(k, e.target.value)}
                  />
                </div>
              )
            })}
            <button
              onClick={saveNestedEditor}
              className="mt-2 w-full py-1 bg-green-600 hover:bg-green-700 text-white rounded text-xs transition-colors"
            >
              Save Nested
            </button>
          </div>
        )}
      </div>
    </div>,
    document.body
  )
}

export default SkillPromptPanel

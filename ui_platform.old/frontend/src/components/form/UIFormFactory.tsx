import React, { useEffect, useState } from 'react'
import { Plus, Trash, X, Pencil } from 'lucide-react'
import { z } from 'zod'

/* ===========================
   Types
=========================== */

export type UISchema = {
  type: 'object'
  properties: Record<string, UISchemaField>
  required?: string[]
}

export type UISchemaField = {
  type: 'string' | 'number' | 'integer' | 'boolean' | 'array' | 'object'
  title?: string
  description?: string
  enum?: string[]
  items?: UISchemaField
  properties?: Record<string, UISchemaField>
  ui?: {
    widget?: 'radio'
    permission?: 'read' | 'write' | 'hidden'
    visibleIf?: {
      path: string
      equals: any
    }
    keyValue?: boolean
  }
}

/* ===========================
   Props
=========================== */

interface UIFormFactoryProps {
  schema: UISchema | Record<string, any>
  value: Record<string, any>
  onChange: (value: Record<string, any>) => void
  readOnly?: boolean
}

/* ===========================
   Utilities
=========================== */

const getAtPath = (obj: any, path: string) =>
  path.split('.').reduce((a, k) => a?.[k], obj)

const setAtPath = (obj: any, path: string, value: any) => {
  const clone = structuredClone(obj)
  const parts = path.split('.')
  let curr = clone
  parts.slice(0, -1).forEach((p) => (curr[p] ??= {}))
  curr[parts.at(-1)!] = value
  return clone
}

const isCollectionArray = (val: any) =>
  Array.isArray(val) && val.length > 0 && typeof val[0] === 'object' && 'name' in val[0]

const wrapAsSchema = (data: any): any => {
  if (data === null || data === undefined) return { type: 'object', properties: {} }
  if (Array.isArray(data)) {
    const first = data[0]
    if (typeof first === 'object' && first !== null) return { type: 'array', items: wrapAsSchema(first) }
    return { type: 'array', items: { type: typeof first === 'number' ? 'number' : 'string' } }
  }
  if (typeof data === 'object') return { type: 'object', properties: Object.fromEntries(Object.entries(data).map(([k, v]) => [k, wrapAsSchema(v)])) }
  if (typeof data === 'number') return { type: 'number' }
  if (typeof data === 'boolean') return { type: 'boolean' }
  return { type: 'string' }
}

const validateAgainstSchema = (schema: UISchema | UISchemaField, value: any, path = ''): string | null => {
  if (!schema) return null
  if (schema.type === 'array') {
    if (!Array.isArray(value)) return `${path || 'value'} must be an array`
    if (schema.items) for (let i = 0; i < value.length; i++) { const err = validateAgainstSchema(schema.items, value[i], `${path}[${i}]`); if (err) return err }
    return null
  }
  if (schema.type === 'object') {
    if (typeof value !== 'object' || value === null) return `${path || 'value'} must be an object`
    if (schema.properties) for (const [k, f] of Object.entries(schema.properties)) { const err = validateAgainstSchema(f, value[k], path ? `${path}.${k}` : k); if (err) return err }
    return null
  }
  if (schema.type === 'string' && typeof value !== 'string') return `${path || 'value'} must be a string`
  if ((schema.type === 'number' || schema.type === 'integer') && typeof value !== 'number') return `${path || 'value'} must be a number`
  if (schema.type === 'boolean' && typeof value !== 'boolean') return `${path || 'value'} must be a boolean`
  return null
}


/* ===========================
   Component
=========================== */

const UIFormFactory: React.FC<UIFormFactoryProps> = ({
  value,
  onChange,
  readOnly = false,
}) => {
  const [localValue, setLocalValue] = useState(value)
  const [error, setError] = useState<string | null>(null)
  const [kvEditor, setKvEditor] = useState<{
    path: string
    data: Record<string, string>
  } | null>(null)

  useEffect(() => setLocalValue(value), [value])

  const schema = wrapAsSchema(value)

  const validateAndCommit = (next: any) => {
    const err = validateAgainstSchema(schema, next)
    if (err) {
      setError(err)
      return
    }
    setError(null)
    setLocalValue(next)
    onChange(next)
  }

  /* ===========================
     Field Renderer
  =========================== */

  const renderField = (
    field: UISchemaField,
    path: string,
    val: any
  ) => {
    if (!field) return null
    if (field.ui?.permission === 'hidden') return null
    if (field.ui?.visibleIf) {
      const actual = getAtPath(localValue, field.ui.visibleIf.path)
      if (actual !== field.ui.visibleIf.equals) return null
    }
    const disabled = readOnly || field.ui?.permission === 'read'

    /* ---------- Primitive ---------- */
    if (['string', 'number', 'integer'].includes(field.type)) {
      if (field.enum || field.ui?.widget === 'radio') {
        return (
          <div className="space-y-1 text-[11px]" key={path}>
            <div className="text-gray-300 font-medium">{field.title ?? path}</div>
            <div className="flex gap-2 flex-wrap">
              {field.enum?.map(opt => (
                <label
                  key={opt}
                  className="flex items-center gap-2 text-gray-200 cursor-pointer hover:text-green-400 transition-colors duration-200"
                >
                  <input
                    type="radio"
                    disabled={disabled}
                    checked={val === opt}
                    onChange={() =>
                      validateAndCommit(setAtPath(localValue, path, opt))
                    }
                    className="h-4 w-4 accent-green-500"
                  />
                  {opt}
                </label>
              ))}
            </div>
          </div>
        )
      }

      const isDescription = !!field.description
      return (
        <div className="space-y-1 text-[11px]" key={path}>
          <div className="text-gray-300 font-medium">{field.title ?? path}</div>
          {isDescription ? (
            <textarea
              disabled={disabled}
              className="w-full bg-gray-800 text-gray-200 p-2 rounded text-[11px] resize-none focus:outline-none focus:ring-2 focus:ring-green-500 hover:ring-green-400 transition-all duration-200"
              value={val ?? ''}
              rows={3}
              onChange={e =>
                validateAndCommit(setAtPath(localValue, path, e.target.value))
              }
            />
          ) : (
            <input
              disabled={disabled}
              className="w-full bg-gray-800 text-gray-200 p-2 rounded text-[11px] h-8 focus:outline-none focus:ring-2 focus:ring-green-500 hover:ring-green-400 transition-all duration-200"
              type={field.type === 'string' ? 'text' : 'number'}
              value={val ?? ''}
              onChange={e =>
                validateAndCommit(
                  setAtPath(
                    localValue,
                    path,
                    field.type === 'integer'
                      ? parseInt(e.target.value || '0', 10)
                      : field.type === 'number'
                      ? Number(e.target.value)
                      : e.target.value
                  )
                )
              }
            />
          )}
          {field.description && (
            <div className="text-gray-400 text-[10px]">{field.description}</div>
          )}
        </div>
      )
    }

    /* ---------- Boolean ---------- */
    if (field.type === 'boolean') {
      return (
        <label
          key={path}
          className="flex items-center gap-2 text-[11px] text-gray-200 cursor-pointer hover:text-green-400 transition-colors duration-200"
        >
          <input
            type="checkbox"
            disabled={disabled}
            checked={!!val}
            onChange={e =>
              validateAndCommit(setAtPath(localValue, path, e.target.checked))
            }
            className="h-4 w-4 accent-green-500"
          />
          {field.title ?? path}
        </label>
      )
    }

    /* ---------- Array ---------- */
    if (field.type === 'array' && field.items) {
      if (isCollectionArray(val)) {
        return (
          <div key={path} className="space-y-3 border border-gray-700 rounded p-2">
            {val.map((item: any, idx: number) => (
              <div key={idx} className="border-b border-gray-700 pb-2 last:border-b-0">
                <div className="bg-gray-700 px-2 py-1 rounded font-semibold text-gray-200">
                  {item.name || `Section ${idx + 1}`}
                </div>
                {Object.keys(item)
                  .filter(k => k !== 'name')
                  .map(k => (
                    <div key={k} className="flex gap-2 items-center mt-1">
                      <input
                        className="w-[90px] bg-gray-800 p-1 text-gray-300 text-[11px] h-6 rounded"
                        value={k}
                        disabled
                      />
                      <input
                        className="flex-1 bg-gray-800 p-1 text-gray-200 text-[11px] h-6 rounded focus:outline-none hover:ring-green-400 transition-all duration-200"
                        value={item[k]}
                        onChange={(e) => {
                          const copy = [...val]
                          copy[idx][k] = e.target.value
                          validateAndCommit(setAtPath(localValue, path, copy))
                        }}
                      />
                      <button
                        className="p-1 rounded hover:bg-red-600 transition-colors"
                        onClick={() => {
                          const copy = [...val]
                          delete copy[idx][k]
                          validateAndCommit(setAtPath(localValue, path, copy))
                        }}
                      >
                        <Trash size={12} className="text-red-400" />
                      </button>
                    </div>
                  ))}
                <button
                  className="text-green-400 text-[11px] flex items-center gap-1 hover:text-green-500 transition-colors mt-1"
                  onClick={() => {
                    const copy = [...val]
                    if (!copy.length) copy.push({ name: `Item 1` })
                    copy[copy.length - 1][`key_${Date.now()}`] = ''
                    validateAndCommit(setAtPath(localValue, path, copy))
                  }}
                >
                  <Plus size={12} /> Add field
                </button>
              </div>
            ))}
          </div>
        )
      }

      return (
        <div className="space-y-2 text-[11px]" key={path}>
          <div className="text-gray-300 font-medium">{field.title ?? path}</div>
          {(val ?? []).map((item: any, idx: number) => (
            <div key={idx} className="flex gap-2 items-center">
              {renderField(field.items!, `${path}.${idx}`, item)}
              {!disabled && (
                <button
                  className="p-1 rounded hover:bg-red-600 transition-colors"
                  onClick={() => {
                    const next = [...val]
                    next.splice(idx, 1)
                    validateAndCommit(setAtPath(localValue, path, next))
                  }}
                >
                  <Trash size={14} className="text-red-400" />
                </button>
              )}
            </div>
          ))}
          {!disabled && (
            <button
              className="flex items-center gap-1 text-green-400 text-[11px] hover:text-green-500 transition-colors"
              onClick={() =>
                validateAndCommit(setAtPath(localValue, path, [...(val ?? []), '']))
              }
            >
              <Plus size={12} /> Add
            </button>
          )}
        </div>
      )
    }

    /* ---------- Object ---------- */
    if (field.type === 'object' && field.properties) {
      if (field.ui?.keyValue) {
        return (
          <button
            className="text-[11px] bg-gray-700 px-2 py-1 rounded hover:bg-gray-600 transition-colors"
            key={path}
            onClick={() => setKvEditor({ path, data: val ?? {} })}
          >
            Edit {field.title ?? path}
          </button>
        )
      }

      return (
        <div key={path} className="space-y-1 pl-2 text-[11px]">
          <div className="text-gray-300 font-medium">{field.title ?? path}</div>
          {Object.entries(field.properties).map(([k, f]) =>
            renderField(f, `${path}.${k}`, val?.[k])
          )}
        </div>
      )
    }

    return null
  }

  /* ===========================
     Render
  =========================== */

  return (
    <div className="bg-gray-900 h-full w-full overflow-y-auto p-3 space-y-3 text-[11px]">
      {error && (
        <div className="text-red-400 bg-red-950 p-2 rounded text-[10px]">{error}</div>
      )}

      {Object.entries(schema.properties).map(([key, field]) =>
        renderField(field, key, localValue[key])
      )}

      {/* Key-Value Floating Editor */}
      {kvEditor && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-4 rounded-xl w-[420px] space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-200 text-[11px] font-semibold">Key-Value Editor</span>
              <button className="p-1 hover:bg-gray-700 rounded" onClick={() => setKvEditor(null)}>
                <X size={14} />
              </button>
            </div>

            {Object.entries(kvEditor.data).map(([k, v]) => (
              <div key={k} className="flex gap-2 items-center text-[11px]">
                <input
                  className="flex-1 bg-gray-800 p-1 h-5 text-gray-300 rounded"
                  value={k}
                  disabled
                />
                <input
                  className="flex-1 bg-gray-800 p-1 h-5 text-gray-200 rounded"
                  value={v}
                  onChange={(e) =>
                    setKvEditor({ ...kvEditor, data: { ...kvEditor.data, [k]: e.target.value } })
                  }
                />
                <button
                  className="p-1 rounded hover:bg-red-600 transition-colors"
                  onClick={() => {
                    const next = { ...kvEditor.data }
                    delete next[k]
                    setKvEditor({ ...kvEditor, data: next })
                  }}
                >
                  <Trash size={12} />
                </button>
              </div>
            ))}

            <button
              className="flex items-center gap-1 text-green-400 text-[11px] hover:text-green-500 transition-colors"
              onClick={() =>
                setKvEditor({ ...kvEditor, data: { ...kvEditor.data, '': '' } })
              }
            >
              <Plus size={12} /> Add
            </button>

            <button
              className="w-full bg-green-600 hover:bg-green-500 text-white rounded py-1 text-[11px]"
              onClick={() => {
                validateAndCommit(setAtPath(localValue, kvEditor.path, kvEditor.data))
                setKvEditor(null)
              }}
            >
              Save
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default UIFormFactory

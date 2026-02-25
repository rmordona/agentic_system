import React, { useMemo } from 'react'
import { FileText, FileCode, Layers } from 'lucide-react'
import UIFormFactory from '../../components/form/UIFormFactory'

interface SkillControlPanelProps {
  activePanel: 'prompt' | 'skill' | 'context'
  formData: any
  setFormData: React.Dispatch<React.SetStateAction<any>>
  switchPanel: (panel: 'prompt' | 'skill' | 'context') => void
  onSave: () => void
  jsonError?: string | null
}


/* ===========================
   Component
=========================== */
const SkillControlPanel: React.FC<SkillControlPanelProps> = ({
  activePanel,
  formData,
  setFormData,
  switchPanel,
  onSave,
  jsonError,
}) => {
  if (!formData) {
    return <div className="text-red-400 text-xs">{jsonError || 'Invalid JSON'}</div>
  }

  // ✅ Wrap formData safely into UISchema
  const wrappedFormData = Array.isArray(formData)
    ? { collections: formData }
    : formData

  return (
    <div className="w-[400px] bg-gray-800 border-r border-gray-700 p-3 flex flex-col text-xs">
      {/* Panel Switcher */}
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

      {/* Form Factory Integration */}
      <div className="flex-1 overflow-y-auto">
        <UIFormFactory
          value={formData}
          onChange={(val) => {
            // If wrapped, unwrap collections back to top-level array
            if (Array.isArray(formData)) {
              setFormData(val.collections || [])
            } else {
              setFormData(val)
            }
          }}
        />
      </div>

      <div className="mt-auto">
        <button
          onClick={onSave}
          className="w-full py-1 bg-green-600 hover:bg-green-700 text-white rounded text-xs transition-colors"
        >
          Save
        </button>
      </div>
    </div>
  )
}

export default SkillControlPanel

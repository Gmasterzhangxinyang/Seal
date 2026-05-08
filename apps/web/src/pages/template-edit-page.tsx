import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { apiFetch, apiPost, apiPut } from '@/lib/api-client'
import type { Template, TemplateField } from '@/types/api'

export function TemplateEditPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isNew = !id

  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [description, setDescription] = useState('')
  const [keywords, setKeywords] = useState('')
  const [regex, setRegex] = useState('')
  const [stampPosition, setStampPosition] = useState('')
  const [stampKeywords, setStampKeywords] = useState('')
  const [fields, setFields] = useState<TemplateField[]>([
    { field_name: '', field_label: '', field_category: 'required', ocr_pattern: '', validation_rule: '' },
  ])
  const [loading, setLoading] = useState(!isNew)

  useEffect(() => {
    if (isNew) return
    apiFetch<Template>(`/templates/${id}`)
      .then((tpl) => {
        setName(tpl.name)
        setCode(tpl.code)
        setDescription(tpl.description || '')
        try {
          const kw = typeof tpl.classification_keywords === 'string'
            ? JSON.parse(tpl.classification_keywords)
            : tpl.classification_keywords
          setKeywords(Array.isArray(kw) ? kw.join(', ') : '')
        } catch { setKeywords('') }
        setRegex(tpl.classification_regex || '')
        setStampPosition(tpl.stamp_position || '')
        setStampKeywords(tpl.stamp_keywords || '')
        if (tpl.fields?.length) setFields(tpl.fields)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id, isNew])

  const addField = () => {
    setFields([...fields, { field_name: '', field_label: '', field_category: 'required', ocr_pattern: '', validation_rule: '' }])
  }

  const updateField = (idx: number, key: keyof TemplateField, value: string) => {
    const updated = [...fields]
    updated[idx] = { ...updated[idx], [key]: value }
    setFields(updated)
  }

  const removeField = (idx: number) => {
    setFields(fields.filter((_, i) => i !== idx))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const body = {
      name,
      code,
      description,
      classification_keywords: keywords.split(',').map((k) => k.trim()).filter(Boolean),
      classification_regex: regex,
      stamp_position: stampPosition,
      stamp_keywords: stampKeywords,
      fields: fields.filter((f) => f.field_name.trim()),
    }

    try {
      if (isNew) {
        await apiPost('/templates', body)
      } else {
        await apiPut(`/templates/${id}`, body)
      }
      navigate('/admin/templates')
    } catch (err) {
      alert(err instanceof Error ? err.message : '保存失败')
    }
  }

  if (loading) return <div className="text-center py-8 text-muted-foreground">加载中...</div>

  return (
    <div className="card bg-white rounded-xl shadow p-6">
      <h2 className="text-lg font-bold text-[#1d3557] mb-4">
        {isNew ? '新建模板' : '编辑模板'}
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">模板名称 *</label>
            <input value={name} onChange={(e) => setName(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm" required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">模板编码 *</label>
            <input value={code} onChange={(e) => setCode(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm" disabled={!isNew} required />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">描述</label>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm" rows={2} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">分类关键词（逗号分隔）</label>
            <input value={keywords} onChange={(e) => setKeywords(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">分类正则</label>
            <input value={regex} onChange={(e) => setRegex(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">盖章位置（如 0.82,0.85）</label>
            <input value={stampPosition} onChange={(e) => setStampPosition(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">盖章关键词（逗号分隔）</label>
            <input value={stampKeywords} onChange={(e) => setStampKeywords(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
        </div>

        {/* 字段编辑 */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-bold">字段定义</label>
            <button type="button" onClick={addField} className="text-sm text-[#457b9d] hover:underline">
              + 添加字段
            </button>
          </div>
          <div className="space-y-2">
            {fields.map((f, idx) => (
              <div key={idx} className="grid grid-cols-[1fr_1fr_100px_2fr_2fr_40px] gap-2 items-center">
                <input value={f.field_name} onChange={(e) => updateField(idx, 'field_name', e.target.value)} placeholder="字段名" className="px-2 py-1.5 border rounded text-sm" />
                <input value={f.field_label} onChange={(e) => updateField(idx, 'field_label', e.target.value)} placeholder="显示标签" className="px-2 py-1.5 border rounded text-sm" />
                <select value={f.field_category} onChange={(e) => updateField(idx, 'field_category', e.target.value)} className="px-2 py-1.5 border rounded text-sm">
                  <option value="required">必填</option>
                  <option value="optional">选填</option>
                  <option value="forbidden">禁填</option>
                </select>
                <input value={f.ocr_pattern} onChange={(e) => updateField(idx, 'ocr_pattern', e.target.value)} placeholder="OCR 正则" className="px-2 py-1.5 border rounded text-sm font-mono text-xs" />
                <input value={f.validation_rule} onChange={(e) => updateField(idx, 'validation_rule', e.target.value)} placeholder="验证规则 JSON" className="px-2 py-1.5 border rounded text-sm font-mono text-xs" />
                <button type="button" onClick={() => removeField(idx)} className="text-red-400 hover:text-red-600 text-lg">&times;</button>
              </div>
            ))}
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button type="submit" className="px-6 py-2 bg-[#457b9d] text-white rounded-lg font-semibold hover:opacity-90">
            保存
          </button>
          <button type="button" onClick={() => navigate('/admin/templates')} className="px-6 py-2 bg-gray-200 rounded-lg hover:bg-gray-300">
            取消
          </button>
        </div>
      </form>
    </div>
  )
}

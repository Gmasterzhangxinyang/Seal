import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { apiFetch, apiPost, apiPut } from '@/lib/api-client'
import type { Template, TemplateField } from '@/types/api'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'
import { Spinner } from '@/components/ui/spinner'

export function TemplateEditPage() {
  const { t } = useTranslation('admin')
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
    {
      field_name: '',
      field_label: '',
      field_category: 'required',
      ocr_pattern: '',
      validation_rule: '',
    },
  ])
  const [loading, setLoading] = useState(!isNew)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isNew) return
    apiFetch<Template>(`/templates/${id}`)
      .then((tpl) => {
        setName(tpl.name)
        setCode(tpl.code)
        setDescription(tpl.description || '')
        try {
          const kw =
            typeof tpl.classification_keywords === 'string'
              ? JSON.parse(tpl.classification_keywords)
              : tpl.classification_keywords
          setKeywords(Array.isArray(kw) ? kw.join(', ') : '')
        } catch {
          setKeywords('')
        }
        setRegex(tpl.classification_regex || '')
        setStampPosition(tpl.stamp_position || '')
        setStampKeywords(tpl.stamp_keywords || '')
        if (tpl.fields?.length) setFields(tpl.fields)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id, isNew])

  const addField = () => {
    setFields([
      ...fields,
      {
        field_name: '',
        field_label: '',
        field_category: 'required',
        ocr_pattern: '',
        validation_rule: '',
      },
    ])
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
    setError(null)
    const body = {
      name,
      code,
      description,
      classification_keywords: keywords
        .split(',')
        .map((k) => k.trim())
        .filter(Boolean),
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
      setError(err instanceof Error ? err.message : t('saveFailed'))
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  return (
    <div>
      <PageHeader title={isNew ? t('newTemplate') : t('editTemplate')} />

      <Card>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  {t('templateNameLabel')} *
                </label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  {t('templateCodeLabel')} *
                </label>
                <Input
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  disabled={!isNew}
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                {t('description')}
              </label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                className="min-h-[60px]"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  {t('classificationKeywords')}
                </label>
                <Input
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  {t('classificationRegex')}
                </label>
                <Input
                  value={regex}
                  onChange={(e) => setRegex(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  {t('stampPosition')}
                </label>
                <Input
                  value={stampPosition}
                  onChange={(e) => setStampPosition(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  {t('stampKeywords')}
                </label>
                <Input
                  value={stampKeywords}
                  onChange={(e) => setStampKeywords(e.target.value)}
                />
              </div>
            </div>

            {/* Field definitions */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-semibold text-foreground">
                  {t('fieldDefinition')}
                </label>
                <Button type="button" variant="ghost" size="sm" onClick={addField}>
                  {t('addField')}
                </Button>
              </div>
              <div className="space-y-2">
                {fields.map((f, idx) => (
                  <div
                    key={idx}
                    className="grid grid-cols-[1fr_1fr_100px_2fr_2fr_40px] gap-2 items-center"
                  >
                    <Input
                      value={f.field_name}
                      onChange={(e) => updateField(idx, 'field_name', e.target.value)}
                      placeholder={t('fieldName')}
                    />
                    <Input
                      value={f.field_label}
                      onChange={(e) => updateField(idx, 'field_label', e.target.value)}
                      placeholder={t('displayLabel')}
                    />
                    <Select
                      value={f.field_category}
                      onChange={(e) => updateField(idx, 'field_category', e.target.value)}
                    >
                      <option value="required">{t('required')}</option>
                      <option value="optional">{t('optionalCat')}</option>
                      <option value="forbidden">{t('forbidden')}</option>
                    </Select>
                    <Input
                      value={f.ocr_pattern}
                      onChange={(e) => updateField(idx, 'ocr_pattern', e.target.value)}
                      placeholder={t('ocrRegex')}
                      className="font-mono text-xs"
                    />
                    <Input
                      value={f.validation_rule}
                      onChange={(e) => updateField(idx, 'validation_rule', e.target.value)}
                      placeholder={t('validationRule')}
                      className="font-mono text-xs"
                    />
                    <button
                      type="button"
                      onClick={() => removeField(idx)}
                      className="text-muted-foreground hover:text-destructive text-lg transition-colors cursor-pointer"
                    >
                      &times;
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}

            <div className="flex gap-3 pt-2">
              <Button type="submit">
                {t('common:save')}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => navigate('/admin/templates')}
              >
                {t('common:cancel')}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

export interface User {
  username: string
  email: string
  role: 'admin' | 'reviewer' | 'operator'
}

export interface StampResult {
  status: 'approved' | 'rejected' | 'pending_review' | 'error'
  errors?: string[]
  warnings?: string[]
  message?: string
  fields?: Record<string, string>
  review_id?: number
}

export interface CameraInfo {
  index: number
  resolution: string
}

export interface CameraListResponse {
  cameras: CameraInfo[]
  current: number
}

export interface PendingStampItem {
  id: number
  timestamp: string
  operator_id: string
  doc_type: string
  doc_type_name: string
}

export interface AuditLog {
  id: number
  timestamp: string
  operator_id: string
  doc_type: string
  doc_type_name?: string
  qr_content: string | null
  result: string
  errors: string | null
  fields: string | null
  ocr_text: string | null
  before_image: string | null
  after_image: string | null
}

export interface ReviewItem {
  id: number
  timestamp: string
  operator_id: string
  doc_type: string
  doc_type_name?: string
  doc_fields: string | null
  ocr_text: string | null
  warnings: string | null
  image_path: string | null
  status: string
  errors: string | null
}

export interface Template {
  id: number
  name: string
  code: string
  description: string
  is_system: number
  sort_order: number
  classification_keywords: string
  classification_regex: string
  requires_stamp: number
  stamp_position: string
  stamp_keywords: string
  fields: TemplateField[]
  example_image: string | null
  field_stats?: { required: number; optional: number; forbidden: number }
}

export interface TemplateField {
  id?: number
  field_name: string
  field_label: string
  field_category: 'required' | 'optional' | 'forbidden'
  ocr_pattern: string
  validation_rule: string
}

export interface StatsData {
  total: number
  approved: number
  rejected: number
  pending_review: number
  pending_queue: number
  type_distribution: Record<string, number>
  result_distribution: Record<string, number>
  daily_trend: [string, string, number][]
  recent: (string | number)[][]
}

export interface CalibrationData {
  corners?: Record<string, Record<string, number>>
}

export interface UserItem {
  username: string
  email: string
  role: string
  created_at: string
}

export interface ArmConfig {
  arm_type: string
  value_min: number
  value_max: number
  value_mid: number
}

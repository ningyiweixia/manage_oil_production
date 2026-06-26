import { http, unwrap } from './http'

export interface DictionaryItem {
  id: number
  dict_type: string
  item_label: string
  item_value: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export async function listDictionaryItems(dictType: string): Promise<DictionaryItem[]> {
  return unwrap<DictionaryItem[]>(http.get('/dictionaries/', { params: { dict_type: dictType } }))
}

export async function listAllDictionaryItems(activeOnly = false): Promise<DictionaryItem[]> {
  return unwrap<DictionaryItem[]>(http.get('/dictionaries/', { params: { active_only: activeOnly } }))
}

export async function createDictionaryItem(payload: Pick<DictionaryItem, 'dict_type' | 'item_label' | 'item_value'> & { is_active?: boolean }) {
  return unwrap<DictionaryItem>(http.post('/dictionaries/', payload))
}

export async function updateDictionaryItem(id: number, payload: Partial<Pick<DictionaryItem, 'item_label' | 'item_value' | 'is_active'>>) {
  return unwrap<DictionaryItem>(http.put(`/dictionaries/${id}`, payload))
}

export async function setDictionaryActive(id: number, isActive: boolean) {
  return unwrap<DictionaryItem>(http.patch(`/dictionaries/${id}/active`, null, { params: { is_active: isActive } }))
}

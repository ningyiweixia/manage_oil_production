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

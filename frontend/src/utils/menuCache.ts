import type { CurrentUser, LoginResponse, MenuNode } from '../api/auth'

export const MENU_SCHEMA_VERSION = '2026-07-07-phase3-operation-menu-system-support-menu'
const MENU_SCHEMA_VERSION_KEY = 'menu_schema_version'

export function storeSessionMenus(payload: {
  user?: LoginResponse['user'] | CurrentUser | Record<string, unknown>
  permissions?: unknown[]
  menus?: MenuNode[]
}) {
  localStorage.setItem('current_user', JSON.stringify(payload.user || {}))
  localStorage.setItem('permissions', JSON.stringify(payload.permissions || []))
  localStorage.setItem('menus', JSON.stringify(payload.menus || []))
  localStorage.setItem(MENU_SCHEMA_VERSION_KEY, MENU_SCHEMA_VERSION)
}

export function clearSessionMenus() {
  localStorage.removeItem('menus')
  localStorage.removeItem(MENU_SCHEMA_VERSION_KEY)
}

export function loadCachedMenus(): MenuNode[] {
  if (localStorage.getItem(MENU_SCHEMA_VERSION_KEY) !== MENU_SCHEMA_VERSION) {
    clearSessionMenus()
    return []
  }
  try {
    return JSON.parse(localStorage.getItem('menus') || '[]') as MenuNode[]
  } catch {
    clearSessionMenus()
    return []
  }
}

export function refreshSessionMenus(currentUser: CurrentUser) {
  const permissions = currentUser.permissions?.map((item) => item.code) || []
  storeSessionMenus({
    user: currentUser,
    permissions,
    menus: currentUser.menus || []
  })
}

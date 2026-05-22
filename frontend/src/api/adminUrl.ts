const API_URL = import.meta.env.VITE_API_URL || '/api/v1'

export function getAdminBaseUrl(): string {
  if (!API_URL || API_URL.startsWith('/')) {
    return '/admin/'
  }

  try {
    const url = new URL(API_URL)
    return `${url.origin}/admin/`
  } catch {
    return '/admin/'
  }
}

export function getAdminLoginUrl(): string {
  return `${getAdminBaseUrl()}login`
}

export function redirectToAdminLogin(): void {
  document.cookie = `admin_redirect=${encodeURIComponent(window.location.pathname)}; path=/; SameSite=Lax; max-age=300`
  window.location.href = getAdminLoginUrl()
}

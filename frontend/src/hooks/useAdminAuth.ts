// ============================================
// Хук проверки авторизации для страниц Admin
// ============================================

import { useEffect, useState } from 'react';

interface AdminAuthResult {
  /** Авторизация подтверждена */
  isAuthenticated: boolean;
  /** Проверка ещё не завершена */
  isChecking: boolean;
}

/**
 * Проверяет наличие активной admin-сессии через `/admin/api/session`.
 * При отсутствии сессии сохраняет текущий путь в cookie и редиректит на `/admin/login`.
 */
export function useAdminAuth(): AdminAuthResult {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await fetch('/admin/api/session', {
          credentials: 'include',
        });
        if (response.ok) {
          setIsAuthenticated(true);
        } else {
          // Сохраняем URL возврата в cookie (форма SQLAdmin не передаёт query params)
          document.cookie = `admin_redirect=${encodeURIComponent(window.location.pathname)}; path=/; SameSite=Lax; max-age=300`;
          window.location.href = '/admin/login';
        }
      } catch {
        document.cookie = `admin_redirect=${encodeURIComponent(window.location.pathname)}; path=/; SameSite=Lax; max-age=300`;
        window.location.href = '/admin/login';
      } finally {
        setIsChecking(false);
      }
    };

    checkAuth();
  }, []);

  return { isAuthenticated, isChecking };
}

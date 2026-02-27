// ============================================
// Страница редактора системного анализа
// ============================================

import { useParams, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { AnalysisEditor, useAnalysisStore } from '../analysis';

const AnalysisEditorPage = () => {
  const { surveyId } = useParams<{ surveyId: string }>();
  const navigate = useNavigate();
  const isDirty = useAnalysisStore((state) => state.isDirty);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  // Проверка авторизации (аналогично EditorPage)
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await fetch('/admin/api/session', {
          credentials: 'include',
        });
        if (response.ok) {
          setIsAuthenticated(true);
        } else {
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

  useEffect(() => {
    if (!surveyId) {
      navigate('/admin/surveys');
    }
  }, [surveyId, navigate]);

  // Предупреждение при закрытии вкладки
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = 'У вас есть несохранённые изменения. Вы уверены, что хотите покинуть страницу?';
        return e.returnValue;
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty]);

  if (!surveyId) return null;

  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <p className="text-slate-600">Проверка доступа...</p>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return <AnalysisEditor surveyId={parseInt(surveyId)} />;
};

export default AnalysisEditorPage;

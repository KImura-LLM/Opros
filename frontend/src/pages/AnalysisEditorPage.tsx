// ============================================
// Страница редактора системного анализа
// ============================================

import { useParams, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { AnalysisEditor, useAnalysisStore } from '../analysis';
import { useAdminAuth } from '../hooks/useAdminAuth';

const AnalysisEditorPage = () => {
  const { surveyId } = useParams<{ surveyId: string }>();
  const navigate = useNavigate();
  const isDirty = useAnalysisStore((state) => state.isDirty);
  const { isAuthenticated, isChecking } = useAdminAuth();

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

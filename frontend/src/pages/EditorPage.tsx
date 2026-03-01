// ============================================
// Страница редактора опросника
// ============================================

import { useParams, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { SurveyEditor, useEditorStore } from '../editor';
import { useAdminAuth } from '../hooks/useAdminAuth';

const EditorPage = () => {
  const { surveyId } = useParams<{ surveyId: string }>();
  const navigate = useNavigate();
  const isDirty = useEditorStore(state => state.isDirty);
  const { isAuthenticated, isChecking } = useAdminAuth();
  
  useEffect(() => {
    // Если ID не указан, редирект на список
    if (!surveyId) {
      navigate('/admin/surveys');
    }
  }, [surveyId, navigate]);
  
  // Предупреждение при закрытии вкладки/браузера
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
  
  if (!surveyId) {
    return null;
  }
  
  // Показываем загрузку пока проверяем авторизацию
  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <p className="text-slate-600">Проверка доступа...</p>
      </div>
    );
  }
  
  // Не авторизован — не показываем UI редактора
  if (!isAuthenticated) {
    return null;
  }
  
  return <SurveyEditor surveyId={parseInt(surveyId)} />;
};

export default EditorPage;

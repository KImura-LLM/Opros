// ============================================
// Страница редактора опросника
// ============================================

import { useParams, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { SurveyEditor, useEditorStore } from '../editor';

const EditorPage = () => {
  const { surveyId } = useParams<{ surveyId: string }>();
  const navigate = useNavigate();
  const isDirty = useEditorStore(state => state.isDirty);
  
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
  
  return <SurveyEditor surveyId={parseInt(surveyId)} />;
};

export default EditorPage;

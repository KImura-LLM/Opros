// ============================================
// Панель инструментов редактора (верхняя)
// ============================================

import { useState, useRef } from 'react';
import { 
  Save, 
  Undo2, 
  Redo2, 
  Download, 
  Upload,
  Play,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  Loader2,
  Clock,
} from 'lucide-react';
import { useEditorStore } from '../store';

interface ToolbarProps {
  onPreview: () => void;
}

const Toolbar = ({ onPreview }: ToolbarProps) => {
  const { 
    survey,
    isDirty, 
    isSaving, 
    lastSaved,
    saveSurvey, 
    undo, 
    redo, 
    canUndo, 
    canRedo,
    validate,
    validationResult,
    exportJSON,
    importJSON,
    updateSurveyMeta,
  } = useEditorStore();
  
  const [isValidating, setIsValidating] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importText, setImportText] = useState('');
  const [editingName, setEditingName] = useState(false);
  const [tempName, setTempName] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const handleSave = async () => {
    await saveSurvey();
  };
  
  const handleValidate = async () => {
    setIsValidating(true);
    await validate();
    setIsValidating(false);
  };
  
  const handleExport = () => {
    const json = exportJSON();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `survey_${survey?.name || 'export'}_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };
  
  const handleImportClick = () => {
    fileInputRef.current?.click();
  };
  
  const handleFileImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    // Предупреждение о потере несохранённых изменений
    if (isDirty) {
      const confirmed = confirm(
        'У вас есть несохранённые изменения. При импорте они будут потеряны. Продолжить?'
      );
      if (!confirmed) {
        event.target.value = '';
        return;
      }
    }
    
    const reader = new FileReader();
    reader.onload = async (e) => {
      const text = e.target?.result as string;
      await importJSON(text);
    };
    reader.readAsText(file);
    
    // Сброс input для возможности загрузки того же файла
    event.target.value = '';
  };
  
  const handleTextImport = async () => {
    if (importText.trim()) {
      // Предупреждение о потере несохранённых изменений
      if (isDirty) {
        const confirmed = confirm(
          'У вас есть несохранённые изменения. При импорте они будут потеряны. Продолжить?'
        );
        if (!confirmed) return;
      }
      
      await importJSON(importText);
      setShowImportModal(false);
      setImportText('');
    }
  };
  
  const handleNameEdit = () => {
    setTempName(survey?.name || '');
    setEditingName(true);
  };
  
  const handleNameSave = () => {
    if (tempName.trim()) {
      updateSurveyMeta({ name: tempName.trim() });
    }
    setEditingName(false);
  };
  
  const formatLastSaved = (date: Date | null) => {
    if (!date) return null;
    return date.toLocaleTimeString('ru-RU', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };
  
  return (
    <div className="bg-white border-b border-gray-200 px-4 py-2">
      <div className="flex items-center justify-between">
        {/* Левая часть: название и статус */}
        <div className="flex items-center gap-4">
          {editingName ? (
            <input
              type="text"
              value={tempName}
              onChange={(e) => setTempName(e.target.value)}
              onBlur={handleNameSave}
              onKeyDown={(e) => e.key === 'Enter' && handleNameSave()}
              className="px-2 py-1 text-lg font-semibold border border-blue-500 rounded focus:ring-2 focus:ring-blue-500 outline-none"
              autoFocus
            />
          ) : (
            <h1 
              onClick={handleNameEdit}
              className="text-lg font-semibold text-gray-800 cursor-pointer hover:text-blue-600"
              title="Нажмите для редактирования"
            >
              {survey?.name || 'Новый опросник'}
            </h1>
          )}
          
          {/* Индикатор статуса */}
          <div className="flex items-center gap-2 text-sm">
            {isDirty && (
              <span className="text-yellow-600 flex items-center gap-1">
                <div className="w-2 h-2 bg-yellow-500 rounded-full" />
                Не сохранено
              </span>
            )}
            
            {isSaving && (
              <span className="text-blue-600 flex items-center gap-1">
                <Loader2 size={14} className="animate-spin" />
                Сохранение...
              </span>
            )}
            
            {!isDirty && !isSaving && lastSaved && (
              <span className="text-green-600 flex items-center gap-1">
                <Clock size={14} />
                Сохранено в {formatLastSaved(lastSaved)}
              </span>
            )}
          </div>
        </div>
        
        {/* Центральная часть: основные действия */}
        <div className="flex items-center gap-2">
          {/* Undo/Redo */}
          <div className="flex items-center border-r border-gray-200 pr-2 mr-2">
            <button
              onClick={undo}
              disabled={!canUndo()}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded disabled:opacity-40 disabled:cursor-not-allowed"
              title="Отменить (Ctrl+Z)"
            >
              <Undo2 size={18} />
            </button>
            <button
              onClick={redo}
              disabled={!canRedo()}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded disabled:opacity-40 disabled:cursor-not-allowed"
              title="Повторить (Ctrl+Y)"
            >
              <Redo2 size={18} />
            </button>
          </div>
          
          {/* Сохранение */}
          <button
            onClick={handleSave}
            disabled={!isDirty || isSaving}
            className="
              flex items-center gap-2 px-3 py-1.5 
              bg-blue-600 text-white rounded-lg 
              hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors
            "
          >
            {isSaving ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Save size={16} />
            )}
            Сохранить
          </button>
          
          {/* Валидация */}
          <button
            onClick={handleValidate}
            disabled={isValidating}
            className="
              flex items-center gap-2 px-3 py-1.5 
              border border-gray-300 text-gray-700 rounded-lg 
              hover:bg-gray-50 disabled:opacity-50
              transition-colors
            "
          >
            {isValidating ? (
              <Loader2 size={16} className="animate-spin" />
            ) : validationResult?.valid ? (
              <CheckCircle size={16} className="text-green-600" />
            ) : validationResult ? (
              <AlertCircle size={16} className="text-red-600" />
            ) : (
              <CheckCircle size={16} />
            )}
            Проверить
          </button>
          
          {/* Предпросмотр */}
          <button
            onClick={onPreview}
            className="
              flex items-center gap-2 px-3 py-1.5 
              border border-gray-300 text-gray-700 rounded-lg 
              hover:bg-gray-50 transition-colors
            "
          >
            <Play size={16} />
            Предпросмотр
          </button>
        </div>
        
        {/* Правая часть: импорт/экспорт */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleImportClick}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded"
            title="Импорт JSON"
          >
            <Upload size={18} />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            onChange={handleFileImport}
            className="hidden"
          />
          
          <button
            onClick={handleExport}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded"
            title="Экспорт JSON"
          >
            <Download size={18} />
          </button>
        </div>
      </div>
      
      {/* Результаты валидации */}
      {validationResult && (validationResult.errors.length > 0 || validationResult.warnings.length > 0) && (
        <div className="mt-2 pt-2 border-t border-gray-100">
          <div className="flex flex-wrap gap-2">
            {validationResult.errors.map((error, index) => (
              <span 
                key={`error-${index}`}
                className="inline-flex items-center gap-1 px-2 py-1 bg-red-50 text-red-700 text-xs rounded-full"
              >
                <AlertCircle size={12} />
                {error.message}
              </span>
            ))}
            {validationResult.warnings.map((warning, index) => (
              <span 
                key={`warning-${index}`}
                className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-50 text-yellow-700 text-xs rounded-full"
              >
                <AlertTriangle size={12} />
                {warning.message}
              </span>
            ))}
          </div>
        </div>
      )}
      
      {/* Модал импорта текста */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6">
            <h3 className="text-lg font-semibold mb-4">Импорт JSON</h3>
            <textarea
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              className="w-full h-64 p-3 border border-gray-200 rounded-lg font-mono text-sm"
              placeholder="Вставьте JSON..."
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setShowImportModal(false)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Отмена
              </button>
              <button
                onClick={handleTextImport}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Импортировать
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Toolbar;

// ============================================
// Панель редактирования связи (условий перехода)
// ============================================

import { useState, useEffect } from 'react';
import { X, AlertCircle } from 'lucide-react';
import { useEditorStore } from '../store';
import { FlowEdge, SurveyNodeData } from '../types';

interface EdgeEditorProps {
  edge: FlowEdge | null;
  onClose: () => void;
}

const EdgeEditor = ({ edge, onClose }: EdgeEditorProps) => {
  const { nodes, updateEdge } = useEditorStore();
  const [condition, setCondition] = useState('');
  const [isDefault, setIsDefault] = useState(false);
  
  useEffect(() => {
    if (edge) {
      setCondition(edge.data?.condition || '');
      setIsDefault(edge.data?.isDefault || false);
    }
  }, [edge]);
  
  if (!edge) {
    return null;
  }
  
  const sourceNode = nodes.find(n => n.id === edge.source);
  const targetNode = nodes.find(n => n.id === edge.target);
  const sourceData = sourceNode?.data as SurveyNodeData | undefined;
  const targetData = targetNode?.data as SurveyNodeData | undefined;
  
  const hasOptions = sourceData?.options && sourceData.options.length > 0;
  
  const handleSave = () => {
    updateEdge(edge.id, {
      condition: condition.trim() || undefined,
      isDefault,
    });
    onClose();
  };
  
  const handleSelectOption = (optionId: string) => {
    setCondition(`selected == "${optionId}"`);
    setIsDefault(false);
  };
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div 
        className="bg-white rounded-lg shadow-xl w-[500px] max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Заголовок */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-800">
            Настройка условия перехода
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded"
          >
            <X size={20} />
          </button>
        </div>
        
        {/* Информация о связи */}
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <div className="text-sm space-y-2">
            <div>
              <span className="text-gray-500">От:</span>{' '}
              <span className="font-medium text-gray-800">
                {sourceData?.question_text || sourceNode?.id}
              </span>
            </div>
            <div>
              <span className="text-gray-500">К:</span>{' '}
              <span className="font-medium text-gray-800">
                {targetData?.question_text || targetNode?.id}
              </span>
            </div>
          </div>
        </div>
        
        {/* Основное содержимое */}
        <div className="px-6 py-4 space-y-4">
          {/* Выбор "По умолчанию" */}
          <div className="flex items-start gap-3">
            <input
              type="checkbox"
              id="isDefault"
              checked={isDefault}
              onChange={(e) => {
                setIsDefault(e.target.checked);
                if (e.target.checked) {
                  setCondition('');
                }
              }}
              className="mt-1 h-4 w-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
            />
            <div className="flex-1">
              <label 
                htmlFor="isDefault"
                className="block text-sm font-medium text-gray-700 cursor-pointer"
              >
                Переход по умолчанию
              </label>
              <p className="text-xs text-gray-500 mt-1">
                Используется, если не выполнено ни одно другое условие
              </p>
            </div>
          </div>
          
          {!isDefault && (
            <>
              {/* Быстрый выбор варианта ответа */}
              {hasOptions && (
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Выбрать вариант ответа
                  </label>
                  <div className="space-y-2">
                    {sourceData.options!.map((option) => (
                      <button
                        key={option.id}
                        onClick={() => handleSelectOption(option.id)}
                        className={`
                          w-full px-4 py-2 text-left text-sm rounded-lg border-2 transition-colors
                          ${condition === `selected == "${option.id}"` 
                            ? 'border-blue-500 bg-blue-50 text-blue-800' 
                            : 'border-gray-200 hover:border-gray-300 text-gray-700'
                          }
                        `}
                      >
                        {option.text}
                      </button>
                    ))}
                  </div>
                  
                  <div className="flex items-center gap-2 mt-3 mb-2">
                    <div className="flex-1 border-t border-gray-200" />
                    <span className="text-xs text-gray-500">или</span>
                    <div className="flex-1 border-t border-gray-200" />
                  </div>
                </div>
              )}
              
              {/* Ручной ввод условия */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  Условие (Python-подобный синтаксис)
                </label>
                <textarea
                  value={condition}
                  onChange={(e) => setCondition(e.target.value)}
                  placeholder='Например: selected == "yes" или age > 18'
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
                  rows={3}
                />
                
                {/* Подсказки */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <div className="flex items-start gap-2">
                    <AlertCircle size={16} className="text-blue-600 mt-0.5 flex-shrink-0" />
                    <div className="text-xs text-blue-800 space-y-1">
                      <p className="font-medium">Доступные переменные:</p>
                      <ul className="list-disc list-inside ml-2 space-y-0.5">
                        <li><code className="bg-blue-100 px-1 rounded">selected</code> - выбранный вариант (ID опции)</li>
                        <li><code className="bg-blue-100 px-1 rounded">value</code> - числовое значение (для slider)</li>
                        <li><code className="bg-blue-100 px-1 rounded">text</code> - текстовый ответ</li>
                        {hasOptions && (
                          <li><code className="bg-blue-100 px-1 rounded">"{sourceData.options![0].id}"</code> - ID варианта ответа</li>
                        )}
                      </ul>
                      <p className="mt-2">
                        <strong>Примеры:</strong><br/>
                        <code className="bg-blue-100 px-1 rounded">selected == "yes"</code> (для single_choice)<br/>
                        <code className="bg-blue-100 px-1 rounded">"option_1" in selected</code> (для multi_choice)<br/>
                        <code className="bg-blue-100 px-1 rounded">value &gt;= 7</code> (для slider)
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
        
        {/* Футер с кнопками */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Отмена
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Сохранить
          </button>
        </div>
      </div>
    </div>
  );
};

export default EdgeEditor;

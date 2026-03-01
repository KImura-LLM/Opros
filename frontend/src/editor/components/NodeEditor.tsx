// ============================================
// Панель редактирования узла (правая панель)
// ============================================

import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  X, 
  Plus, 
  Trash2, 
  GripVertical,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useEditorStore } from '../store';
import { NODE_TYPE_CONFIG, SurveyNodeData, NodeOption, NodeType, AdditionalField } from '../types';

// Время debounce в миллисекундах
const DEBOUNCE_DELAY = 500;

const NodeEditor = () => {
  const { nodes, selectedNodeId, updateNode, selectNode, edges, groups, assignNodeToGroup } = useEditorStore();
  
  const selectedNode = nodes.find(n => n.id === selectedNodeId);
  const nodeData = selectedNode?.data as SurveyNodeData | undefined;
  
  const [localData, setLocalData] = useState<Partial<SurveyNodeData>>({});
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    basic: true,
    options: true,
    settings: false,
    exclusive: false,
    additional_fields: true,
  });
  
  // Debounce таймер для автосохранения
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedDataRef = useRef<string>('');
  
  // Debounced обновление узла
  const debouncedUpdateNode = useCallback((nodeId: string, data: Partial<SurveyNodeData>) => {
    // Очищаем предыдущий таймер
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    
    // Создаём новый таймер
    debounceTimerRef.current = setTimeout(() => {
      const dataHash = JSON.stringify(data);
      // Сохраняем только если данные изменились
      if (dataHash !== lastSavedDataRef.current) {
        updateNode(nodeId, data);
        lastSavedDataRef.current = dataHash;
      }
    }, DEBOUNCE_DELAY);
  }, [updateNode]);
  
  // Очистка таймера при размонтировании
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);
  
  // Синхронизация локального состояния с выбранным узлом
  useEffect(() => {
    if (nodeData) {
      setLocalData({
        question_text: nodeData.question_text,
        description: nodeData.description,
        required: nodeData.required,
        options: nodeData.options ? [...nodeData.options] : [],
        additional_fields: nodeData.additional_fields ? [...nodeData.additional_fields] : [],
        min_value: nodeData.min_value,
        max_value: nodeData.max_value,
        step: nodeData.step,
        placeholder: nodeData.placeholder,
        max_length: nodeData.max_length,
        is_final: nodeData.is_final,
        exclusive_option: nodeData.exclusive_option,
      });
    }
  }, [selectedNodeId, nodeData]);
  
  if (!selectedNode || !nodeData) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6 w-80">
        <p className="text-gray-500 text-center">
          Выберите узел для редактирования
        </p>
      </div>
    );
  }
  
  const config = NODE_TYPE_CONFIG[nodeData.type as NodeType];
  
  const handleChange = (field: keyof SurveyNodeData, value: unknown) => {
    setLocalData((prev: Partial<SurveyNodeData>) => ({ ...prev, [field]: value }));
    // Запускаем debounced сохранение при каждом изменении
    if (selectedNodeId) {
      debouncedUpdateNode(selectedNodeId, { ...localData, [field]: value });
    }
  };
  
  const handleBlur = () => {
    // Принудительно сохраняем при потере фокуса (отменяем debounce)
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    if (selectedNodeId) {
      const dataHash = JSON.stringify(localData);
      if (dataHash !== lastSavedDataRef.current) {
        updateNode(selectedNodeId, localData);
        lastSavedDataRef.current = dataHash;
      }
    }
  };
  
  const handleAddOption = () => {
    const newOptions = [
      ...(localData.options || []),
      { 
        id: `opt_${Date.now()}`, 
        text: 'Новый вариант', 
        value: `opt_${Date.now()}` 
      },
    ];
    setLocalData((prev: Partial<SurveyNodeData>) => ({ ...prev, options: newOptions }));
    updateNode(selectedNodeId!, { options: newOptions });
  };
  
  const handleUpdateOption = (index: number, field: keyof NodeOption, value: string) => {
    const newOptions = [...(localData.options || [])];
    newOptions[index] = { ...newOptions[index], [field]: value };
    setLocalData((prev: Partial<SurveyNodeData>) => ({ ...prev, options: newOptions }));
  };
  
  const handleDeleteOption = (index: number) => {
    const newOptions = (localData.options || []).filter((_: NodeOption, i: number) => i !== index);
    setLocalData((prev: Partial<SurveyNodeData>) => ({ ...prev, options: newOptions }));
    updateNode(selectedNodeId!, { options: newOptions });
  };
  
  const handleOptionsBlur = () => {
    updateNode(selectedNodeId!, { options: localData.options });
  };

  // --- Дополнительные поля ввода ---
  const handleAddAdditionalField = (type: 'text' | 'number') => {
    const newField: AdditionalField = {
      id: `field_${Date.now()}`,
      type,
      label: type === 'text' ? 'Текстовое поле' : 'Числовое поле',
      placeholder: '',
    };
    const newFields = [...(localData.additional_fields || []), newField];
    setLocalData((prev: Partial<SurveyNodeData>) => ({ ...prev, additional_fields: newFields }));
    updateNode(selectedNodeId!, { additional_fields: newFields });
  };

  const handleUpdateAdditionalField = (
    index: number,
    field: Partial<AdditionalField>
  ) => {
    const newFields = [...(localData.additional_fields || [])];
    newFields[index] = { ...newFields[index], ...field };
    setLocalData((prev: Partial<SurveyNodeData>) => ({ ...prev, additional_fields: newFields }));
  };

  const handleAdditionalFieldBlur = () => {
    updateNode(selectedNodeId!, { additional_fields: localData.additional_fields });
  };

  const handleDeleteAdditionalField = (index: number) => {
    const newFields = (localData.additional_fields || []).filter(
      (_: AdditionalField, i: number) => i !== index
    );
    setLocalData((prev: Partial<SurveyNodeData>) => ({ ...prev, additional_fields: newFields }));
    updateNode(selectedNodeId!, { additional_fields: newFields });
  };
  
  const toggleSection = (section: string) => {
    setExpandedSections((prev: Record<string, boolean>) => ({ ...prev, [section]: !prev[section] }));
  };
  
  // Получаем связи для текущего узла
  const outgoingEdges = edges.filter(e => e.source === selectedNodeId);
  
  return (
    <div className="bg-white rounded-lg shadow-lg w-80 max-h-[calc(100vh-120px)] overflow-y-auto">
      {/* Заголовок */}
      <div 
        className="sticky top-0 px-4 py-3 border-b border-gray-200 flex items-center justify-between bg-white z-10"
        style={{ borderLeftColor: config.color, borderLeftWidth: 4 }}
      >
        <div>
          <h3 className="font-semibold text-gray-800">{config.name}</h3>
          <p className="text-xs text-gray-500">{nodeData.id}</p>
        </div>
        <button 
          onClick={() => selectNode(null)}
          className="p-1 hover:bg-gray-100 rounded"
        >
          <X size={18} className="text-gray-500" />
        </button>
      </div>
      
      {/* Основные настройки */}
      <div className="border-b border-gray-100">
        <button
          onClick={() => toggleSection('basic')}
          className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50"
        >
          <span className="font-medium text-sm text-gray-700">Основное</span>
          {expandedSections.basic ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
        
        {expandedSections.basic && (
          <div className="px-4 pb-4 space-y-4">
            {/* Текст вопроса */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Текст вопроса *
              </label>
              <textarea
                value={localData.question_text || ''}
                onChange={(e) => handleChange('question_text', e.target.value)}
                onBlur={handleBlur}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={3}
                placeholder="Введите текст вопроса..."
              />
            </div>
            
            {/* Описание */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Описание (подсказка)
              </label>
              <textarea
                value={localData.description || ''}
                onChange={(e) => handleChange('description', e.target.value)}
                onBlur={handleBlur}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={2}
                placeholder="Дополнительное описание..."
              />
            </div>
            
            {/* Обязательность */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={localData.required ?? true}
                onChange={(e) => {
                  handleChange('required', e.target.checked);
                  updateNode(selectedNodeId!, { required: e.target.checked });
                }}
                className="w-4 h-4 text-blue-500 rounded focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Обязательный вопрос</span>
            </label>
          </div>
        )}
      </div>
      
      {/* Варианты ответа */}
      {config.has_options && (
        <div className="border-b border-gray-100">
          <button
            onClick={() => toggleSection('options')}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50"
          >
            <span className="font-medium text-sm text-gray-700">
              Варианты ответа ({localData.options?.length || 0})
            </span>
            {expandedSections.options ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          
          {expandedSections.options && (
            <div className="px-4 pb-4 space-y-2">
              {(localData.options || []).map((option: NodeOption, index: number) => (
                <div 
                  key={option.id} 
                  className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg"
                >
                  <GripVertical size={14} className="text-gray-400 cursor-move" />
                  <input
                    type="text"
                    value={option.text}
                    onChange={(e) => handleUpdateOption(index, 'text', e.target.value)}
                    onBlur={handleOptionsBlur}
                    className="flex-1 px-2 py-1 text-sm border border-gray-200 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Текст варианта"
                  />
                  <button
                    onClick={() => handleDeleteOption(index)}
                    className="p-1 text-red-500 hover:bg-red-50 rounded"
                    title="Удалить"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
              
              <button
                onClick={handleAddOption}
                className="w-full py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg flex items-center justify-center gap-2 border border-dashed border-blue-300"
              >
                <Plus size={16} />
                Добавить вариант
              </button>
            </div>
          )}
        </div>
      )}
      
      {/* Дополнительные поля ввода (только для multi_choice_with_input) */}
      {nodeData.type === 'multi_choice_with_input' && (
        <div className="border-b border-gray-100">
          <button
            onClick={() => toggleSection('additional_fields')}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50"
          >
            <span className="font-medium text-sm text-gray-700">
              Доп. поля ввода ({localData.additional_fields?.length || 0})
            </span>
            {expandedSections.additional_fields ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {expandedSections.additional_fields && (
            <div className="px-4 pb-4 space-y-3">
              <p className="text-xs text-gray-500">
                Поля, которые появятся ниже вариантов выбора.
              </p>

              {(localData.additional_fields || []).map((field: AdditionalField, index: number) => (
                <div key={field.id} className="p-3 bg-gray-50 rounded-lg space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-500 uppercase">
                      {field.type === 'text' ? '↔ Текст' : '# Число'}
                    </span>
                    <button
                      onClick={() => handleDeleteAdditionalField(index)}
                      className="p-1 text-red-500 hover:bg-red-50 rounded"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>

                  <input
                    type="text"
                    value={field.label}
                    onChange={(e) => handleUpdateAdditionalField(index, { label: e.target.value })}
                    onBlur={handleAdditionalFieldBlur}
                    placeholder="Название поля"
                    className="w-full px-2 py-1 text-sm border border-gray-200 rounded focus:ring-2 focus:ring-blue-500"
                  />

                  <input
                    type="text"
                    value={field.placeholder || ''}
                    onChange={(e) => handleUpdateAdditionalField(index, { placeholder: e.target.value })}
                    onBlur={handleAdditionalFieldBlur}
                    placeholder="Placeholder (placeholder)"
                    className="w-full px-2 py-1 text-sm border border-gray-200 rounded focus:ring-2 focus:ring-blue-500"
                  />

                  {field.type === 'number' && (
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="number"
                        value={field.min ?? ''}
                        onChange={(e) => handleUpdateAdditionalField(index, { min: parseInt(e.target.value) || undefined })}
                        onBlur={handleAdditionalFieldBlur}
                        placeholder="Мин"
                        className="w-full px-2 py-1 text-sm border border-gray-200 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <input
                        type="number"
                        value={field.max ?? ''}
                        onChange={(e) => handleUpdateAdditionalField(index, { max: parseInt(e.target.value) || undefined })}
                        onBlur={handleAdditionalFieldBlur}
                        placeholder="Макс"
                        className="w-full px-2 py-1 text-sm border border-gray-200 rounded focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  )}
                </div>
              ))}

              <div className="flex gap-2">
                <button
                  onClick={() => handleAddAdditionalField('text')}
                  className="flex-1 py-2 text-sm text-purple-600 hover:bg-purple-50 rounded-lg flex items-center justify-center gap-1 border border-dashed border-purple-300"
                >
                  <Plus size={14} /> Текст
                </button>
                <button
                  onClick={() => handleAddAdditionalField('number')}
                  className="flex-1 py-2 text-sm text-purple-600 hover:bg-purple-50 rounded-lg flex items-center justify-center gap-1 border border-dashed border-purple-300"
                >
                  <Plus size={14} /> Число
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Настройка взаимоисключающего варианта для multi_choice */}
      {(nodeData.type === 'multi_choice' || nodeData.type === 'multi_choice_with_input') &&
        (localData.options || []).length > 0 && (
        <div className="border-b border-gray-100">
          <button
            onClick={() => toggleSection('exclusive')}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50"
          >
            <span className="font-medium text-sm text-gray-700">Настройки исключения</span>
            {expandedSections.exclusive ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {expandedSections.exclusive && (
            <div className="px-4 pb-4 space-y-3">
              <p className="text-xs text-gray-500">
                Выбранный вариант снимает все остальные при выборе—и наоборот.
              </p>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Вариант-исключение
                </label>
                <select
                  value={localData.exclusive_option || ''}
                  onChange={(e) => {
                    const val = e.target.value || undefined;
                    handleChange('exclusive_option', val);
                    updateNode(selectedNodeId!, { exclusive_option: val });
                  }}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
                >
                  <option value="">— не задан —</option>
                  {(localData.options || []).map((opt: NodeOption) => (
                    <option key={opt.id} value={opt.value || opt.id}>
                      {opt.text}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Настройки для slider */}
      {config.has_min_max && (
        <div className="border-b border-gray-100">
          <button
            onClick={() => toggleSection('settings')}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50"
          >
            <span className="font-medium text-sm text-gray-700">Настройки шкалы</span>
            {expandedSections.settings ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          
          {expandedSections.settings && (
            <div className="px-4 pb-4 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Мин. значение
                  </label>
                  <input
                    type="number"
                    value={localData.min_value ?? 1}
                    onChange={(e) => handleChange('min_value', parseInt(e.target.value))}
                    onBlur={handleBlur}
                    className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Макс. значение
                  </label>
                  <input
                    type="number"
                    value={localData.max_value ?? 10}
                    onChange={(e) => handleChange('max_value', parseInt(e.target.value))}
                    onBlur={handleBlur}
                    className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Шаг
                </label>
                <input
                  type="number"
                  value={localData.step ?? 1}
                  onChange={(e) => handleChange('step', parseInt(e.target.value))}
                  onBlur={handleBlur}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Настройки для text_input */}
      {nodeData.type === 'text_input' && (
        <div className="px-4 py-4 border-b border-gray-100 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Placeholder
            </label>
            <input
              type="text"
              value={localData.placeholder || ''}
              onChange={(e) => handleChange('placeholder', e.target.value)}
              onBlur={handleBlur}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Введите текст..."
            />
          </div>
          
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Макс. длина текста
            </label>
            <input
              type="number"
              value={localData.max_length || ''}
              onChange={(e) => handleChange('max_length', parseInt(e.target.value) || undefined)}
              onBlur={handleBlur}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Без ограничения"
            />
          </div>
        </div>
      )}
      
      {/* Настройки для info_screen */}
      {nodeData.type === 'info_screen' && (
        <div className="px-4 py-4 border-b border-gray-100">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={localData.is_final ?? true}
              onChange={(e) => {
                handleChange('is_final', e.target.checked);
                updateNode(selectedNodeId!, { is_final: e.target.checked });
              }}
              className="w-4 h-4 text-blue-500 rounded focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Финальный экран (конец опроса)</span>
          </label>
        </div>
      )}
      
      {/* Группа вопроса (для итогового отчёта) */}
      <div className="px-4 py-4 border-b border-gray-100">
        <label className="block text-xs font-medium text-gray-600 mb-2">
          Группа отчёта
        </label>
        <select
          value={nodeData.group_id || ''}
          onChange={(e) => {
            const val = e.target.value || null;
            assignNodeToGroup(selectedNodeId!, val);
          }}
          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
        >
          <option value="">— без группы —</option>
          {groups.map(g => (
            <option key={g.id} value={g.id}>{g.name}</option>
          ))}
        </select>
        <p className="text-xs text-gray-400 mt-1">
          Вопросы одной группы объединяются в отчёте для врача
        </p>
      </div>

      {/* Связи */}
      <div className="px-4 py-4">
        <h4 className="text-xs font-medium text-gray-600 mb-2">
          Переходы ({outgoingEdges.length})
        </h4>
        
        {outgoingEdges.length === 0 ? (
          <p className="text-xs text-gray-400">
            Соедините с другим узлом, чтобы создать переход
          </p>
        ) : (
          <div className="space-y-2">
            {outgoingEdges.map(edge => {
              const targetNode = nodes.find(n => n.id === edge.target);
              return (
                <div 
                  key={edge.id}
                  className="flex items-center gap-2 p-2 bg-gray-50 rounded text-xs"
                >
                  <span className="text-gray-500">→</span>
                  <span className="font-medium truncate flex-1">
                    {targetNode?.data.question_text || edge.target}
                  </span>
                  {edge.data?.condition && (
                    <span className="text-blue-600 text-xs">
                      {edge.data.condition}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default NodeEditor;

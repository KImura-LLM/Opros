// ============================================
// Модальное окно предпросмотра опросника
// ============================================

import { useState, useEffect } from 'react';
import { X, ChevronRight, ChevronLeft, CheckCircle } from 'lucide-react';
import { useEditorStore } from '../store';
import { SurveyNodeData, NodeType } from '../types';
import { BodyMap } from '../../components/inputs/BodyMap';

interface PreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const PreviewModal = ({ isOpen, onClose }: PreviewModalProps) => {
  const { nodes, edges, survey } = useEditorStore();
  
  const [currentNodeId, setCurrentNodeId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [history, setHistory] = useState<string[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  
  // Инициализация при открытии
  useEffect(() => {
    if (isOpen && survey) {
      const startNode = nodes.find(n => n.data.isStart)?.id || survey.start_node || nodes[0]?.id;
      setCurrentNodeId(startNode);
      setAnswers({});
      setHistory([]);
      setIsComplete(false);
    }
  }, [isOpen, survey, nodes]);
  
  if (!isOpen) return null;
  
  const currentNode = nodes.find(n => n.id === currentNodeId);
  const nodeData = currentNode?.data as SurveyNodeData | undefined;
  
  // Определение следующего узла на основе логики
  const getNextNode = (): string | null => {
    if (!nodeData) return null;
    
    const nodeEdges = edges.filter(e => e.source === currentNodeId);
    
    if (nodeEdges.length === 0) return null;
    
    // Находим подходящее правило
    const answer = answers[currentNodeId!];
    
    // Сначала ищем условные переходы
    for (const edge of nodeEdges) {
      if (edge.data?.condition) {
        const condition = edge.data.condition;
        
        // Простая проверка условий
        if (condition.includes("selected == '")) {
          const match = condition.match(/selected == '([^']+)'/);
          if (match && answer === match[1]) {
            return edge.target;
          }
        }
        
        if (condition.includes("selected contains '")) {
          const match = condition.match(/selected contains '([^']+)'/);
          if (match && Array.isArray(answer) && answer.includes(match[1])) {
            return edge.target;
          }
        }
      }
    }
    
    // Если условия не сработали, ищем переход по умолчанию
    const defaultEdge = nodeEdges.find(e => e.data?.isDefault || !e.data?.condition);
    return defaultEdge?.target || nodeEdges[0]?.target || null;
  };
  
  const handleAnswer = (value: unknown) => {
    if (!currentNodeId) return;
    setAnswers((prev: Record<string, unknown>) => ({ ...prev, [currentNodeId]: value }));
  };
  
  const handleNext = () => {
    if (!currentNodeId) return;
    
    const nextId = getNextNode();
    
    if (nextId) {
      setHistory((prev: string[]) => [...prev, currentNodeId]);
      setCurrentNodeId(nextId);
      
      // Проверяем, является ли следующий узел финальным
      const nextNode = nodes.find(n => n.id === nextId);
      if (nextNode?.data.is_final || nextNode?.data.type === 'info_screen') {
        // Показываем финальный экран, потом завершаем
      }
    } else {
      setIsComplete(true);
    }
  };
  
  const handleBack = () => {
    if (history.length === 0) return;
    
    const prevId = history[history.length - 1];
    setHistory((prev: string[]) => prev.slice(0, -1));
    setCurrentNodeId(prevId);
    setIsComplete(false);
  };
  
  const handleRestart = () => {
    const startNode = nodes.find(n => n.data.isStart)?.id || survey?.start_node || nodes[0]?.id;
    setCurrentNodeId(startNode);
    setAnswers({});
    setHistory([]);
    setIsComplete(false);
  };
  
  // Рендер контента в зависимости от типа узла
  const renderNodeContent = () => {
    if (!nodeData) return null;
    
    const currentAnswer = answers[currentNodeId!];
    
    switch (nodeData.type as NodeType) {
      case 'single_choice':
        return (
          <div className="space-y-2">
            {nodeData.options?.map(option => (
              <button
                key={option.id}
                onClick={() => handleAnswer(option.value || option.id)}
                className={`
                  w-full text-left p-4 rounded-lg border-2 transition-all
                  ${currentAnswer === (option.value || option.id)
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                  }
                `}
              >
                <div className="flex items-center gap-3">
                  <div className={`
                    w-5 h-5 rounded-full border-2 flex items-center justify-center
                    ${currentAnswer === (option.value || option.id)
                      ? 'border-blue-500 bg-blue-500'
                      : 'border-gray-300'
                    }
                  `}>
                    {currentAnswer === (option.value || option.id) && (
                      <div className="w-2 h-2 bg-white rounded-full" />
                    )}
                  </div>
                  <span>{option.text}</span>
                </div>
              </button>
            ))}
          </div>
        );
        
      case 'multi_choice':
      case 'multi_choice_with_input':
        const selectedValues = (currentAnswer as string[]) || [];
        return (
          <div className="space-y-2">
            {nodeData.options?.map(option => {
              const isSelected = selectedValues.includes(option.value || option.id);
              return (
                <button
                  key={option.id}
                  onClick={() => {
                    const value = option.value || option.id;
                    const newValues = isSelected
                      ? selectedValues.filter(v => v !== value)
                      : [...selectedValues, value];
                    handleAnswer(newValues);
                  }}
                  className={`
                    w-full text-left p-4 rounded-lg border-2 transition-all
                    ${isSelected
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                    }
                  `}
                >
                  <div className="flex items-center gap-3">
                    <div className={`
                      w-5 h-5 rounded border-2 flex items-center justify-center
                      ${isSelected
                        ? 'border-blue-500 bg-blue-500'
                        : 'border-gray-300'
                      }
                    `}>
                      {isSelected && <CheckCircle size={14} className="text-white" />}
                    </div>
                    <span>{option.text}</span>
                  </div>
                </button>
              );
            })}
          </div>
        );
        
      case 'text_input':
        return (
          <textarea
            value={(currentAnswer as string) || ''}
            onChange={(e) => handleAnswer(e.target.value)}
            placeholder={nodeData.placeholder || 'Введите ответ...'}
            maxLength={nodeData.max_length}
            className="w-full p-4 border-2 border-gray-200 rounded-lg focus:border-blue-500 focus:ring-0 resize-none"
            rows={4}
          />
        );
        
      case 'slider':
        const sliderValue = (currentAnswer as number) || nodeData.min_value || 1;
        return (
          <div className="space-y-4">
            <input
              type="range"
              min={nodeData.min_value || 1}
              max={nodeData.max_value || 10}
              step={nodeData.step || 1}
              value={sliderValue}
              onChange={(e) => handleAnswer(parseInt(e.target.value))}
              className="w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
            <div className="flex justify-between text-sm text-gray-500">
              <span>{nodeData.min_value || 1}</span>
              <span className="text-2xl font-bold text-blue-600">{sliderValue}</span>
              <span>{nodeData.max_value || 10}</span>
            </div>
          </div>
        );
        
      case 'info_screen':
        return (
          <div className="text-center py-8">
            <CheckCircle size={64} className="mx-auto text-green-500 mb-4" />
            <p className="text-gray-600">{nodeData.description}</p>
          </div>
        );

      case 'body_map':
        return (
          <BodyMap
            options={(nodeData.options || []).map(o => ({
              id: o.id,
              text: o.text,
              value: o.value || o.id,
              icon: o.icon
            }))}
            value={(currentAnswer as string[]) || []}
            onChange={(val) => handleAnswer(val)}
          />
        );
        
      case 'consent_screen':
        return (
          <div className="space-y-4">
            <p className="text-gray-600">{nodeData.description}</p>
            <label className="flex items-center gap-3 p-4 border rounded-lg bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors">
               <input 
                  type="checkbox" 
                  className="w-5 h-5 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                  checked={!!currentAnswer}
                  onChange={(e) => handleAnswer(e.target.checked)}
               />
               <span className="text-sm font-medium text-gray-700">Я даю согласие на обработку персональных данных</span>
            </label>
          </div>
        );

      default:
        return <p className="text-gray-500">Тип "{nodeData.type}" не поддерживается в предпросмотре</p>;
    }
  };
  
  // Проверка, можно ли перейти к следующему вопросу
  const canProceed = () => {
    if (!nodeData) return false;
    if (!nodeData.required) return true;
    if (nodeData.type === 'info_screen') return true;
    
    const answer = answers[currentNodeId!];
    
    if (answer === undefined || answer === null) return false;
    if (Array.isArray(answer) && answer.length === 0) return false;
    if (typeof answer === 'string' && answer.trim() === '') return false;
    
    return true;
  };
  
  // Прогресс
  const totalNodes = nodes.filter(n => n.data.type !== 'info_screen').length;
  const answeredNodes = history.length;
  const progress = totalNodes > 0 ? (answeredNodes / totalNodes) * 100 : 0;
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col">
        {/* Заголовок */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="font-semibold text-gray-800">Предпросмотр</h2>
            <p className="text-xs text-gray-500">
              {survey?.name} • Вопрос {history.length + 1}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <X size={20} />
          </button>
        </div>
        
        {/* Прогресс бар */}
        <div className="px-6 py-2">
          <div className="h-1 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
        
        {/* Контент */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {isComplete ? (
            <div className="text-center py-8">
              <CheckCircle size={64} className="mx-auto text-green-500 mb-4" />
              <h3 className="text-xl font-semibold text-gray-800 mb-2">
                Опрос завершён!
              </h3>
              <p className="text-gray-600 mb-4">
                Собрано {Object.keys(answers).length} ответов
              </p>
              <button
                onClick={handleRestart}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Пройти заново
              </button>
            </div>
          ) : nodeData ? (
            <>
              <h3 className="text-lg font-medium text-gray-800 mb-2">
                {nodeData.question_text}
                {nodeData.required && <span className="text-red-500 ml-1">*</span>}
              </h3>
              
              {nodeData.description && (
                <p className="text-sm text-gray-500 mb-4">
                  {nodeData.description}
                </p>
              )}
              
              {renderNodeContent()}
            </>
          ) : (
            <p className="text-gray-500 text-center">Узел не найден</p>
          )}
        </div>
        
        {/* Навигация */}
        {!isComplete && (
          <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
            <button
              onClick={handleBack}
              disabled={history.length === 0}
              className="
                flex items-center gap-2 px-4 py-2 
                text-gray-600 hover:bg-gray-100 rounded-lg
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              <ChevronLeft size={18} />
              Назад
            </button>
            
            <button
              onClick={handleNext}
              disabled={!canProceed()}
              className="
                flex items-center gap-2 px-4 py-2 
                bg-blue-600 text-white rounded-lg hover:bg-blue-700
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              {nodeData?.type === 'info_screen' && nodeData?.is_final ? 'Завершить' : 'Далее'}
              <ChevronRight size={18} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default PreviewModal;

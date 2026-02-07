// ============================================
// Кастомный узел для React Flow
// ============================================

import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { 
  CircleDot, 
  CheckSquare, 
  Type, 
  SlidersHorizontal, 
  User, 
  Info,
  ListPlus,
  Star,
  GripVertical,
  Trash2,
  Copy,
  ShieldCheck,
  LucideIcon,
} from 'lucide-react';
import { NODE_TYPE_CONFIG, NodeType, FlowNodeData } from '../types';
import { useEditorStore } from '../store';

// Иконки по типу
const ICONS: Record<NodeType, LucideIcon> = {
  single_choice: CircleDot,
  multi_choice: CheckSquare,
  multi_choice_with_input: ListPlus,
  text_input: Type,
  slider: SlidersHorizontal,
  body_map: User,
  info_screen: Info,
  consent_screen: ShieldCheck,
};

interface SurveyNodeProps {
  id: string;
  data: FlowNodeData;
  selected?: boolean;
}

const SurveyNode = memo(({ data, selected, id }: SurveyNodeProps) => {
  const { selectNode, deleteNode, duplicateNode, setStartNode } = useEditorStore();
  
  const config = NODE_TYPE_CONFIG[data.type] || {
    name: 'Неизвестный',
    color: '#6b7280',
    icon: 'info',
  };
  const Icon = ICONS[data.type] || Info;
  
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    selectNode(id);
  };
  
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Удалить этот узел?')) {
      deleteNode(id);
    }
  };
  
  const handleDuplicate = (e: React.MouseEvent) => {
    e.stopPropagation();
    duplicateNode(id);
  };
  
  const handleSetStart = (e: React.MouseEvent) => {
    e.stopPropagation();
    setStartNode(id);
  };
  
  return (
    <div
      onClick={handleClick}
      className={`
        relative min-w-[280px] max-w-[320px] rounded-lg shadow-lg 
        border-2 transition-all duration-200
        ${selected ? 'border-blue-500 shadow-blue-200' : 'border-gray-200'}
        ${data.isStart ? 'ring-2 ring-green-400 ring-offset-2' : ''}
        bg-white
      `}
      style={{ 
        borderLeftColor: config.color, 
        borderLeftWidth: 4,
      }}
    >
      {/* Входной Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-gray-400 !border-2 !border-white"
      />
      
      {/* Заголовок */}
      <div 
        className="px-3 py-2 border-b border-gray-100 flex items-center gap-2"
        style={{ backgroundColor: `${config.color}10` }}
      >
        <GripVertical size={14} className="text-gray-400 cursor-move" />
        <Icon size={16} style={{ color: config.color }} />
        <span className="text-xs font-medium text-gray-600">{config.name}</span>
        
        {data.isStart && (
          <span className="ml-auto text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full flex items-center gap-1">
            <Star size={10} />
            Старт
          </span>
        )}
        
        {data.required && !data.isStart && (
          <span className="ml-auto text-xs text-red-500">*</span>
        )}
      </div>
      
      {/* Контент */}
      <div className="px-3 py-3">
        <p className="text-sm font-medium text-gray-800 line-clamp-2">
          {data.question_text}
        </p>
        
        {data.description && (
          <p className="text-xs text-gray-500 mt-1 line-clamp-1">
            {data.description}
          </p>
        )}
        
        {/* Превью вариантов ответа */}
        {data.options && data.options.length > 0 && (
          <div className="mt-2 space-y-1">
            {data.options.slice(0, 3).map(opt => (
              <div key={opt.id} className="flex items-center gap-2 text-xs text-gray-600">
                {data.type === 'single_choice' ? (
                  <div className="w-3 h-3 rounded-full border border-gray-300" />
                ) : (
                  <div className="w-3 h-3 rounded border border-gray-300" />
                )}
                <span className="truncate">{opt.text}</span>
              </div>
            ))}
            {data.options.length > 3 && (
              <span className="text-xs text-gray-400">
                +{data.options.length - 3} ещё...
              </span>
            )}
          </div>
        )}
      </div>
      
      {/* Панель действий */}
      {selected && (
        <div className="absolute -top-2 -right-2 flex gap-1">
          {!data.isStart && (
            <button
              onClick={handleSetStart}
              className="p-1.5 bg-green-500 text-white rounded-full shadow hover:bg-green-600 transition"
              title="Сделать стартовым"
            >
              <Star size={12} />
            </button>
          )}
          <button
            onClick={handleDuplicate}
            className="p-1.5 bg-blue-500 text-white rounded-full shadow hover:bg-blue-600 transition"
            title="Дублировать"
          >
            <Copy size={12} />
          </button>
          <button
            onClick={handleDelete}
            className="p-1.5 bg-red-500 text-white rounded-full shadow hover:bg-red-600 transition"
            title="Удалить"
          >
            <Trash2 size={12} />
          </button>
        </div>
      )}
      
      {/* Выходной Handle */}
      {data.type !== 'info_screen' && (
        <Handle
          type="source"
          position={Position.Bottom}
          className="!w-3 !h-3 !bg-blue-500 !border-2 !border-white"
        />
      )}
    </div>
  );
});

SurveyNode.displayName = 'SurveyNode';

export default SurveyNode;

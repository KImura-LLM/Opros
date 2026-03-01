// ============================================
// Панель инструментов (палитра узлов + группы)
// ============================================

import { useState } from 'react';
import { LucideIcon } from 'lucide-react';
import { 
  CircleDot, 
  CheckSquare, 
  Type, 
  SlidersHorizontal, 
  User, 
  Info,
  ListPlus,
  GripVertical,
  ShieldCheck,
  FolderOpen,
} from 'lucide-react';
import { NODE_TYPE_CONFIG, NodeType } from '../types';
import GroupsPanel from './GroupsPanel';

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

// Вкладки левой панели
type PaletteTab = 'types' | 'groups';

interface NodePaletteProps {
  onDragStart: (event: React.DragEvent, nodeType: NodeType) => void;
}

const NodePalette = ({ onDragStart }: NodePaletteProps) => {
  const nodeTypes = Object.values(NODE_TYPE_CONFIG);
  const [activeTab, setActiveTab] = useState<PaletteTab>('types');
  
  return (
    <div>
      {/* Переключатель вкладок */}
      <div className="flex mb-4 border border-gray-200 rounded-lg overflow-hidden">
        <button
          onClick={() => setActiveTab('types')}
          className={`
            flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors
            ${activeTab === 'types'
              ? 'bg-blue-600 text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
            }
          `}
        >
          <GripVertical size={14} />
          Типы вопросов
        </button>
        <button
          onClick={() => setActiveTab('groups')}
          className={`
            flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors
            ${activeTab === 'groups'
              ? 'bg-blue-600 text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
            }
          `}
        >
          <FolderOpen size={14} />
          Группы
        </button>
      </div>
      
      {/* Содержимое вкладки */}
      {activeTab === 'types' ? (
        <div className="bg-white rounded-lg shadow-lg p-4 w-64">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <GripVertical size={16} />
            Типы вопросов
          </h3>
          
          <p className="text-xs text-gray-500 mb-4">
            Перетащите на холст для добавления
          </p>
          
          <div className="space-y-2">
            {nodeTypes.map(nodeType => {
              const Icon = ICONS[nodeType.id];
              
              return (
                <div
                  key={nodeType.id}
                  draggable
                  onDragStart={(e) => onDragStart(e, nodeType.id)}
                  className="
                    flex items-center gap-3 p-3 rounded-lg border border-gray-200
                    cursor-grab hover:border-gray-300 hover:shadow-sm
                    active:cursor-grabbing transition-all duration-150
                    bg-gradient-to-r from-white to-gray-50
                  "
                  style={{ borderLeftColor: nodeType.color, borderLeftWidth: 3 }}
                >
                  <div 
                    className="p-2 rounded-lg"
                    style={{ backgroundColor: `${nodeType.color}15` }}
                  >
                    <Icon size={18} style={{ color: nodeType.color }} />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800">
                      {nodeType.name}
                    </p>
                    <p className="text-xs text-gray-500 truncate">
                      {nodeType.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <GroupsPanel />
      )}
    </div>
  );
};

export default NodePalette;

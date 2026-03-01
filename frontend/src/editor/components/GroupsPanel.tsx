// ============================================
// Панель управления группами вопросов
// ============================================

import { useState } from 'react';
import { Plus, Trash2, Pencil, Check, X, FolderOpen } from 'lucide-react';
import { useEditorStore } from '../store';

const GroupsPanel = () => {
  const { groups, addGroup, updateGroup, deleteGroup, nodes } = useEditorStore();
  
  const [newGroupName, setNewGroupName] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  
  // Подсчёт узлов в каждой группе
  const getNodeCount = (groupId: string) => {
    return nodes.filter(n => n.data.group_id === groupId).length;
  };
  
  // Создание группы
  const handleAdd = () => {
    const name = newGroupName.trim();
    if (!name) return;
    addGroup(name);
    setNewGroupName('');
  };
  
  // Начало редактирования
  const handleStartEdit = (groupId: string, currentName: string) => {
    setEditingId(groupId);
    setEditingName(currentName);
  };
  
  // Сохранение редактирования
  const handleSaveEdit = () => {
    if (!editingId) return;
    const name = editingName.trim();
    if (name) {
      updateGroup(editingId, name);
    }
    setEditingId(null);
    setEditingName('');
  };
  
  // Отмена редактирования
  const handleCancelEdit = () => {
    setEditingId(null);
    setEditingName('');
  };
  
  // Удаление группы
  const handleDelete = (groupId: string) => {
    const count = getNodeCount(groupId);
    const msg = count > 0
      ? `Удалить группу? У ${count} вопрос(ов) будет снята привязка к этой группе.`
      : 'Удалить группу?';
    if (confirm(msg)) {
      deleteGroup(groupId);
    }
  };
  
  return (
    <div className="bg-white rounded-lg shadow-lg p-4 w-64 mt-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
        <FolderOpen size={16} />
        Группы отчёта
      </h3>
      
      <p className="text-xs text-gray-500 mb-4">
        Группы для структурирования итогового отчёта врачу
      </p>
      
      {/* Список существующих групп */}
      <div className="space-y-2 mb-4">
        {groups.length === 0 && (
          <p className="text-xs text-gray-400 italic">
            Нет созданных групп
          </p>
        )}
        
        {groups.map(group => (
          <div
            key={group.id}
            className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg border border-gray-200"
          >
            {editingId === group.id ? (
              // Режим редактирования
              <>
                <input
                  type="text"
                  value={editingName}
                  onChange={(e) => setEditingName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSaveEdit();
                    if (e.key === 'Escape') handleCancelEdit();
                  }}
                  className="flex-1 px-2 py-1 text-sm border border-blue-400 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  autoFocus
                />
                <button
                  onClick={handleSaveEdit}
                  className="p-1 text-green-600 hover:bg-green-50 rounded"
                  title="Сохранить"
                >
                  <Check size={14} />
                </button>
                <button
                  onClick={handleCancelEdit}
                  className="p-1 text-gray-400 hover:bg-gray-100 rounded"
                  title="Отмена"
                >
                  <X size={14} />
                </button>
              </>
            ) : (
              // Режим просмотра
              <>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">
                    {group.name}
                  </p>
                  <p className="text-xs text-gray-400">
                    {getNodeCount(group.id)} вопрос(ов)
                  </p>
                </div>
                <button
                  onClick={() => handleStartEdit(group.id, group.name)}
                  className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                  title="Переименовать"
                >
                  <Pencil size={13} />
                </button>
                <button
                  onClick={() => handleDelete(group.id)}
                  className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                  title="Удалить"
                >
                  <Trash2 size={13} />
                </button>
              </>
            )}
          </div>
        ))}
      </div>
      
      {/* Форма добавления новой группы */}
      <div className="flex gap-2">
        <input
          type="text"
          value={newGroupName}
          onChange={(e) => setNewGroupName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleAdd();
          }}
          placeholder="Название группы..."
          className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <button
          onClick={handleAdd}
          disabled={!newGroupName.trim()}
          className="
            p-2 text-white bg-blue-600 rounded-lg
            hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed
            transition-colors
          "
          title="Добавить группу"
        >
          <Plus size={16} />
        </button>
      </div>
    </div>
  );
};

export default GroupsPanel;

// ============================================
// Главный компонент редактора опросника
// ============================================

import { useCallback, useEffect, useState, useRef } from 'react';
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  Connection,
  NodeChange,
  EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
  ReactFlowProvider,
  ConnectionLineType,
  Node,
  Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import './editor.css';

import { useEditorStore } from './store';
import { NodeType, FlowNode, FlowEdge, NODE_TYPE_CONFIG } from './types';
import SurveyNode from './components/SurveyNode';
import NodePalette from './components/NodePalette';
import NodeEditor from './components/NodeEditor';
import Toolbar from './components/Toolbar';
import PreviewModal from './components/PreviewModal';
import EdgeEditor from './components/EdgeEditor';

// Регистрация кастомных узлов
const nodeTypes = {
  surveyNode: SurveyNode,
};

interface SurveyEditorProps {
  surveyId: number;
}

const SurveyEditorInner = ({ surveyId }: SurveyEditorProps) => {
  const {
    nodes: storeNodes,
    edges: storeEdges,
    setNodes,
    setEdges,
    addNode,
    selectNode,
    selectedNodeId,
    loadSurvey,
    isLoading,
    error,
    addEdge: storeAddEdge,
  } = useEditorStore();

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [nodes, setLocalNodes] = useNodesState<any>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [edges, setLocalEdges] = useEdgesState<any>([]);
  const [showPreview, setShowPreview] = useState(false);
  const [selectedEdge, setSelectedEdge] = useState<FlowEdge | null>(null);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);

  // Синхронизация со store
  useEffect(() => {
    setLocalNodes(storeNodes as Node[]);
  }, [storeNodes, setLocalNodes]);

  useEffect(() => {
    setLocalEdges(storeEdges as Edge[]);
  }, [storeEdges, setLocalEdges]);

  // Загрузка опросника при монтировании
  useEffect(() => {
    loadSurvey(surveyId);

    // Cleanup при размонтировании
    return () => {
      useEditorStore.getState().stopAutosave();
    };
  }, [surveyId, loadSurvey]);

  // Горячие клавиши
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+Z - Undo
      if (e.ctrlKey && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        useEditorStore.getState().undo();
      }

      // Ctrl+Y или Ctrl+Shift+Z - Redo
      if ((e.ctrlKey && e.key === 'y') || (e.ctrlKey && e.shiftKey && e.key === 'z')) {
        e.preventDefault();
        useEditorStore.getState().redo();
      }

      // Ctrl+S - Save
      if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        useEditorStore.getState().saveSurvey();
      }

      // Delete - Delete selected node
      if (e.key === 'Delete' && selectedNodeId) {
        e.preventDefault();
        useEditorStore.getState().deleteNode(selectedNodeId);
      }

      // Escape - Deselect
      if (e.key === 'Escape') {
        selectNode(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedNodeId, selectNode]);

  // Обработка изменения узлов
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const newNodes = applyNodeChanges(changes, nodes) as FlowNode[];
      setLocalNodes(newNodes);
      
      // Синхронизация с store только для перемещения
      const hasPositionChange = changes.some(
        c => c.type === 'position' && c.dragging === false
      );
      if (hasPositionChange) {
        setNodes(newNodes);
      }
    },
    [nodes, setLocalNodes, setNodes]
  );

  // Обработка изменения связей
  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      const newEdges = applyEdgeChanges(changes, edges) as FlowEdge[];
      setLocalEdges(newEdges);
      
      // Синхронизация с store при удалении
      const hasRemove = changes.some(c => c.type === 'remove');
      if (hasRemove) {
        setEdges(newEdges);
      }
    },
    [edges, setLocalEdges, setEdges]
  );

  // Создание новой связи
  const handleConnect = useCallback(
    (connection: Connection) => {
      if (connection.source && connection.target) {
        storeAddEdge(connection.source, connection.target);
      }
    },
    [storeAddEdge]
  );

  // Drag and drop нового узла
  const handleDragStart = useCallback(
    (event: React.DragEvent, nodeType: NodeType) => {
      event.dataTransfer.setData('application/reactflow', nodeType);
      event.dataTransfer.effectAllowed = 'move';
    },
    []
  );

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow') as NodeType;
      if (!type || !NODE_TYPE_CONFIG[type]) return;

      const reactFlowBounds = reactFlowWrapper.current?.getBoundingClientRect();
      if (!reactFlowBounds || !reactFlowInstance) return;

      const position = (reactFlowInstance as { screenToFlowPosition: (pos: { x: number; y: number }) => { x: number; y: number } }).screenToFlowPosition({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      addNode(type, position);
    },
    [reactFlowInstance, addNode]
  );

  // Клик на canvas для снятия выделения
  const handlePaneClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  // Клик на узле
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: any) => {
      selectNode(node.id);
      setSelectedEdge(null);
    },
    [selectNode]
  );

  // Клик на связи
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleEdgeClick = useCallback(
    (_: React.MouseEvent, edge: any) => {
      selectNode(null);
      setSelectedEdge(edge as FlowEdge);
    },
    [selectNode]
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Загрузка опросника...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center bg-white p-8 rounded-lg shadow-lg">
          <p className="text-red-600 font-semibold mb-2">Ошибка загрузки</p>
          <p className="text-gray-600">{error}</p>
          <button
            onClick={() => loadSurvey(surveyId)}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Попробовать снова
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Тулбар */}
      <Toolbar onPreview={() => setShowPreview(true)} />

      {/* Основная область */}
      <div className="flex-1 flex overflow-hidden">
        {/* Левая панель - палитра узлов */}
        <div className="w-72 p-4 overflow-y-auto bg-gray-50 border-r border-gray-200">
          <NodePalette onDragStart={handleDragStart} />
        </div>

        {/* Центр - React Flow canvas */}
        <div className="flex-1" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onConnect={handleConnect}
            onInit={setReactFlowInstance}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onPaneClick={handlePaneClick}
            onNodeClick={handleNodeClick}
            onEdgeClick={handleEdgeClick}
            nodeTypes={nodeTypes}
            fitView
            snapToGrid
            snapGrid={[15, 15]}
            defaultEdgeOptions={{
              type: 'smoothstep',
              animated: false,
              style: { strokeWidth: 2 },
            }}
            connectionLineType={ConnectionLineType.SmoothStep}
            proOptions={{ hideAttribution: true }}
          >
            <Controls />
            <MiniMap 
              nodeStrokeWidth={3}
              pannable
              zoomable
              style={{
                backgroundColor: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
              }}
            />
      
      {/* Редактор связи */}
      <EdgeEditor edge={selectedEdge} onClose={() => setSelectedEdge(null)} />
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
          </ReactFlow>
        </div>

        {/* Правая панель - редактор узла */}
        <div className="w-80 p-4 overflow-y-auto bg-gray-50 border-l border-gray-200">
          <NodeEditor />
        </div>
      </div>

      {/* Модал предпросмотра */}
      <PreviewModal isOpen={showPreview} onClose={() => setShowPreview(false)} />
    </div>
  );
};

// Оборачиваем в ReactFlowProvider
const SurveyEditor = (props: SurveyEditorProps) => (
  <ReactFlowProvider>
    <SurveyEditorInner {...props} />
  </ReactFlowProvider>
);

export default SurveyEditor;

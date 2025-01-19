import React, { useRef, useState } from 'react';
import { useDrag, useDrop, DropTargetMonitor } from 'react-dnd';
import { useApp } from '../contexts/AppContext';
import type { Capability } from '../types/api';

interface DragItem {
  id: number;
  type: string;
  parentId: number | null;
  index: number;
  capability: Capability;
  width?: number;
  height?: number;
}

interface Props {
  capability: Capability;
  index: number;
  parentId: number | null;
  onEdit: (capability: Capability) => void;
  onDelete?: (capability: Capability) => void;
}

interface DropResult {
  moved: boolean;
}

// Global state for copied capability
let copiedCapability: Capability | null = null;

// Helper function to check if a capability is a descendant of another
const isDescendantOf = (capability: Capability, potentialAncestorId: number): boolean => {
  if (!capability.children) return false;
  return capability.children.some(child => 
    child.id === potentialAncestorId || isDescendantOf(child, potentialAncestorId)
  );
};

export const DraggableCapability: React.FC<Props> = ({
  capability,
  index,
  parentId,
  onEdit,
}) => {
  const ref = useRef<HTMLDivElement>(null);
  const { 
    userSession, 
    moveCapability, 
    activeUsers, 
    createCapability, 
    deleteCapability,
    currentDropTarget,
    setCurrentDropTarget 
  } = useApp();
  const [isExpanded, setIsExpanded] = useState(true);

  const isLocked = activeUsers.some(user => 
    user.locked_capabilities.includes(capability.id) && 
    user.session_id !== userSession?.session_id
  );

  const [{ isDragging }, drag] = useDrag({
    type: 'CAPABILITY',
    item: () => {
      if (ref.current) {
        const rect = ref.current.getBoundingClientRect();
        return {
          id: capability.id,
          type: 'CAPABILITY',
          parentId,
          index,
          width: rect.width,
          height: rect.height,
          capability,
        };
      }
      return { 
        id: capability.id, 
        type: 'CAPABILITY', 
        parentId, 
        index,
        capability,
      };
    },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
    canDrag: !isLocked,
    end: (item, monitor) => {
      if (!monitor.didDrop()) {
        if (isLocked) {
          const element = ref.current;
          if (element) {
            element.classList.add('shake-animation');
            setTimeout(() => {
              element.classList.remove('shake-animation');
            }, 500);
          }
        }
      }
      setCurrentDropTarget(null);
    },
  });

  const [{ isOver, canDrop }, drop] = useDrop<DragItem, DropResult, { isOver: boolean; canDrop: boolean }>({
    accept: 'CAPABILITY',
    canDrop: (item: DragItem) => {
      // Prevent dropping on self or descendants
      if (item.id === capability.id) return false;
      if (isDescendantOf(item.capability, capability.id)) return false;
      return true;
    },
  hover: (item: DragItem, monitor: DropTargetMonitor) => {
      if (!monitor.isOver({ shallow: true })) return;
      if (!ref.current || item.id === capability.id) return;
      if (isDescendantOf(item.capability, capability.id)) return;

      const newDropTarget = {
        capabilityId: capability.id,
        type: 'child' as const
      };

      if (!currentDropTarget || currentDropTarget.capabilityId !== newDropTarget.capabilityId) {
        setCurrentDropTarget(newDropTarget);
      }
    },
  drop: (item: DragItem) => {
      if (!currentDropTarget) return { moved: false };

      // Always make the dropped item a child of the target
      const targetPosition = {
        targetParentId: capability.id,
        targetIndex: capability.children?.length || 0
      };

      // If dropping on same parent, still allow it but place at end
      // This enables re-attaching to same parent if desired
      moveCapability(item.id, targetPosition.targetParentId, targetPosition.targetIndex)
        .then(() => {
          // Success is handled by the context refreshing the tree
        })
        .catch(error => {
          console.error('Failed to move capability:', error);
        });

      // Return synchronously - the actual move will happen asynchronously
      return { moved: true };
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
      canDrop: monitor.canDrop(),
    }),
  });

  drag(drop(ref));

  return (
    <div
      ref={ref}
      className={`
        py-1.5 px-2 mb-1 rounded-lg border relative capability-container capability-transition
        ${isDragging ? 'opacity-50 dragging' : 'opacity-100'}
        ${isLocked ? 'border-red-300 bg-red-50 cursor-not-allowed' : 'border-gray-200 bg-white cursor-grab hover:border-blue-300'}
        ${isLocked ? 'shake-animation' : ''}
        ${isOver && canDrop && currentDropTarget?.capabilityId === capability.id ? 
          `drop-target-${currentDropTarget.type} active` : ''}
      `}
      style={{
        willChange: isDragging ? 'transform, opacity' : undefined,
        transform: isDragging ? 'translate3d(0,0,0)' : undefined,
        pointerEvents: isDragging ? 'none' : 'auto'
      }}
    >
      <div className="flex items-center group">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-0.5 text-gray-400 hover:text-gray-600"
          style={{ visibility: capability.children?.length ? 'visible' : 'hidden' }}
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d={isExpanded ? "M19 9l-7 7-7-7" : "M9 5l7 7-7 7"}
            />
          </svg>
        </button>
        <div className={`text-gray-400 ml-0.5 ${isLocked ? 'cursor-not-allowed' : 'cursor-grab active:cursor-grabbing'}`}>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9h8M8 15h8" />
          </svg>
        </div>
        <h3 className="font-medium text-gray-900 ml-2">{capability.name}</h3>
        <div className="flex items-center space-x-1 ml-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          {isLocked && (
            <span className="text-xs text-red-500">
              Locked by {activeUsers.find(u => 
                u.locked_capabilities.includes(capability.id)
              )?.nickname}
            </span>
          )}
          <button
            onClick={() => onEdit(capability)}
            className="p-0.5 text-gray-400 hover:text-gray-600"
            disabled={isLocked}
            title="Edit"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
          </button>
          <button
            onClick={() => {
              copiedCapability = capability;
            }}
            className="p-0.5 text-gray-400 hover:text-gray-600"
            disabled={isLocked}
            title="Copy"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
            </svg>
          </button>
          <button
            onClick={async () => {
              if (copiedCapability) {
                await createCapability(copiedCapability.name, capability.id);
              }
            }}
            className="p-0.5 text-gray-400 hover:text-gray-600"
            disabled={isLocked || !copiedCapability}
            title="Paste"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </button>
          <button
            onClick={async () => {
              if (window.confirm('Are you sure you want to delete this capability?')) {
                await deleteCapability(capability.id);
              }
            }}
            className="p-0.5 text-gray-400 hover:text-gray-600"
            disabled={isLocked}
            title="Delete"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
      {capability.children && capability.children.length > 0 && isExpanded && (
        <div className="pl-4 mt-1 border-l border-gray-100">
          {capability.children.map((child, childIndex) => (
            <DraggableCapability
              key={child.id}
              capability={child}
              index={childIndex}
              parentId={capability.id}
              onEdit={onEdit}
            />
          ))}
        </div>
      )}
    </div>
  );
};

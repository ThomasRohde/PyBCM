import React, { useRef } from 'react';
import { useDrag, useDrop } from 'react-dnd';
import { useApp } from '../contexts/AppContext';
import type { Capability } from '../types/api';

interface DragItem {
  id: number;
  type: string;
  parentId: number | null;
  index: number;
}

interface Props {
  capability: Capability;
  index: number;
  parentId: number | null;
  onEdit: (capability: Capability) => void;
}

export const DraggableCapability: React.FC<Props> = ({
  capability,
  index,
  parentId,
  onEdit,
}) => {
  const ref = useRef<HTMLDivElement>(null);
  const { userSession, moveCapability, activeUsers } = useApp();

  const isLocked = activeUsers.some(user => 
    user.locked_capabilities.includes(capability.id) && 
    user.session_id !== userSession?.session_id
  );

  const [{ isDragging }, drag] = useDrag({
    type: 'CAPABILITY',
    item: { id: capability.id, type: 'CAPABILITY', parentId, index },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
    canDrag: !isLocked,
  });

  const [{ isOver }, drop] = useDrop({
    accept: 'CAPABILITY',
    hover: (item: DragItem, monitor) => {
      if (!ref.current) return;
      
      const dragIndex = item.index;
      const hoverIndex = index;
      const dragParentId = item.parentId;
      const hoverParentId = parentId;

      // Don't replace items with themselves
      if (dragIndex === hoverIndex && dragParentId === hoverParentId) {
        return;
      }

      // Get rectangle on screen
      const hoverBoundingRect = ref.current.getBoundingClientRect();
      
      // Get vertical middle
      const hoverMiddleY = (hoverBoundingRect.bottom - hoverBoundingRect.top) / 2;
      
      // Get mouse position
      const clientOffset = monitor.getClientOffset();
      if (!clientOffset) return;
      
      // Get pixels to the top
      const hoverClientY = clientOffset.y - hoverBoundingRect.top;

      // Only perform the move when the mouse has crossed half of the items height
      if (dragIndex < hoverIndex && hoverClientY < hoverMiddleY) return;
      if (dragIndex > hoverIndex && hoverClientY > hoverMiddleY) return;

      // Time to actually perform the action
      moveCapability(item.id, hoverParentId, hoverIndex);

      // Note: we're mutating the monitor item here!
      // Generally it's better to avoid mutations,
      // but it's good here for the sake of performance
      // to avoid expensive index searches.
      item.index = hoverIndex;
      item.parentId = hoverParentId;
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
    }),
  });

  drag(drop(ref));

  return (
    <div
      ref={ref}
      className={`
        p-3 mb-2 rounded-lg border 
        ${isDragging ? 'opacity-50' : 'opacity-100'}
        ${isOver ? 'bg-blue-50' : 'bg-white'}
        ${isLocked ? 'border-red-300' : 'border-gray-200'}
        transition-colors duration-200
      `}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <h3 className="font-medium text-gray-900">{capability.name}</h3>
          {capability.description && (
            <p className="text-sm text-gray-500">{capability.description}</p>
          )}
        </div>
        <div className="flex items-center space-x-2">
          {isLocked && (
            <span className="text-xs text-red-500">
              Locked by {activeUsers.find(u => 
                u.locked_capabilities.includes(capability.id)
              )?.nickname}
            </span>
          )}
          <button
            onClick={() => onEdit(capability)}
            className="p-1 text-gray-400 hover:text-gray-600"
            disabled={isLocked}
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
              />
            </svg>
          </button>
        </div>
      </div>
      {capability.children && capability.children.length > 0 && (
        <div className="pl-6 mt-2 border-l border-gray-200">
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

import React, { useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { ApiClient } from '../api/client';
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

// Helper function to find the nearest locked ancestor by another user
const findLockedAncestor = (
  capabilities: Capability[], 
  parentId: number | null, 
  activeUsers: { session_id: string; nickname: string; locked_capabilities: number[]; }[],
  currentUserNickname?: string
): { nickname: string } | null => {
  if (!parentId) return null;
  
  const parent = capabilities.find(c => c.id === parentId);
  if (!parent) return null;

  // Check if parent is locked by another user
  const lockingUser = activeUsers.find(user => 
    user.locked_capabilities.includes(parent.id) && 
    user.nickname !== currentUserNickname
  );
  if (lockingUser) {
    return { nickname: lockingUser.nickname };
  }

  // Recursively check parent's parent
  return findLockedAncestor(capabilities, parent.parent_id, activeUsers, currentUserNickname);
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
    deleteCapability,
    currentDropTarget,
    setCurrentDropTarget,
  } = useApp();
  const [isExpanded, setIsExpanded] = useState(true);

  const { capabilities } = useApp();

  const directLockingUser = activeUsers.find(u => 
    u.locked_capabilities.includes(capability.id)
  );
  const ancestorLock = findLockedAncestor(capabilities, parentId, activeUsers, userSession?.nickname);

  const isLockedByMe = userSession && directLockingUser?.nickname === userSession.nickname;
  const isLockedByOthers = (directLockingUser && directLockingUser.nickname !== userSession?.nickname) || 
    ancestorLock !== null;

  const isLocked = isLockedByMe || isLockedByOthers;

  const effectiveLockingUser = directLockingUser || 
    (ancestorLock ? { nickname: ancestorLock.nickname } : null);

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
    canDrag: !isLockedByMe && !isLockedByOthers,
    end: (_, monitor) => {
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
      
      // Check if the dragged item is locked or its parent is locked
      const isDraggedItemLocked = activeUsers.some(user => 
        user.locked_capabilities.includes(item.id)
      );
      if (isDraggedItemLocked) return false;
      
      // Check if this capability is locked
      if (isLocked) return false;
      
      return true;
    },
    hover: (item: DragItem, monitor: DropTargetMonitor) => {
      if (!monitor.isOver({ shallow: true })) return;
      if (!ref.current || item.id === capability.id) return;
      if (isDescendantOf(item.capability, capability.id)) return;
      if (isLocked) return;

      // Always treat drops as child operations
      const newDropTarget = {
        capabilityId: capability.id,
        type: 'child' as const
      };

      // Only set if changed (prevents spamming state updates)
      if (!currentDropTarget || currentDropTarget.capabilityId !== newDropTarget.capabilityId) {
        setCurrentDropTarget(newDropTarget);
      }
    },
    drop: (item: DragItem) => {
      if (!currentDropTarget) return { moved: false };
      
      // Check if either item is locked
      const isDraggedItemLocked = activeUsers.some(user => 
        user.locked_capabilities.includes(item.id)
      );
      if (isDraggedItemLocked || isLocked) {
        toast.error('Cannot move locked capabilities');
        return { moved: false };
      }

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
          toast.error('Cannot move capability - target is locked');
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
    <div className="relative">
      {isOver && currentDropTarget?.capabilityId === capability.id && (
        <div className="absolute top-0 left-0 w-full flex items-center justify-center pointer-events-none z-10">
          <span className={`text-sm font-bold px-2 py-1 rounded ${canDrop ? 
            'text-gray-700 bg-gray-200' : 
            'text-red-700 bg-red-100'}`}>
            {canDrop ? 'Drop as Child' : 'Cannot Drop - Locked'}
          </span>
        </div>
      )}
      <div className={`
        py-1.5 px-2 mb-1 rounded-lg border relative capability-container capability-transition
        ${isLocked ? 'border-red-300' : 'border-gray-200'}
      `}>
        {/* Header section with drag and drop functionality */}
        <div
          ref={ref}
          className={`
            relative rounded
            ${isDragging ? 'opacity-50 dragging' : 'opacity-100'}
            ${isLocked ? 'bg-red-50 cursor-not-allowed' : 'bg-white cursor-grab hover:bg-gray-50'}
            ${isLocked ? 'shake-animation' : ''}
            ${isOver && currentDropTarget?.capabilityId === capability.id ? 
              canDrop ? `drop-target-${currentDropTarget.type} active` : 'drop-target-locked' : ''}
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
            <h3 
              className="flex-1 font-medium text-gray-900 ml-2" 
              title={!isDragging && capability.description ? capability.description : undefined}
            >
              {capability.name}
            </h3>
            <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              {isLocked && (
                <span className="text-xs text-red-500">
                  {directLockingUser ? 
                    `Locked by ${directLockingUser.nickname}` : 
                    `Locked by ancestor (${effectiveLockingUser?.nickname})`}
                </span>
              )}
              <button
                onClick={async () => {
                  if (!userSession) return;
                  try {
                    if (isLockedByMe) {
                      await ApiClient.unlockCapability(capability.id, userSession.nickname);
                    } else {
                      await ApiClient.lockCapability(capability.id, userSession.nickname);
                    }
                  } catch (error) {
                    console.error('Failed to toggle lock:', error);
                    toast.error('Failed to toggle lock');
                  }
                }}
                className={`p-0.5 ${isLockedByOthers ? 'text-red-500' : isLockedByMe ? 'text-blue-500' : 'text-gray-400 hover:text-gray-600'}`}
                disabled={Boolean(isLockedByOthers)}
                title={isLockedByOthers ? `Locked by ${effectiveLockingUser?.nickname}` : isLockedByMe ? 'Unlock' : 'Lock'}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d={isLockedByMe || isLockedByOthers ? 
                      "M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8V7a4 4 0 00-8 0v4h8z" : 
                      "M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"
                    }
                  />
                </svg>
              </button>
              <button
                onClick={() => onEdit(capability)}
                className="p-0.5 text-gray-400 hover:text-gray-600"
                disabled={Boolean(isLockedByOthers)}
                title="Edit"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
              </button>
              <button
                onClick={async () => {
                  if (!userSession) return;
                  try {
                    console.log('Copying capability:', capability.id);
                    // Lock the capability before copying
                    await ApiClient.lockCapability(capability.id, userSession.nickname);
                    const context = await ApiClient.getCapabilityContext(capability.id);
                    await navigator.clipboard.writeText(context.rendered_context);
                    copiedCapability = capability;
                    console.log('Capability copied:', copiedCapability);
                    toast.success('Capability context copied to clipboard');
                  } catch (error) {
                    console.error('Failed to copy capability context:', error);
                    toast.error('Failed to copy capability context');
                  }
                }}
                className="p-0.5 text-gray-400 hover:text-gray-600"
                disabled={Boolean(isLocked)}
                title="Copy"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
                </svg>
              </button>
              <button
                onClick={async () => {
                  if (!userSession) return;
                  console.log('Paste button clicked');
                  try {
                    // Unlock the capability before pasting
                    if (isLockedByMe) {
                      await ApiClient.unlockCapability(capability.id, userSession.nickname);
                    }
                    const clipboardText = await navigator.clipboard.readText();
                    console.log('Clipboard content:', clipboardText);
                    let capabilities: Array<{
                      name: string;
                      description?: string;
                      children?: RecursiveCapability[];
                    }>;
                    try {
                      capabilities = JSON.parse(clipboardText);
                    } catch {
                      toast.error('Invalid clipboard content - expected JSON capabilities list');
                      return;
                    }

                    if (!Array.isArray(capabilities)) {
                      toast.error('Invalid clipboard content - expected array of capabilities');
                      return;
                    }

                    // Create capabilities recursively
                    interface RecursiveCapability {
                      name: string;
                      description?: string;
                      children?: RecursiveCapability[];
                    }

                    const createCapabilityTree = async (caps: RecursiveCapability[], parentId: number | null = null) => {
                      for (const cap of caps) {
                        const newCap = await ApiClient.createCapability({
                          name: cap.name,
                          description: cap.description,
                          parent_id: parentId
                        }, userSession?.nickname || '');
                        if (cap.children?.length) {
                          await createCapabilityTree(cap.children, newCap.id);
                        }
                      }
                    };

                    await createCapabilityTree(capabilities, capability.id);
                    toast.success('Capabilities pasted successfully');
                  } catch (error) {
                    console.error('Failed to paste capabilities:', error);
                    toast.error('Failed to paste capabilities');
                  }
                }}
                className="p-0.5 text-gray-400 hover:text-gray-600"
                disabled={Boolean(isLocked)}
                title="Paste JSON from clipboard"
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
                disabled={Boolean(isLocked)}
                title="Delete"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>
        {/* Children section */}
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
    </div>
  );
};

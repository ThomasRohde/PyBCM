
import React, { useState } from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { useApp } from '../contexts/AppContext';
import { DraggableCapability } from './DraggableCapability';
import type { Capability } from '../types/api';

interface EditModalProps {
  capability?: Capability;
  onSave: (name: string, description: string | null) => void;
  onClose: () => void;
}

const EditModal: React.FC<EditModalProps> = ({ capability, onSave, onClose }) => {
  const [name, setName] = useState(capability?.name || '');
  const [description, setDescription] = useState(capability?.description || '');
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSaving) return;
    
    setIsSaving(true);
    try {
      await onSave(name, description || null);
    } catch (error) {
      console.error('Failed to save capability:', error);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white/90 backdrop-blur-sm shadow-xl rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-semibold mb-4">
          {capability ? 'Edit Capability' : 'New Capability'}
        </h2>
        <form onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                rows={3}
              />
            </div>
          </div>
          <div className="flex justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
              disabled={isSaving}
            >
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export const CapabilityTree: React.FC = () => {
  const { capabilities, createCapability, updateCapability, deleteCapability, userSession } = useApp();
  const [editingCapability, setEditingCapability] = useState<Capability | undefined>();
  const [showNewModal, setShowNewModal] = useState(false);
  const [globalExpanded, setGlobalExpanded] = useState<boolean | undefined>(true);

  const handleEdit = (capability: Capability) => {
    // Special case to reset global expanded state
    if (capability.description === 'RESET_GLOBAL_EXPANDED') {
      setGlobalExpanded(undefined);
      return;
    }
    setEditingCapability(capability);
  };

  const handleSave = async (name: string, description: string | null) => {
    try {
      if (editingCapability) {
        await updateCapability(editingCapability.id, name, description);
        setEditingCapability(undefined);
      } else {
        await createCapability(name, description, null);
        setShowNewModal(false);
      }
    } catch (error) {
      console.error('Failed to save capability:', error);
      // Keep modal open if there's an error
      return;
    }
  };

  if (!userSession) {
    return (
      <div className="p-4 text-center text-gray-500">
        Please log in to view and manage capabilities
      </div>
    );
  }

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="p-4">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold text-gray-900">Capabilities</h1>
            <div className="flex gap-2">
              <button
                onClick={() => setGlobalExpanded(true)}
                className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                title="Expand All"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              <button
                onClick={() => setGlobalExpanded(false)}
                className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                title="Collapse All"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>
          <button
            onClick={() => setShowNewModal(true)}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
          >
            New Capability
          </button>
        </div>

        <div className="space-y-4">
          {capabilities.map((capability, index) => (
            <DraggableCapability
              key={capability.id}
              capability={capability}
              index={index}
              parentId={null}
              onEdit={handleEdit}
              globalExpanded={globalExpanded}
              onDelete={async (cap) => {
                if (window.confirm('Are you sure you want to delete this capability?')) {
                  await deleteCapability(cap.id);
                }
              }}
            />
          ))}
        </div>

        {(editingCapability || showNewModal) && (
          <EditModal
            capability={editingCapability}
            onSave={handleSave}
            onClose={() => {
              setEditingCapability(undefined);
              setShowNewModal(false);
            }}
          />
        )}
      </div>
    </DndProvider>
  );
};

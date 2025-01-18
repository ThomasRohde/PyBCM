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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(name, description || null);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-semibold mb-4">
          {capability ? 'Edit Capability' : 'New Capability'}
        </h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
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
          <div className="mb-4">
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
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export const CapabilityTree: React.FC = () => {
  const { capabilities, createCapability, updateCapability, userSession } = useApp();
  const [editingCapability, setEditingCapability] = useState<Capability | undefined>();
  const [showNewModal, setShowNewModal] = useState(false);

  const handleEdit = (capability: Capability) => {
    setEditingCapability(capability);
  };

  const handleSave = async (name: string, description: string | null) => {
    if (editingCapability) {
      await updateCapability(editingCapability.id, name, description);
      setEditingCapability(undefined);
    } else {
      await createCapability(name);
      setShowNewModal(false);
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
          <h1 className="text-2xl font-bold text-gray-900">Capabilities</h1>
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

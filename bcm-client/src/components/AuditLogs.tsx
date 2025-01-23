import { useState, useEffect } from 'react';
import { ApiClient } from '../api/client';
import { AuditLogEntry } from '../types/api';

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const data = await ApiClient.getLogs();
        // Sort logs by timestamp (newest first)
        data.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
        setLogs(data);
      } catch (err) {
        setError('Failed to load audit logs');
        console.error('Error loading logs:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, []);

  const formatChanges = (log: AuditLogEntry): string => {
    const changes: string[] = [];

    if (log.old_values && log.new_values) {
      // Handle updates - show what changed
      for (const key of new Set([...Object.keys(log.old_values), ...Object.keys(log.new_values)])) {
        const oldVal = log.old_values[key as keyof typeof log.old_values];
        const newVal = log.new_values[key as keyof typeof log.new_values];
        if (oldVal !== newVal) {
          if (key === 'parent_id') {
            const oldName = oldVal ? log.old_values.parent_name || `Unknown (ID: ${oldVal})` : 'None';
            const newName = newVal ? log.new_values.parent_name || `Unknown (ID: ${newVal})` : 'None';
            changes.push(`Moved from '${oldName}' to '${newName}'`);
          } else if (key === 'name') {
            changes.push(`Name changed from '${oldVal}' to '${newVal}'`);
          } else if (key === 'description') {
            const newDesc = newVal || '(empty)';
            // Replace newlines with spaces and truncate if too long
            const displayDesc = newDesc.toString().replace(/\n/g, ' ');
            changes.push(`Description: '${displayDesc.length > 100 ? displayDesc.slice(0, 97) + '...' : displayDesc}'`);
          } else {
            changes.push(`${key}: ${oldVal} → ${newVal}`);
          }
        }
      }
    } else if (log.new_values) {
      // Handle creation - show new values
      for (const [key, value] of Object.entries(log.new_values)) {
        if (key === 'parent_id' && value) {
          const parentName = log.new_values.parent_name || `Unknown (ID: ${value})`;
          changes.push(`Parent: ${parentName}`);
        } else if (key === 'description') {
          const displayDesc = (value || '(empty)').toString().replace(/\n/g, ' ');
          changes.push(`Description: '${displayDesc.length > 100 ? displayDesc.slice(0, 97) + '...' : displayDesc}'`);
        } else if (key !== 'id') {
          changes.push(`${key}: ${value}`);
        }
      }
    } else if (log.old_values) {
      // Handle deletion - show what was deleted
      for (const [key, value] of Object.entries(log.old_values)) {
        if (key === 'parent_id' && value) {
          const parentName = log.old_values.parent_name || `Unknown (ID: ${value})`;
          changes.push(`Parent was: ${parentName}`);
        } else {
          changes.push(`${key}: ${value}`);
        }
      }
    }

    return changes.join(' | ');
  };

  const filteredLogs = logs.filter(log => {
    const searchLower = searchTerm.toLowerCase();
    return (
      log.capability_name.toLowerCase().includes(searchLower) ||
      log.operation.toLowerCase().includes(searchLower) ||
      formatChanges(log).toLowerCase().includes(searchLower)
    );
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen text-red-600">
        {error}
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <div className="mb-4">
        <input
          type="text"
          placeholder="Search logs..."
          className="w-full p-2 border border-gray-300 rounded shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full bg-white border border-gray-300">
          <thead>
            <tr className="bg-gray-100">
              <th className="px-4 py-2 text-left border-b">Timestamp</th>
              <th className="px-4 py-2 text-left border-b">Operation</th>
              <th className="px-4 py-2 text-left border-b">Capability</th>
              <th className="px-4 py-2 text-left border-b">Changes</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.map((log, index) => (
              <tr key={index} className="hover:bg-gray-50">
                <td className="px-4 py-2 border-b whitespace-nowrap">
                  {new Date(log.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-2 border-b whitespace-nowrap">
                  {log.operation}
                </td>
                <td className="px-4 py-2 border-b">
                  {log.capability_name}
                  {log.capability_id && ` (ID: ${log.capability_id})`}
                </td>
                <td className="px-4 py-2 border-b">
                  {formatChanges(log)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

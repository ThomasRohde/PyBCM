import { useState, useEffect } from 'react';
import { ApiClient } from '../api/client';
import { AuditLogEntry } from '../types/api';
import BackButton from './BackButton';

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortColumn, setSortColumn] = useState<'timestamp' | 'operation' | 'capability_name'>('timestamp');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const operationLabels: Record<string, string> = {
    'CREATE': 'Created',
    'ID_ASSIGN': 'ID Assignment',
    'UPDATE': 'Updated',
    'DELETE': 'Deleted',
    'MOVE': 'Moved',
    'IMPORT': 'Imported'
  };

  const [selectedOperations, setSelectedOperations] = useState<string[]>(
    Object.keys(operationLabels).filter(op => op !== 'ID_ASSIGN')
  );

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

  const handleSort = (column: 'timestamp' | 'operation' | 'capability_name') => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const sortedAndFilteredLogs = logs.filter(log => {
    const searchLower = searchTerm.toLowerCase();
    const matchesSearch = (
      log.capability_name.toLowerCase().includes(searchLower) ||
      log.operation.toLowerCase().includes(searchLower) ||
      formatChanges(log).toLowerCase().includes(searchLower)
    );
    const matchesOperation = selectedOperations.length === 0 || selectedOperations.includes(log.operation);
    return matchesSearch && matchesOperation;
  }).sort((a, b) => {
    let comparison = 0;
    
    switch (sortColumn) {
      case 'timestamp':
        comparison = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
        break;
      case 'operation':
        comparison = a.operation.localeCompare(b.operation);
        break;
      case 'capability_name':
        comparison = a.capability_name.localeCompare(b.capability_name);
        break;
    }

    return sortDirection === 'asc' ? comparison : -comparison;
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
      <BackButton />
      <div className="space-y-4 mb-4">
        <input
          type="text"
          placeholder="Search logs..."
          className="w-full p-2 border border-gray-300 rounded shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        
        <div className="flex flex-wrap gap-4">
          {Object.entries(operationLabels).map(([operation, label]) => (
            <label key={operation} className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={selectedOperations.includes(operation)}
                onChange={(e) => {
                  setSelectedOperations(prev =>
                    e.target.checked
                      ? [...prev, operation]
                      : prev.filter(op => op !== operation)
                  );
                }}
                className="form-checkbox h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
              />
              <span>{label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full bg-white border border-gray-300">
          <thead>
            <tr className="bg-gray-100">
              <th 
                className="px-4 py-2 text-left border-b cursor-pointer hover:bg-gray-200 min-w-[140px]"
                onClick={() => handleSort('timestamp')}
              >
                <div className="flex items-center gap-1">
                  <span>Timestamp</span>
                  {sortColumn === 'timestamp' && <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>}
                </div>
              </th>
              <th 
                className="px-4 py-2 text-left border-b cursor-pointer hover:bg-gray-200 min-w-[120px]"
                onClick={() => handleSort('operation')}
              >
                <div className="flex items-center gap-1">
                  <span>Operation</span>
                  {sortColumn === 'operation' && <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>}
                </div>
              </th>
              <th 
                className="px-4 py-2 text-left border-b cursor-pointer hover:bg-gray-200 min-w-[140px]"
                onClick={() => handleSort('capability_name')}
              >
                <div className="flex items-center gap-1">
                  <span>Capability</span>
                  {sortColumn === 'capability_name' && <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>}
                </div>
              </th>
              <th className="px-4 py-2 text-left border-b">Changes</th>
            </tr>
          </thead>
          <tbody>
            {sortedAndFilteredLogs.map((log, index) => (
              <tr key={index} className="hover:bg-gray-50">
                <td className="px-4 py-2 border-b whitespace-nowrap">
                  {new Date(log.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-2 border-b whitespace-nowrap">
                  {operationLabels[log.operation] || log.operation}
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

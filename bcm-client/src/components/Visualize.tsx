import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiClient } from '../api/client';
import type { LayoutModel, Settings } from '../types/api';

export const Visualize: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [model, setModel] = useState<LayoutModel | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  // Handle mouse movement for tooltip positioning
  const handleMouseMove = (e: React.MouseEvent) => {
    if (tooltipRef.current) {
      tooltipRef.current.style.left = `${e.pageX + 10}px`;
      tooltipRef.current.style.top = `${e.pageY + 10}px`;
    }
  };

  // Handle mouse enter for showing tooltip
  const handleNodeMouseEnter = (e: React.MouseEvent, name: string, description: string) => {
    e.stopPropagation();
    if (tooltipRef.current && description) {
      tooltipRef.current.textContent = `${name}: ${description}`;
      tooltipRef.current.style.display = 'block';
      tooltipRef.current.style.left = `${e.pageX + 10}px`;
      tooltipRef.current.style.top = `${e.pageY + 10}px`;
    }
  };

  // Handle mouse leave for hiding tooltip
  const handleNodeMouseLeave = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (tooltipRef.current) {
      tooltipRef.current.style.display = 'none';
    }
  };

  // Fetch data on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [layoutData, settingsData] = await Promise.all([
          ApiClient.getLayout(Number(id)),
          ApiClient.getSettings()
        ]);
        // Validate layout data
        if (!layoutData || typeof layoutData.width !== 'number' || typeof layoutData.height !== 'number') {
          console.error('Invalid layout data received:', layoutData);
          throw new Error('Invalid layout data structure');
        }
        
        setModel(layoutData);
        setSettings(settingsData);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id]);

  if (loading || !settings || !model) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  // Create CSS variables for colors
  const colorVars: Record<string, string> = {};
  for (let i = 0; i <= 6; i++) {
    const colorKey = `color_${i}` as keyof Settings;
    colorVars[`--level-${i}-color`] = String(settings[colorKey] || '#ffffff');
  }
  colorVars['--leaf-color'] = String(settings.color_leaf || '#ffffff');

  const getAllNodes = (node: LayoutModel): React.ReactNode[] => {
    const nodes: React.ReactNode[] = [];
    const addNode = (n: LayoutModel, level: number) => {
      // Validate node coordinates and dimensions
      if (typeof n.x !== 'number' || typeof n.y !== 'number' || 
          typeof n.width !== 'number' || typeof n.height !== 'number') {
        console.error('Invalid node data:', n);
        return;
      }

      const color = !n.children?.length ? 'var(--leaf-color)' : `var(--level-${Math.min(level, 6)}-color)`;
      const positionClass = n.children?.length ? 'has-children' : 'leaf-node';
      
      nodes.push(
        <div
          key={n.id}
          className={`node level-${level} ${positionClass}`}
          style={{
            position: 'absolute',
            left: `${n.x}px`,
            top: `${n.y}px`,
            width: `${n.width}px`,
            height: `${n.height}px`,
            backgroundColor: color,
            zIndex: level,
            border: '1px solid #ddd',
            padding: `${settings.padding}px`
          }}
          onMouseEnter={(e) => handleNodeMouseEnter(e, n.name, n.description || '')}
          onMouseLeave={(e) => handleNodeMouseLeave(e)}
          onMouseMove={handleMouseMove}
        >
          <div 
            className="node-content"
            style={{
              position: 'absolute',
              top: n.children?.length ? settings.top_padding : '50%',
              left: '50%',
              transform: n.children?.length ? 'translate(-50%, 0)' : 'translate(-50%, -50%)',
              width: 'calc(100% - 20px)',
              textAlign: 'center'
            }}
          >
            {n.name}
          </div>
        </div>
      );

      n.children?.forEach(child => addNode(child, level + 1));
    };

    addNode(node, 0);
    return nodes;
  };

  return (
    <div className="h-screen flex flex-col" style={colorVars}>
      <div className="bg-gray-100 p-4 flex items-center justify-between">
        <button
          onClick={() => navigate('/')}
          className="flex items-center text-gray-600 hover:text-gray-900"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back
        </button>
      </div>
      <div className="flex-1 overflow-auto">
        <div className="min-h-full w-full p-10">
          <div 
            id="model-container"
            className="relative mx-auto bg-gray-50 rounded-lg"
            style={{
              width: Math.max(model.width + 200, window.innerWidth - 80),
              height: Math.max(model.height + 200, window.innerHeight - 160),
              minWidth: '800px',
              minHeight: '600px',
              padding: '20px',
              boxShadow: '0 0 20px rgba(0,0,0,0.1)'
            }}
          >
            {getAllNodes(model)}
          </div>
        </div>
      </div>
      <div 
        ref={tooltipRef} 
        className="fixed hidden bg-black/80 text-white p-2.5 rounded max-w-xs pointer-events-none" 
        style={{ zIndex: 10000 }}
      />
    </div>
  );
};

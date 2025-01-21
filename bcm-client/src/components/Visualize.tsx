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

  // Set up tooltip event listeners
  useEffect(() => {
    // Set up tooltip event listeners
    const handleMouseMove = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.classList.contains('node')) {
        const description = target.getAttribute('data-description');
        const name = target.getAttribute('data-name');
        if (description && tooltipRef.current) {
          tooltipRef.current.textContent = `${name}: ${description}`;
          tooltipRef.current.style.display = 'block';
          tooltipRef.current.style.left = `${e.pageX + 10}px`;
          tooltipRef.current.style.top = `${e.pageY + 10}px`;
        }
      }
    };

    const handleMouseLeave = () => {
      if (tooltipRef.current) {
        tooltipRef.current.style.display = 'none';
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, []);

  // Fetch data on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [layoutData, settingsData] = await Promise.all([
          ApiClient.getLayout(Number(id)),
          ApiClient.getSettings()
        ]);
        console.log('Layout Data:', JSON.stringify(layoutData, null, 2));
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
      const color = !n.children?.length ? 'var(--leaf-color)' : `var(--level-${Math.min(level, 6)}-color)`;
      const positionClass = n.children?.length ? 'has-children' : 'leaf-node';
      
      nodes.push(
        <div
          key={n.id}
          className={`node level-${level} ${positionClass}`}
          style={{
            left: `${n.x}px`,
            top: `${n.y}px`,
            width: `${n.width}px`,
            height: `${n.height}px`,
            backgroundColor: color,
          }}
          data-description={n.description || ''}
          data-name={n.name}
        >
          <div className="node-content">{n.name}</div>
        </div>
      );

      n.children?.forEach(child => addNode(child, level + 1));
    };

    addNode(node, 0);
    return nodes;
  };

  return (
    <div className="h-screen flex flex-col" style={colorVars}>
      <div className="bg-gray-100 p-4 flex items-center">
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
              width: Math.max(model.width + 120, window.innerWidth - 80),
              height: Math.max(model.height + 120, window.innerHeight - 160),
              padding: '20px',
              boxShadow: '0 0 20px rgba(0,0,0,0.1)'
            }}
          >
            {getAllNodes(model)}
          </div>
        </div>
      </div>
      <div ref={tooltipRef} className="fixed hidden bg-black/80 text-white p-2.5 rounded z-50 max-w-xs" />
    </div>
  );
};

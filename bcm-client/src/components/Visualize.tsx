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
    if (!tooltipRef.current || !description) return;
    
    const target = e.currentTarget as HTMLElement;
    const relatedTarget = e.relatedTarget as HTMLElement;
    
    // Don't trigger if moving between parent and its children
    if (relatedTarget && (
      target.contains(relatedTarget) || 
      (relatedTarget.closest('.node') === target)
    )) {
      return;
    }

    tooltipRef.current.textContent = `${name}: ${description}`;
    tooltipRef.current.style.display = 'block';
    tooltipRef.current.style.left = `${e.pageX + 10}px`;
    tooltipRef.current.style.top = `${e.pageY + 10}px`;
  };

  // Handle mouse leave for hiding tooltip
  const handleNodeMouseLeave = (e: React.MouseEvent) => {
    if (!tooltipRef.current) return;
    
    const target = e.currentTarget as HTMLElement;
    const relatedTarget = e.relatedTarget as HTMLElement;
    
    // Don't hide if moving between parent and its children
    if (relatedTarget && (
      target.contains(relatedTarget) || 
      (relatedTarget.closest('.node') === target)
    )) {
      return;
    }

    tooltipRef.current.style.display = 'none';
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

  // Utility function to determine if a color is light or dark
  const getContrastColor = (hexColor: string): string => {
    // Convert hex to RGB
    const r = parseInt(hexColor.slice(1, 3), 16);
    const g = parseInt(hexColor.slice(3, 5), 16);
    const b = parseInt(hexColor.slice(5, 7), 16);
    
    // Calculate relative luminance using sRGB
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    
    // Return black for light colors, white for dark colors
    return luminance > 0.5 ? '#000000' : '#ffffff';
  };

  const getAllNodes = (node: LayoutModel): React.ReactNode[] => {
    const nodes: React.ReactNode[] = [];
    const addNode = (n: LayoutModel, level: number) => {
      // Validate node coordinates and dimensions
      if (typeof n.x !== 'number' || typeof n.y !== 'number' || 
          typeof n.width !== 'number' || typeof n.height !== 'number') {
        console.error('Invalid node data:', n);
        return;
      }

      const bgColor = !n.children?.length ? String(settings.color_leaf) : String(settings[`color_${Math.min(level, 6)}` as keyof Settings]);
      const textColor = getContrastColor(bgColor);
      const positionClass = n.children?.length ? 'has-children' : 'leaf-node';
      
      // Add children first
      n.children?.forEach(child => addNode(child, level + 1));

      // Then add parent node
      nodes.push(
        <React.Fragment key={n.id}>
          <div
            className={`node level-${level} ${positionClass}`}
            style={{
              '--node-padding': `${settings.padding}px`,
              '--top-padding': `${settings.top_padding}px`,
              left: `${n.x}px`,
              top: `${n.y}px`,
              width: `${n.width}px`,
              height: `${n.height}px`,
              backgroundColor: bgColor,
              '--text-color': textColor,
              paddingTop: n.children?.length ? '0px' : `${settings.top_padding}px`
            } as React.CSSProperties}
            onMouseEnter={(e) => handleNodeMouseEnter(e, n.name, n.description || '')}
            onMouseLeave={handleNodeMouseLeave}
            onMouseMove={handleMouseMove}
          >
            <div className={`node-content ${n.children?.length ? 'parent-label' : ''}`}>
              {n.name}
            </div>
          </div>
        </React.Fragment>
      );
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

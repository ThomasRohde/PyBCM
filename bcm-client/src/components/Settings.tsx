import { useEffect, useState } from 'react';
import { Settings, TemplateSettings } from '../types/api';
import { ApiClient } from '../api/client';
import BackButton from './BackButton';

export default function SettingsComponent() {
  const [settings, setSettings] = useState<Settings>({
    theme: 'litera',
    max_ai_capabilities: 10,
    first_level_range: '5-10',
    first_level_template: {
      selected: 'first_level_prompt.j2',
      available: ['first_level_prompt.j2', 'first_level_prompt_gpt.j2']
    },
    normal_template: {
      selected: 'expansion_prompt.j2',
      available: ['expansion_prompt.j2', 'expansion_prompt_gpt.j2']
    },
    font_size: 10,
    model: 'openai:gpt-4',
    context_include_parents: true,
    context_include_siblings: true,
    context_first_level: true,
    context_tree: true,
    layout_algorithm: 'Simple - fast',
    root_font_size: 20,
    box_min_width: 120,
    box_min_height: 80,
    horizontal_gap: 20,
    vertical_gap: 20,
    padding: 30,
    top_padding: 40,
    target_aspect_ratio: 1.0,
    max_level: 6,
    color_0: '#5B8C85',
    color_1: '#6B5B95',
    color_2: '#806D5B',
    color_3: '#5B7065',
    color_4: '#8B635C',
    color_5: '#707C8C',
    color_6: '#7C6D78',
    color_leaf: '#E0E0E0'
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [originalSettings, setOriginalSettings] = useState<Settings | null>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    lookAndFeel: false,
    aiGeneration: false,
    templates: false,
    context: false,
    layout: false,
    colors: false
  });

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await ApiClient.getSettings();
      setSettings(data);
      setOriginalSettings(data);
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await ApiClient.updateSettings(settings);
      setOriginalSettings(settings);
    } catch (error) {
      console.error('Failed to save settings:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (field: keyof Settings, value: string | number | boolean | TemplateSettings) => {
    setSettings(prev => ({ ...prev, [field]: value }));
  };

  const hasChanges = () => {
    if (!originalSettings) return false;
    return Object.keys(settings).some(key => {
      const k = key as keyof Settings;
      return settings[k] !== originalSettings[k];
    });
  };

  if (loading) {
    return <div className="p-4">Loading settings...</div>;
  }

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <BackButton />

      <h1 className="text-3xl font-bold mb-8">Settings</h1>
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Look & Feel Section */}
        <section className="space-y-4">
          <button
            onClick={() => toggleSection('lookAndFeel')}
            className="w-full flex items-center justify-between text-xl font-semibold py-2 hover:bg-gray-50"
          >
            <h2>Look & Feel</h2>
            <svg
              className={`w-6 h-6 transform transition-transform ${expandedSections.lookAndFeel ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {expandedSections.lookAndFeel && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Theme</label>
              <select
                value={settings.theme}
                onChange={e => handleChange('theme', e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                {['cosmo', 'flatly', 'litera', 'minty', 'lumen', 'sandstone', 'yeti', 'pulse', 'united', 'morph', 'journal', 'darkly', 'superhero', 'solar', 'cyborg', 'vapor'].map(theme => (
                  <option key={theme} value={theme}>{theme}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Font Size</label>
              <input
                type="number"
                value={settings.font_size}
                onChange={e => handleChange('font_size', parseInt(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
          </div>
          )}
        </section>

        {/* AI Generation Section */}
        <section className="space-y-4">
          <button
            onClick={() => toggleSection('aiGeneration')}
            className="w-full flex items-center justify-between text-xl font-semibold py-2 hover:bg-gray-50"
          >
            <h2>AI Generation</h2>
            <svg
              className={`w-6 h-6 transform transition-transform ${expandedSections.aiGeneration ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {expandedSections.aiGeneration && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Max AI Capabilities</label>
              <input
                type="number"
                value={settings.max_ai_capabilities}
                onChange={e => handleChange('max_ai_capabilities', parseInt(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">First Level Range</label>
              <input
                type="text"
                value={settings.first_level_range}
                onChange={e => handleChange('first_level_range', e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Model</label>
              <input
                type="text"
                value={settings.model}
                onChange={e => handleChange('model', e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
          </div>
          )}
        </section>

        {/* Templates Section */}
        <section className="space-y-4">
          <button
            onClick={() => toggleSection('templates')}
            className="w-full flex items-center justify-between text-xl font-semibold py-2 hover:bg-gray-50"
          >
            <h2>Templates</h2>
            <svg
              className={`w-6 h-6 transform transition-transform ${expandedSections.templates ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {expandedSections.templates && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">First-Level Prompt Template</label>
                <select
                  value={typeof settings.first_level_template === 'string' 
                    ? settings.first_level_template 
                    : settings.first_level_template.selected}
                  onChange={e => handleChange('first_level_template', {
                    selected: e.target.value,
                    available: typeof settings.first_level_template === 'string' 
                      ? [e.target.value]
                      : settings.first_level_template.available
                  })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                >
                  {(typeof settings.first_level_template === 'string' 
                    ? [settings.first_level_template]
                    : settings.first_level_template.available).map(template => (
                    <option key={template} value={template}>{template}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Expansion Prompt Template</label>
                <select
                  value={typeof settings.normal_template === 'string'
                    ? settings.normal_template
                    : settings.normal_template.selected}
                  onChange={e => handleChange('normal_template', {
                    selected: e.target.value,
                    available: typeof settings.normal_template === 'string'
                      ? [e.target.value]
                      : settings.normal_template.available
                  })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                >
                  {(typeof settings.normal_template === 'string'
                    ? [settings.normal_template]
                    : settings.normal_template.available).map(template => (
                    <option key={template} value={template}>{template}</option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </section>

        {/* Context Settings Section */}
        <section className="space-y-4">
          <button
            onClick={() => toggleSection('context')}
            className="w-full flex items-center justify-between text-xl font-semibold py-2 hover:bg-gray-50"
          >
            <h2>Context Settings</h2>
            <svg
              className={`w-6 h-6 transform transition-transform ${expandedSections.context ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {expandedSections.context && (
          <div className="space-y-2">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={settings.context_include_parents}
                onChange={e => handleChange('context_include_parents', e.target.checked)}
                className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
              <span className="ml-2">Include parent nodes in context</span>
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={settings.context_include_siblings}
                onChange={e => handleChange('context_include_siblings', e.target.checked)}
                className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
              <span className="ml-2">Include sibling nodes in context</span>
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={settings.context_first_level}
                onChange={e => handleChange('context_first_level', e.target.checked)}
                className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
              <span className="ml-2">Include first level nodes in context</span>
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={settings.context_tree}
                onChange={e => handleChange('context_tree', e.target.checked)}
                className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
              <span className="ml-2">Include full tree structure in context</span>
            </label>
          </div>
          )}
        </section>

        {/* Layout Settings Section */}
        <section className="space-y-4">
          <button
            onClick={() => toggleSection('layout')}
            className="w-full flex items-center justify-between text-xl font-semibold py-2 hover:bg-gray-50"
          >
            <h2>Layout Settings</h2>
            <svg
              className={`w-6 h-6 transform transition-transform ${expandedSections.layout ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {expandedSections.layout && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Layout Algorithm</label>
              <select
                value={settings.layout_algorithm}
                onChange={e => handleChange('layout_algorithm', e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="Simple - fast">Simple - fast</option>
                <option value="Advanced - slow">Advanced - slow</option>
                <option value="Experimental">Experimental</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Max Level</label>
              <input
                type="number"
                value={settings.max_level}
                onChange={e => handleChange('max_level', parseInt(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Root Font Size</label>
              <input
                type="number"
                value={settings.root_font_size}
                onChange={e => handleChange('root_font_size', parseInt(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Box Min Width</label>
              <input
                type="number"
                value={settings.box_min_width}
                onChange={e => handleChange('box_min_width', parseInt(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Box Min Height</label>
              <input
                type="number"
                value={settings.box_min_height}
                onChange={e => handleChange('box_min_height', parseInt(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Horizontal Gap</label>
              <input
                type="number"
                value={settings.horizontal_gap}
                onChange={e => handleChange('horizontal_gap', parseInt(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Vertical Gap</label>
              <input
                type="number"
                value={settings.vertical_gap}
                onChange={e => handleChange('vertical_gap', parseInt(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Padding</label>
              <input
                type="number"
                value={settings.padding}
                onChange={e => handleChange('padding', parseInt(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Top Padding</label>
              <input
                type="number"
                value={settings.top_padding}
                onChange={e => handleChange('top_padding', parseInt(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Target Aspect Ratio</label>
              <input
                type="number"
                step="0.1"
                value={settings.target_aspect_ratio}
                onChange={e => handleChange('target_aspect_ratio', parseFloat(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
          </div>
          )}
        </section>

        {/* Color Settings Section */}
        <section className="space-y-4">
          <button
            onClick={() => toggleSection('colors')}
            className="w-full flex items-center justify-between text-xl font-semibold py-2 hover:bg-gray-50"
          >
            <h2>Color Settings</h2>
            <svg
              className={`w-6 h-6 transform transition-transform ${expandedSections.colors ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {expandedSections.colors && (
          <div className="grid grid-cols-2 gap-4">
            {[0, 1, 2, 3, 4, 5, 6].map(level => (
              <div key={level}>
                <label className="block text-sm font-medium text-gray-700">Level {level} Color</label>
                <input
                  type="color"
                  value={settings[`color_${level}` as keyof Settings] as string}
                  onChange={e => handleChange(`color_${level}` as keyof Settings, e.target.value)}
                  className="mt-1 block w-full"
                />
              </div>
            ))}
            <div>
              <label className="block text-sm font-medium text-gray-700">Leaf Color</label>
              <input
                type="color"
                value={settings.color_leaf}
                onChange={e => handleChange('color_leaf', e.target.value)}
                className="mt-1 block w-full"
              />
            </div>
          </div>
          )}
        </section>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving || !hasChanges()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  );
}

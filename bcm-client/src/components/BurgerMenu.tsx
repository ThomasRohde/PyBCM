import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiClient } from '../api/client';
import { useApp } from '../contexts/AppContext';

export default function BurgerMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const { userSession } = useApp();

  return (
    <>
      <button
        aria-label="Open main menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 left-4 p-2 text-gray-600 hover:text-gray-900 focus:outline-none z-50"
      >
        {/* Hamburger icon */}
        <svg className="w-6 h-6" fill="none" stroke="currentColor" 
             viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path strokeLinecap="round" strokeLinejoin="round" 
                strokeWidth="2" 
                d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Overlay */}
      <div 
        className={`fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity 
        ${isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
        onClick={() => setIsOpen(false)} 
        aria-hidden="true"
      ></div>

      {/* Sliding menu */}
      <nav
        className={`fixed top-0 left-0 w-64 h-full bg-white z-50 transform 
        ${isOpen ? 'translate-x-0' : '-translate-x-full'} 
        transition-transform duration-300 ease-in-out`}
      >
        <button
          onClick={() => setIsOpen(false)}
          aria-label="Close menu"
          className="absolute top-4 right-4 p-2 focus:outline-none"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <div className="pt-16">
          <ul className="space-y-2">
            <li>
              <Link 
                to="/about" 
                className="block px-4 py-2 text-gray-800 hover:bg-gray-100 transition-colors duration-200"
                onClick={() => setIsOpen(false)}
              >
                About
              </Link>
            </li>
            <li>
              <Link 
                to="/settings" 
                className="block px-4 py-2 text-gray-800 hover:bg-gray-100 transition-colors duration-200"
                onClick={() => setIsOpen(false)}
              >
                Settings
              </Link>
            </li>
            <li>
              <button
                onClick={async () => {
                  try {
                    if (!userSession) return;
                    const data = await ApiClient.exportCapabilities(userSession.session_id);
                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'capabilities.json';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                  } catch (error) {
                    console.error('Export failed:', error);
                    alert('Failed to export capabilities');
                  }
                  setIsOpen(false);
                }}
                className="block w-full text-left px-4 py-2 text-gray-800 hover:bg-gray-100 transition-colors duration-200"
              >
                Export Capabilities
              </button>
            </li>
            <li>
              <input
                type="file"
                id="import-input"
                className="hidden"
                accept=".json"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    try {
                      const text = await file.text();
                      const data = JSON.parse(text);
                      if (!userSession) return;
                      await ApiClient.importCapabilities(data, userSession.session_id);
                      // Reset the input
                      e.target.value = '';
                    } catch (error) {
                      console.error('Import failed:', error);
                      alert('Failed to import capabilities');
                    }
                  }
                  setIsOpen(false);
                }}
              />
              <button
                onClick={() => {
                  document.getElementById('import-input')?.click();
                }}
                className="block w-full text-left px-4 py-2 text-gray-800 hover:bg-gray-100 transition-colors duration-200"
              >
                Import Capabilities
              </button>
            </li>
          </ul>
        </div>
      </nav>
    </>
  );
}

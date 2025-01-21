import { useNavigate, useLocation } from 'react-router-dom';
import { useEffect } from 'react';

export default function BackButton() {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Backspace' && location.pathname !== '/') {
        navigate(-1);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate, location]);

  if (location.pathname === '/') return null;

  return (
    <button
      onClick={() => navigate(-1)}
      className="fixed top-4 left-16 p-2 text-gray-600 hover:text-gray-900 focus:outline-none z-50"
      aria-label="Go back"
    >
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
      </svg>
    </button>
  );
}

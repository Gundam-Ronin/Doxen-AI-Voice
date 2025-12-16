import Link from 'next/link';
import { useRouter } from 'next/router';
import { useState } from 'react';
import { useBusiness } from '../contexts/BusinessContext';

const menuItems = [
  { name: 'Dashboard', path: '/', icon: '📊' },
  { name: 'Live Calls', path: '/calls', icon: '📞' },
  { name: 'Analytics', path: '/analytics', icon: '📈' },
  { name: 'Quotes', path: '/quotes', icon: '💰' },
  { name: 'Outbound', path: '/outbound', icon: '📤' },
  { name: 'Knowledgebase', path: '/knowledgebase', icon: '📚' },
  { name: 'Personality', path: '/personality', icon: '🤖' },
  { name: 'Technicians', path: '/technicians', icon: '👷' },
  { name: 'Settings', path: '/settings', icon: '⚙️' },
];

export default function Sidebar() {
  const router = useRouter();
  const { businesses, selectedBusiness, selectBusiness, loading, error } = useBusiness();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  return (
    <aside className="w-64 h-screen fixed left-0 top-0 glass-panel border-r border-white/10 p-4 flex flex-col">
      <div className="mb-8 px-4">
        <h1 className="text-2xl font-bold neon-text">CORTANA</h1>
        <p className="text-xs text-white/50 mt-1">Doxen Strategy Group</p>
      </div>

      <nav className="flex-1 space-y-2">
        {menuItems.map((item) => (
          <Link
            key={item.path}
            href={item.path}
            className={`sidebar-item ${
              router.pathname === item.path ? 'sidebar-item-active' : ''
            }`}
          >
            <span className="text-xl">{item.icon}</span>
            <span>{item.name}</span>
          </Link>
        ))}
      </nav>

      <div className="mt-auto pt-4 border-t border-white/10">
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="w-full glass-card p-4 hover:bg-white/10 transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-r from-neon-blue to-neon-purple flex items-center justify-center">
                <span className="text-lg">🏢</span>
              </div>
              <div className="flex-1 text-left">
                <p className="font-medium text-sm truncate">
                  {loading ? 'Loading...' : error ? 'Error' : (selectedBusiness?.name || 'Select Business')}
                </p>
                <p className="text-xs text-white/50">
                  {error ? error : (selectedBusiness?.industry || 'No businesses')}
                </p>
              </div>
              <span className="text-white/50 text-xs">
                {dropdownOpen ? '▲' : '▼'}
              </span>
            </div>
          </button>

          {dropdownOpen && businesses.length > 0 && (
            <div className="absolute bottom-full left-0 right-0 mb-2 glass-card border border-white/20 rounded-lg overflow-hidden max-h-64 overflow-y-auto">
              {businesses.map((business) => (
                <button
                  key={business.id}
                  onClick={() => {
                    selectBusiness(business);
                    setDropdownOpen(false);
                  }}
                  className={`w-full px-4 py-3 text-left hover:bg-white/10 transition-colors flex items-center gap-3 ${
                    selectedBusiness?.id === business.id ? 'bg-white/10' : ''
                  }`}
                >
                  <div className="w-8 h-8 rounded-full bg-gradient-to-r from-neon-blue to-neon-purple flex items-center justify-center text-sm">
                    {business.name?.charAt(0) || '?'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{business.name}</p>
                    <p className="text-xs text-white/50">{business.industry || 'General'}</p>
                  </div>
                  {selectedBusiness?.id === business.id && (
                    <span className="text-neon-blue">✓</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

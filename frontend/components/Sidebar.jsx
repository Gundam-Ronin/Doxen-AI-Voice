import Link from 'next/link';
import { useRouter } from 'next/router';

const menuItems = [
  { name: 'Dashboard', path: '/', icon: '📊' },
  { name: 'Live Calls', path: '/calls', icon: '📞' },
  { name: 'Knowledgebase', path: '/knowledgebase', icon: '📚' },
  { name: 'Personality', path: '/personality', icon: '🤖' },
  { name: 'Technicians', path: '/technicians', icon: '👷' },
  { name: 'Settings', path: '/settings', icon: '⚙️' },
];

export default function Sidebar() {
  const router = useRouter();

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
        <div className="glass-card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-r from-neon-blue to-neon-purple flex items-center justify-center">
              <span className="text-lg">🏢</span>
            </div>
            <div>
              <p className="font-medium text-sm">Demo Business</p>
              <p className="text-xs text-white/50">Pro Plan</p>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}

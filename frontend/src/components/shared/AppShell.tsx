import { BarChart3, Bell, Images, Map, PlaySquare, Settings, Shapes } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { useHealth } from '../../hooks/useHealth';

const nav = [
  { to: '/', label: 'Map', icon: Map },
  { to: '/compare', label: 'Compare', icon: Images },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/regions', label: 'Regions', icon: Shapes },
  { to: '/runs', label: 'Runs', icon: PlaySquare },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const health = useHealth();
  const demoMode = import.meta.env.VITE_ENABLE_MSW === 'true';
  const label = demoMode ? 'Demo data mode' : health.isLoading ? 'Checking services' : health.isError ? 'API unavailable' : health.data?.status === 'ok' ? 'Services healthy' : 'Services degraded';
  const tone = demoMode || health.isLoading ? 'border-amber-300 bg-amber-50 text-amber-900' : health.isError || health.data?.status === 'degraded' ? 'border-amber-300 bg-amber-50 text-amber-900' : 'border-emerald-300 bg-emerald-50 text-emerald-800';
  return (
    <div className="min-h-screen bg-bg text-text">
      <header className="sticky top-0 z-40 border-b border-border bg-surface">
        <div className="flex h-14 items-center gap-4 px-4">
          <div className="min-w-fit">
            <div className="text-base font-semibold leading-5">DeforestWatch</div>
            <div className="text-xs text-muted">Hasdeo Aranya monitoring</div>
          </div>
          <nav className="flex flex-1 gap-1 overflow-x-auto">
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `focus-ring flex min-h-9 items-center gap-2 rounded-md px-3 text-sm font-medium ${
                    isActive ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'
                  }`
                }
              >
                <Icon size={16} aria-hidden />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className={`hidden rounded-full border px-3 py-1 text-xs font-medium sm:block ${tone}`} title="Database and Earth Engine dependency status">
            {label}
          </div>
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}

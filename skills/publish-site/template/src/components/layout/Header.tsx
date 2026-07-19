import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import ThemeToggle from '@/components/ui/ThemeToggle';

const navItems = [
  { label: '首页', path: '/' },
  { label: '档案', path: '/reports' },
  { label: '索引', path: '/tags' },
];

export default function Header() {
  const location = useLocation();

  return (
    <header className="border-b border-border">
      {/* Top accent line */}
      <div className="h-[2px] bg-gradient-to-r from-accent via-accent/40 to-transparent" />
      <div className="mx-auto max-w-6xl px-6">
        {/* Top bar */}
        <div className="flex items-center justify-between py-6">
          <Link to="/" className="no-underline">
            <div className="flex flex-col items-start">
              <span className="font-[family-name:var(--font-family-display)] text-2xl font-bold tracking-tight text-text-bright md:text-3xl">Vantage</span>
              <span className="mt-0.5 text-[0.65rem] uppercase tracking-[0.25em] text-text-muted">深度技术调研与洞察</span>
            </div>
          </Link>

          <div className="hidden items-center gap-3 md:flex">
            <span className="issue-label mr-2 text-sm">Vol. 01 — 2026</span>
            <ThemeToggle />
          </div>
        </div>

        {/* Nav bar */}
        <nav className="flex items-center gap-8 border-t border-border py-3">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                'accent-line text-[0.8rem] font-medium uppercase tracking-[0.15em] no-underline transition-colors',
                location.pathname === item.path ? 'text-text-bright' : 'text-text-muted hover:text-text-secondary',
              )}
            >
              {item.label}
            </Link>
          ))}
          <div className="ml-auto hidden text-[0.7rem] tracking-wider text-text-muted md:block">
            {new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long' })}
          </div>
        </nav>
      </div>
    </header>
  );
}

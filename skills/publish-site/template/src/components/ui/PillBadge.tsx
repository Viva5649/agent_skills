import { cn } from '@/lib/utils';

interface PillBadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'accent';
  className?: string;
  onClick?: () => void;
}

export default function PillBadge({ children, variant = 'default', className, onClick }: PillBadgeProps) {
  const base = 'inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold transition-colors';
  const variants = {
    default:
      'bg-black/[0.04] text-text-secondary border border-black/[0.06] hover:bg-black/[0.07] dark:bg-white/[0.06] dark:text-text-secondary dark:border-white/[0.08] dark:hover:bg-white/[0.1]',
    accent: 'bg-accent/10 text-accent border border-accent/25 hover:bg-accent/20',
  };

  const Component = onClick ? 'button' : 'span';

  return (
    <Component className={cn(base, variants[variant], onClick && 'cursor-pointer', className)} onClick={onClick}>
      {children}
    </Component>
  );
}

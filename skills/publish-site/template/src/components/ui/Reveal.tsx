import { type ReactNode } from 'react';
import { useScrollReveal } from '@/hooks/useScrollReveal';
import { cn } from '@/lib/utils';

type RevealVariant = 'fade-up' | 'fade-in' | 'slide-left' | 'slide-right';

interface RevealProps {
  children: ReactNode;
  variant?: RevealVariant;
  delay?: number;
  duration?: number;
  className?: string;
  as?: keyof JSX.IntrinsicElements;
}

const variantStyles: Record<RevealVariant, { hidden: string; visible: string }> = {
  'fade-up': {
    hidden: 'opacity-0 translate-y-6',
    visible: 'opacity-100 translate-y-0',
  },
  'fade-in': {
    hidden: 'opacity-0',
    visible: 'opacity-100',
  },
  'slide-left': {
    hidden: 'opacity-0 -translate-x-6',
    visible: 'opacity-100 translate-x-0',
  },
  'slide-right': {
    hidden: 'opacity-0 translate-x-6',
    visible: 'opacity-100 translate-x-0',
  },
};

export default function Reveal({ children, variant = 'fade-up', delay = 0, duration = 700, className }: RevealProps) {
  const { ref, isVisible } = useScrollReveal();
  const styles = variantStyles[variant];

  return (
    <div
      ref={ref}
      className={cn('transition-all ease-out', isVisible ? styles.visible : styles.hidden, className)}
      style={{
        transitionDuration: `${duration}ms`,
        transitionDelay: `${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}

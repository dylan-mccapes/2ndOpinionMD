import type { ButtonHTMLAttributes, ReactNode } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'accent';
type ButtonSize = 'sm' | 'md';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  children: ReactNode;
}

const BASE =
  'inline-flex items-center justify-center font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150 whitespace-nowrap';

const VARIANT: Record<ButtonVariant, string> = {
  primary:   'bg-[var(--accent-green)] text-black hover:brightness-110',
  secondary: 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border border-[var(--border-color)] hover:border-[var(--text-muted)]',
  danger:    'bg-[var(--accent-red)] text-white hover:brightness-110',
  accent:    'bg-[var(--accent-blue)] text-white hover:brightness-110',
};

const SIZE: Record<ButtonSize, string> = {
  sm: 'px-4 py-2 text-xs',
  md: 'px-5 py-2.5 text-sm',
};

export function Button({
  variant = 'secondary',
  size = 'sm',
  className = '',
  children,
  ...props
}: ButtonProps) {
  return (
    <button className={`${BASE} ${VARIANT[variant]} ${SIZE[size]} ${className}`.trim()} {...props}>
      {children}
    </button>
  );
}

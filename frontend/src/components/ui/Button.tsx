import type { ButtonHTMLAttributes, ReactNode } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'accent';
type ButtonSize = 'sm' | 'md';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  children: ReactNode;
}

const BASE =
  'rounded font-mono font-bold tracking-wide cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150';

const VARIANT: Record<ButtonVariant, string> = {
  primary: 'bg-[var(--accent-green)] text-black',
  secondary: 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border border-[var(--border-color)]',
  danger: 'bg-[var(--accent-red)] text-white',
  accent: 'bg-[var(--accent-blue)] text-white',
};

const SIZE: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
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

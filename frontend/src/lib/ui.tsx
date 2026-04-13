/**
 * COMFORT_UX Component Library
 *
 * Single source of truth for spacing, color, and layout primitives.
 * All spacing/sizing uses inline styles — Tailwind v4 utility generation
 * is unreliable in this project, so we never rely on px-*, py-*, gap-*,
 * w-*, h-*, mb-*, etc. utility classes for any dimension.
 *
 * Usage:
 *   import { DS, Card, SectionLabel, Divider, LeftTrack, StatusDot, Badge, PatientNav } from '../lib/ui';
 */

import type { CSSProperties, ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';

// ─── Design tokens ──────────────────────────────────────────────────────────

export const DS = {
  // Padding
  pad: {
    card:    '1.5rem',           // outer card (all sides)
    cardH:   '1.25rem 1.5rem',   // header/footer strips (less vertical)
    inner:   '1rem',             // inner blocks / nested cards
    sm:      '0.75rem 1rem',     // compact inner sections
    xs:      '0.5rem 0.75rem',   // badges, chips, tight rows
  },

  // Gap (use in style={{ gap: DS.gap.md }} etc.)
  gap: {
    xs:  '0.25rem',
    sm:  '0.375rem',
    md:  '0.5rem',
    lg:  '0.75rem',
    xl:  '1rem',
    '2xl': '1.5rem',
  },

  // Margin shorthands
  mb: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '0.75rem',
    lg: '1rem',
    xl: '1.5rem',
    '2xl': '2rem',
  },

  // Colors
  color: {
    bgPrimary:   'var(--bg-primary)',
    bgSecondary: 'var(--bg-secondary)',
    bgTertiary:  'var(--bg-tertiary)',
    textPrimary:   'var(--text-primary)',
    textSecondary: 'var(--text-secondary)',
    textMuted:     'var(--text-muted)',
    border:  'var(--border-color)',
    green:   'var(--accent-green)',
    yellow:  'var(--accent-yellow)',
    red:     'var(--accent-red)',
    blue:    'var(--accent-blue)',
    cyan:    'var(--accent-cyan)',
  },

  // Shared borders
  border: '1px solid var(--border-color)',
  radius: 'var(--radius)',

  // Left-track accents (apply to a section wrapper)
  track: {
    green:  { borderLeft: '3px solid var(--accent-green)',  paddingLeft: '1rem' } as CSSProperties,
    blue:   { borderLeft: '3px solid var(--accent-blue)',   paddingLeft: '1rem' } as CSSProperties,
    yellow: { borderLeft: '3px solid var(--accent-yellow)', paddingLeft: '1rem' } as CSSProperties,
    cyan:   { borderLeft: '3px solid var(--accent-cyan)',   paddingLeft: '1rem' } as CSSProperties,
  },

  // Status dot size
  dotSize: '0.4rem',
} as const;

// ─── Composed style objects (spread into style={{}}) ────────────────────────

/** Standard card shell. */
export const cardStyle: CSSProperties = {
  backgroundColor: DS.color.bgSecondary,
  border: DS.border,
  borderRadius: DS.radius,
  padding: DS.pad.card,
};

/** Card with no padding (use CardHeader / CardBody inside). */
export const cardBareStyle: CSSProperties = {
  backgroundColor: DS.color.bgSecondary,
  border: DS.border,
  borderRadius: DS.radius,
  overflow: 'hidden',
};

/** Inner block inside a card (tertiary bg). */
export const innerBlockStyle: CSSProperties = {
  backgroundColor: DS.color.bgTertiary,
  borderRadius: DS.radius,
  padding: DS.pad.inner,
};

// ─── Components ─────────────────────────────────────────────────────────────

interface CardProps {
  children: ReactNode;
  style?: CSSProperties;
  className?: string;
  /** Strip outer padding so you can use CardHeader + CardBody inside */
  bare?: boolean;
}

/** Padded card container. */
export function Card({ children, style, className, bare }: CardProps) {
  return (
    <div
      className={className}
      style={{ ...(bare ? cardBareStyle : cardStyle), ...style }}
    >
      {children}
    </div>
  );
}

/** Horizontal strip for split-layout cards (header, footer). */
export function CardSection({
  children,
  style,
  divider = false,
}: {
  children: ReactNode;
  style?: CSSProperties;
  divider?: boolean;
}) {
  return (
    <div
      style={{
        padding: DS.pad.cardH,
        ...(divider ? { borderBottom: DS.border } : {}),
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/** Standard COMFORT_UX section label. */
export function SectionLabel({
  children,
  style,
}: {
  children: ReactNode;
  style?: CSSProperties;
}) {
  return (
    <p
      className="text-xs font-sans font-medium uppercase tracking-widest"
      style={{ color: DS.color.textMuted, marginBottom: DS.mb.md, ...style }}
    >
      {children}
    </p>
  );
}

/** 1px horizontal divider. */
export function Divider({ style }: { style?: CSSProperties }) {
  return <div style={{ borderTop: DS.border, ...style }} />;
}

/** Section wrapper with a left-border accent track. */
export function LeftTrack({
  children,
  color = 'blue',
  style,
}: {
  children: ReactNode;
  color?: keyof typeof DS.track;
  style?: CSSProperties;
}) {
  return (
    <div style={{ ...DS.track[color], ...style }}>
      {children}
    </div>
  );
}

type DotVariant = 'idle' | 'running' | 'complete' | 'error';

const DOT_COLOR: Record<DotVariant, string> = {
  idle:     DS.color.textMuted,
  running:  DS.color.cyan,
  complete: DS.color.green,
  error:    DS.color.red,
};

/** Status indicator: dot + label. */
export function StatusDot({
  variant = 'idle',
  label,
  color,
}: {
  variant?: DotVariant;
  label?: string;
  /** Override color — accepts any CSS color or var() */
  color?: string;
}) {
  const dotColor = color ?? DOT_COLOR[variant];
  const isPulsing = variant === 'running';

  return (
    <span
      className="flex items-center"
      style={{ gap: DS.gap.md }}
    >
      <span
        className={isPulsing ? 'animate-pulse' : undefined}
        style={{
          display: 'inline-block',
          width: DS.dotSize,
          height: DS.dotSize,
          borderRadius: '9999px',
          backgroundColor: dotColor,
          flexShrink: 0,
        }}
      />
      {label && (
        <span className="text-xs font-mono" style={{ color: dotColor }}>
          {label}
        </span>
      )}
    </span>
  );
}

/** Small chip / badge. */
export function Badge({
  children,
  color = DS.color.textSecondary,
  bg = DS.color.bgTertiary,
  style,
}: {
  children: ReactNode;
  color?: string;
  bg?: string;
  style?: CSSProperties;
}) {
  return (
    <span
      className="text-xs font-sans rounded"
      style={{
        padding: '0.2rem 0.55rem',
        backgroundColor: bg,
        color,
        border: DS.border,
        ...style,
      }}
    >
      {children}
    </span>
  );
}

/** Score tile (stress, sleep, etc.). */
export function ScoreChip({
  label,
  value,
  color = DS.color.textPrimary,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center rounded"
      style={{ padding: '0.75rem 1.25rem', backgroundColor: DS.color.bgTertiary, minWidth: '6rem' }}
    >
      <span
        className="text-xs font-sans"
        style={{ color: DS.color.textMuted, marginBottom: '0.375rem' }}
      >
        {label}
      </span>
      <span className="text-lg font-mono font-bold" style={{ color }}>
        {value}
      </span>
    </div>
  );
}

/** Inline feedback message (error, success, muted). */
export function InlineMessage({
  children,
  variant = 'muted',
  style,
}: {
  children: ReactNode;
  variant?: 'error' | 'success' | 'muted';
  style?: CSSProperties;
}) {
  const color =
    variant === 'error'   ? DS.color.red
    : variant === 'success' ? DS.color.green
    : DS.color.textMuted;

  return (
    <p className="text-xs font-sans" style={{ color, ...style }}>
      {children}
    </p>
  );
}

// ─── Patient navigation strip ────────────────────────────────────────────────

const PATIENT_TABS = [
  { label: 'OVERVIEW',  to: '/patient'   },
  { label: 'JOURNAL',   to: '/journal'   },
  { label: 'TIMELINE',  to: '/timeline'  },
  { label: 'DETECTIVE', to: '/eohd'      },
  { label: 'SETTINGS',  to: '/settings'  },
];

/**
 * Horizontal tab strip shared across all patient-facing pages.
 * Reads the current route internally — just drop in <PatientNav />.
 */
export function PatientNav() {
  const { pathname } = useLocation();

  return (
    <nav className="flex" style={{ gap: DS.gap.xs, borderBottom: DS.border }}>
      {PATIENT_TABS.map((tab) => {
        const active = pathname === tab.to;
        return (
          <Link
            key={tab.to}
            to={tab.to}
            className="text-xs font-mono tracking-wide no-underline"
            style={{
              padding: '0.5rem 0.75rem',
              color: active ? DS.color.green : DS.color.textSecondary,
              borderBottom: active
                ? `2px solid ${DS.color.green}`
                : '2px solid transparent',
            }}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}

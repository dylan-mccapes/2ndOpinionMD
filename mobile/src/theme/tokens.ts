/**
 * 2OPMD Mobile — Design Tokens
 *
 * Source of visual truth for the mobile app.
 * Derived from:
 *   - mobile_spec/STYLE_GUIDE.md (color palette, typography)
 *   - mobile_spec/FIGMA_PAGE_STRUCTURE_COMPONENTS.md (02 — Brand + Tokens)
 *   - mobile_spec/2opmd_design_commandments.md (design north star)
 */

// ─── Colors ──────────────────────────────────────────────────────────────────

export const colors = {
  // Backgrounds
  bgPrimary: '#000000',
  bgSurface: '#1A1A1A',
  bgElevated: '#2C2C2C',

  // Text
  textPrimary: '#FFFFFF',
  textSecondary: '#AAAAAA',
  textTertiary: '#A0A0A0',

  // Accents
  accentPrimary: '#4A90D9',
  accentGreen: '#4CAF50',
  accentAmber: '#F5A623',

  // Buttons
  buttonBg: '#FFFFFF',
  buttonText: '#000000',

  // Separators
  separator: '#333333',

  // Severity
  severityMild: '#81C784',
  severityModerate: '#F5A623',
  severitySevere: '#E76F51',
  severityFlare: '#FF7043',

  // Status
  statusSuccess: '#4CAF50',
  statusWarning: '#F5A623',
  statusError: '#E76F51',
  statusInfo: '#4A90D9',

  // Emotion families
  emotionWarm: '#E76F51',
  emotionWarmAlt: '#FF7043',
  emotionCool: '#7093E1',
  emotionCoolAlt: '#56B9B7',
  emotionPositive: '#81C784',
  emotionPositiveAlt: '#4CAF50',

  // Misc
  linkBlue: '#007AFF',
  transparent: 'transparent',
  white: '#FFFFFF',
  black: '#000000',
  offWhite: '#F5F5F0',
} as const;

// ─── Typography ──────────────────────────────────────────────────────────────

export const typography = {
  fonts: {
    serif: 'Georgia',
    sans: 'System',
  },
  sizes: {
    headline: 30,
    sectionTitle: 24,
    body: 17,
    label: 15,
    button: 18,
    secondaryAction: 14,
    caption: 13,
    link: 16,
    small: 12,
  },
  weights: {
    regular: '400' as const,
    medium: '500' as const,
    semibold: '600' as const,
    bold: '700' as const,
  },
} as const;

// ─── Spacing ─────────────────────────────────────────────────────────────────

export const spacing = {
  /** 4px */
  xs: 4,
  /** 8px */
  sm: 8,
  /** 12px */
  md: 12,
  /** 16px */
  lg: 16,
  /** 20px */
  xl: 20,
  /** 24px */
  xxl: 24,
  /** 32px */
  xxxl: 32,
  /** Horizontal screen padding */
  screenHorizontal: 22,
  /** Section vertical spacing */
  sectionVertical: 28,
  /** List item vertical spacing */
  listItemVertical: 18,
} as const;

// ─── Radius ──────────────────────────────────────────────────────────────────

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  pill: 26,
  full: 9999,
} as const;

// ─── Shadows ─────────────────────────────────────────────────────────────────

export const shadows = {
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 3,
  },
  elevated: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
} as const;

// ─── Component Constants ─────────────────────────────────────────────────────

export const components = {
  button: {
    minHeight: 52,
    borderWidth: 1.5,
  },
  icon: {
    standard: 24,
    small: 20,
  },
  progressBar: {
    height: 2,
  },
  bottomNav: {
    height: 80,
  },
} as const;

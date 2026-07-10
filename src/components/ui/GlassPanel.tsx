import React from 'react';

export interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'liquid' | 'soft' | 'solid';
  elevation?: 1 | 2 | 3;
  interactive?: boolean;
}

export const SVGRefractionFilter: React.FC = () => (
  <svg style={{ position: 'absolute', width: 0, height: 0, pointerEvents: 'none' }} aria-hidden="true">
    <defs>
      <filter id="liquid-refraction">
        <feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="2" result="noise" />
        <feDisplacementMap in="SourceGraphic" in2="noise" scale="5" xChannelSelector="R" yChannelSelector="G" />
      </filter>
    </defs>
  </svg>
);

export const GlassPanel: React.FC<GlassPanelProps> = ({
  children,
  variant = 'soft',
  elevation = 2,
  interactive = false,
  className = '',
  style = {},
  ...props
}) => {
  const getElevationClass = () => {
    switch (elevation) {
      case 1:
        return 'glass-lvl1';
      case 3:
        return 'glass-lvl3';
      case 2:
      default:
        return 'glass-lvl2';
    }
  };

  const getVariantStyles = () => {
    if (variant === 'solid') {
      return 'bg-panel-solid border border-border-primary shadow-sm';
    }
    if (variant === 'liquid') {
      return `${getElevationClass()} transition-all duration-200`;
    }
    // 'soft' is standard glass
    return `${getElevationClass()}`;
  };

  const interactiveClasses = interactive
    ? 'hover:translate-y-[-2px] hover:shadow-lg active:translate-y-[0.5px] cursor-pointer transition-all duration-200'
    : '';

  const mergedStyles = style;

  return (
    <div
      className={`rounded-2xl ${getVariantStyles()} ${interactiveClasses} ${className}`}
      style={mergedStyles}
      {...props}
    >
      {children}
    </div>
  );
};

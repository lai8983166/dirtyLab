export function LiquidGlassFilters() {
  return (
    <svg
      aria-hidden="true"
      className="liquid-filter-defs"
      focusable="false"
      height="0"
      width="0"
    >
      <defs>
        <filter
          id="liquid-glass-panel"
          colorInterpolationFilters="sRGB"
          height="140%"
          width="140%"
          x="-20%"
          y="-20%"
        >
          <feTurbulence
            baseFrequency="0.006 0.012"
            numOctaves="2"
            result="noise"
            seed="92"
            type="fractalNoise"
          />
          <feGaussianBlur in="noise" result="softNoise" stdDeviation="0.7" />
          <feDisplacementMap
            in="SourceGraphic"
            in2="softNoise"
            result="displaced"
            scale="22"
            xChannelSelector="R"
            yChannelSelector="G"
          />
          <feColorMatrix
            in="displaced"
            type="saturate"
            values="1.18"
          />
        </filter>

      </defs>
    </svg>
  );
}

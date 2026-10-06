type BasiraLogoProps = {
  compact?: boolean;
  dark?: boolean;
};

export function BasiraLogo({
  compact = false,
  dark = false,
}: BasiraLogoProps) {
  return (
    <div
      className={`basira-logo ${
        dark ? "basira-logo-dark" : ""
      }`}
      aria-label="بصيرة"
    >
      <svg
        className="basira-logo-mark"
        viewBox="0 0 72 82"
        role="img"
        aria-hidden="true"
      >
        <defs>
          <linearGradient
            id="basira-outer"
            x1="10"
            y1="8"
            x2="62"
            y2="72"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0" stopColor="#1E7B68" />
            <stop offset="1" stopColor="#0F5D4E" />
          </linearGradient>

          <linearGradient
            id="basira-inner"
            x1="20"
            y1="12"
            x2="53"
            y2="67"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0" stopColor="#3D9A83" />
            <stop offset="1" stopColor="#0E463C" />
          </linearGradient>

          <radialGradient
            id="basira-light"
            cx="50%"
            cy="48%"
            r="52%"
          >
            <stop
              offset="0"
              stopColor="#FFFDF5"
            />
            <stop
              offset="0.38"
              stopColor="#FFE2A0"
            />
            <stop
              offset="1"
              stopColor="#D4B574"
              stopOpacity="0"
            />
          </radialGradient>

          <filter
            id="basira-glow"
            x="-100%"
            y="-100%"
            width="300%"
            height="300%"
          >
            <feGaussianBlur
              stdDeviation="4"
              result="blur"
            />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* outer mishkat */}
        <path
          d="
            M36 3
            C22 11 11 22 11 37
            V69
            H61
            V37
            C61 22 50 11 36 3
            Z
          "
          fill="url(#basira-outer)"
        />

        {/* inner niche */}
        <path
          d="
            M36 13
            C26 20 19 28 19 39
            V67
            H53
            V39
            C53 28 46 20 36 13
            Z
          "
          fill="url(#basira-inner)"
        />

        {/* golden inner arch */}
        <path
          d="
            M36 18
            C28.5 24 24 31.5 24 41
            V66
            H27
            V41
            C27 33 30 27 36 22
            C42 27 45 33 45 41
            V66
            H48
            V41
            C48 31.5 43.5 24 36 18
            Z
          "
          fill="#D4B574"
          opacity="0.86"
        />

        {/* glow */}
        <circle
          className="basira-logo-halo"
          cx="36"
          cy="49"
          r="18"
          fill="url(#basira-light)"
        />

        {/* light */}
        <path
          d="
            M36 29
            C38.5 41 42 45 52 49
            C42 52.5 38.5 57 36 69
            C33.5 57 30 52.5 20 49
            C30 45 33.5 41 36 29
            Z
          "
          className="basira-logo-light"
          fill="#FFFDF5"
          filter="url(#basira-glow)"
        />

        <path
          d="M36 50 V78"
          stroke="#F2CF80"
          strokeWidth="2"
          strokeLinecap="round"
          opacity="0.9"
        />

        {/* base */}
        <path
          d="M7 70 H65 L61 74 H11 Z"
          fill="#0E2A26"
        />
      </svg>

      {!compact && (
        <div className="basira-logo-copy">
          <div className="basira-logo-arabic">
            بصيرة
          </div>

          <div className="basira-logo-english">
            BASIRA
          </div>

          <div className="basira-logo-tagline">
            VERIFICATION ENGINE
          </div>
        </div>
      )}

      {compact && (
        <div className="basira-logo-copy compact">
          <div className="basira-logo-arabic">
            بصيرة
          </div>

          <div className="basira-logo-tagline">
            VERIFICATION ENGINE
          </div>
        </div>
      )}
    </div>
  );
}

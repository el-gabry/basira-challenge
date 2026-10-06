export function HeroMushaf() {
  return (
    <div
      className="hero-mushaf"
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 380 330"
        role="presentation"
      >
        <defs>
          <linearGradient
            id="bookCover"
            x1="0"
            y1="0"
            x2="1"
            y2="1"
          >
            <stop
              offset="0"
              stopColor="#173E36"
            />
            <stop
              offset="1"
              stopColor="#071E1B"
            />
          </linearGradient>

          <linearGradient
            id="goldEdge"
            x1="0"
            y1="0"
            x2="1"
            y2="1"
          >
            <stop
              offset="0"
              stopColor="#F5D98E"
            />
            <stop
              offset="0.5"
              stopColor="#B98A35"
            />
            <stop
              offset="1"
              stopColor="#F0CC78"
            />
          </linearGradient>

          <linearGradient
            id="wood"
            x1="0"
            y1="0"
            x2="1"
            y2="1"
          >
            <stop
              offset="0"
              stopColor="#9D7135"
            />
            <stop
              offset="0.55"
              stopColor="#5C3B1E"
            />
            <stop
              offset="1"
              stopColor="#2F1E12"
            />
          </linearGradient>

          <radialGradient
            id="mushafGlow"
            cx="50%"
            cy="50%"
            r="50%"
          >
            <stop
              offset="0"
              stopColor="#FFE7A3"
              stopOpacity="0.74"
            />
            <stop
              offset="0.42"
              stopColor="#D4B574"
              stopOpacity="0.2"
            />
            <stop
              offset="1"
              stopColor="#D4B574"
              stopOpacity="0"
            />
          </radialGradient>

          <filter
            id="softGlow"
            x="-80%"
            y="-80%"
            width="260%"
            height="260%"
          >
            <feGaussianBlur
              stdDeviation="9"
            />
          </filter>
        </defs>

        {/* light behind the Mushaf */}
        <ellipse
          className="mushaf-light-aura"
          cx="205"
          cy="136"
          rx="124"
          ry="116"
          fill="url(#mushafGlow)"
          filter="url(#softGlow)"
        />

        {/* rear book */}
        <g
          className="mushaf-book-stack"
          transform="translate(90 49) rotate(-4 110 75)"
        >
          <rect
            x="20"
            y="36"
            width="220"
            height="75"
            rx="6"
            fill="#092A26"
            stroke="url(#goldEdge)"
            strokeWidth="4"
          />

          <path
            d="M35 52H225"
            stroke="#D4B574"
            strokeWidth="2"
            opacity="0.78"
          />

          <path
            d="M35 94H225"
            stroke="#D4B574"
            strokeWidth="2"
            opacity="0.58"
          />

          <path
            d="
              M62 73
              H198
              M78 61
              L92 73
              L78 85
              M182 61
              L168 73
              L182 85
            "
            stroke="#D4B574"
            strokeWidth="2"
            fill="none"
            opacity="0.66"
          />
        </g>

        {/* main closed Mushaf */}
        <g
          transform="translate(89 75)"
          className="mushaf-main-book"
        >
          <path
            d="
              M22 18
              Q112 -4 215 20
              V119
              Q112 99 22 119
              Z
            "
            fill="url(#bookCover)"
            stroke="url(#goldEdge)"
            strokeWidth="4"
          />

          <path
            d="
              M36 33
              Q112 14 201 35
              V101
              Q112 84 36 102
              Z
            "
            fill="none"
            stroke="#D4B574"
            strokeWidth="2"
            opacity="0.9"
          />

          <path
            d="
              M118 41
              L133 57
              L118 73
              L103 57
              Z
            "
            fill="none"
            stroke="#E5C36F"
            strokeWidth="2.4"
          />

          <circle
            cx="118"
            cy="57"
            r="4"
            fill="#F6DA8E"
          />

          <path
            d="
              M50 51
              H83
              M153 51
              H186
              M50 82
              H83
              M153 82
              H186
            "
            stroke="#B78C43"
            strokeWidth="2"
            opacity="0.72"
          />
        </g>

        {/* Rehal / wooden stand */}
        <g className="mushaf-rehal">
          <path
            d="
              M92 201
              L187 272
              L173 291
              L70 217
              Z
            "
            fill="url(#wood)"
            stroke="#D4B574"
            strokeWidth="2"
          />

          <path
            d="
              M278 201
              L184 272
              L198 291
              L301 217
              Z
            "
            fill="url(#wood)"
            stroke="#D4B574"
            strokeWidth="2"
          />

          <path
            d="
              M109 212
              L177 263
            "
            stroke="#E0BA6A"
            strokeWidth="2"
            opacity="0.62"
          />

          <path
            d="
              M263 212
              L195 263
            "
            stroke="#E0BA6A"
            strokeWidth="2"
            opacity="0.62"
          />
        </g>

        {/* point of light touching the book */}
        <g className="mushaf-light-point">
          <path
            d="
              M192 96
              C196 119 202 125 223 132
              C202 139 196 145 192 168
              C188 145 182 139 161 132
              C182 125 188 119 192 96
              Z
            "
            fill="#FFF7D8"
          />

          <circle
            cx="192"
            cy="132"
            r="6"
            fill="#FFFFFF"
          />
        </g>
      </svg>
    </div>
  );
}

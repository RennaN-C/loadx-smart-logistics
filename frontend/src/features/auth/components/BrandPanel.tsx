import { BrandMark, Icon } from "../../../components/Icon";

/**
 * Static decorative world-map overlay. Kept in the upper sky only so that no
 * route, node or animation crosses the truck, vehicle or login form.
 * The detailed silhouette is SVG (device-pixel sharp), not a blurred bitmap.
 */
const SOUTH_AMERICA =
  "M196 443 L197 416 L180 409 L202 397 L194 359 L218 258 L178 238 L140 185 L170 139 L150 110 L172 118 L208 94 L208 112 L220 95 L278 103 L301 126 L353 137 L363 154 L343 169 L389 165 L399 178 L433 175 L470 198 L442 228 L426 277 L371 295 L371 312 L333 345 L302 336 L309 363 L256 377 L266 387 L237 406 L250 416 L229 425 L232 439 Z";

export function BrandPanel() {
  return (
    <aside className="login-brand">
      <img
        className="login-hero-photo"
        src="/images/login-cinematic-scene-hd.webp"
        alt=""
        aria-hidden="true"
        width={1800}
        height={2000}
        fetchPriority="high"
      />
      <div className="login-map-veil" aria-hidden="true" />
      <svg className="login-world-map" viewBox="0 0 540 480" fill="none" aria-hidden="true" focusable="false">
        <defs>
          <pattern id="login-world-dots" width="9" height="9" patternUnits="userSpaceOnUse">
            <circle cx="4.5" cy="4.5" r="1.15" fill="#41b9eb" opacity=".85" />
          </pattern>
          <linearGradient id="login-world-arc" x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="#067cb5" stopOpacity="0" />
            <stop offset=".55" stopColor="#31c9fb" stopOpacity=".94" />
            <stop offset="1" stopColor="#098abc" stopOpacity=".15" />
          </linearGradient>
        </defs>
        <path className="login-world-horizon" d="M55 95 C165 -72 422 -48 538 108" stroke="url(#login-world-arc)" strokeWidth="2.5" />
        <path className="login-world-outline" d={SOUTH_AMERICA} fill="rgba(7,62,93,.18)" stroke="#259fcf" strokeWidth="1.25" />
        <path d={SOUTH_AMERICA} fill="url(#login-world-dots)" opacity=".95" />
        <g className="login-world-connections" stroke="#eec06a" strokeWidth="1.7" strokeLinecap="round">
          <path d="M339 269 Q280 158 239 162" />
          <path d="M339 269 Q373 176 422 200" />
          <path d="M339 269 Q283 235 205 239" />
          <path d="M339 269 Q327 334 280 359" />
        </g>
        <g className="login-world-points" fill="#ffce76">
          <circle cx="339" cy="269" r="5" />
          <circle cx="239" cy="162" r="3.4" />
          <circle cx="422" cy="200" r="3.4" />
          <circle cx="205" cy="239" r="3.4" />
          <circle cx="280" cy="359" r="3.4" />
        </g>
        <path d="M339 244 C325 244 317 254 317 265 C317 279 339 298 339 298 C339 298 361 279 361 265 C361 254 352 244 339 244 Z" fill="#f6c76a" />
        <circle cx="339" cy="263" r="7" fill="#10283d" />
      </svg>

      <p className="login-wordmark"><BrandMark size={25} /> LOADX</p>
      <div className="login-brand-main">
        <div>
          <p className="login-brand-eyebrow"><span aria-hidden="true" /> SMART LOGISTICS</p>
          <h1 className="login-brand-mark">Planejamento inteligente para<br /><em>uma logística mais eficiente.</em></h1>
          <p className="login-brand-tag">
            Planejamento, controle e rastreabilidade de cargas em uma única plataforma.
          </p>
        </div>
      </div>

      <div className="login-brand-bottom">
        <ol className="login-journey">
          <li><Icon name="planning" size={26} /><span>Planejamento<br />de cargas</span></li>
          <li><Icon name="package" size={26} /><span>Conferência<br />de volumes</span></li>
          <li><Icon name="truck" size={26} /><span>Acompanhamento<br />de entregas</span></li>
        </ol>
        <div className="login-brand-footer"><p className="login-brand-foot">LOADX · LOGÍSTICA INTELIGENTE</p></div>
      </div>
    </aside>
  );
}

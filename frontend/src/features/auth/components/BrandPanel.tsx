export function BrandPanel() {
  return (
    <aside className="login-brand">
      <div>
        <p className="login-brand-eyebrow">SISTEMA INTERNO · ACESSO RESTRITO</p>
        <h1 className="login-brand-mark">LOADX</h1>
        <p className="login-brand-tag">
          Planejamento de carga, otimização 3D e acompanhamento logístico de ponta a ponta.
        </p>
        <p className="login-brand-roles">ADMINISTRAÇÃO · LOGÍSTICA · CONFERÊNCIA · MOTORISTAS</p>
      </div>

      <svg className="login-brand-diagram" viewBox="0 0 260 160" fill="none" aria-hidden="true">
        <rect x="30" y="20" width="210" height="110" rx="2" stroke="var(--brand-fg)" strokeOpacity="0.45" />
        <line x1="30" y1="132" x2="30" y2="12" stroke="var(--accent)" strokeOpacity="0.8" strokeWidth="1.4" />
        <line x1="30" y1="132" x2="252" y2="132" stroke="var(--accent)" strokeOpacity="0.8" strokeWidth="1.4" />
        <text x="18" y="16" fill="var(--accent)" fontFamily="Consolas, monospace" fontSize="10" opacity="0.85">
          y
        </text>
        <text x="250" y="145" fill="var(--accent)" fontFamily="Consolas, monospace" fontSize="10" opacity="0.85">
          x
        </text>

        <rect
          x="35"
          y="90"
          width="55"
          height="40"
          fill="var(--brand-fg)"
          fillOpacity="0.1"
          stroke="var(--brand-fg)"
          strokeOpacity="0.55"
        />
        <rect
          x="96"
          y="100"
          width="45"
          height="30"
          fill="var(--brand-fg)"
          fillOpacity="0.1"
          stroke="var(--brand-fg)"
          strokeOpacity="0.55"
        />
        <rect
          x="147"
          y="55"
          width="40"
          height="75"
          fill="var(--accent)"
          fillOpacity="0.18"
          stroke="var(--accent)"
          strokeOpacity="0.7"
        />
        <rect
          x="193"
          y="95"
          width="35"
          height="35"
          fill="var(--brand-fg)"
          fillOpacity="0.1"
          stroke="var(--brand-fg)"
          strokeOpacity="0.55"
          strokeDasharray="2 2"
        />

        <text x="150" y="150" fill="var(--brand-fg)" fontFamily="Consolas, monospace" fontSize="9" opacity="0.5">
          x, y, z — cm
        </text>
      </svg>

      <p className="login-brand-foot">LOADX · AMBIENTE LOCAL · V0.1</p>
    </aside>
  );
}

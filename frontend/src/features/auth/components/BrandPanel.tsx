import { BrandMark } from "../../../components/Icon";

export function BrandPanel() {
  return (
    <aside className="login-brand">
      <p className="login-wordmark"><BrandMark size={25} /> LOADX</p>
      <div className="login-brand-main">
        <div>
          <p className="login-brand-eyebrow">SMART LOGISTICS</p>
          <h1 className="login-brand-mark">Logística inteligente.<br />Operação conectada.</h1>
          <p className="login-brand-tag">
            Planejamento, controle e rastreabilidade de cargas em uma única plataforma.
          </p>
        </div>

        <svg className="login-brand-diagram" viewBox="0 0 440 220" fill="none" aria-hidden="true">
          <defs><pattern id="loadx-access-grid" width="28" height="24" patternUnits="userSpaceOnUse" patternTransform="skewX(-12)"><path d="M28 0H0V24" stroke="#38566c" strokeOpacity=".5" /></pattern></defs>
          <rect width="440" height="220" rx="8" fill="#112330" />
          <rect width="440" height="220" rx="8" fill="url(#loadx-access-grid)" />
          {[80, 155, 230].map((x) => <g key={x} transform={`translate(${x} 100)`}>
            <path d="M0 20 15 0H56L41 20Z" fill="#ffbf54" />
            <path d="M0 20H41V42H0Z" fill="#e8a431" />
            <path d="M41 20 56 0V22L41 42Z" fill="#bd7c1d" />
          </g>)}
          <path d="M337 130H378M365 117 378 130 365 143" stroke="#79aef8" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M313 130H320" stroke="#79aef8" strokeWidth="5" strokeLinecap="round" />
        </svg>
      </div>

      <p className="login-brand-foot">LOADX · LOGÍSTICA INTELIGENTE</p>
    </aside>
  );
}

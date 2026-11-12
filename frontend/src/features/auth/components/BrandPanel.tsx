import { BrandMark, Icon } from "../../../components/Icon";

/**
 * The approved desktop reference is a decorative static illustration.
 * All authentication remains live React; the brand copy stays semantic and
 * visible at mobile widths (and available to assistive technology on desktop).
 * No procedural map or overlays should cross the truck.
 */
export function BrandPanel() {
  return (
    <aside className="login-brand">
      <img
        className="login-reference-art"
        src="/images/login-reference-left.avif"
        alt=""
        aria-hidden="true"
        width={1006}
        height={941}
        fetchPriority="high"
        decoding="async"
      />
      <div className="login-brand-live">
        <p className="login-wordmark"><BrandMark size={38} /> <span>LOADX</span></p>
        <div className="login-brand-main">
          <div>
            <p className="login-brand-eyebrow">SMART LOGISTICS</p>
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
          <div className="login-brand-footer">
            <p className="login-brand-foot">LOADX · LOGÍSTICA INTELIGENTE</p>
          </div>
        </div>
      </div>
    </aside>
  );
}

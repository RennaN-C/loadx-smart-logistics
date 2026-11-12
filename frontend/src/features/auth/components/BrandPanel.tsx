import { Icon } from "../../../components/Icon";

/** Decorative scene and geographic artwork stay separate from readable UI. */
export function BrandPanel() {
  return (
    <aside className="login-brand">
      <picture className="login-scene">
        <source media="(max-width: 820px)" srcSet="data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=" />
        <img
          className="login-scene-photo"
          src="/images/login-scene-hd.webp"
          srcSet="/images/login-scene-1024.webp 1024w, /images/login-scene-hd.webp 1606w"
          sizes="60vw"
          alt=""
          aria-hidden="true"
          width={1606}
          height={979}
          fetchPriority="high"
          decoding="async"
        />
      </picture>
      <img className="login-globe" src="/images/login-globe.svg" width={480} height={530} alt="" aria-hidden="true" />
      <div className="login-brand-live">
        <div className="login-wordmark" aria-label="LoadX Smart Logistics">
          <img className="login-brand-symbol" src="/branding/loadx-login-mark.svg" width={164} height={86} alt="" aria-hidden="true" />
          <div className="login-wordmark-type"><span>Load<span className="login-gold">X</span></span><small>SMART LOGISTICS</small></div>
        </div>
        <div className="login-brand-main">
          <h1>Planejamento inteligente para<br /><em>uma logística mais eficiente.</em></h1>
          <p className="login-brand-tag">Planejamento, controle e rastreabilidade de cargas em uma única plataforma.</p>
        </div>
        <ul className="login-journey">
          <li><Icon name="calendar" size={36} /><span>Planejamento<br />de Cargas</span></li>
          <li><Icon name="package" size={36} /><span>Conferência<br />de Volumes</span></li>
          <li><Icon name="truck" size={36} /><span>Acompanhamento<br />de Entregas</span></li>
        </ul>
      </div>
    </aside>
  );
}

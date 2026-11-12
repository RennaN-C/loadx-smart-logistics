import { BrandMark, Icon } from "../../../components/Icon";
import { useState } from "react";

export function BrandPanel() {
  const [motionPaused, setMotionPaused] = useState(false);
  return (
    <aside className={`login-brand${motionPaused ? " is-motion-paused" : ""}`}>
      <img className="login-hero-photo" src="/images/login-cinematic-scene.webp" alt="" aria-hidden="true" width={900} height={1000} fetchPriority="high" />
      <div className="login-atmosphere" aria-hidden="true" />
      <svg className="login-routes" viewBox="0 0 1000 900" fill="none" aria-hidden="true" focusable="false">
        {[
          "M 675 415 C 720 362 767 326 835 330",
          "M 835 330 C 912 259 885 189 785 166",
          "M 598 522 C 649 449 755 432 835 330",
        ].map((path, index) => <g key={path} className={`login-route login-route-${index + 1}`}>
          <path d={path} className="login-route-track" />
          <path d={path} className="login-route-signal" pathLength="1" />
        </g>)}
        <circle className="login-route-hub" cx="835" cy="330" r="5" />
        <circle className="login-route-hub" cx="598" cy="522" r="3" />
        <circle className="login-route-hub" cx="785" cy="166" r="3" />
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
        <div className="login-brand-footer"><p className="login-brand-foot">LOADX · LOGÍSTICA INTELIGENTE</p><button type="button" className="login-motion-toggle" aria-pressed={motionPaused} onClick={() => setMotionPaused((value) => !value)}>{motionPaused ? "Ativar efeitos" : "Pausar efeitos"}</button></div>
      </div>
    </aside>
  );
}

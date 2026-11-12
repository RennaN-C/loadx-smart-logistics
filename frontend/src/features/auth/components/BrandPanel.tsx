import { BrandMark, Icon } from "../../../components/Icon";
import { useState } from "react";

export function BrandPanel() {
  const [motionPaused, setMotionPaused] = useState(false);
  return (
    <aside className={`login-brand${motionPaused ? " is-motion-paused" : ""}`}>
      <img className="login-hero-photo" src="/images/login-logistics-hero-v2.webp" alt="" aria-hidden="true" width={1024} height={1536} fetchPriority="high" />
      <div className="login-atmosphere" aria-hidden="true" />
      <svg className="login-routes" viewBox="0 0 1000 900" fill="none" aria-hidden="true" focusable="false">
        {[
          "M 220 550 Q 490 190 815 290",
          "M 390 660 Q 920 510 815 290",
          "M 815 290 Q 720 90 520 110",
        ].map((path, index) => <g key={path} className={`login-route login-route-${index + 1}`}>
          <path d={path} className="login-route-track" />
          <path d={path} className="login-route-signal" pathLength="1" />
        </g>)}
        <circle className="login-route-hub" cx="815" cy="290" r="5" />
        <circle className="login-route-hub" cx="390" cy="660" r="3" />
        <circle className="login-route-hub" cx="520" cy="110" r="3" />
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

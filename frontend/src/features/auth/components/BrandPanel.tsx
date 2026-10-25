import { BrandMark } from "../../../components/Icon";
import { useState } from "react";

export function BrandPanel() {
  const [motionPaused, setMotionPaused] = useState(false);
  return (
    <aside className={`login-brand${motionPaused ? " is-motion-paused" : ""}`}>
      <img className="login-hero-photo" src="/images/login-logistics-hero-v2.webp" alt="" aria-hidden="true" width={1024} height={1536} fetchPriority="high" />
      <p className="login-wordmark"><BrandMark size={25} /> LOADX</p>
      <div className="login-brand-main">
        <div>
          <p className="login-brand-eyebrow"><span aria-hidden="true" /> SMART LOGISTICS</p>
          <h1 className="login-brand-mark">Logística inteligente.<br />Operação conectada.</h1>
          <p className="login-brand-tag">
            Planejamento, controle e rastreabilidade de cargas em uma única plataforma.
          </p>
        </div>
      </div>

      <div className="login-brand-bottom">
        <ol className="login-journey"><li><span>01</span> Planejar</li><li><span>02</span> Conferir</li><li><span>03</span> Entregar</li></ol>
        <div className="login-brand-footer"><p className="login-brand-foot">LOADX · LOGÍSTICA INTELIGENTE</p><button type="button" className="login-motion-toggle" aria-pressed={motionPaused} onClick={() => setMotionPaused((value) => !value)}>{motionPaused ? "Ativar efeitos" : "Pausar efeitos"}</button></div>
      </div>
    </aside>
  );
}

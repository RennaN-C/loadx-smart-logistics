import { useId } from "react";

/** Decorative artwork; it represents no persisted load plan or operational metric. */
export function LoginIllustration() {
  const id = useId();
  return <svg className="login-brand-diagram" viewBox="0 0 600 350" fill="none" aria-hidden="true">
    <defs>
      <linearGradient id={`${id}-floor`} x1="140" y1="90" x2="430" y2="320" gradientUnits="userSpaceOnUse"><stop stopColor="#23455a" /><stop offset="1" stopColor="#102735" /></linearGradient>
      <linearGradient id={`${id}-body`} x1="190" y1="170" x2="360" y2="280" gradientUnits="userSpaceOnUse"><stop stopColor="#436377" /><stop offset="1" stopColor="#213a4c" /></linearGradient>
      <radialGradient id={`${id}-glow`}><stop stopColor="#ffb432" stopOpacity=".22" /><stop offset="1" stopColor="#ffb432" stopOpacity="0" /></radialGradient>
      <pattern id={`${id}-grid`} width="42" height="42" patternUnits="userSpaceOnUse" patternTransform="matrix(1 .55 -1 .55 300 0)"><path d="M42 0H0V42" stroke="#6a94ac" strokeOpacity=".13" /></pattern>
    </defs>
    <ellipse cx="320" cy="205" rx="245" ry="145" fill={`url(#${id}-glow)`} />
    <rect x="10" y="15" width="580" height="320" fill={`url(#${id}-grid)`} />
    <path className="login-route-track" d="M35 255H135Q165 255 165 225V85Q165 55 195 55H355Q385 55 385 85V283Q385 308 410 308H565" stroke="#416579" strokeWidth="1.5" strokeDasharray="5 8" />
    <path className="login-route-signal" d="M35 255H135Q165 255 165 225V85Q165 55 195 55H355Q385 55 385 85V283Q385 308 410 308H565" stroke="#ffc05a" strokeWidth="2" strokeDasharray="20 760" />
    <g className="login-truck-art">
      <path d="m146 201 176-96 217 119-176 98Z" fill="#071723" fillOpacity=".45" />
      <path d="m168 182 142-78 168 92-141 78Z" fill={`url(#${id}-floor)`} stroke="#63879c" strokeOpacity=".5" />
      <path d="m168 182 169 92v28l-169-92Z" fill={`url(#${id}-body)`} />
      <path d="m337 274 141-78v28l-141 78Z" fill="#182f40" />
      <path d="M168 182V96l142-78v86M168 96l169 92 141-78M337 188v86M478 110v86M310 18l168 92" stroke="#7195a9" strokeWidth="2" strokeLinejoin="round" />
      <path d="m168 96 169 92v86l-169-92Z" fill="#88b5cf" fillOpacity=".035" />
      {[{ x: 215, y: 123 }, { x: 269, y: 152 }, { x: 323, y: 181 }].map(({ x, y }) => <g key={x} transform={`translate(${x} ${y})`}>
        <path d="m0 0 37-20 47 26-37 20Z" fill="#ffd58b" /><path d="m0 0 47 26v44L0 44Z" fill="#dca246" /><path d="m47 26 37-20v44L47 70Z" fill="#ad732b" />
        <path d="m15-8 47 26v44M0 22l47 26 37-20" stroke="#80551e" strokeOpacity=".38" /><path d="m15-8 13-7 47 26-13 7Z" fill="#fff1cb" fillOpacity=".55" />
      </g>)}
      <path d="m398 240 80-44 46 25 22 43-82 45-66-36Z" fill="#dce8ed" /><path d="m478 196 46 25 22 43-44-24Z" fill="#a5bcc9" />
      <path d="m414 241 58-32v36l-58 32Z" fill="#244456" /><path d="m480 209 33 18 12 25-33-18Z" fill="#183747" />
      <path d="m398 273 66 36 82-45v16l-82 45-66-36Z" fill="#728c9d" />
      <ellipse cx="224" cy="238" rx="13" ry="20" transform="rotate(-27 224 238)" fill="#08141f" /><ellipse cx="224" cy="238" rx="6" ry="10" transform="rotate(-27 224 238)" fill="#668292" />
      <ellipse cx="449" cy="296" rx="13" ry="20" transform="rotate(27 449 296)" fill="#08141f" /><ellipse cx="449" cy="296" rx="6" ry="10" transform="rotate(27 449 296)" fill="#668292" />
      <path d="m513 270 19-10" stroke="#ffd58b" strokeWidth="5" strokeLinecap="round" />
    </g>
    {[{ x: 35, y: 255 }, { x: 355, y: 55 }, { x: 565, y: 308 }].map(({ x, y }, index) => <g key={x} className={`login-route-node login-route-node-${index}`}><circle cx={x} cy={y} r="13" fill="#ffb432" fillOpacity=".1" /><circle cx={x} cy={y} r="4" fill="#ffc05a" /></g>)}
  </svg>;
}

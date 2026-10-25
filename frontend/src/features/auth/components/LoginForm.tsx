import { Link } from "react-router-dom";
import { MfaRequired } from "../mfaTypes";
import { MfaChallengePanel } from "./MfaChallengePanel";
import { useState, type FormEvent } from "react";

import { ApiError } from "../../../types/api";
import { useAuth } from "../hooks/useAuth";
import { mapLoginErrorToMessage } from "./loginErrorMessages";
import { AlertBanner } from "../../../components/AlertBanner";
import { BrandMark, Icon } from "../../../components/Icon";

export function LoginForm() {
  const { login, pendingMfa, beginMfa } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await login(email, password);
    } catch (error) {
      if (error instanceof MfaRequired) { beginMfa?.(error.challenge); setPassword(""); setIsSubmitting(false); return; }
      const apiError =
        error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      setErrorMessage(mapLoginErrorToMessage(apiError));
      setIsSubmitting(false);
    }
  }

  if (pendingMfa) return <MfaChallengePanel key={pendingMfa.challenge_token} challenge={pendingMfa} />;

  return (
    <form className="login-card" onSubmit={handleSubmit}>
      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

      <div className="login-card-intro">
        <span className="login-access-mark" aria-hidden="true"><BrandMark size={25} /></span>
        <p className="login-access-eyebrow">ACESSO À PLATAFORMA</p>
        <h2>Entrar</h2>
        <p className="login-lede">Sua operação começa com uma visão clara.<br />Use suas credenciais internas para continuar.</p>
      </div>

      <fieldset disabled={isSubmitting} className="login-fieldset">
        <div className="login-field">
          <label className="login-field-label" htmlFor="email">
            E-MAIL
          </label>
          <input
            type="email"
            id="email"
            name="email"
            placeholder="nome@empresa.com"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>

        <div className="login-field">
          <div className="login-field-label-row">
            <label className="login-field-label" htmlFor="password">
              SENHA
            </label>
            <button
              type="button"
              className="login-toggle"
              aria-pressed={showPassword}
              aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
              onClick={() => setShowPassword((value) => !value)}
            >
              {showPassword ? "Ocultar" : "Mostrar"}
            </button>
          </div>
          <input
            type={showPassword ? "text" : "password"}
            id="password"
            name="password"
            placeholder="••••••••"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
      </fieldset>

      <button type="submit" className="btn-primary login-submit" disabled={isSubmitting}>
        {isSubmitting ? (
          <>
            <span className="spinner" aria-hidden="true" />
            <span>Entrando…</span>
          </>
        ) : (
          <><span>Entrar</span><Icon name="arrow-right" size={18} /></>
        )}
      </button>

      <Link className="login-recovery-link" to="/password-recovery">Esqueci minha senha</Link>
      <p className="login-hint">Não tem acesso? Fale com o administrador do sistema.</p>
    </form>
  );
}

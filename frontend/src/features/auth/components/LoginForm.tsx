import { Link } from "react-router-dom";
import { MfaRequired } from "../mfaTypes";
import { MfaChallengePanel } from "./MfaChallengePanel";
import { useState, type FormEvent } from "react";

import { ApiError } from "../../../types/api";
import { useAuth } from "../hooks/useAuth";
import { mapLoginErrorToMessage } from "./loginErrorMessages";
import { AlertBanner } from "../../../components/AlertBanner";
import { Icon } from "../../../components/Icon";

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
        <img className="login-access-mark" src="/branding/loadx-login-mark.svg" width={88} height={46} alt="" aria-hidden="true" />
        <h2 aria-label="Bem-vindo ao LoadX">Bem-vindo ao Load<span className="login-card-highlight">X</span></h2>
        <p className="login-card-subtitle">Smart Logistics</p>
        <p className="login-lede">Acesse sua conta para planejar cargas<br />e acompanhar sua operação logística.</p>
      </div>

      <fieldset disabled={isSubmitting} className="login-fieldset">
        <div className="login-field">
          <label className="login-field-label" htmlFor="email">
            E-mail
          </label>
          <input
            type="email"
            id="email"
            name="email"
            placeholder="Digite seu e-mail"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>

        <div className="login-field">
          <div className="login-field-label-row">
            <label className="login-field-label" htmlFor="password">
              Senha
            </label>
          </div>
          <div className="login-password-control">
            <input
              type={showPassword ? "text" : "password"}
              id="password"
              name="password"
              placeholder="Digite sua senha"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
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
        </div>
      </fieldset>

      <Link className="login-recovery-link" to="/password-recovery">Esqueci minha senha</Link>

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

      <p className="login-hint">Não tem acesso? Fale com o administrador do sistema.</p>
    </form>
  );
}

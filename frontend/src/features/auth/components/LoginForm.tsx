import { useState, type FormEvent } from "react";

import { ApiError } from "../../../types/api";
import { useAuth } from "../hooks/useAuth";
import { mapLoginErrorToMessage } from "./loginErrorMessages";

export function LoginForm() {
  const { login } = useAuth();
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
      const apiError =
        error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado.");
      setErrorMessage(mapLoginErrorToMessage(apiError));
      setIsSubmitting(false);
    }
  }

  return (
    <form className="login-card" onSubmit={handleSubmit}>
      {errorMessage ? (
        <div className="login-alert" role="alert">
          {errorMessage}
        </div>
      ) : null}

      <div>
        <h2>Entrar</h2>
        <p className="login-lede">Use suas credenciais internas para continuar.</p>
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
              {showPassword ? "ocultar" : "mostrar"}
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

      <button type="submit" className="login-submit" disabled={isSubmitting}>
        {isSubmitting ? (
          <>
            <span className="spinner" aria-hidden="true" />
            <span>Entrando…</span>
          </>
        ) : (
          "Entrar"
        )}
      </button>

      <p className="login-hint">Não tem acesso? Fale com o administrador do sistema.</p>
    </form>
  );
}

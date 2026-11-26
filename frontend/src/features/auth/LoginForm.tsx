import { useEffect, useState, type FormEvent } from "react";
import { registrationUsernameError } from "../../../js/username-policy.js";
import { safeNext } from "../../../js/auth.js";
import { auth, errorMessage } from "../../services/apiClient";
import { useSession } from "../../components/common/Navbar";

export function LoginForm({ register = false }: { register?: boolean }) {
  const params = new URLSearchParams(location.search);
  const next = safeNext(params.get("next"));
  const query = next === "/" ? "" : "?next=" + encodeURIComponent(next);
  const { user } = useSession();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [message, setMessage] = useState(
    params.get("registered") === "1"
      ? "Your account was created. Please log in."
      : "",
  );
  const [fields, setFields] = useState<Record<string, string>>({});
  useEffect(() => {
    if (user && !register) location.assign(next);
  }, [user, register, next]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const name = String(data.get("username"));
    const password = String(data.get("password"));
    const usernameError = register ? registrationUsernameError(name) : "";
    if (usernameError) {
      setFields({ username: usernameError });
      setMessage("");
      setFailed(false);
      return;
    }
    setBusy(true);
    setFields({});
    setMessage("");
    setFailed(false);
    try {
      if (register) {
        await auth.register(name, password);
        location.assign(
          "/login.html?registered=1&next=" + encodeURIComponent(next),
        );
      } else {
        await auth.login(name, password);
        location.assign(next);
      }
    } catch (error) {
      setFailed(true);
      setMessage(errorMessage(error));
      setFields((error as { fields?: Record<string, string> }).fields || {});
      (form.elements.namedItem("password") as HTMLInputElement).value = "";
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="narrow auth-wrap">
      <h1>{register ? "Create an account" : "Log in"}</h1>
      {register && (
        <p className="muted">
          An account ID and a password are all that is needed.
        </p>
      )}
      {message && (
        <p
          className={
            failed ? "message message-error" : "message message-success"
          }
          role={failed ? "alert" : "status"}
        >
          {message}
        </p>
      )}
      <form className="card form" method="post" onSubmit={submit}>
        <div className="field">
          <label htmlFor="username">Account ID</label>
          <input
            id="username"
            name="username"
            required
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            aria-invalid={fields.username ? true : undefined}
            aria-describedby={fields.username ? "username-error" : undefined}
          />
          {fields.username && (
            <p className="field-error" id="username-error">
              {fields.username}
            </p>
          )}
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            required
            maxLength={256}
            autoComplete={register ? "new-password" : "current-password"}
            aria-invalid={fields.password ? true : undefined}
            aria-describedby={fields.password ? "password-error" : undefined}
          />
          {fields.password && (
            <p className="field-error" id="password-error">
              {fields.password}
            </p>
          )}
        </div>
        <button className="button" disabled={busy}>
          {register ? "Register" : "Log in"}
        </button>
      </form>
      <p className="muted auth-switch">
        {register ? "Already registered? " : "No account yet? "}
        <a href={(register ? "/login.html" : "/register.html") + query}>
          {register ? "Log in" : "Register"}
        </a>
      </p>
    </div>
  );
}

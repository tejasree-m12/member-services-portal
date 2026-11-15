import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { ErrorMessage, Field } from "../components/ui.jsx";
import { useAuth } from "../context/AuthContext.jsx";

export default function LoginPage() {
  const { user, login } = useAuth();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to={location.state?.from || "/"} replace />;

  async function handleSubmit(event) {
    event.preventDefault(); // stop the browser's default full-page form submit
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError(err);
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <form className="card login-card" onSubmit={handleSubmit}>
        <h1>Member Services Portal</h1>
        <p className="muted">Sign in to continue.</p>
        <ErrorMessage error={error} />
        <Field label="Email">
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="username"
            required
            autoFocus
          />
        </Field>
        <Field label="Password">
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
        </Field>
        <button className="btn btn-primary btn-block" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
        <p className="muted small">
          Demo data only. After running <code>flask seed</code>, sign in with admin@example.com / Admin#12345.
        </p>
      </form>
    </div>
  );
}

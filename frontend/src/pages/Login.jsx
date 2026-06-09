import { ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Navigate } from "react-router-dom";

import Button from "../components/Button";
import Input from "../components/Input";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";

export default function Login() {
  const { isAuthenticated, isReady, login } = useAuth();
  const { t } = useLanguage();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isReady && isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(username, password);
    } catch (loginError) {
      setError(loginError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-panel px-4 py-10">
      <section className="w-full max-w-md rounded-lg border border-line bg-white p-6 shadow-sm">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-accent text-white">
            <ShieldCheck size={22} />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-ink">ML-NIDS</h1>
            <p className="text-sm text-muted">{t("Network traffic analysis panel")}</p>
          </div>
        </div>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <Input label={t("Username")} value={username} onChange={(event) => setUsername(event.target.value)} />
          <Input
            label={t("Password")}
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-danger">{error}</div> : null}
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? t("Signing in...") : t("Sign in")}
          </Button>
        </form>
      </section>
    </main>
  );
}

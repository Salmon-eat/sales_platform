import { redirect } from "next/navigation";

import { apiFetch } from "@/lib/api";
import { getCurrentUser } from "@/lib/auth";

import { LoginForm } from "./LoginForm";

type AuthConfig = { google_client_id: string | null; dev_login: boolean };

export default async function LoginPage() {
  const user = await getCurrentUser().catch(() => null);
  if (user && user.role !== "user") redirect("/admin");
  const config = await apiFetch<AuthConfig>("/auth/config").catch(() => ({ google_client_id: null, dev_login: false }));

  return <LoginForm googleClientId={config.google_client_id} devLogin={config.dev_login} />;
}

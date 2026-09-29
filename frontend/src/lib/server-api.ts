import "server-only";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { Admin } from "@/lib/types";

export async function serverApi<T>(path: string): Promise<T> {
  const cookieStore = await cookies();
  const token = cookieStore.get("visa_selfie_session");
  if (!token) redirect("/login");
  const response = await fetch(
    `${process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000"}/api${path}`,
    {
      headers: { Cookie: `visa_selfie_session=${encodeURIComponent(token.value)}` },
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    },
  );
  if (response.status === 401) redirect("/login");
  if (!response.ok) throw new Error("The administration service is unavailable.");
  return response.json();
}

export async function requireAdmin(): Promise<Admin> {
  return serverApi<Admin>("/auth/me");
}

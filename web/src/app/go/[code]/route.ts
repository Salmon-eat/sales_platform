import { type NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

/**
 * Ad link for a blogger or a channel: citobazar.com/go/<code> -> the chosen page with utm tags.
 * The click is counted by the API; the site tracker then remembers the source for 30 days.
 */
export async function GET(request: NextRequest, { params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  const home = new URL("/", request.url);
  if (!/^[a-z0-9-]{3,60}$/i.test(code)) return NextResponse.redirect(home, 302);

  try {
    const res = await fetch(`${API_URL}/v1/go/${encodeURIComponent(code.toLowerCase())}`, {
      method: "POST",
      headers: { "User-Agent": request.headers.get("user-agent") ?? "" },
      cache: "no-store",
      signal: AbortSignal.timeout(2000),
    });
    if (!res.ok) return NextResponse.redirect(home, 302);
    const link = (await res.json()) as { target: string; channel: string; code: string };
    const target = new URL(link.target, request.url);
    if (target.origin !== home.origin) return NextResponse.redirect(home, 302);
    target.searchParams.set("utm_source", link.channel);
    target.searchParams.set("utm_medium", "link");
    target.searchParams.set("utm_campaign", link.code);
    const response = NextResponse.redirect(target, 302);
    response.headers.set("Cache-Control", "no-store");
    response.headers.set("X-Robots-Tag", "noindex");
    return response;
  } catch {
    return NextResponse.redirect(home, 302);
  }
}

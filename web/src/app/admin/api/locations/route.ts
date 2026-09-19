import { type NextRequest, NextResponse } from "next/server";

import { ApiError, apiFetch } from "@/lib/api";
import { getToken } from "@/lib/auth";

/** City autocomplete for the listing form: forwards to /v1/admin/locations with the session header. */
export async function GET(request: NextRequest) {
  const token = await getToken();
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  try {
    return NextResponse.json(await apiFetch(`/admin/locations?${request.nextUrl.searchParams}`, { token }));
  } catch (error) {
    const status = error instanceof ApiError ? error.status : 502;
    return NextResponse.json({ detail: "error" }, { status });
  }
}

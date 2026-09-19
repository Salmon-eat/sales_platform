import { type NextRequest, NextResponse } from "next/server";

import { ApiError, apiFetch } from "@/lib/api";
import { getToken } from "@/lib/auth";

/** GDPR access request: everything about the person as a JSON file (admins only, checked by the API). */
export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const token = await getToken();
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  if (!/^\d+$/.test(id)) return NextResponse.json({ detail: "Not found" }, { status: 404 });
  try {
    const data = await apiFetch<unknown>(`/admin/applications/${id}/person-data`, { token });
    return new NextResponse(JSON.stringify(data, null, 2), {
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Disposition": `attachment; filename="bazarcito-person-data-${id}.json"`,
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    const status = error instanceof ApiError ? error.status : 502;
    return NextResponse.json({ detail: "error" }, { status });
  }
}

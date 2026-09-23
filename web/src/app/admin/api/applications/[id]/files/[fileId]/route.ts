import { type NextRequest, NextResponse } from "next/server";

import { getToken } from "@/lib/auth";

const API_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

/** The candidate's CV for staff: passed through from the API with its download headers (never inline). */
export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string; fileId: string }> }) {
  const { id, fileId } = await params;
  const token = await getToken();
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  if (!/^\d+$/.test(id) || !/^\d+$/.test(fileId)) return NextResponse.json({ detail: "Not found" }, { status: 404 });
  const res = await fetch(`${API_URL}/v1/admin/applications/${id}/files/${fileId}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) return NextResponse.json({ detail: "error" }, { status: res.status });
  const headers = new Headers({
    "Content-Type": res.headers.get("content-type") ?? "application/octet-stream",
    "Content-Disposition": res.headers.get("content-disposition") ?? "attachment",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; sandbox",
    "Cache-Control": "no-store",
  });
  return new NextResponse(res.body, { headers });
}

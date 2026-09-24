import { type NextRequest, NextResponse } from "next/server";

import { accountToken } from "@/lib/account";

const API_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

/** The candidate's CV for the person who posted the vacancy; always a download, never opened inline. */
export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const token = await accountToken();
  if (!token) return NextResponse.json({ error: "signed_out" }, { status: 401 });

  const { id } = await params;
  if (!/^\d+$/.test(id)) return NextResponse.json({ error: "bad_id" }, { status: 400 });

  const response = await fetch(`${API_URL}/v1/my/candidates/${id}/cv`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!response.ok) {
    return NextResponse.json({ error: "not_found" }, { status: response.status });
  }
  return new NextResponse(response.body, {
    status: 200,
    headers: {
      "Content-Type": "application/octet-stream",
      "Content-Disposition": response.headers.get("content-disposition") ?? "attachment",
      "X-Content-Type-Options": "nosniff",
      "Cache-Control": "no-store",
    },
  });
}

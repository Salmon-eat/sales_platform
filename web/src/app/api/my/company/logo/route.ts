import { type NextRequest, NextResponse } from "next/server";

import { accountToken } from "@/lib/account";

const API_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const MAX_BYTES = 8 * 1024 * 1024;

/** The firm's logo: posted here so the server can add the session token. */
export async function POST(request: NextRequest) {
  const token = await accountToken();
  if (!token) return NextResponse.json({ error: "signed_out" }, { status: 401 });

  const body = await request.arrayBuffer();
  if (body.byteLength > MAX_BYTES) {
    return NextResponse.json({ error: "file_too_large" }, { status: 413 });
  }

  const response = await fetch(`${API_URL}/v1/my/company/logo?lang=es`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/octet-stream" },
    body,
  });
  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}

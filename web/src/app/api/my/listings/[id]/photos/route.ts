import { type NextRequest, NextResponse } from "next/server";

import { accountToken } from "@/lib/account";

const API_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const MAX_BYTES = 8 * 1024 * 1024;

/**
 * The browser cannot call the API itself: the session token lives in an httpOnly cookie that only the
 * server reads. So the photo is posted here and passed on with the token attached.
 */
export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const token = await accountToken();
  if (!token) return NextResponse.json({ error: "signed_out" }, { status: 401 });

  const { id } = await params;
  if (!/^\d+$/.test(id)) return NextResponse.json({ error: "bad_id" }, { status: 400 });

  const body = await request.arrayBuffer();
  if (body.byteLength > MAX_BYTES) {
    return NextResponse.json({ error: "file_too_large" }, { status: 413 });
  }

  const response = await fetch(`${API_URL}/v1/my/listings/${id}/photos`, {
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

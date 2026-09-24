import { type NextRequest, NextResponse } from "next/server";

import { accountToken } from "@/lib/account";

const API_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const MAX_BYTES = 5 * 1024 * 1024;

/** The CV file: the browser posts it here, the server adds the session token and passes it on. */
export async function POST(request: NextRequest) {
  const token = await accountToken();
  if (!token) return NextResponse.json({ error: "signed_out" }, { status: 401 });

  const body = await request.arrayBuffer();
  if (body.byteLength > MAX_BYTES) {
    return NextResponse.json({ error: "file_too_large" }, { status: 413 });
  }

  const response = await fetch(`${API_URL}/v1/my/resume/file?lang=es`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/octet-stream",
      // the name travels percent-encoded: HTTP headers cannot carry Cyrillic
      "X-File-Name": request.headers.get("x-file-name") ?? "",
    },
    body,
  });
  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}

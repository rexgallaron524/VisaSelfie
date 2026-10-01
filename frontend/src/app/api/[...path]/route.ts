import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Stream uploads and playback instead of buffering videos in the web server.
async function proxy(request: NextRequest) {
  const url = new URL(
    request.nextUrl.pathname + request.nextUrl.search,
    process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000",
  );
  const headers = new Headers();
  for (const name of [
    "content-type",
    "content-length",
    "cookie",
    "authorization",
    "x-recording-challenge",
    "origin",
    "range",
    "user-agent",
  ]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const init: RequestInit & { duplex?: "half" } = {
    method: request.method,
    headers,
    cache: "no-store",
    redirect: "manual",
    signal: request.signal,
  };
  if (!["GET", "HEAD"].includes(request.method)) {
    init.body = request.body;
    init.duplex = "half";
  }
  try {
    const upstream = await fetch(url, init);
    const outgoing = new Headers();
    for (const name of [
      "content-type",
      "content-length",
      "content-range",
      "accept-ranges",
      "content-disposition",
      "retry-after",
      "x-request-id",
    ]) {
      const value = upstream.headers.get(name);
      if (value) outgoing.set(name, value);
    }
    for (const cookie of upstream.headers.getSetCookie())
      outgoing.append("set-cookie", cookie);
    outgoing.set("Cache-Control", "no-store");
    return new Response(upstream.body, {
      status: upstream.status,
      headers: outgoing,
    });
  } catch {
    return Response.json(
      { detail: "The service is temporarily unavailable. Please retry." },
      { status: 503 },
    );
  }
}

export {
  proxy as GET,
  proxy as POST,
  proxy as DELETE,
  proxy as HEAD,
  proxy as OPTIONS,
};

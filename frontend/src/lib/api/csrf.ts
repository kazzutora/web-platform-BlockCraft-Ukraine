const CSRF_COOKIE = "csrftoken";

export function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.split("; ").find((part) => part.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

let pending: Promise<void> | null = null;

/** Django's CSRF token; fetches /api/v1/csrf once if the cookie is not set yet. */
export async function getCsrfToken(): Promise<string> {
  let token = readCookie(CSRF_COOKIE);
  if (!token) {
    pending ??= fetch("/api/v1/csrf", { credentials: "include" }).then(() => undefined);
    await pending;
    pending = null;
    token = readCookie(CSRF_COOKIE);
  }
  return token ?? "";
}

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

/** openapi-fetch middleware: adds X-CSRFToken to every unsafe request. */
export const csrfMiddleware = {
  async onRequest({ request }: { request: Request }) {
    if (!SAFE_METHODS.has(request.method)) {
      request.headers.set("X-CSRFToken", await getCsrfToken());
    }
    return request;
  },
};

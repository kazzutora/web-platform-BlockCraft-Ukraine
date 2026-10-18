/** The pending allauth flow from a 401 response body, e.g. "verify_email" or "provider_signup". */
export function pendingFlow(body: unknown): string | null {
  if (!body || typeof body !== "object" || !("data" in body)) return null;
  const data = (body as { data?: { flows?: Array<{ id: string; is_pending?: boolean }> } }).data;
  return data?.flows?.find((flow) => flow.is_pending)?.id ?? null;
}

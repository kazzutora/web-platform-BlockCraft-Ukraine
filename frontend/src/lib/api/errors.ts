import type { components as allauth } from "./allauth";
import type { components } from "./schema";

export type ApiError = components["schemas"]["ApiError"];
type AllauthErrorResponse = allauth["schemas"]["ErrorResponse"];

export type FieldErrors = Record<string, string>;

/** Field → first message, from our API ({fields}) or allauth ({errors: [{param}]}). */
export function fieldErrors(error: unknown, rename: Record<string, string> = {}): FieldErrors {
  const result: FieldErrors = {};
  if (!error || typeof error !== "object") return result;

  if ("fields" in error && error.fields && typeof error.fields === "object") {
    for (const [field, messages] of Object.entries((error as ApiError).fields)) {
      if (messages?.[0]) result[rename[field] ?? field] = messages[0];
    }
  }
  if ("errors" in error && Array.isArray(error.errors)) {
    for (const item of (error as AllauthErrorResponse).errors ?? []) {
      const field = item.param ? (rename[item.param] ?? item.param) : "root";
      result[field] ??= item.message;
    }
  }
  return result;
}

/** A message for the whole form: errors without a field, or our API `detail`. */
export function generalError(error: unknown, fallback: string): string {
  const fields = fieldErrors(error);
  if (fields.root) return fields.root;
  if (fields.non_field_errors) return fields.non_field_errors;
  if (error && typeof error === "object" && "detail" in error && !Object.keys(fields).length) {
    return String((error as ApiError).detail);
  }
  return fallback;
}

import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import { fieldErrors, generalError } from "@/lib/api/errors";

/** Puts API errors on form fields; the rest becomes the `root` form error. */
export function applyErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fields: Array<Path<T>>,
  fallback: string,
): void {
  const byField = fieldErrors(error);
  let placed = false;
  for (const field of fields) {
    if (byField[field]) {
      setError(field, { message: byField[field] });
      placed = true;
    }
  }
  if (!placed || byField.root || byField.non_field_errors) {
    setError("root" as Path<T>, { message: generalError(error, fallback) });
  }
}

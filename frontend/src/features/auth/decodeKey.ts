/** Keys from email links arrive URL-encoded (`MQ%3A…`); allauth expects them decoded. */
export function decodeKey(key: string): string {
  try {
    return decodeURIComponent(key);
  } catch {
    return key;
  }
}

const STORAGE_KEY = "bc:pending-action";
const MAX_AGE_MS = 30 * 60 * 1000;

type PendingAction = { key: string; path: string; at: number };

/** Remembers what a guest tried to do, to replay it after sign-in. */
export function rememberPendingAction(key: string, path: string): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ key, path, at: Date.now() }));
  } catch {
    // Private mode or storage disabled: the user simply repeats the action
  }
}

/** Returns true once if the stored action matches `key` on this page, and forgets it. */
export function takePendingAction(key: string, path: string): boolean {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return false;
    const pending = JSON.parse(raw) as PendingAction;
    if (pending.key !== key || pending.path !== path) return false;
    sessionStorage.removeItem(STORAGE_KEY);
    return Date.now() - pending.at < MAX_AGE_MS;
  } catch {
    return false;
  }
}

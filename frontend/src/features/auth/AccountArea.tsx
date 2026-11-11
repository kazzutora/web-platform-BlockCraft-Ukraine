import { cookies } from "next/headers";

import { looksSignedIn } from "@/lib/session";

import { AccountMenu } from "./AccountMenu";

/** Reads the session cookies on the server; render inside <Suspense>. */
export async function AccountArea() {
  const signedIn = looksSignedIn(await cookies());
  return <AccountMenu signedIn={signedIn} />;
}

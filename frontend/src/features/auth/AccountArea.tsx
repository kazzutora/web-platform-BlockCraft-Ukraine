import { cookies } from "next/headers";

import { AccountMenu } from "./AccountMenu";

/** Reads the session cookie on the server; render inside <Suspense>. */
export async function AccountArea() {
  const signedIn = (await cookies()).has("sessionid");
  return <AccountMenu signedIn={signedIn} />;
}

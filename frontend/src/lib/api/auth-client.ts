import createClient from "openapi-fetch";

import type { paths } from "./allauth";
import { csrfMiddleware } from "./csrf";

/** allauth headless (browser client): sign-up, sign-in, email, password, OAuth. */
export const auth = createClient<paths>({ baseUrl: "", credentials: "include" });
auth.use(csrfMiddleware);

import createClient from "openapi-fetch";

import { csrfMiddleware } from "./csrf";
import type { paths } from "./schema";

/** API client for the browser: same origin, session cookie and CSRF header. */
export const api = createClient<paths>({ baseUrl: "", credentials: "include" });
api.use(csrfMiddleware);

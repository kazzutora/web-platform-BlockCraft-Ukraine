import { cookies } from "next/headers";

import { getGameContext } from "./context";
import { GameChip } from "./GameChip";

/** Server part of the chip: reads «Моя гра» once per render (inside <Suspense>). */
export async function GameChipArea() {
  const [context, jar] = await Promise.all([getGameContext(), cookies()]);
  return <GameChip initial={context} signedIn={jar.has("sessionid")} />;
}

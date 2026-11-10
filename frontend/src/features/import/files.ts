/**
 * Everything /import does with the player's files happens here, in the browser: SHA-1 of
 * each jar, and modrinth.index.json out of a .mrpack. Only hashes and that index leave.
 */

const HEX = Array.from({ length: 256 }, (_, n) => n.toString(16).padStart(2, "0"));

export async function sha1(file: Blob): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-1", await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), (byte) => HEX[byte]).join("");
}

/** Hashes many files a few at a time, reporting progress (a mods folder has hundreds). */
export async function hashAll(
  files: File[],
  onProgress: (done: number) => void,
  parallel = 4,
): Promise<{ hash: string; name: string }[]> {
  const result: { hash: string; name: string }[] = new Array(files.length);
  let next = 0;
  let done = 0;
  async function worker() {
    while (next < files.length) {
      const index = next++;
      const file = files[index];
      result[index] = { hash: await sha1(file), name: file.name };
      onProgress(++done);
    }
  }
  await Promise.all(Array.from({ length: Math.min(parallel, files.length) }, worker));
  return result;
}

const INDEX_NAME = "modrinth.index.json";
const EOCD = 0x06054b50;
const CENTRAL = 0x02014b50;
const LOCAL = 0x04034b50;

export class NotAModpack extends Error {}

/**
 * modrinth.index.json of a .mrpack, without unpacking the rest (configs can weigh a lot).
 * Reads the zip's central directory, then inflates just that entry.
 */
export async function readMrpackIndex(file: Blob): Promise<unknown> {
  try {
    return await readIndex(file);
  } catch (error) {
    // A truncated archive or a ZIP64 one reads past its end: that is «not a modpack» too
    if (error instanceof NotAModpack) throw error;
    throw new NotAModpack(error instanceof Error ? error.message : "broken archive");
  }
}

/** The index is a list of files: anything bigger is not one. */
const INDEX_MAX_BYTES = 5 * 1024 * 1024;

async function readIndex(file: Blob): Promise<unknown> {
  const tailSize = Math.min(file.size, 66_000);
  const tail = new DataView(await file.slice(file.size - tailSize).arrayBuffer());
  let end = -1;
  for (let i = tailSize - 22; i >= 0; i--) {
    if (tail.getUint32(i, true) === EOCD) {
      end = i;
      break;
    }
  }
  if (end < 0) throw new NotAModpack("no zip directory");
  const entries = tail.getUint16(end + 10, true);
  const size = tail.getUint32(end + 12, true);
  const offset = tail.getUint32(end + 16, true);
  const directory = new DataView(await file.slice(offset, offset + size).arrayBuffer());
  const decoder = new TextDecoder();
  let position = 0;
  for (let n = 0; n < entries; n++) {
    if (directory.getUint32(position, true) !== CENTRAL) break;
    const method = directory.getUint16(position + 10, true);
    const compressed = directory.getUint32(position + 20, true);
    const nameLength = directory.getUint16(position + 28, true);
    const extraLength = directory.getUint16(position + 30, true);
    const commentLength = directory.getUint16(position + 32, true);
    const local = directory.getUint32(position + 42, true);
    const name = decoder.decode(
      new Uint8Array(directory.buffer, directory.byteOffset + position + 46, nameLength),
    );
    if (name === INDEX_NAME) {
      const header = new DataView(await file.slice(local, local + 30).arrayBuffer());
      if (header.getUint32(0, true) !== LOCAL) throw new NotAModpack("broken entry");
      const start = local + 30 + header.getUint16(26, true) + header.getUint16(28, true);
      const data = file.slice(start, start + compressed);
      const bytes =
        method === 0
          ? await data.arrayBuffer()
          : method === 8
            ? await new Response(
                (new Response(await data.arrayBuffer()).body as ReadableStream).pipeThrough(
                  new DecompressionStream("deflate-raw"),
                ),
              ).arrayBuffer()
            : null;
      if (!bytes) throw new NotAModpack("unknown compression");
      if (bytes.byteLength > INDEX_MAX_BYTES) throw new NotAModpack("index too large");
      return JSON.parse(decoder.decode(bytes));
    }
    position += 46 + nameLength + extraLength + commentLength;
  }
  throw new NotAModpack("no modrinth.index.json");
}

export type IndexFile = { path: string; hashes: { sha1?: string } };
export type MrpackIndex = {
  name?: string;
  files?: IndexFile[];
  dependencies?: Record<string, string>;
};

/** Files of an index as hashes for /compat/identify (paths become names). */
export function indexFiles(index: MrpackIndex): { hash: string; name: string }[] {
  return (index.files ?? [])
    .filter((file) => file.hashes?.sha1)
    .map((file) => ({
      hash: file.hashes.sha1 as string,
      name:
        String(file.path ?? "")
          .split("/")
          .pop() ?? "",
    }));
}

/** Only what Minecraft loads: jars and zips; a .mrpack is handled on its own. */
export function isModFile(file: File): boolean {
  return /\.(jar|zip)$/i.test(file.name);
}

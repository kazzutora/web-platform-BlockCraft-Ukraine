import { describe, expect, it } from "vitest";

import { NotAModpack, hashAll, indexFiles, readMrpackIndex, sha1 } from "./files";

/** A minimal zip: one or more entries, stored or deflated (as .mrpack files are). */
async function zip(entries: { name: string; text: string; deflate?: boolean }[]): Promise<Blob> {
  const encoder = new TextEncoder();
  const locals: Uint8Array[] = [];
  const centrals: Uint8Array[] = [];
  let offset = 0;
  for (const entry of entries) {
    const name = encoder.encode(entry.name);
    const raw = encoder.encode(entry.text);
    const data = entry.deflate
      ? new Uint8Array(
          await new Response(
            (new Response(raw).body as ReadableStream).pipeThrough(
              new CompressionStream("deflate-raw"),
            ),
          ).arrayBuffer(),
        )
      : raw;
    const method = entry.deflate ? 8 : 0;
    const local = new DataView(new ArrayBuffer(30));
    local.setUint32(0, 0x04034b50, true);
    local.setUint16(8, method, true);
    local.setUint32(18, data.length, true);
    local.setUint32(22, raw.length, true);
    local.setUint16(26, name.length, true);
    locals.push(new Uint8Array(local.buffer), name, data);
    const central = new DataView(new ArrayBuffer(46));
    central.setUint32(0, 0x02014b50, true);
    central.setUint16(10, method, true);
    central.setUint32(20, data.length, true);
    central.setUint32(24, raw.length, true);
    central.setUint16(28, name.length, true);
    central.setUint32(42, offset, true);
    centrals.push(new Uint8Array(central.buffer), name);
    offset += 30 + name.length + data.length;
  }
  const centralSize = centrals.reduce((sum, part) => sum + part.length, 0);
  const end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true);
  end.setUint16(8, entries.length, true);
  end.setUint16(10, entries.length, true);
  end.setUint32(12, centralSize, true);
  end.setUint32(16, offset, true);
  return new Blob([...locals, ...centrals, new Uint8Array(end.buffer)].map((part) => part.slice()));
}

const index = {
  formatVersion: 1,
  name: "Друзі",
  files: [
    { path: "mods/sodium.jar", hashes: { sha1: "a".repeat(40) } },
    { path: "x", hashes: {} },
  ],
  dependencies: { minecraft: "1.21.1", "fabric-loader": "0.16.0" },
};

describe("files in the browser", () => {
  it("counts SHA-1 like Modrinth does", async () => {
    expect(await sha1(new Blob(["abc"]))).toBe("a9993e364706816aba3e25717850c26c9cd0d89d");
  });

  it("hashes many files and reports progress", async () => {
    const seen: number[] = [];
    const files = ["a", "b", "c"].map((text) => new File([text], `${text}.jar`));

    const hashes = await hashAll(files, (done) => seen.push(done), 2);

    expect(hashes.map((item) => item.name)).toEqual(["a.jar", "b.jar", "c.jar"]);
    expect(seen.at(-1)).toBe(3);
  });

  it.each([false, true])(
    "reads modrinth.index.json out of a .mrpack (deflated: %s)",
    async (deflate) => {
      const archive = await zip([
        { name: "overrides/config/a.json", text: "{}" },
        { name: "modrinth.index.json", text: JSON.stringify(index), deflate },
      ]);

      const read = await readMrpackIndex(archive);

      expect(read).toEqual(index);
      expect(indexFiles(read as typeof index)).toEqual([
        { hash: "a".repeat(40), name: "sodium.jar" },
      ]);
    },
  );

  it("refuses what is not a modpack", async () => {
    await expect(readMrpackIndex(new Blob(["not a zip"]))).rejects.toBeInstanceOf(NotAModpack);
    const noIndex = await zip([{ name: "readme.txt", text: "hi" }]);
    await expect(readMrpackIndex(noIndex)).rejects.toBeInstanceOf(NotAModpack);
    const whole = await zip([{ name: "modrinth.index.json", text: JSON.stringify(index) }]);
    const truncated = new Blob([(await whole.arrayBuffer()).slice(10)]);
    await expect(readMrpackIndex(truncated)).rejects.toBeInstanceOf(NotAModpack);
  });
});

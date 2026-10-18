/** Minecraft versions as numbers: "1.21.11" > "1.21.4", "26.1" > "1.21.11". */
function key(version: string): number[] {
  return (version.match(/\d+/g) ?? ["0"]).map(Number);
}

export function versionDescending(a: string, b: string): number {
  const left = key(a);
  const right = key(b);
  for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
    const diff = (right[index] ?? 0) - (left[index] ?? 0);
    if (diff) return diff;
  }
  return 0;
}

import Image from "next/image";

export type IllustrationName =
  | "home"
  | "mods"
  | "packs"
  | "skins"
  | "servers"
  | "moments"
  | "worlds"
  | "empty"
  | "void"
  | "error";

/**
 * Final artwork (PNG/WebP in public/illustrations/) replaces the placeholder
 * as soon as its path is listed here, e.g. `mods: "/illustrations/mods.webp"`.
 */
const finalArtwork: Partial<Record<IllustrationName, string>> = {};

/** [x, y, z, grass top] — voxels of the placeholder scenes. */
type Voxel = [number, number, number, boolean?];

const scenes: Record<IllustrationName, Voxel[]> = {
  home: [
    [0, 0, 0, true],
    [1, 0, 0, true],
    [2, 0, 0, true],
    [0, 1, 0, true],
    [1, 1, 0],
    [2, 1, 0, true],
    [1, 1, 1],
    [1, 1, 2, true],
  ],
  mods: [
    [0, 0, 0, true],
    [2, 0, 0],
    [2, 0, 1, true],
  ],
  packs: [
    [0, 0, 0],
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1, true],
    [1, 0, 1, true],
    [0, 1, 1, true],
  ],
  skins: [
    [0, 0, 0],
    [0, 0, 1],
    [0, 0, 2, true],
  ],
  servers: [
    [0, 0, 0],
    [1, 0, 0],
    [0, 1, 0],
    [1, 1, 0],
    [1, 1, 1],
    [1, 1, 2, true],
  ],
  moments: [
    [0, 0, 0, true],
    [1, 0, 0],
    [1, 0, 1, true],
  ],
  worlds: [
    [0, 0, 0, true],
    [1, 0, 0, true],
    [2, 0, 0, true],
    [0, 1, 0, true],
    [1, 1, 0, true],
    [2, 1, 0, true],
    [0, 2, 0, true],
    [1, 2, 0, true],
    [2, 2, 0, true],
  ],
  empty: [[0, 0, 0]],
  void: [
    [0, 0, 2],
    [2, 1, 0],
    [3, -1, 3],
  ],
  error: [
    [0, 0, 0],
    [1, 0, 0, true],
    [0, 1, 0, true],
    [2, 1, 1],
  ],
};

const U = 10; // half of the cube width in SVG units

function cube([x, y, z, grass]: Voxel) {
  const cx = (x - y) * U;
  const cy = ((x + y) * U) / 2 - z * U;
  const n = [cx, cy - U / 2];
  const e = [cx + U, cy];
  const s = [cx, cy + U / 2];
  const w = [cx - U, cy];
  const down = (p: number[]) => [p[0], p[1] + U];
  const points = (...ps: number[][]) => ps.map((p) => p.join(",")).join(" ");
  return {
    key: `${x}-${y}-${z}`,
    top: points(n, e, s, w),
    left: points(w, s, down(s), down(w)),
    right: points(s, e, down(e), down(s)),
    grass: Boolean(grass),
    bounds: [w[0], n[1], e[0], down(s)[1]],
  };
}

type IllustrationProps = {
  name: IllustrationName;
  /** Rendered width and height in px (≤ 160 in catalog headers). */
  size?: number;
  className?: string;
};

/** Section illustration: voxel placeholder in theme colors until final artwork lands. */
export function Illustration({ name, size = 160, className }: IllustrationProps) {
  const artwork = finalArtwork[name];
  if (artwork) {
    return <Image src={artwork} alt="" width={size} height={size} className={className} />;
  }

  // Painter's order: back to front, bottom to top
  const cubes = [...scenes[name]]
    .sort((a, b) => a[0] + a[1] - (b[0] + b[1]) || a[2] - b[2])
    .map(cube);
  const minX = Math.min(...cubes.map((c) => c.bounds[0]));
  const minY = Math.min(...cubes.map((c) => c.bounds[1]));
  const maxX = Math.max(...cubes.map((c) => c.bounds[2]));
  const maxY = Math.max(...cubes.map((c) => c.bounds[3]));
  const side = Math.max(maxX - minX, maxY - minY) + 4;
  const viewBox = [(minX + maxX - side) / 2, (minY + maxY - side) / 2, side, side].join(" ");

  return (
    <svg
      viewBox={viewBox}
      width={size}
      height={size}
      aria-hidden
      className={className}
      stroke="var(--text)"
      strokeWidth={0.75}
      strokeLinejoin="miter"
    >
      {cubes.map((c) => (
        <g key={c.key} strokeDasharray={name === "empty" ? "2 1.5" : undefined}>
          <polygon points={c.left} fill="var(--line)" />
          <polygon points={c.right} fill="var(--text-muted)" />
          <polygon points={c.top} fill={c.grass ? "var(--accent)" : "var(--surface)"} />
        </g>
      ))}
    </svg>
  );
}

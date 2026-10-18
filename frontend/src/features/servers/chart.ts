import type { StatsPoint } from "./types";

export type ChartGeometry = {
  /** SVG path of the players line, broken where the server was offline. */
  line: string;
  /** Closed path under the line for the fill. */
  area: string;
  /** Y of the gridline labels from the bottom: 0, half, max. */
  ticks: Array<{ y: number; value: number }>;
};

/** Players over time → paths for a `width`×`height` SVG (time on X, players on Y). */
export function chartGeometry(points: StatsPoint[], width: number, height: number): ChartGeometry {
  const max = Math.max(1, ...points.map((point) => point.players));
  const top = Math.ceil(max * 1.1);
  const times = points.map((point) => new Date(point.ts).getTime());
  const start = Math.min(...times);
  const span = Math.max(1, Math.max(...times) - start);
  const x = (time: number) => ((time - start) / span) * width;
  const y = (players: number) => height - (players / top) * height;

  const segments: string[][] = [];
  let current: string[] = [];
  points.forEach((point, index) => {
    if (!point.is_online) {
      if (current.length) segments.push(current);
      current = [];
      return;
    }
    const coords = `${x(times[index]).toFixed(1)},${y(point.players).toFixed(1)}`;
    current.push(current.length ? `L${coords}` : `M${coords}`);
  });
  if (current.length) segments.push(current);

  const line = segments.map((segment) => segment.join(" ")).join(" ");
  const area = segments
    .map((segment) => {
      const first = segment[0].slice(1).split(",")[0];
      const last = segment[segment.length - 1].slice(1).split(",")[0];
      return `${segment.join(" ")} L${last},${height} L${first},${height} Z`;
    })
    .join(" ");
  const ticks = [0, Math.round(top / 2), top].map((value) => ({ y: y(value), value }));
  return { line, area, ticks };
}

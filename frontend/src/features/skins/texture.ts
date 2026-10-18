import { skinsCopy } from "./copy";
import { MAX_FILE_BYTES, type SkinModel } from "./types";

const errors = skinsCopy.form.errors;

/** Same probe as the server (apps/skins/textures.py): the 4th column of a slim arm is empty. */
const SLIM_PROBE = { x: 54, y: 20, width: 2, height: 12 };

export type SkinFileCheck =
  { ok: true; model: SkinModel; legacy: boolean } | { ok: false; error: string };

export function checkFile(file: Pick<File, "type" | "name" | "size">): string | null {
  const png = file.type === "image/png" || file.name.toLowerCase().endsWith(".png");
  if (!png) return errors.type;
  if (file.size > MAX_FILE_BYTES) return errors.size;
  return null;
}

export function checkDimensions(width: number, height: number): string | null {
  return width === 64 && (height === 64 || height === 32) ? null : errors.dimensions(width, height);
}

/** RGBA pixels of a 64×64 texture → arm model; legacy 64×32 skins are always classic. */
export function detectModel(pixels: Uint8ClampedArray, height: number): SkinModel {
  if (height !== 64) return "classic";
  for (let y = SLIM_PROBE.y; y < SLIM_PROBE.y + SLIM_PROBE.height; y += 1) {
    for (let x = SLIM_PROBE.x; x < SLIM_PROBE.x + SLIM_PROBE.width; x += 1) {
      if (pixels[(y * 64 + x) * 4 + 3] !== 0) return "classic";
    }
  }
  return "slim";
}

/** Checks a chosen file in the browser before upload; the server checks again. */
export async function inspectSkinFile(file: File): Promise<SkinFileCheck> {
  const fileError = checkFile(file);
  if (fileError) return { ok: false, error: fileError };
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    return { ok: false, error: errors.broken };
  }
  const { width, height } = bitmap;
  const sizeError = checkDimensions(width, height);
  if (sizeError) {
    bitmap.close();
    return { ok: false, error: sizeError };
  }
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) return { ok: true, model: "classic", legacy: height === 32 };
  context.drawImage(bitmap, 0, 0);
  bitmap.close();
  const pixels = context.getImageData(0, 0, width, height).data;
  return { ok: true, model: detectModel(pixels, height), legacy: height === 32 };
}

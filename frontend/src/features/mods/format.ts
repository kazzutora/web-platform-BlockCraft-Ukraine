const compact = new Intl.NumberFormat("uk-UA", { notation: "compact", maximumFractionDigits: 1 });
const sizeUnits = ["Б", "КБ", "МБ", "ГБ"];

/** 248 165 612 → «248,2 млн». */
export function formatCount(value: number): string {
  return compact.format(value);
}

export function formatFileSize(bytes: number): string {
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < sizeUnits.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toLocaleString("uk-UA", { maximumFractionDigits: 1 })} ${sizeUnits[unit]}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("uk-UA", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

const loaderNames: Record<string, string> = {
  fabric: "Fabric",
  forge: "Forge",
  neoforge: "NeoForge",
  quilt: "Quilt",
  iris: "Iris",
  optifine: "OptiFine",
  canvas: "Canvas",
  vanilla: "Vanilla",
  minecraft: "Minecraft",
};

export function loaderName(loader: string): string {
  return loaderNames[loader] ?? loader;
}

/** Loaders players pick in BlockCraft; Modrinth also lists babric, bukkit, datapack… */
export const mainLoaders = ["fabric", "forge", "neoforge", "quilt"];

export function mainLoadersOf(loaders: readonly string[]): string[] {
  return loaders.filter((loader) => mainLoaders.includes(loader));
}

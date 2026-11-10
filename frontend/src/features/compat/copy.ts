import type { components } from "@/lib/api/schema";
import { plural } from "@/lib/plural";

type Schemas = components["schemas"];
type Params = Record<string, string>;

/**
 * Every explanation of compatibility, by the codes the API returns (tech.md 9.4).
 * The engine never sends sentences: wording lives only here.
 */
export const compatCopy = {
  title: "Що встановити",
  intro: (target: string) => `Усе, що потрібно, щоб це запустилося на ${target}.`,
  status: {
    ok: "Сумісно",
    warnings: (count: number) =>
      plural(count, { one: "попередження", few: "попередження", many: "попереджень" }),
    errors: "Є проблеми",
    incomplete: "Довантажуємо залежності з Modrinth…",
  },
  item: {
    ok: "Сумісно",
    no_version: (target: string) => `Немає версії для ${target}`,
    pinned_incompatible: (target: string) => `Обрана версія не підходить для ${target}`,
    mod_needs_loader: "Потрібен лоадер: без модів цей мод не запуститься",
  } satisfies Record<Schemas["CompatItemStatusEnum"], string | ((target: string) => string)>,
  reason: {
    requested: "ти обрав",
    dependency: (by: string) => `потрібен для ${by}`,
    implicit: (by: string, loader: string) =>
      `додано: шейдерам${loader ? ` на ${loader}` : ""} потрібен цей мод (для ${by})`,
  },
  warning: {
    version_mismatch: (p: Params) =>
      `${p.required_by || "Інший мод"} просить іншу версію ${p.project}; беремо сумісну з твоєю грою.`,
    optifine_manual: (p: Params) =>
      `${p.project} працює через OptiFine. Його немає на Modrinth — встанови вручну з optifine.net.`,
    beta_only: (p: Params) => `${p.project}: для цієї гри є лише бета-версія.`,
    pinned_other_game: (p: Params) =>
      `${p.project}: автор збірки поклав файл, позначений для іншої версії гри. Зазвичай працює, але гарантій немає.`,
    unknown_dependency: (p: Params) =>
      `${p.required_by} посилається на файл, якого немає ні в нас, ні на Modrinth. Може не запуститися.`,
  } satisfies Record<Schemas["CompatWarningCodeEnum"], (p: Params) => string>,
  conflict: (a: string, b: string, by: string) =>
    `${a} і ${b} несумісні — так вказав автор ${by}. Залиш лише один із них.`,
  nearest: "Найближчі версії гри з файлом:",
  missing: "Частини залежностей ще немає в нашому каталозі — додаємо їх з Modrinth.",
  unavailable: (count: number) =>
    count === 1
      ? "Одної обов’язкової залежності немає навіть на Modrinth: автор її прибрав. Без неї гра може не запуститися."
      : `${count} обов’язкових залежностей немає навіть на Modrinth: автори їх прибрали. Без них гра може не запуститися.`,
  hidden: "прибрано з нашого каталогу модератором",
  changeGame: "Змінити «Мою гру» можна в шапці.",
  suggestions: "Можна додати за бажанням:",
  download: "Завантажити",
  downloadFor: (target: string) => `Завантажити для ${target}`,
  nearestButton: (version: string) => `Найближча версія: ${version}`,
  noFiles: "У цього проєкту немає файлів для підтримуваних версій гри.",
  makePack: "Зробити збірку з цього",
  error: "Не вдалося перевірити сумісність. Онови сторінку.",
};

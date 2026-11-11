import type { SearchKind } from "./types";

export const searchCopy = {
  title: "Пошук",
  close: "Закрити",
  open: "Пошук (Ctrl+K)",
  placeholder: "Моди, збірки, скіни, сервери…",
  label: "Що шукаємо?",
  submit: "Шукати",
  hint: "Можна з помилкою чи українською: «sodim» і «содіум» знайдуть Sodium, «шейдери» — шейдери.",
  notForGame: (game: string) => (game ? `не для ${game}` : "не для «Моєї гри»"),
  onlyMine: (game: string) => `Лише для ${game}`,
  mineLabel: "Що показувати",
  /** Names of the `source` codes of the index. */
  sources: { modrinth: "Modrinth", mineskin: "MineSkin", mojang: "Mojang" } as Record<
    string,
    string
  >,
  empty: (q: string) => `За запитом «${q}» нічого не знайшли.`,
  start: "Почни вводити — підкажемо.",
  loading: "Шукаємо…",
  error: "Пошук зараз недоступний. Спробуй за хвилину.",
  all: (q: string) => `Усі результати для «${q}»`,
  more: (count: number) => `Показати всі: ${count}`,
  next: "Далі",
  allKinds: "Усе",
  tabsLabel: "Розділи результатів",
  kinds: {
    mod: "Моди",
    pack: "Збірки",
    skin: "Скіни",
    server: "Сервери",
    collection: "Колекції",
  } satisfies Record<SearchKind, string>,
  kind: {
    mod: "Мод",
    resourcepack: "Ресурспак",
    shader: "Шейдер",
    pack: "Збірка",
    skin: "Скін",
    server: "Сервер",
    collection: "Колекція",
  },
  items: { one: "елемент", few: "елементи", many: "елементів" },
  mods: { one: "мод", few: "моди", many: "модів" },
};

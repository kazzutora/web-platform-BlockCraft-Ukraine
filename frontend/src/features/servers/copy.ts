import type { PluralForms } from "@/lib/plural";

import type { ContentKind, VerificationState } from "./types";

const languageNames = new Intl.DisplayNames(["uk"], { type: "language" });
const regionNames = new Intl.DisplayNames(["uk"], { type: "region" });

/** «uk» → «українська»; unknown codes stay as they are. */
export function languageName(code: string): string {
  try {
    return languageNames.of(code) ?? code;
  } catch {
    return code;
  }
}

/** «UA» → «Україна». */
export function countryName(code: string): string {
  try {
    return regionNames.of(code.toUpperCase()) ?? code;
  } catch {
    return code;
  }
}

export const serversCopy = {
  title: "Сервери",
  description:
    "Реальні сервери Minecraft з Modrinth і від їхніх власників: мова, онлайн і що потрібно, щоб зайти.",
  label: "Сервер",
  plural: { one: "сервер", few: "сервери", many: "серверів" } satisfies PluralForms,
  add: "Додати свій сервер",
  empty: "Таких серверів ще немає. Спробуй прибрати частину фільтрів.",
  kinds: { vanilla: "Без модів", modded: "З модами" } satisfies Record<ContentKind, string>,
  editions: { java: "Java", bedrock: "Bedrock", both: "Java і Bedrock" } as Record<string, string>,
  filters: {
    language: "Мова",
    allLanguages: "Усі мови",
    country: "Країна",
    anyCountry: "Будь-яка країна",
    kind: "Що потрібно",
    version: "Версія",
    anyVersion: "Будь-яка версія",
    category: "Режим",
    online: "Зараз онлайн",
    sort: "Сортування",
    sorts: [
      { value: "popular", label: "Популярні" },
      { value: "online", label: "За онлайном" },
      { value: "new", label: "Нові" },
      { value: "top", label: "Найкращі" },
    ],
  },
  card: {
    pack: "потрібна збірка",
    source: (name: string, source: string) => `${name} на ${source}`,
  },
  live: {
    online: (players: number, max: number) => `${players} / ${max}`,
    onlineLabel: (players: number) => `Онлайн: ${players}`,
    offline: "Офлайн",
    unknown: "Перевіряємо…",
    players: "гравців онлайн",
    latency: (ms: number) => `${ms} мс`,
  },
  copyIp: "Скопіювати IP",
  copied: (address: string) => `Скопійовано: ${address}`,
  copyFailed: "Не вдалося скопіювати. Виділи адресу вручну.",
  verified: "Власник підтвердив",
  join: {
    title: "Щоб зайти",
    version: (version: string) => `Версія ${version}`,
    versions: (list: string) => `Підходять: ${list}`,
    anyVersion: "Версію сервер не вказав — спробуй найновішу.",
    pack: "Потрібна збірка",
    packPending: "Збірку для входу ще завантажуємо з Modrinth — зазирни за кілька хвилин.",
    packMissing: "Сервер з модами, але збірку для входу не вказано. Подробиці — в описі.",
    takePack: "Взяти збірку",
    fits: "Твоя гра підходить.",
    notFits: (game: string) => `«Моя гра» (${game}) не підходить: обери цю версію в лаунчері.`,
    notFitsPack: "Збірка під іншу гру, ніж «Моя гра», — лаунчер поставить усе сам.",
    howTo: "Minecraft → «Мережева гра» → «Додати сервер» → встав адресу.",
  },
  detail: {
    tabsLabel: "Розділи сервера",
    tabs: { about: "Про сервер", stats: "Онлайн", reviews: "Відгуки" },
    noDescription: "Опису поки немає.",
    ownerDescription: "Від власника",
    discord: "Discord",
    website: "Сайт",
    country: "Країна",
    languages: "Мови",
    categories: "Режими й особливості",
    owner: "Власник",
    reviewsHint: "Свій відгук можна оновити: новий замінить попередній.",
    waiting: "Сервер чекає підтвердження: у каталозі його ще немає. Додай код у MOTD.",
    source: (name: string, source: string) => `${name} на ${source}`,
    edit: "Редагувати",
    delete: "Видалити",
    deleteTitle: "Видалити сервер?",
    deleteText: "Він зникне з каталогу, добірок і обраного разом зі статистикою.",
    cancel: "Скасувати",
    deleted: "Сервер видалено",
    error: "Не вдалося. Спробуй ще раз.",
    claim: "Це мій сервер",
  },
  stats: {
    ranges: [
      { value: "24h", label: "24 години" },
      { value: "7d", label: "7 днів" },
    ],
    uptime: (percent: number) => `Аптайм ${percent.toLocaleString("uk-UA")} %`,
    peak: (players: number) => `Пік: ${players}`,
    empty: "Статистика з’явиться після перших перевірок — кожні 5 хвилин.",
    chartLabel: (range: string, peak: number, uptime: string) =>
      `Графік онлайну за ${range}: пік ${peak} гравців, ${uptime}.`,
    noUptime: "аптайм ще невідомий",
  },
  verify: {
    title: "Підтверди, що це твій сервер",
    steps: (code: string) => [
      `Додай код ${code} у MOTD сервера (рядок під назвою в списку серверів).`,
      "Перезапусти сервер або онови MOTD.",
      "Натисни «Перевірити». Після перевірки код можна прибрати.",
    ],
    check: "Перевірити",
    copyCode: "Скопіювати код",
    states: {
      idle: "",
      checking: "Перевіряємо MOTD…",
      verified: "Готово: тепер ти власник сервера.",
      missing: "Коду в MOTD не знайшли. Перевір, що зберіг зміни, і спробуй ще раз.",
      offline: "Сервер не відповідає. Переконайся, що він увімкнений.",
    } satisfies Record<VerificationState, string>,
  },
  addForm: {
    title: "Мій сервер",
    lead: "Сервер мусить відповісти на пінг. Потім підтвердиш, що він твій, кодом у MOTD, і зможеш написати опис українською та вказати збірку для входу. Якщо сервер уже є в каталозі з Modrinth — так само станеш його власником.",
    address: "Адреса",
    addressHint: "Як у Minecraft: play.example.com або IP; порт — через двокрапку.",
    edition: "Видання",
    submit: "Перевірити й додати",
    done: "Сервер відповів. Тепер додай код у MOTD.",
    error: "Не вдалося додати сервер.",
    required: "Вкажи адресу сервера.",
  },
  form: {
    editTitle: "Редагувати сервер",
    name: "Назва",
    summary: "Коротко",
    summaryHint: "Один-два речення для каталогу, до 280 символів.",
    description: "Опис українською",
    descriptionHint: "Markdown, до 5000 символів. Показуємо над описом з Modrinth.",
    discord: "Запрошення в Discord",
    website: "Сайт",
    pack: "Збірка для входу",
    packHint:
      "Почни вводити — підкажемо твої збірки, опубліковані для всіх; або slug модпака з Modrinth (з адреси /packs/…). Порожнє — збірку знову бере Modrinth.",
    languages: "Мови",
    languagesHint: "Коди через кому: uk, en.",
    country: "Країна",
    countryHint: "Двобуквений код: UA, PL. Порожнє — не вказано.",
    kind: "Що потрібно",
    versions: "Версії",
    versionsHint: "Через кому: 1.21.1, 1.21.4.",
    recommended: "Рекомендована версія",
    fromSource:
      "Назву, мови, країну й версії сервера з Modrinth змінюють на Modrinth — ми синхронізуємо їх кожні 6 годин.",
    submit: "Зберегти",
    saved: "Зміни збережено",
    error: "Не вдалося зберегти сервер.",
    errors: {
      url: "Посилання має починатися з https://",
      languages: "Коди мов — дві латинські літери через кому.",
      country: "Код країни — дві латинські літери.",
    },
  },
  mine: {
    title: "Мої сервери",
    empty: "Серверів поки немає — додай свій.",
    waiting: "Чекає коду в MOTD",
  },
};

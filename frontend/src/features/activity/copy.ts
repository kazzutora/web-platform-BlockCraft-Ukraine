import type { PluralForms } from "@/lib/plural";
import type { components } from "@/lib/api/schema";

type ActivityType = components["schemas"]["ActivityItem"]["type"];
type Counts = components["schemas"]["SharedCounts"];

export const activityCopy = {
  me: {
    title: "Моє",
    game: "Моя гра",
    gameNone: "Ще не обрано — обери версію й лоадер, і каталоги підлаштуються.",
    gameChange: "Змінити",
    took: "Взяв",
    tookEmpty: "Тут з’явиться те, що ти завантажуєш: файли модів, .mrpack, IP серверів, скіни.",
    shared: "Поділився",
    sharedEmpty: "Збери збірку, додай скін чи сервер, напиши відгук або переклад — і це буде тут.",
    share: "Поділитися",
    all: "Показати ще",
    links: [
      { href: "/me/saved", label: "Збережене" },
      { href: "/me/collections", label: "Добірки" },
      { href: "/me/packs", label: "Мої збірки й сервери" },
      { href: "/me/notifications", label: "Сповіщення" },
      { href: "/me/settings", label: "Налаштування" },
    ],
    error: "Не вдалося завантажити.",
  },
  types: {
    took: "",
    pack: "Збірка",
    collection: "Добірка",
    review: "Відгук",
    translation: "Переклад",
    server: "Сервер",
    skin: "Скін",
  } satisfies Record<ActivityType, string>,
  actions: {
    download: "Завантажив",
    export_mrpack: "Завантажив .mrpack",
    copy_ip: "Скопіював IP",
    download_png: "Завантажив PNG",
  } as Record<string, string>,
  statuses: {
    draft: "чернетка",
    hidden: "приховано",
    private: "лише я",
    link: "за посиланням",
    pending: "чекає модератора",
    rejected: "відхилено",
    superseded: "замінено новішим",
  } as Record<string, string>,
  counts: {
    packs: { one: "збірка", few: "збірки", many: "збірок" },
    collections: { one: "добірка", few: "добірки", many: "добірок" },
    reviews: { one: "відгук", few: "відгуки", many: "відгуків" },
    translations: { one: "переклад", few: "переклади", many: "перекладів" },
    servers: { one: "сервер", few: "сервери", many: "серверів" },
    skins: { one: "скін", few: "скіни", many: "скінів" },
  } satisfies Record<keyof Counts, PluralForms>,
  profile: {
    shared: "Поділився",
    empty: "Гравець ще нічим не поділився.",
  },
};

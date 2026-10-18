import type { NotificationType } from "./types";

type Payload = { title?: string; reason?: string; actor?: string; excerpt?: string };

export const notificationsCopy = {
  title: "Сповіщення",
  bell: (count: number) => (count ? `Сповіщення: ${count} нових` : "Сповіщення"),
  empty: "Поки тихо. Тут з’являться відповіді, відгуки й рішення модераторів.",
  all: "Усі сповіщення",
  markAll: "Позначити всі прочитаними",
  more: "Показати ще",
  error: "Не вдалося завантажити сповіщення.",
  someone: "Хтось",
  texts: {
    approved: (p: Payload) => `«${p.title}» опубліковано — тепер його бачать усі.`,
    rejected: (p: Payload) =>
      `«${p.title}» не пройшов модерацію${p.reason ? `: ${p.reason}` : "."}`,
    hidden: (p: Payload) =>
      p.excerpt
        ? `Твій коментар «${p.excerpt}» приховано після скарг.`
        : `«${p.title}» приховано після скарг. Модератори вирішили, що він порушує правила.`,
    restored: (p: Payload) => `«${p.title}» знову доступний: скарги не підтвердилися.`,
    reply: (p: Payload) =>
      `${p.actor}: відповідь на твій коментар до «${p.title}» — «${p.excerpt}»`,
    review: (p: Payload) =>
      p.excerpt
        ? `Новий відгук на «${p.title}» від ${p.actor}: «${p.excerpt}»`
        : `Нова оцінка «${p.title}» від ${p.actor}.`,
    warning: (p: Payload) => `Попередження від модераторів: ${p.reason}`,
  } satisfies Record<NotificationType, (payload: Payload) => string>,
  prefs: {
    title: "Що надсилати",
    hint: "Рішення модераторів приходять завжди.",
    reply: "Відповіді на мої коментарі",
    review: "Нові відгуки на мої роботи",
  },
};

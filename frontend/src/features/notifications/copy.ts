import type { NotificationType } from "./types";

type Payload = { title?: string; reason?: string; actor?: string; excerpt?: string };

export const notificationsCopy = {
  title: "Сповіщення",
  bell: (count: number) => (count ? `Сповіщення: ${count} нових` : "Сповіщення"),
  empty: "Поки тихо. Тут з’являться відгуки й рішення модераторів.",
  all: "Усі сповіщення",
  markAll: "Позначити всі прочитаними",
  more: "Показати ще",
  error: "Не вдалося завантажити сповіщення.",
  someone: "Хтось",
  texts: {
    hidden: (p: Payload) =>
      `«${p.title}» приховано після скарг. Модератори вирішили, що він порушує правила.`,
    restored: (p: Payload) => `«${p.title}» знову доступний: скарги не підтвердилися.`,
    review: (p: Payload) =>
      p.excerpt
        ? `Новий відгук на «${p.title}» від ${p.actor}: «${p.excerpt}»`
        : `Нова оцінка «${p.title}» від ${p.actor}.`,
    warning: (p: Payload) => `Попередження від модераторів: ${p.reason}`,
  } satisfies Record<NotificationType, (payload: Payload) => string>,
  prefs: {
    title: "Що надсилати",
    hint: "Рішення модераторів приходять завжди.",
    review: "Нові відгуки на мої роботи",
  },
};

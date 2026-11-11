import type { NotificationType } from "./types";

type Payload = { title?: string; reason?: string; actor?: string; excerpt?: string };

export const notificationsCopy = {
  title: "Сповіщення",
  bell: (count: number) => (count ? `Сповіщення: ${count} нових` : "Сповіщення"),
  empty: "Поки тихо. Тут з’являться відгуки, відповіді, переклади й рішення модераторів.",
  all: "Усі сповіщення",
  markAll: "Позначити всі прочитаними",
  more: "Показати ще",
  error: "Не вдалося завантажити сповіщення.",
  someone: "Хтось",
  texts: {
    hidden: (p: Payload) =>
      `«${p.title}» приховано після скарг. Модератори вирішили, що він порушує правила.`,
    restored: (p: Payload) => `«${p.title}» знову доступний: скарги не підтвердилися.`,
    review_on_your_pack: (p: Payload) =>
      p.excerpt
        ? `Новий відгук на твою збірку «${p.title}» від ${p.actor}: «${p.excerpt}»`
        : `Нова оцінка твоєї збірки «${p.title}» від ${p.actor}.`,
    review_on_your_server: (p: Payload) =>
      p.excerpt
        ? `Новий відгук на твій сервер «${p.title}» від ${p.actor}: «${p.excerpt}»`
        : `Нова оцінка твого сервера «${p.title}» від ${p.actor}.`,
    review_reply: (p: Payload) =>
      `${p.actor} відповів на твій відгук про «${p.title}»: «${p.excerpt}»`,
    server_verified: (p: Payload) =>
      `Сервер «${p.title}» підтверджено: тепер ти власник — напиши опис українською.`,
    translation_published: (p: Payload) =>
      `Твій переклад «${p.title}» схвалено: він уже на сторінці з твоїм підписом.`,
    translation_rejected: (p: Payload) =>
      `Переклад «${p.title}» відхилено${p.reason ? `: ${p.reason}` : "."}`,
    warning: (p: Payload) => `Попередження від модераторів: ${p.reason}`,
    pack_attention: (p: Payload) =>
      p.reason === "errors"
        ? `У збірці «${p.title}» з’явилися проблеми сумісності: Modrinth щось змінив. Перевір її.`
        : `У збірці «${p.title}» з’явилися попередження сумісності. Глянь, чи все гаразд.`,
  } satisfies Record<NotificationType, (payload: Payload) => string>,
  prefs: {
    title: "Що надсилати",
    hint: "Рішення модераторів приходять завжди.",
    review_on_your_pack: "Нові відгуки на мої збірки",
    review_on_your_server: "Нові відгуки на мої сервери",
    review_reply: "Відповіді на мої відгуки",
  },
};

import type { components } from "@/lib/api/schema";

type Field = components["schemas"]["TranslationFieldEnum"];
type Status = components["schemas"]["TranslationStatusEnum"];

export const translationsCopy = {
  ukrainian: "Опис українською",
  by: "переклав",
  summaryBy: (nickname: string) => `короткий опис переклав @${nickname}`,
  showOriginal: "Показати оригінал",
  showUkrainian: "Показати українською",
  original: "Оригінал (з джерела)",
  missing: "Опису українською ще немає — запропонуй переклад.",
  propose: "Запропонувати переклад",
  improve: "Запропонувати кращий переклад",
  fields: { summary: "Короткий опис", description: "Опис" } satisfies Record<Field, string>,
  field: "Що перекладаєш",
  text: "Переклад",
  textHint: {
    summary: "Один-два речення, до 300 символів.",
    description: "Markdown, до 20 000 символів. Перекладай зміст, а не дослівно.",
  } satisfies Record<Field, string>,
  submit: "Надіслати модераторам",
  cancel: "Скасувати",
  sent: "Переклад надіслано: модератор перегляне його найближчим часом.",
  error: "Не вдалося надіслати переклад.",
  statuses: {
    pending: "чекає модератора",
    published: "опубліковано",
    rejected: "відхилено",
    superseded: "замінено",
  } satisfies Record<Status, string>,
  mine: "Мої переклади",
  queue: "Чекають рішення",
  approve: "Схвалити",
  reject: "Відхилити",
  rejectReason: "Причина (побачить автор)",
  decided: "Рішення збережено",
  rejectedBecause: (reason: string) => `Причина: ${reason}`,
};

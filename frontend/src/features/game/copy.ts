/** Texts of «Моя гра» (GameChip, profile fields). */
export const gameCopy = {
  chip: {
    empty: "Моя гра",
    label: (game: string) => `Моя гра: ${game}`,
    title: "Моя гра",
    intro: "Сайт показує моди, збірки й файли під цю версію та лоадер.",
    version: "Версія гри",
    anyVersion: "Будь-яка версія",
    loader: "Лоадер",
    apply: "Застосувати",
    reset: "Скинути",
    howTo: "Не знаю свою версію",
    howToText:
      "Версія написана в лаунчері біля кнопки «Грати» та в лівому нижньому куті головного меню гри.",
    error: "Не вдалося зберегти «Мою гру». Спробуй ще раз.",
  },
  /** Under catalog filters while «Моя гра» is not chosen (tech.md 10.2). */
  invite: "Тут усе популярне. Обери «Мою гру» в шапці — покажемо лише те, що запуститься у тебе.",
};

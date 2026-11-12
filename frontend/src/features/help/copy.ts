import type { IconName } from "@/components/ui/Icon";
import type { components } from "@/lib/api/schema";

import type { CrashLoader } from "./crash/parse";

export type GoalId = components["schemas"]["GoalsEnum"];

const LOADERS: Record<string, string> = {
  fabric: "Fabric",
  quilt: "Quilt",
  forge: "Forge",
  neoforge: "NeoForge",
};

export const loaderTitle = (loader: CrashLoader | string) => LOADERS[loader] ?? loader;

export const helpCopy = {
  hub: {
    title: "Що не так з грою?",
    description: "Обери, що сталося, — покажемо, як це виправити під твою версію гри.",
    problems: [
      {
        href: "/help/crash",
        icon: "warning",
        title: "Гра вилітає або не запускається",
        text: "Встав лог — знайдемо, якого мода бракує чи який не під твою версію.",
      },
      {
        href: "/help/goal?goals=fps",
        icon: "gamepad",
        title: "Лагає, мало FPS",
        text: "Зберемо набір модів оптимізації під твою гру.",
      },
      {
        href: "/import",
        icon: "reload",
        title: "Хочу на нову версію",
        text: "Перетягни папку mods — покажемо, що оновиться, а що ще не вийшло.",
      },
      {
        href: "/servers",
        icon: "server",
        title: "Не можу зайти на сервер",
        text: "На сторінці сервера — яка версія чи збірка потрібна, щоб зайти.",
      },
      {
        href: "/packs/new",
        icon: "users",
        title: "Граю з другом у моди",
        text: "Збери збірку й кинь посилання: у друга буде все те саме.",
      },
      {
        href: "/help/goal",
        icon: "blocks",
        title: "Хочу кращу гру",
        text: "Мінікарта, рецепти, шейдери — обери цілі, решту підберемо.",
      },
    ] satisfies { href: string; icon: IconName; title: string; text: string }[],
    homeLink: "Гра вилітає чи лагає? Вирішити проблему",
  },
  crash: {
    title: "Чому гра не запускається",
    description:
      "Встав вміст latest.log або crash-report. Ми читаємо його у твоєму браузері й питаємо сервер лише про назви модів — сам лог нікуди не відправляється.",
    label: "Лог гри",
    placeholder: "[12:00:00] [main/ERROR]: Incompatible mods found!…",
    where:
      "Де взяти: папка гри → logs/latest.log або crash-reports/. У Modrinth App і Prism Launcher — вкладка «Logs» профілю.",
    file: "Відкрити файл .log",
    submit: "Знайти причину",
    checking: "Шукаємо моди в каталозі…",
    summary: (count: number, context: string) =>
      `${count === 1 ? "Знайшли 1 проблему" : `Знайшли проблем: ${count}`}${context ? ` · ${context}` : ""}`,
    context: (loader: string, loaderVersion: string, game: string) =>
      [loader && [loader, loaderVersion].filter(Boolean).join(" "), game && `Minecraft ${game}`]
        .filter(Boolean)
        .join(" · "),
    nothing: "Відомих помилок не знайшли.",
    nothingHint:
      "Перевір, що вставив увесь лог від початку. Якщо гра падає вже в світі, причина — у рядку «Caused by» нижче; пошукай цей мод у каталозі й онови його.",
    firstError: "Перша помилка в лозі",
    notInCatalog: "немає в нашому каталозі",
    findings: {
      missing: (mod: string, needs: string, range: string) =>
        `${mod} потребує ${needs}${range ? ` (${range})` : ""}, а його не встановлено.`,
      missingMany: (needs: string, range: string, mods: string[]) =>
        `Не встановлено ${needs}${range ? ` (${range})` : ""}, а він потрібен модам (${mods.length}): ${mods.join(", ")}.`,
      wrongGame: (mod: string, expected: string, actual: string) =>
        `${mod} зроблено для Minecraft ${expected}, а в тебе ${actual}.`,
      wrongLoader: (mod: string, loader: string, expected: string, actual: string) =>
        `${mod} потребує ${loader} ${expected}, а встановлено ${actual}.`,
      wrongDependency: (mod: string, needs: string, expected: string, actual: string) =>
        `${mod} працює з ${needs} ${expected}, а встановлено ${actual}.`,
      optional: "Це необов’язкова залежність: можна й просто прибрати її.",
      loaderTooNew: (loader: string) =>
        `Твій ${loader} новіший, ніж дозволяє мод: онови мод до свіжої версії або прибери його.`,
      loaderTooOld: (loader: string) => `Онови ${loader} до новішої версії в лаунчері.`,
      incompatible: (mod: string, other: string) => `${mod} і ${other} не працюють разом.`,
      incompatibleHint: "Онови обидва до найсвіжіших версій під свою гру або прибери один.",
      duplicate: (id: string) => `Мод ${id} встановлено кілька разів:`,
      duplicateHint: "Залиш один файл, решту видали з папки mods.",
      java: (required: number, current: number) =>
        `Потрібна Java ${required}, а гра запущена на Java ${current}.`,
      javaHint: (required: number) =>
        `У налаштуваннях профілю лаунчера (Modrinth App, Prism Launcher) обери Java ${required} або новішу.`,
    },
    actions: {
      get: (name: string) => `Взяти ${name}`,
      forGame: (name: string, game: string) => `${name} для ${game}`,
      open: (name: string) => `Відкрити ${name}`,
      search: (name: string) => `Шукати «${name}»`,
      latestLoader: (loader: string, game: string, version: string) =>
        `Найновіший стабільний ${loader} для ${game}: ${version}`,
    },
    error: "Не вдалося перевірити моди. Спробуй ще раз.",
  },
  goal: {
    title: "Збірка за ціллю",
    description:
      "Обери, чого хочеш від гри, — підберемо найпопулярніші сумісні моди з Modrinth, додамо залежності й перевіримо, що все запуститься разом.",
    goalsLabel: "Чого хочеш від гри",
    goals: {
      fps: { title: "Більше FPS", text: "Рушій рендерингу, оптимізація світу й пам’яті." },
      beauty: { title: "Красива картинка", text: "Шейдери й усе, що їм потрібно." },
      maps: { title: "Карта й мінікарта", text: "Мінікарта в куті екрана й карта світу." },
      inventory: { title: "Інвентар і рецепти", text: "Рецепти, сортування, підказки." },
    } satisfies Record<GoalId, { title: string; text: string }>,
    game: (game: string) => `Під твою гру: ${game}`,
    noGame: "Спершу обери «Мою гру» — версію й лоадер модів.",
    needsLoader:
      "Збірці потрібен лоадер модів: обери Fabric, Forge, NeoForge чи Quilt у «Моїй грі».",
    pick: "Підібрати",
    picking: "Підбираємо…",
    chosen: "Що підібрали",
    nothing: (slot: string) => `${slot}: під цю гру нічого не знайшли`,
    slots: {
      renderer: "Рушій рендерингу",
      game_logic: "Оптимізація світу",
      memory: "Пам’ять",
      entities: "Сутності",
      drawing: "Малювання",
      culling: "Невидимі блоки",
      background: "Гра у фоні",
      shader: "Шейдер",
      minimap: "Мінікарта",
      world_map: "Карта світу",
      recipes: "Рецепти",
      sorting: "Сортування інвентаря",
      food: "Їжа й насичення",
      looking_at: "Що перед тобою",
    } as Record<string, string>,
    resolution: "Що встановити",
    save: "Зберегти як збірку",
    saving: "Зберігаємо…",
    signIn: "Увійди, щоб зберегти збірку",
    saved: "Збірку збережено — допрацюй її в конструкторі.",
    error: "Не вдалося підібрати. Спробуй ще раз.",
    saveError: "Не вдалося зберегти збірку.",
  },
};

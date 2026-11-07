/** «Звідки дані» (/sources) and the footer line. */
export const sourcesCopy = {
  title: "Звідки дані",
  description:
    "Звідки BlockCraft бере моди, збірки, сервери й скіни і коли востаннє оновлював дані.",
  lead: "Ми не створюємо й не зберігаємо модів, збірок, скінів чи серверів. Усе береться з відкритих джерел; ми підбираємо це під твою гру, перевіряємо сумісність і додаємо переклади й відгуки українською.",
  site: "Сайт",
  terms: "Умови використання",
  openLabel: (name: string, what: string) => `${what}: ${name}`,
  onDemand: "Регулярної синхронізації поки немає.",
  never: "Ще не синхронізували.",
  lastSync: "Остання синхронізація",
  running: "Іде зараз",
  jobsLabel: "Що беремо",
  status: {
    ok: "успішно",
    partial: "з помилками",
    failed: "не вдалася",
    running: "виконується",
  },
  counts: {
    created: "нових",
    updated: "оновлено",
    unchanged: "без змін",
    skipped: "пропущено",
    failed: "помилок",
  },
  disclaimer: "Не є офіційним продуктом Minecraft. Не пов’язано з Mojang або Microsoft.",
  error: "Не вдалося завантажити список джерел. Онови сторінку трохи згодом.",
  footer: "Дані: Modrinth, MineSkin, Mojang",
};

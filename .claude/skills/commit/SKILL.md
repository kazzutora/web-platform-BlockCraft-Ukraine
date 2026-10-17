---
name: commit
description: Підготувати й зробити коміт поточних змін у форматі Conventional Commits. Лише за явним запитом користувача.
disable-model-invocation: true
allowed-tools: Bash(git status *) Bash(git diff *) Bash(git add *) Bash(git commit *)
---

## Зміни

!`git status --short`

!`git diff --stat`

!`git diff --cached --stat`

## Інструкції

1. Переглянь зміни. Якщо серед них є `.env*` (крім `.env.example`), великі бінарні файли, дампи БД або випадкові файли — не додавай їх і скажи мені.
2. Якщо зміни логічно різні (напр. фіча + рефакторинг) — запропонуй розбити на кілька комітів.
3. Повідомлення англійською за Conventional Commits:
   - тип: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `style`, `perf`;
   - scope — застосунок або область: `mods`, `skins`, `servers`, `library`, `social`, `accounts`, `ui`, `infra`, `docs`;
   - заголовок ≤ 72 символів, у наказовому способі: `feat(mods): add download resolver`;
   - тіло — 1–4 пункти «що й навіщо», посилання на ID задачі: `Task: 3.6`.
4. Покажи мені повідомлення й список файлів, після підтвердження — `git add` потрібних файлів і `git commit`.
5. Ніколи не роби `git push`.

---
paths:
  - "frontend/**/*.{ts,tsx,css}"
---

# Фронтенд (Next.js + TypeScript)

- App Router. Сторінки каталогів і об'єктів — Server Components з даними через `src/lib/api/server-client.ts`; інтерактив — окремі Client Components (`"use client"`) якомога нижче в дереві.
- Запити з браузера — `src/lib/api/client.ts` (openapi-fetch) + TanStack Query; ключі лише з `src/lib/query-keys.ts`.
- Мутації «Зберегти», «Лайк», «В колекцію», «Оцінити» — оптимістичні: `onMutate` оновлює кеш, `onError` відкочує й показує тост.
- Стан фільтрів каталогу живе в URL (query string), значення за замовчуванням — з профілю гри користувача.
- Форми — react-hook-form + zod; помилки з API (`fields`) мапляться на поля форми.
- Компоненти: `components/ui` — без бізнес-логіки й запитів; `features/<name>` — логіка розділу.
- Файли компонентів — `PascalCase.tsx`, хуки — `useSomething.ts`, один експорт компонента на файл.
- Тексти інтерфейсу українською; не розкидай рядки по JSX — тримай їх на початку файлу або в `features/<name>/copy.ts`.
- Зображення — `next/image`; 3D-скіни — `dynamic(() => import(...), { ssr: false })` з fallback-зображенням.
- Доступність: інтерактивне — лише `button` / `a`, видимий фокус, `aria-label` для іконок, контраст ≥ 4.5:1.
- Перед будь-якою роботою з виглядом застосовуй skill `design-system`.

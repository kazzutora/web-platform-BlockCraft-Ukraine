---
paths:
  - "backend/**/*.py"
---

# Бекенд (Django + DRF)

- Структура застосунку: `models.py` (лише поля й Meta) → `services.py` (усі зміни стану, транзакції) → `selectors.py` (складне читання) → `serializers.py` → `views.py` (тонкі ViewSet-и) → `urls.py`.
- Сервіси — функції з ключовими аргументами: `def add_favorite(*, user: User, kind: str, obj_id: str) -> Favorite`. Помилки домену — `core.exceptions.DomainError(code=..., message=...)`, обробник перетворює їх у формат `{"detail","code","fields"}`.
- Типізуй сигнатури сервісів, селекторів і клієнтів.
- Моделі контенту наслідують міксини з `apps/core/models.py` (`TimeStamped`, `Authored`, `Publishable`, `Engagement`) і реєструються в `apps/core/kinds.py`.
- Узагальнені зв'язки (обране, лайки, відгуки, коментарі, скарги) — через `content_type` + `object_id` з індексом і unique-обмеженнями.
- Масиви версій / лоадерів — `ArrayField` з GIN-індексом.
- Фільтри каталогів — django-filter у `filters.py`; пагінація — класи з `apps/core/pagination.py`.
- Кожен новий ендпоінт: permission-клас, тротлінг-скоуп (якщо запис), `extend_schema` для нестандартних відповідей, тест на права й на успішний сценарій.
- Celery-задачі ідемпотентні, приймають id (не об'єкти), обробляють великі обсяги пачками.
- HTTP до зовнішніх сервісів — httpx з таймаутом, повторами й pydantic-схемами відповіді; ніколи в циклі запиту користувача без кешу.
- Тести: pytest-стиль, фабрики з `tests/factories.py`, `api_client` / `auth_client` фікстури з `conftest.py`, моки зовнішніх API обов'язкові.
- Міграції: одна логічна зміна — одна міграція; дані мігруй окремою `RunPython` з `reverse_code`.

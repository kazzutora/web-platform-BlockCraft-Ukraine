"""Ukrainian names of Modrinth categories and how shader categories map to GPU load."""

CATEGORY_NAMES_UK: dict[str, str] = {
    # mods
    "adventure": "Пригоди",
    "cursed": "Дивне",
    "decoration": "Декор",
    "economy": "Економіка",
    "equipment": "Спорядження",
    "food": "Їжа",
    "game-mechanics": "Механіки гри",
    "library": "Бібліотеки",
    "magic": "Магія",
    "management": "Керування",
    "minigame": "Мініігри",
    "mobs": "Моби",
    "optimization": "Оптимізація",
    "social": "Спілкування",
    "storage": "Сховища",
    "technology": "Технології",
    "transportation": "Транспорт",
    "utility": "Корисне",
    "worldgen": "Генерація світу",
    # resource packs
    "combat": "Бій",
    "modded": "Для модів",
    "realistic": "Реалістичні",
    "simplistic": "Прості",
    "themed": "Тематичні",
    "tweaks": "Правки",
    "vanilla-like": "Як ванільні",
    "audio": "Звуки",
    "blocks": "Блоки",
    "core-shaders": "Ядрові шейдери",
    "entities": "Істоти",
    "environment": "Довкілля",
    "fonts": "Шрифти",
    "gui": "Інтерфейс",
    "items": "Предмети",
    "locale": "Переклади",
    "models": "Моделі",
    # shaders
    "cartoon": "Мультяшні",
    "fantasy": "Фентезі",
    "semi-realistic": "Напівреалістичні",
    "atmosphere": "Атмосфера",
    "bloom": "Світіння",
    "colored-lighting": "Кольорове світло",
    "foliage": "Листя",
    "path-tracing": "Трасування шляхів",
    "pbr": "PBR",
    "reflections": "Відбиття",
    "shadows": "Тіні",
    "potato": "Дуже слабкий ПК",
    "low": "Слабкий ПК",
    "medium": "Середній ПК",
    "high": "Потужний ПК",
    "screenshot": "Для скриншотів",
}

# Shaders declare the performance profiles they ship; the lightest one is the minimum
# hardware they run on, so it defines `gpu_load`
GPU_LOAD_BY_CATEGORY = {
    "potato": "light",
    "low": "light",
    "medium": "medium",
    "high": "heavy",
    "screenshot": "heavy",
}
_GPU_ORDER = {"light": 0, "medium": 1, "heavy": 2}


def category_name_uk(slug: str) -> str:
    return CATEGORY_NAMES_UK.get(slug) or slug.replace("-", " ").capitalize()


def gpu_load_for(categories: list[str]) -> str:
    """Lightest declared impact: what the shader can run on at minimum."""
    loads = [GPU_LOAD_BY_CATEGORY[c] for c in categories if c in GPU_LOAD_BY_CATEGORY]
    return min(loads, key=_GPU_ORDER.__getitem__) if loads else ""

"""Ukrainian names of Modrinth server categories (tag_category, project_type
`minecraft_java_server`), grouped as Modrinth groups them."""

#: header → (Ukrainian group name, {slug: Ukrainian name})
SERVER_CATEGORIES: dict[str, tuple[str, dict[str, str]]] = {
    "minecraft_server_gameplay": (
        "Режим",
        {
            "anarchy": "Анархія",
            "battle-royale": "Королівська битва",
            "bedwars": "BedWars",
            "factions": "Фракції",
            "gens": "Генератори",
            "kitpvp": "KitPvP",
            "lifesteal": "Lifesteal",
            "microgames": "Мікроігри",
            "minigames": "Мініігри",
            "oneblock": "Один блок",
            "parkour": "Паркур",
            "prison": "В’язниця",
            "racing": "Перегони",
            "rpg": "RPG",
            "skyblock": "SkyBlock",
            "towns": "Міста",
            "vanilla-like": "Як ванільний",
        },
    ),
    "minecraft_server_community": (
        "Спільнота",
        {
            "competitive": "Змагання",
            "creator-community": "Для авторів",
            "mmo": "MMO",
            "recording-smp": "SMP для запису",
            "roleplay": "Рольова гра",
            "smp": "SMP",
            "social": "Спілкування",
            "technical": "Технічний",
        },
    ),
    "minecraft_server_features": (
        "Особливості",
        {
            "bosses": "Боси",
            "classes": "Класи",
            "custom-content": "Власний контент",
            "dungeons": "Підземелля",
            "economy": "Економіка",
            "media": "Медіа",
            "op": "OP",
            "personal-worlds": "Особисті світи",
            "plots": "Ділянки",
            "pokemon": "Покемони",
            "pve": "PvE",
            "pvp": "PvP",
            "questing": "Квести",
            "teams": "Команди",
        },
    ),
    "minecraft_server_meta": (
        "Правила",
        {
            "adventure-mode": "Режим пригод",
            "creative-mode": "Творчий режим",
            "crossplay": "Java і Bedrock",
            "hardcore-mode": "Хардкор",
            "keep-inventory": "Речі не випадають",
            "network": "Мережа серверів",
            "offline-mode": "Піратський вхід",
            "survival-mode": "Виживання",
            "whitelisted": "Вайтліст",
            "world-resets": "Скидання світу",
        },
    ),
}


def server_categories() -> list[dict[str, str]]:
    """For /meta: every known category with its Ukrainian name and group."""
    return [
        {"slug": slug, "name": name, "header": header, "header_name": header_name}
        for header, (header_name, names) in SERVER_CATEGORIES.items()
        for slug, name in names.items()
    ]

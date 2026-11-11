"""Ukrainian words players type → the words Modrinth content is described with (R8.2).

Meilisearch synonyms are one-way here: «шейдери» also finds «shader», not the other way.
The second half of R8.2, a Cyrillic query transliterated to Latin («содіум» → «sodium»), is
in `services.search`.
"""

#: word → what it also means; keys lowercase, as players type them
SYNONYMS_UK: dict[str, list[str]] = {
    # content types
    "шейдер": ["shader", "shaders"],
    "шейдери": ["shader", "shaders"],
    "текстури": ["resourcepack", "texture", "textures"],
    "текстурпак": ["resourcepack", "texture"],
    "ресурспак": ["resourcepack"],
    "ресурспаки": ["resourcepack"],
    "датапак": ["datapack"],
    "датапаки": ["datapack"],
    "мод": ["mod"],
    "моди": ["mod", "mods"],
    "збірка": ["modpack", "pack"],
    "збірки": ["modpack", "pack"],
    "модпак": ["modpack"],
    "сервер": ["server"],
    "скін": ["skin"],
    # what mods do
    "оптимізація": ["optimization", "performance", "fps"],
    "оптимізації": ["optimization", "performance", "fps"],
    "фпс": ["fps", "performance"],
    "лаги": ["performance", "optimization", "lag"],
    "мінікарта": ["minimap"],
    "міні-карта": ["minimap"],
    "карта": ["map"],
    "мапа": ["map"],
    "зброя": ["weapons", "guns"],
    "меблі": ["furniture"],
    "декор": ["decoration"],
    "магія": ["magic"],
    "техніка": ["technology", "tech"],
    "технології": ["technology", "tech"],
    "пригоди": ["adventure"],
    "виживання": ["survival"],
    "генерація": ["worldgen", "generation"],
    "світ": ["world", "worldgen"],
    "біоми": ["biomes", "worldgen"],
    "інвентар": ["inventory"],
    "рецепти": ["recipes"],
    "звуки": ["audio", "sound"],
    "інтерфейс": ["gui", "hud", "interface"],
    "покемони": ["pokemon", "cobblemon"],
    "дракони": ["dragons"],
    "транспорт": ["transportation", "vehicles"],
    "літаки": ["aircraft", "planes"],
    "машини": ["cars", "vehicles"],
    "освітлення": ["lighting", "light"],
    "реалістичні": ["realistic"],
    "реалістичний": ["realistic"],
    "моби": ["mobs"],
    "їжа": ["food"],
    "фермерство": ["farming"],
    "сховище": ["storage"],
    "бібліотека": ["library", "api"],
}

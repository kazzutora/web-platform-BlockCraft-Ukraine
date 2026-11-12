"""«Збірка за ціллю» (R8.5): what each goal is made of.

A goal is a list of slots; a slot names real Modrinth projects, best first. The first
candidate that serves «Моя гра» fills the slot; the compat engine then adds dependencies
and reports conflicts. Slots with the same name in two goals are filled once.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Slot:
    name: str
    #: Modrinth slugs, best first
    candidates: tuple[str, ...]
    #: Left empty when one of these is already picked (JourneyMap is a minimap and a map)
    unless: tuple[str, ...] = ()


GOALS: dict[str, tuple[Slot, ...]] = {
    "fps": (
        Slot("renderer", ("sodium", "embeddium")),
        Slot("game_logic", ("lithium",)),
        Slot("memory", ("ferrite-core", "modernfix")),
        Slot("entities", ("entityculling",)),
        Slot("drawing", ("immediatelyfast",)),
        Slot("culling", ("moreculling",)),
        Slot("background", ("dynamic-fps",)),
    ),
    "beauty": (
        Slot("renderer", ("sodium", "embeddium")),
        # The engine adds Iris (or Oculus) for the shader by itself
        Slot("shader", ("complementary-reimagined", "bsl-shaders")),
    ),
    "maps": (
        Slot("minimap", ("xaeros-minimap", "journeymap")),
        Slot("world_map", ("xaeros-world-map",), unless=("journeymap",)),
    ),
    "inventory": (
        Slot("recipes", ("jei", "emi", "rei")),
        Slot("sorting", ("inventory-profiles-next", "mouse-tweaks")),
        Slot("food", ("appleskin",)),
        Slot("looking_at", ("jade", "wthit")),
    ),
}

#: For the title of a saved pack
GOAL_TITLES = {
    "fps": "Більше FPS",
    "beauty": "Красива картинка",
    "maps": "Карта й мінікарта",
    "inventory": "Інвентар і рецепти",
}

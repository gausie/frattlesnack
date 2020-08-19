from typing import Dict
from enum import Enum

class Organ(Enum):
    Stomach = "fullness"
    Liver = "inebriety"
    Spleen = "spleen_hit"

organ_cleaners = {
    Organ.Spleen: {
        "extra-greasy slider": 5,
        "jar of fermented pickle juice": 5,
        "mojo filter": 1,
    },
    Organ.Liver: {
        "Alien plant pod": 3,
        "cuppa Sobrie tea": 1,
        "Mr. Burnsger": 2,
        "spice melange": 3,
        "The Plumber's mushroom stew": 1,
        "Ultra Mega Sour Ball": 3,
    },
    Organ.Stomach: {
        "alien animal milk": 3,
        "Cuppa Voraci tea": 1,
        "Doc Clock's thyme cocktail": 2,
        "lupine appetite hormones": 3,
        "spice melange": 3,
        "sweet tooth": 1,
        "The Mad Liquor": 1,
        "Ultra Mega Sour Ball": 3,
    },
}

limits = {
    "alien animal milk": 1,
    "alien plant pod": 1,
    "cuppa Sobrie tea": 1,
    "cuppa Voraci tea": 1,
    "Doc Clock's thyme cocktail": 2,
    "lupine appetite hormones": 1,
    "mojo filter": 3,
    "Mr. Burnsger": 2,
    "spice melange": 1,
    "sweet tooth": 1,
    "The Mad Liquor": 1,
    "The Plumber's mushroom stew": 1,
    "ultra mega sour ball": 1,
}

utensils = {Organ.Stomach: ["Ol' Scratch's salad fork"],
            Organ.Liver: ["Frosty's frosty mug"]}

price_cache = {} # type: Dict[int, float]

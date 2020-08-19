from typing import Dict, List, Optional, Tuple
import math
from frattlesnake import frattlesnake, Item, Modifier, Effect
from pulp import LpProblem, LpMaximize, LpVariable, lpSum
from tqdm import tqdm
from dataclasses import dataclass
from enum import Enum
from dataclasses import dataclass, field

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


other_items = (list(limits.keys()) +
               [item for organ in organ_cleaners.values() for item in organ.keys()] +
               [item for items in utensils.values() for item in items])


price_cache = {} # type: Dict[int, float]

@dataclass
class Consumable:
    item: Optional[Item] = None
    utensil: Optional[Item] = None
    _name: Optional[str] = None
    _effect: Optional[Effect] = None
    _effect_duration: int = 0
    _space: Dict[Organ, int] = field(default_factory=dict)

    @staticmethod
    def from_item(item: Item, utensil: Optional[Item] = None) -> "Consumable":
        consumable = Consumable()
        consumable.item = item
        consumable.utensil = utensil
        return consumable

    @staticmethod
    def all_utensils(item: Item) -> List["Consumable"]:
        without = [Consumable.from_item(item)]

        for organ in [Organ.Stomach, Organ.Liver]:
            if getattr(item, organ.value):
                return [Consumable.from_item(item, Item(utensil)) for utensil in utensils[organ]] + without

        return without

    def __eq__(self, other) -> bool:
        if isinstance(other, Consumable):
            return self.item.id == other.item.id and self.utensil == other.utensil

        return super().__eq__(other)

    def __hash__(self) -> int:
        if self._name:
            return hash(self._name)

        if self.utensil:
            return hash(f"{self.item.id}-{self.utensil.id}")

        return hash(self.item.id)

    def __str__(self) -> str:
        if self._name:
            return self._name

        if self.utensil:
            return f"{self.item.name} with {self.utensil.name}"

        return self.item.name

    def space(self, organ: Organ) -> Optional[int]:
        if self._space.get(organ):
            print(self._space.get(organ))
            return self._space.get(organ)

        if self.item:
            return getattr(self.item, organ.value) or 0

        return 0

    @property
    def effect(self) -> Optional[Effect]:
        if self._effect:
            return self._effect

        if self.item:
            return self.item.effect

        return None

    @property
    def effect_duration(self) -> Optional[int]:
        if self._effect_duration:
            return self._effect_duration

        if self.item:
            return self.item.modifiers.get(Modifier.EffectDuration, 0)

        return 0

    @property
    def price(self) -> Optional[float]:
        if self.item is None:
            return 0

        price = price_cache.get(self.item.id, None)

        if price is None:
            return None

        if self.utensil:
            price += price_cache.get(self.utensil.id)

        return price

    @property
    def adventures(self) -> float:
        if self.item is None:
            return 0

        adventures = self.item.adventures

        if self.utensil:
            if self.utensil == Item("Ol' Scratch's salad fork"):
                adventures = math.ceil(adventures * (1.5 if "SALAD" in self.item.notes else 1.3))

        return adventures

    def profit(self, quantity: int, meat_per_turn: int, base_meat: int, combat_chance: float) -> float:
        if self.price is None:
            return 0

        gain = (self.adventures or 0) * meat_per_turn - self.price

        if self.effect:
            gain += self.effect.modifiers.get(Modifier.MeatDrop, 0.0) * base_meat * self.effect_duration * combat_chance

        return gain * quantity


synthesis_greedy = Consumable(_name="Synthesis: Greed", _effect=Effect("Synthesis: Greed"), _effect_duration=30, _space={Organ.Spleen: 1})


def calculate_diet(base_items: List[Item], meat_per_turn: int, base_meat: int, combat_chance: float, starting_turns: int = 0) -> Tuple[float, Dict[Consumable, int]]:
    items = [i for item in base_items for i in Consumable.all_utensils(item)] + [synthesis_greedy]

    prob = LpProblem("Diet", LpMaximize)
    diet = LpVariable.dicts("consumable", items, 0, None, cat="Integer")

    prob += lpSum([item.profit(diet[item], meat_per_turn, base_meat, combat_chance) for item in items]) + (starting_turns * meat_per_turn)

    def organ_cleaning(organ: Organ) -> int:
        cleaners = organ_cleaners.get(organ, {})
        return lpSum([diet[variant] * space for item, space in cleaners.items() for variant in Consumable.all_utensils(Item(item))])

    def organ_constraint(organ: Organ, limit: int):
        return lpSum([item.space(organ) * diet[item] for item in items]) <= limit + organ_cleaning(organ)

    prob += organ_constraint(Organ.Stomach, 15)
    prob += organ_constraint(Organ.Liver, 15)
    prob += organ_constraint(Organ.Spleen, 15)

    for item, limit in limits.items():
        prob += lpSum([diet[variant] for variant in Consumable.all_utensils(Item(item))]) <= limit

    prob.writeLP("diet.lp")
    prob.setSolver()
    prob.solver.msg = 0
    prob.solve()

    return prob.objective.value(), {item: diet[item].value() for item in items if diet[item].value() > 0}

def populate_price_cache(items: List[Item]):
    with tqdm(items) as t:
        for item in t:
            price_for_ten = item.price(historical=True, quantity=10)
            t.set_description(f"{item.name}")
            if price_for_ten is not None:
                price = price_for_ten / 10
                price_cache[item.id] = price

def relevant(item: Item, organ: Optional[Organ] = None, threshold: float = 5.0) -> bool:
    if item.name in other_items:
        return True

    if organ is None:
        return False

    organ_space = getattr(item, organ.value) or 0
    if organ_space == 0 or item.adventures is None or item.tradeable is False:
        return False

    if "Vampyre" in item.notes or item.virtual:
        return False

    if (item.adventures / organ_space) >= threshold:
        return True

    if item.effect is None:
        return False

    if any(m in item.effect.modifiers for m in [Modifier.MeatDrop, Modifier.ItemDrop, Modifier.FamiliarWeight]):
        return True

    return False

if __name__ == "__main__":
    #frattlesnake.login("onweb")

    items = [item for item in Item.all()
             if (relevant(item, Organ.Stomach) or relevant(item, Organ.Liver) or relevant(item, Organ.Spleen, 1.5)) or relevant(item)]

    populate_price_cache(items)

    profit, diet = calculate_diet(items,
                                  meat_per_turn=5500,
                                  base_meat=275,
                                  combat_chance=0.7,
                                  starting_turns=200)

    print(f"Profit: {profit:,} meat")

    for item, quantity in diet.items():
        print(f"Consume {item} x {quantity} ({str(item.adventures or 0)} turns @ {item.price:,} meat each)")

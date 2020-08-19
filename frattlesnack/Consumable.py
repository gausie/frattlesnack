from dataclasses import dataclass, field
from typing import Dict, List, Optional
from frattlesnake import Item, Modifier, Effect
import math

from .utils import Organ, utensils, price_cache

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
            if self.utensil == Item("Frosty's frosty mug"):
                adventures = math.ceil(adventures * 1.3)

        if "MARTINI" in self.item.notes:
            adventures += 2

        return adventures

    def profit(self, quantity: int, meat_per_turn: int, base_meat: int, combat_chance: float) -> float:
        if self.price is None:
            return 0

        gain = (self.adventures or 0) * meat_per_turn - self.price

        if self.effect:
            gain += self.effect.modifiers.get(Modifier.MeatDrop, 0.0) * base_meat * self.effect_duration * combat_chance

        return gain * quantity
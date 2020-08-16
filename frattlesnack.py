from typing import Dict, List, Literal, Optional
from frattlesnake import frattlesnake, Item, Modifier
from pulp import LpProblem, LpMaximize, LpVariable, lpSum
from tqdm import tqdm

Organ = Literal["fullness", "inebriety", "spleen_hit"]

organ_cleaners = {
    "spleen_hit": {"extra-greasy slider": 5, "jar of fermented pickle juice": 5, "mojo filter": 1}
}

limits = {
    "mojo filter": 3,
}

price_cache = {} # type: Dict[Item, float]

def populate_price_cache(items: List[Item]):
    with tqdm(items) as t:
        for item in t:
            price_for_ten = item.price(historical=True, quantity=10)
            t.set_description(f"{item.name}")
            if price_for_ten is not None:
                price = price_for_ten / 10
                price_cache[item] = price

def relevant(item: Item, organ: Optional[Organ] = None, threshold: float = 5.0) -> bool:
    if organ is None:
        return item == Item("mojo filter")

    organ_space = getattr(item, organ) or 0
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

def profit(item: Item, quantity: int, meat_per_turn: int, base_meat: int, combat_chance: float) -> float:
    income = (item.adventures or 0) * meat_per_turn
    cost = price_cache.get(item)

    if cost is None:
        return 0

    if item.effect is not None:
        extra = item.effect.modifiers.get(Modifier.MeatDrop, 0.0) * base_meat * item.modifiers.get(Modifier.EffectDuration, 0) * combat_chance
    else:
        extra = 0

    return (income - cost + extra) * quantity

def calculate_diet(items: List[Item], starting_turns: int, meat_per_turn: int, base_meat: int, combat_chance: float) -> Dict[Item, int]:
    prob = LpProblem("Diet", LpMaximize)
    diet = LpVariable.dicts("consumable", items, 0, None, cat="Integer")

    prob += lpSum([profit(item, diet[item], meat_per_turn, base_meat, combat_chance) for item in items]) + (starting_turns * meat_per_turn)

    def organ_cleaning(organ: Organ) -> int:
        cleaners = organ_cleaners.get(organ, {})
        return lpSum([diet[Item(item)] * space for item, space in cleaners.items()])

    def organ_constraint(organ: Organ, limit: int):
        return lpSum([(getattr(item, organ) or 0) * diet[item] for item in items]) <= limit + organ_cleaning(organ)

    prob += organ_constraint("fullness", 15)
    prob += organ_constraint("inebriety", 15)
    prob += organ_constraint("spleen_hit", 15)

    for item, limit in limits.items():
        prob += diet[Item(item)] <= limit

    prob.writeLP("diet.lp")
    prob.setSolver()
    prob.solver.msg = 0
    prob.solve()

    return {item: diet[item].value() for item in items if diet[item].value() > 0}

if __name__ == "__main__":
    frattlesnake.login("onweb")

    items = [item for item in Item.all()
             if (relevant(item, "fullness") or relevant(item, "inebriety") or relevant(item, "spleen_hit", 1.5)) or relevant(item)]

    populate_price_cache(items)

    diet = calculate_diet(items=items,
                          starting_turns=200,
                          meat_per_turn=6500,
                          base_meat=250,
                          combat_chance=0.7)

    for item, quantity in diet.items():
        print(f"Consume {item.name} x {quantity}")

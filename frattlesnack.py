from typing import Dict, List, Optional, Tuple
from frattlesnake import Item, Modifier, Effect
from pulp import LpProblem, LpMaximize, LpVariable, lpSum
from tqdm import tqdm
from itertools import groupby
from enum import Enum

from frattlesnack.Consumable import Consumable
from frattlesnack.utils import Organ, limits, organ_cleaners, utensils, price_cache

other_items = (list(limits.keys()) +
               [item for organ in organ_cleaners.values() for item in organ.keys()] +
               [item for items in utensils.values() for item in items])

synthesis_greedy = Consumable(_name="Synthesis: Greed", _effect=Effect("Synthesis: Greed"), _effect_duration=30, _space={Organ.Spleen: 1})

def calculate_diet(base_items: List[Item],
                   meat_per_turn: int,
                   stomach: int,
                   liver: int,
                   spleen: int,
                   base_meat: int,
                   combat_chance: float,
                   starting_turns: int = 0) -> Tuple[float, Dict[Consumable, int]]:
    items = [i for item in base_items for i in Consumable.all_utensils(item)] + [synthesis_greedy]

    prob = LpProblem("Diet", LpMaximize)
    diet = LpVariable.dicts("consumable", items, 0, None, cat="Integer")

    prob += lpSum([item.profit(diet[item], meat_per_turn, base_meat, combat_chance) for item in items]) + (starting_turns * meat_per_turn)

    def organ_cleaning(organ: Organ) -> int:
        cleaners = organ_cleaners.get(organ, {})
        return lpSum([diet[variant] * space for item, space in cleaners.items() for variant in Consumable.all_utensils(Item(item))])

    def organ_constraint(organ: Organ, limit: int):
        return lpSum([item.space(organ) * diet[item] for item in items]) <= limit + organ_cleaning(organ)

    prob += organ_constraint(Organ.Stomach, stomach)
    prob += organ_constraint(Organ.Liver, liver)
    prob += organ_constraint(Organ.Spleen, spleen)

    for item, limit in limits.items():
        prob += lpSum([diet[variant] for variant in Consumable.all_utensils(Item(item))]) <= limit

    turns = lpSum([(item.adventures or 0) * diet[item] for item in diet]) + starting_turns

    for effect, effect_items in groupby(items, lambda i: i.effect):
        if effect is not None:
            effect_items = list(effect_items)
            unit = min([item.effect_duration for item in effect_items if item.effect_duration is not None])
            prob += lpSum([item.effect_duration * diet[item] for item in effect_items]) <= turns + (unit - 1)

    prob.writeLP("diet.lp")
    prob.setSolver()
    prob.solver.msg = 0
    prob.solve()

    return prob.objective.value(), {item: diet[item].value() for item in diet if diet[item].value() > 0}

def populate_price_cache(items: List[Item], average:int=10):
    with tqdm(items) as t:
        for item in t:
            price_for_ten = item.price(historical=True, quantity=average)
            t.set_description(f"{item.name}")
            if price_for_ten is not None:
                price = price_for_ten / average
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

    starting_turns = 200

    items = [item for item in Item.all()
             if (relevant(item, Organ.Stomach) or relevant(item, Organ.Liver) or relevant(item, Organ.Spleen, 1.5)) or relevant(item)]

    populate_price_cache(items)

    profit, diet = calculate_diet(items,
                                  meat_per_turn=7000,
                                  stomach=15,
                                  liver=21,
                                  spleen=15,
                                  base_meat=275,
                                  combat_chance=28/30,
                                  starting_turns=starting_turns)

    cost = 0
    turns = starting_turns

    for item, quantity in diet.items():
        turns += (item.adventures or 0) * quantity
        cost  += item.price * quantity
        print(f"Consume {item} x {quantity} ({str(item.adventures or 0)} turns @ {item.price:,} meat each)")

    print(f"{turns} turns")
    print(f"Profit (net): {profit:,} meat")
    print(f"Profit (gross): {profit - cost:,} meat")
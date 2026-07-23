from itertools import combinations
from types import SimpleNamespace

from src.rl.prebattle import (
    DRAFT_FEATURES,
    GENERAL_IDS,
    FORMATION_FEATURES,
    PrebattlePolicy,
    encode_draft,
    encode_formation,
)
from src.game_data.generals_config import create_general_from_data
from src.game_data.generals_data import GENERALS_DATA


def test_prebattle_encodings_have_stable_dimensions_and_side_order():
    first, second, third = GENERAL_IDS[:3]
    draft = encode_draft([first, second], [third])
    formation = encode_formation(
        [first, second], [third],
        [{"general_id": first, "row": 0, "col": 0}, {"general_id": second, "row": 2, "col": 3}],
        [{"general_id": third, "row": 1, "col": 2}],
    )

    assert len(draft) == DRAFT_FEATURES
    assert len(formation) == FORMATION_FEATURES
    assert sum(draft) == 3.0
    assert sum(formation) == 6.0


def test_prebattle_fallback_always_returns_legal_draft_and_formation():
    pool = [create_general_from_data(item) for item in GENERALS_DATA[:4]]
    policy = PrebattlePolicy()
    selected = policy.choose_draft(pool, [], cost_limit=8.0)

    assert selected
    assert len(selected) == len(pool)
    selected_cost = sum(g.cost for g in selected)
    legal_same_size = [
        combo for size in range(1, len(pool) + 1)
        for combo in combinations(pool, size)
        if sum(g.cost for g in combo) <= 8.0
    ]
    best_feasible_cost = max(sum(g.cost for g in combo) for combo in legal_same_size)
    assert best_feasible_cost - selected_cost <= 1.0

    positions = policy.choose_formation(selected, [], [])
    assert {item["general_id"] for item in positions} == {g.general_id for g in selected}
    assert len({(item["row"], item["col"]) for item in positions}) == len(selected)
    assert all(0 <= item["row"] < 3 and 0 <= item["col"] < 4 for item in positions)

def test_prebattle_draft_has_no_artificial_general_count_limit():
    pool = [
        SimpleNamespace(
            general_id=9000 + index, cost=1.0, force=4,
            intelligence=4, max_hp=8,
        )
        for index in range(8)
    ]
    selected = PrebattlePolicy().choose_draft(pool, [], cost_limit=8.0)

    assert len(selected) == 8
    assert sum(g.cost for g in selected) == 8.0

    positions = PrebattlePolicy().choose_formation(selected, [], [])
    assert len(positions) == 8
    assert len({(item["row"], item["col"]) for item in positions}) == 8
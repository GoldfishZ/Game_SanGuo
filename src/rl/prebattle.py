"""Telemetry-trained draft and formation value models for PvE."""
from __future__ import annotations

from itertools import combinations, permutations
import random
from pathlib import Path

from src.game_data.generals_data import GENERALS_DATA


PREBATTLE_SCHEMA = "sanguo-prebattle-value-v1"
GENERAL_IDS = tuple(sorted(int(item["id"]) for item in GENERALS_DATA))
GENERAL_INDEX = {general_id: index for index, general_id in enumerate(GENERAL_IDS)}
CELL_COUNT = 12
DRAFT_FEATURES = len(GENERAL_IDS) * 2
FORMATION_FEATURES = DRAFT_FEATURES + len(GENERAL_IDS) * CELL_COUNT * 2


def _torch():
    import torch
    return torch


def build_models():
    """Create the two small value networks without importing torch at module import."""
    torch = _torch()
    nn = torch.nn

    class DraftValueNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.network = nn.Sequential(
                nn.Linear(DRAFT_FEATURES, 128), nn.ReLU(),
                nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1),
            )

        def forward(self, features):
            return self.network(features).squeeze(-1)

    class FormationValueNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.network = nn.Sequential(
                nn.Linear(FORMATION_FEATURES, 256), nn.ReLU(),
                nn.Linear(256, 64), nn.ReLU(), nn.Linear(64, 1),
            )

        def forward(self, features):
            return self.network(features).squeeze(-1)

    return DraftValueNet(), FormationValueNet()


def encode_draft(roster_self, roster_enemy):
    vector = [0.0] * DRAFT_FEATURES
    for general_id in roster_self:
        index = GENERAL_INDEX.get(int(general_id))
        if index is not None:
            vector[index] = 1.0
    offset = len(GENERAL_IDS)
    for general_id in roster_enemy:
        index = GENERAL_INDEX.get(int(general_id))
        if index is not None:
            vector[offset + index] = 1.0
    return vector


def encode_formation(roster_self, roster_enemy, formation_self, formation_enemy):
    vector = encode_draft(roster_self, roster_enemy)
    vector.extend([0.0] * (FORMATION_FEATURES - DRAFT_FEATURES))
    side_size = len(GENERAL_IDS) * CELL_COUNT
    for side, formation in enumerate((formation_self, formation_enemy)):
        side_offset = DRAFT_FEATURES + side * side_size
        for position in formation:
            general_id = int(position["general_id"])
            index = GENERAL_INDEX.get(general_id)
            row, col = int(position["row"]), int(position["col"])
            if index is not None and 0 <= row < 3 and 0 <= col < 4:
                vector[side_offset + index * CELL_COUNT + row * 4 + col] = 1.0
    return vector


def snapshot_formation(team):
    return [
        {"general_id": general.general_id, "row": row, "col": col}
        for row in range(3) for col in range(4)
        if (general := team.formation[row][col]) is not None
    ]


class PrebattlePolicy:
    """Search legal draft/formation choices with learned value networks."""

    def __init__(self, checkpoint=None, *, device="cpu"):
        self.device = device
        self.draft_model = self.formation_model = None
        self.metadata = {}
        if checkpoint:
            self.load(checkpoint)

    @property
    def available(self):
        return self.draft_model is not None and self.formation_model is not None

    def load(self, checkpoint):
        torch = _torch()
        state = torch.load(Path(checkpoint), map_location=self.device, weights_only=False)
        if state.get("schema") != PREBATTLE_SCHEMA:
            raise ValueError(f"不兼容的预战模型 schema: {state.get('schema')}")
        if tuple(state.get("general_ids", ())) != GENERAL_IDS:
            raise ValueError("预战模型的武将注册表与当前游戏不一致")
        self.draft_model, self.formation_model = build_models()
        self.draft_model.load_state_dict(state["draft_model"])
        self.formation_model.load_state_dict(state["formation_model"])
        self.draft_model.to(self.device).eval()
        self.formation_model.to(self.device).eval()
        self.metadata = dict(state.get("metadata") or {})
        return self

    @staticmethod
    def _ids(generals):
        return [int(g.general_id) for g in generals]

    def choose_draft(self, pool, enemy_generals, cost_limit=8.0):
        # PvE follows the same rules as a human draft: no artificial roster-size
        # cap. Board capacity is the only structural bound; cost usually limits
        # the practical roster to fewer than twelve generals.
        max_size = min(len(pool), CELL_COUNT)
        candidates = [
            combo
            for size in range(1, max_size + 1)
            for combo in combinations(pool, size)
            if sum(float(g.cost) for g in combo) <= float(cost_limit)
        ]
        if not candidates:
            return []
        # Budget use is constrained before value inference so sparse telemetry
        # cannot justify leaving several points unused. A one-point window keeps
        # low-cost tactical picks (notably ambush generals) available instead of
        # collapsing every draft into the three most expensive cards.
        best_cost = max(sum(float(g.cost) for g in combo) for combo in candidates)
        candidates = [
            combo for combo in candidates
            if sum(float(g.cost) for g in combo) >= best_cost - 1.0 - 1e-9
        ]
        if not self.available:
            return list(max(candidates, key=self._fallback_draft_score))
        torch = _torch()
        enemy_ids = self._ids(enemy_generals)
        features = torch.tensor(
            [encode_draft(self._ids(combo), enemy_ids) for combo in candidates],
            dtype=torch.float32, device=self.device,
        )
        with torch.no_grad():
            index = int(self.draft_model(features).argmax().item())
        return list(candidates[index])

    @staticmethod
    def _fallback_draft_score(combo):
        # Only used when a trained artifact is unavailable.
        return sum(g.force + g.intelligence + 2 * g.max_hp for g in combo)

    def choose_formation(self, generals, enemy_generals, enemy_formation):
        if not generals:
            return []
        cells = tuple((row, col) for row in range(3) for col in range(4))
        if len(generals) > len(cells):
            return []
        if len(generals) <= 4:
            candidates = list(permutations(cells, len(generals)))
        else:
            # Exhaustive 12Pn becomes impractical once the unrestricted draft
            # selects many low-cost generals. Keep the search deterministic and
            # bounded while still evaluating thousands of distinct assignments.
            seed = sum((index + 1) * int(g.general_id) for index, g in enumerate(generals))
            rng = random.Random(seed)
            candidates = []
            seen = set()

            def add_candidate(positions):
                positions = tuple(positions)
                if positions not in seen:
                    seen.add(positions)
                    candidates.append(positions)

            add_candidate(cells[:len(generals)])
            add_candidate(tuple(reversed(cells))[:len(generals)])
            front_first = tuple((row, col) for col in range(4) for row in range(3))
            add_candidate(front_first[:len(generals)])
            add_candidate(tuple(reversed(front_first))[:len(generals)])
            while len(candidates) < 4096:
                add_candidate(rng.sample(cells, len(generals)))
        if not self.available:
            chosen = candidates[0]
        else:
            torch = _torch()
            self_ids, enemy_ids = self._ids(generals), self._ids(enemy_generals)
            best_index, best_value = 0, float("-inf")
            batch_size = 512
            with torch.no_grad():
                for start in range(0, len(candidates), batch_size):
                    batch = candidates[start:start + batch_size]
                    features = []
                    for positions in batch:
                        formation = [
                            {"general_id": general.general_id, "row": cell[0], "col": cell[1]}
                            for general, cell in zip(generals, positions)
                        ]
                        features.append(encode_formation(
                            self_ids, enemy_ids, formation, enemy_formation,
                        ))
                    values = self.formation_model(torch.tensor(
                        features, dtype=torch.float32, device=self.device,
                    ))
                    value, offset = values.max(dim=0)
                    if float(value.item()) > best_value:
                        best_value = float(value.item())
                        best_index = start + int(offset.item())
            chosen = candidates[best_index]
        return [
            {"general_id": general.general_id, "row": row, "col": col}
            for general, (row, col) in zip(generals, chosen)
        ]

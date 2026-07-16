"""Low-memory self-play through the same Web API contract used by game.js."""

from __future__ import annotations

import argparse
from collections import Counter
import gc
import itertools
import json
import random
import sys
import time
import tracemalloc

sys.path.insert(0, ".")

import main_web
from game_data.generals_data import GENERALS_DATA


def api(path, body=None):
    response = main_web.handle_api(path, body or {}, None)
    return response if isinstance(response, dict) else json.loads(response)


def choose_team(pool, rng, team_size=3, cost_limit=8.0):
    """Choose exactly as the frontend allows: non-empty and within its cost cap."""
    affordable = [
        combo for combo in itertools.combinations(pool, team_size)
        if sum(g["cost"] for g in combo) <= cost_limit
    ]
    if not affordable:
        affordable = [(min(pool, key=lambda g: g["cost"]),)]
    return list(rng.choice(affordable))


def random_formation(generals, rng):
    cells = rng.sample([(row, col) for row in range(3) for col in range(4)], len(generals))
    return [
        {"general_id": general["id"], "row": row, "col": col}
        for general, (row, col) in zip(generals, cells)
    ]


def attackable_front(generals):
    """Mirror Team.get_front_row_generals followed by hidden-ambush filtering."""
    by_column = {}
    for general in generals:
        if not general["alive"] or general["row"] < 0:
            continue
        previous = by_column.get(general["col"])
        if previous is None or general["row"] < previous["row"]:
            by_column[general["col"]] = general
    return [g for g in by_column.values() if not g.get("_ambushHidden")]


def validate_state(state):
    if state.get("phase") not in {
        "select_p1", "select_p2", "formation_p1", "formation_p2", "dice", "battle", "over",
    }:
        raise AssertionError(f"invalid phase: {state.get('phase')}")
    for team_key in ("p1", "p2"):
        team = state.get(team_key)
        if not team:
            continue
        if not 0 <= team["morale"] <= team["maxMorale"]:
            raise AssertionError(f"invalid morale: {team_key} {team['morale']}/{team['maxMorale']}")
        occupied = set()
        for general in team["generals"]:
            if not 0 <= general["hp"] <= general["maxHp"]:
                raise AssertionError(f"invalid hp: {general['name']} {general['hp']}/{general['maxHp']}")
            if general["alive"] != (general["hp"] > 0):
                raise AssertionError(f"alive/hp mismatch: {general['name']}")
            if general["row"] >= 0:
                cell = (general["row"], general["col"])
                if cell in occupied:
                    raise AssertionError(f"duplicate formation cell: {team_key} {cell}")
                occupied.add(cell)


def play_one(game_seed, max_turns=300):
    rng = random.Random(game_seed)
    random.seed(game_seed)
    selected_names = set()
    used_skills = set()

    state = api("/api/new")
    p1 = choose_team(state["pool"], rng, cost_limit=state["cost_limit"])
    state = api("/api/select", {"general_ids": [g["id"] for g in p1]})
    p2 = choose_team(state["pool"], rng, cost_limit=state["cost_limit"])
    state = api("/api/select", {"general_ids": [g["id"] for g in p2]})
    selected_names.update(g["name"] for g in p1 + p2)

    state = api("/api/place", {"positions": random_formation(state["p1"]["generals"], rng)})
    state = api("/api/place", {"positions": random_formation(state["p2"]["generals"], rng)})
    state = api("/api/dice")
    validate_state(state)

    actions = 0
    while state["phase"] == "battle" and state["turn"] <= max_turns:
        current_key = state["current_team"]
        enemy_key = "p2" if current_key == "p1" else "p1"

        # The browser lets each living general use its skill once before Skip.
        for general in list(state[current_key]["generals"]):
            current = next((g for g in state[current_key]["generals"] if g["id"] == general["id"]), None)
            if not current or not current["alive"] or current["_hasUsedSkill"] or current["cooldown"]:
                continue
            if not current["skill"] or current["skill"] == "无":
                continue
            if state[current_key]["morale"] < current["skill_cost"]:
                continue
            payload = {"general_id": current["id"]}
            if current["_targetType"] == "AREA_ENEMY":
                payload.update({
                    "area_row": rng.randrange(3),
                    "area_col": rng.randrange(4),
                    "guess": rng.choice(("奇", "偶")),
                })
            before_used = current["_hasUsedSkill"]
            state = api("/api/battle/skill", payload)
            actions += 1
            validate_state(state)
            after = next((g for g in state[current_key]["generals"] if g["id"] == current["id"]), None)
            if after and not before_used and after["_hasUsedSkill"]:
                used_skills.add(current["skill"])
            if state["phase"] != "battle":
                break
        if state["phase"] != "battle":
            break

        # The frontend can then select every general that has not attacked this turn.
        for general in list(state[current_key]["generals"]):
            current = next((g for g in state[current_key]["generals"] if g["id"] == general["id"]), None)
            if not current or not current["alive"] or current["_hasAttacked"]:
                continue
            targets = attackable_front(state[enemy_key]["generals"])
            if not targets:
                break
            target = rng.choice(targets)
            payload = {"attacker_id": current["id"], "target_id": target["id"]}
            if current["_hasSpeedJudgment"] or current["_hasSpeedRequired"]:
                payload["guess"] = rng.choice(("奇", "偶"))
            state = api("/api/battle/attack", payload)
            actions += 1
            validate_state(state)
            if state["phase"] != "battle":
                break
        if state["phase"] != "battle":
            break

        state = api("/api/battle/skip")
        actions += 1
        validate_state(state)

    completed = state["phase"] == "over"
    return {
        "completed": completed,
        "turns": state.get("turn", 0),
        "winner": state.get("winner", ""),
        "actions": actions,
        "selected_names": selected_names,
        "used_skills": used_skills,
        "last_event": state.get("event", ""),
        "rosters": ([g["name"] for g in p1], [g["name"] for g in p2]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--games", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260716)
    parser.add_argument("--max-turns", type=int, default=300)
    parser.add_argument("--progress", type=int, default=1000)
    args = parser.parse_args()

    expected_generals = {data["name"] for data in GENERALS_DATA}
    expected_skills = {
        main_web.ALL_SKILLS[data["skill_id"]].name for data in GENERALS_DATA
    }
    selected_coverage = set()
    skill_coverage = set()
    winners = Counter()
    crashes = []
    stalls = []
    crash_count = 0
    stall_count = 0
    completed = max_turn = total_actions = 0
    start = time.perf_counter()
    tracemalloc.start()
    initial_current, _ = tracemalloc.get_traced_memory()

    for number in range(1, args.games + 1):
        seed = args.seed + number
        try:
            result = play_one(seed, args.max_turns)
            selected_coverage.update(result["selected_names"])
            skill_coverage.update(result["used_skills"])
            max_turn = max(max_turn, result["turns"])
            total_actions += result["actions"]
            if result["completed"]:
                completed += 1
                winners[result["winner"]] += 1
            else:
                stall_count += 1
                if len(stalls) < 10:
                    stalls.append((number, seed, result["turns"], result["rosters"], result["last_event"]))
        except Exception as error:
            crash_count += 1
            if len(crashes) < 10:
                crashes.append((number, seed, repr(error)))

        if number % args.progress == 0 or number == args.games:
            gc.collect()
            current, peak = tracemalloc.get_traced_memory()
            elapsed = time.perf_counter() - start
            print(
                f"{number}/{args.games} completed={completed} stalls={stall_count} "
                f"crashes={crash_count} max_turn={max_turn} "
                f"mem={current/1024/1024:.2f}MiB peak={peak/1024/1024:.2f}MiB "
                f"rate={number/elapsed:.1f} games/s",
                flush=True,
            )

    gc.collect()
    current, peak = tracemalloc.get_traced_memory()
    elapsed = time.perf_counter() - start
    missing_generals = sorted(expected_generals - selected_coverage)
    missing_skills = sorted(expected_skills - skill_coverage)
    failures = args.games - completed
    print("\nWEB API SELF-PLAY SUMMARY")
    print(f"games={args.games} completed={completed} failures={failures} max_turn={max_turn}")
    print(f"actions={total_actions} elapsed={elapsed:.2f}s rate={args.games/elapsed:.1f} games/s")
    print(f"memory_start={initial_current/1024/1024:.2f}MiB current={current/1024/1024:.2f}MiB peak={peak/1024/1024:.2f}MiB")
    print(f"general_coverage={len(selected_coverage)}/{len(expected_generals)} missing={missing_generals}")
    print(f"skill_coverage={len(skill_coverage)}/{len(expected_skills)} missing={missing_skills}")
    print(f"winners={dict(winners)}")
    if stalls:
        print(f"stalls={stalls}")
    if crashes:
        print(f"crashes={crashes}")
    return 1 if failures or missing_generals or missing_skills else 0


if __name__ == "__main__":
    raise SystemExit(main())

import json
from unittest.mock import patch

import main_web
from game_data.generals_config import get_general_by_name


def post(path, body=None):
    response = main_web.handle_api(path, body or {}, None)
    return response if isinstance(response, dict) else json.loads(response)


def test_web_draft_pools_are_distinct_sixteen_each():
    state = post("/api/new")

    p1_ids = {g.general_id for g in main_web.STATE.pool_p1}
    p2_ids = {g.general_id for g in main_web.STATE.pool_p2}

    assert state["phase"] == "select_p1"
    assert len(p1_ids) == 16
    assert len(p2_ids) == 16
    assert p1_ids.isdisjoint(p2_ids)


def test_web_frontend_submits_complete_formation_and_advances():
    post("/api/new")
    p1_pick = [main_web.STATE.pool_p1[0].general_id]
    p2_pick = [main_web.STATE.pool_p2[0].general_id]

    post("/api/select", {"general_ids": [str(p1_pick[0])]})
    post("/api/select", {"general_ids": [str(p2_pick[0])]})
    assert main_web.STATE.phase == "formation_p1"

    placed = post(
        "/api/place",
        {"positions": [{"general_id": p1_pick[0], "row": 0, "col": 0}]},
    )
    assert placed["phase"] == "formation_p2"
    assert placed["p1"]["generals"][0]["row"] == 0
    assert placed["p1"]["generals"][0]["col"] == 0


def test_web_rejects_incomplete_formation_without_advancing():
    post("/api/new")
    p1_picks = [g.general_id for g in main_web.STATE.pool_p1[:2]]
    p2_pick = main_web.STATE.pool_p2[0].general_id
    post("/api/select", {"general_ids": p1_picks})
    post("/api/select", {"general_ids": [p2_pick]})

    state = post("/api/place", {
        "positions": [{"general_id": p1_picks[0], "row": 0, "col": 0}],
    })

    assert state["phase"] == "formation_p1"
    assert "全部武将" in state["event"]

def test_web_selection_accepts_string_ids_from_frontend():
    post("/api/new")
    p1_pick = main_web.STATE.pool_p1[0].general_id

    selected = post("/api/select", {"general_ids": [str(p1_pick)]})

    assert selected["phase"] == "select_p2"
    assert selected["p1"]["generals"][0]["id"] == p1_pick
    assert selected["p1"]["generals"][0]["row"] == -1

def start_two_single_general_battle():
    post("/api/new")
    p1_pick = main_web.STATE.pool_p1[0].general_id
    p2_pick = main_web.STATE.pool_p2[0].general_id
    post("/api/select", {"general_ids": [str(p1_pick)]})
    post("/api/select", {"general_ids": [str(p2_pick)]})
    post("/api/place", {"positions": [{"general_id": p1_pick, "row": 0, "col": 0}]})
    post("/api/place", {"positions": [{"general_id": p2_pick, "row": 0, "col": 0}]})
    battle = post("/api/dice")
    return battle


def test_web_battle_actions_do_not_advance_until_skip():
    battle = start_two_single_general_battle()
    current_team_key = battle["current_team"]
    current = battle[current_team_key]["generals"][0]
    enemy_key = "p2" if current_team_key == "p1" else "p1"
    enemy = battle[enemy_key]["generals"][0]
    current_player = battle["current_player"]
    turn = battle["turn"]

    after_attack = post(
        "/api/battle/attack",
        {"attacker_id": current["id"], "target_id": enemy["id"]},
    )
    assert after_attack["current_player"] == current_player
    assert after_attack["turn"] == turn

    after_skip = post("/api/battle/skip")
    assert after_skip["current_player"] != current_player
    assert after_skip["turn"] == turn + 1


def test_web_battle_skill_does_not_advance_turn():
    battle = start_two_single_general_battle()
    current_team_key = battle["current_team"]
    current = battle[current_team_key]["generals"][0]
    current_player = battle["current_player"]
    turn = battle["turn"]

    after_skill = post("/api/battle/skill", {"general_id": current["id"]})
    assert after_skill["current_player"] == current_player
    assert after_skill["turn"] == turn


def test_web_rejects_out_of_turn_skill_use():
    battle = start_two_single_general_battle()
    current_key = battle["current_team"]
    other_key = "p2" if current_key == "p1" else "p1"
    other = battle[other_key]["generals"][0]
    morale_before = battle[other_key]["morale"]

    state = post("/api/battle/skill", {"general_id": other["id"]})

    assert state[other_key]["morale"] == morale_before
    assert state[other_key]["generals"][0]["_hasUsedSkill"] is False


def test_web_effects_update_once_per_own_turn():
    battle = start_two_single_general_battle()
    bs = main_web.STATE.battle_system
    original_side = bs.current_side
    original_general = original_side.get_alive_generals()[0]
    original_general.active_skill_cooldown = 3

    post("/api/battle/skip")
    assert original_general.active_skill_cooldown == 3

    post("/api/battle/skip")
    assert bs.current_side is original_side
    assert original_general.active_skill_cooldown == 2


def test_web_battle_finishes_at_engine_turn_limit():
    start_two_single_general_battle()
    main_web.STATE.battle_system.turn_count = main_web.STATE.battle_system.max_turns

    state = post("/api/battle/skip")

    assert state["phase"] == "over"
    assert state["winner"] in {"玩家1", "玩家2"}
    assert "战斗结束" in state["event"]


def test_web_serializes_frontend_skill_and_passive_state():
    post("/api/new")
    player = main_web.STATE.controller.player1
    thunder = get_general_by_name("夏侯月姬")
    player.add_general_to_team(thunder)
    data = main_web.STATE._team_json(player)["generals"][0]

    assert data["_targetType"] == "AREA_ENEMY"
    assert data["skill_cost"] == thunder.active_skill.morale_cost
    assert data["_fenceBroken"] is False
    assert data["_reviveUsed"] is False


def test_web_reset_clears_previous_battle_metadata():
    main_web.STATE.turn_count = 99
    main_web.STATE.winner = "旧胜者"
    main_web.STATE.dice_p1 = 6
    main_web.STATE.dice_p2 = 1
    main_web.STATE.compensation = "旧补偿"

    state = post("/api/new")

    assert state["turn"] == 0
    assert state["winner"] == ""
    assert "d1" not in state
    assert "compensation" not in state


def test_web_dice_keeps_rerolling_until_not_tied():
    post("/api/new")
    p1_pick = main_web.STATE.pool_p1[0].general_id
    p2_pick = main_web.STATE.pool_p2[0].general_id
    post("/api/select", {"general_ids": [p1_pick]})
    post("/api/select", {"general_ids": [p2_pick]})
    post("/api/place", {"positions": [{"general_id": p1_pick, "row": 0, "col": 0}]})
    post("/api/place", {"positions": [{"general_id": p2_pick, "row": 0, "col": 0}]})

    with patch("main_web.random.randint", side_effect=[3, 3, 2, 2, 1, 6]):
        state = post("/api/dice")

    assert state["d1"] == 1
    assert state["d2"] == 6
    assert state["first"] == "玩家2"

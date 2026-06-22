import json

import main_web


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


def test_web_placement_does_not_advance_until_confirmed():
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
    assert placed["phase"] == "formation_p1"
    assert placed["p1"]["generals"][0]["row"] == 0
    assert placed["p1"]["generals"][0]["col"] == 0

    confirmed = post("/api/place", {"positions": []})
    assert confirmed["phase"] == "formation_p2"


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
    post("/api/place", {"positions": []})
    post("/api/place", {"positions": [{"general_id": p2_pick, "row": 0, "col": 0}]})
    post("/api/place", {"positions": []})
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
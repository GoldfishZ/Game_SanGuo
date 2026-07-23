import json
from itertools import combinations
from unittest.mock import patch

import main_web
from src.game_data.generals_config import get_general_by_name


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
    assert state["winner"] == "平局"
    assert "战斗结束" in state["event"]


def test_web_serializes_frontend_skill_and_passive_state():
    post("/api/new")
    player = main_web.STATE.controller.player1
    thunder = get_general_by_name("夏侯月姬")
    player.add_general_to_team(thunder)
    data = main_web.STATE._team_json(player)["generals"][0]

    assert data["_targetType"] == "AREA_ENEMY"
    assert data["skill_id"] == "thunder_strike"
    assert data["skill_cost"] == thunder.active_skill.morale_cost
    assert data["_frontOnlyAttack"] is False
    assert data["_forcedTargetId"] is None
    assert data["_fenceBroken"] is False
    assert data["_reviveUsed"] is False

    target = get_general_by_name("张飞")
    main_web.STATE.controller.player2.add_general_to_team(target)
    thunder.add_buff("front_only_attack", 1, 1)
    thunder.add_debuff("forced_attack_target", target, 1)
    dynamic = main_web.STATE._team_json(player)["generals"][0]
    assert dynamic["_frontOnlyAttack"] is True
    assert dynamic["_forcedTargetId"] == target.general_id


def test_web_grand_cavalry_order_auto_targets_caster_column():
    main_web.STATE.reset()
    controller = main_web.STATE.controller
    dong_zhuo = get_general_by_name("董卓")
    ally = get_general_by_name("张辽")
    enemy = get_general_by_name("张飞")
    controller.player1.add_general_to_team(dong_zhuo)
    controller.player1.add_general_to_team(ally)
    controller.player2.add_general_to_team(enemy)
    controller.player1.team.position_general(dong_zhuo, 1, 0)
    controller.player1.team.position_general(ally, 1, 1)
    controller.player2.team.position_general(enemy, 0, 0)
    main_web.STATE.phase = "battle"
    main_web.STATE.battle_system = main_web.BattleSystem(
        controller.player1.team,
        controller.player2.team,
        callbacks=None,
        first_player_team_name=controller.player1.team.team_name,
    )
    morale_before = controller.player1.team.current_morale

    state = post("/api/battle/skill", {"general_id": dong_zhuo.general_id})

    assert state["skill_result"]["success"] is True
    assert state["skill_result"]["targets_affected"] == 2
    assert state["p1"]["morale"] == morale_before - 7
    assert dong_zhuo.get_effective_force() == 12
    assert ally.get_effective_force() == 11

def test_web_weakening_chain_respects_selected_enemy_target():
    main_web.STATE.reset()
    controller = main_web.STATE.controller
    guo_huanghou = get_general_by_name("郭皇后")
    first_enemy = get_general_by_name("张飞")
    selected_enemy = get_general_by_name("甘宁")
    controller.player1.add_general_to_team(guo_huanghou)
    controller.player2.add_general_to_team(first_enemy)
    controller.player2.add_general_to_team(selected_enemy)
    controller.player1.team.position_general(guo_huanghou, 0, 0)
    controller.player2.team.position_general(first_enemy, 0, 0)
    controller.player2.team.position_general(selected_enemy, 1, 0)
    main_web.STATE.phase = "battle"
    main_web.STATE.battle_system = main_web.BattleSystem(
        controller.player1.team,
        controller.player2.team,
        callbacks=None,
        first_player_team_name=controller.player1.team.team_name,
    )
    first_force = first_enemy.get_effective_force()
    selected_force = selected_enemy.get_effective_force()

    state = post("/api/battle/skill", {
        "general_id": guo_huanghou.general_id,
        "target_id": selected_enemy.general_id,
    })

    assert state["skill_result"]["success"] is True
    assert state["skill_result"]["details"][0]["target"] == selected_enemy.name
    assert first_enemy.get_effective_force() == first_force
    assert selected_enemy.get_effective_force() == selected_force - 3

def test_web_thunder_strike_uses_caster_guess_once_and_triggers_on_success():
    """Web 实际路径必须把玩家猜测传入，并用一次成功判定触发整次雷击。"""
    main_web.STATE.reset()
    controller = main_web.STATE.controller
    caster = get_general_by_name("夏侯月姬")
    targets = [get_general_by_name("张飞"), get_general_by_name("甘宁")]
    controller.player1.add_general_to_team(caster)
    for target in targets:
        controller.player2.add_general_to_team(target)
    controller.player1.team.position_general(caster, 0, 0)
    controller.player2.team.position_general(targets[0], 0, 0)
    controller.player2.team.position_general(targets[1], 1, 1)
    main_web.STATE.phase = "battle"
    main_web.STATE.battle_system = main_web.BattleSystem(
        controller.player1.team,
        controller.player2.team,
        callbacks=None,
        first_player_team_name=controller.player1.team.team_name,
    )
    hp_before = [target.current_hp for target in targets]

    with patch("src.models.general.random.randint", return_value=2) as randint:
        state = post("/api/battle/skill", {
            "general_id": caster.general_id,
            "area_row": 0,
            "area_col": 0,
            "guess": "偶",
        })

    result = state["skill_result"]
    assert result["judgment"]["success"] is True
    assert result["triggered"] is True
    assert randint.call_count == 1
    assert all(target.current_hp < hp for target, hp in zip(targets, hp_before))


def test_web_meteor_rite_uses_selected_visual_vertical_column():
    """前端选择的视觉竖列应映射到同一 logical row，而不是通用 2x2 区域。"""
    main_web.STATE.reset()
    controller = main_web.STATE.controller
    xiao_qiao = get_general_by_name("小乔")
    untouched = get_general_by_name("张飞")
    targets = [get_general_by_name("曹操"), get_general_by_name("夏侯惇")]

    controller.player1.add_general_to_team(xiao_qiao)
    controller.player2.add_general_to_team(untouched)
    for target in targets:
        controller.player2.add_general_to_team(target)

    controller.player1.team.position_general(xiao_qiao, 0, 0)
    controller.player2.team.position_general(untouched, 0, 0)
    controller.player2.team.position_general(targets[0], 1, 0)
    controller.player2.team.position_general(targets[1], 1, 3)

    main_web.STATE.phase = "battle"
    main_web.STATE.battle_system = main_web.BattleSystem(
        controller.player1.team,
        controller.player2.team,
        callbacks=None,
        first_player_team_name=controller.player1.team.team_name,
    )
    untouched_hp = untouched.current_hp
    target_hps = [target.current_hp for target in targets]

    state = post("/api/battle/skill", {
        "general_id": xiao_qiao.general_id,
        "skill_row": 1,
    })

    assert "流星的仪式" in state["event"]
    assert untouched.current_hp == untouched_hp
    assert all(target.current_hp < hp for target, hp in zip(targets, target_hps))


def test_web_area_skill_respects_player_selected_2x2_origin():
    main_web.STATE.reset()
    controller = main_web.STATE.controller
    zhang_fei = get_general_by_name("张飞")
    outside = get_general_by_name("甘宁")
    selected = get_general_by_name("太史慈")
    controller.player1.add_general_to_team(zhang_fei)
    controller.player2.add_general_to_team(outside)
    controller.player2.add_general_to_team(selected)
    controller.player1.team.position_general(zhang_fei, 0, 0)
    controller.player2.team.position_general(outside, 0, 0)
    controller.player2.team.position_general(selected, 2, 3)
    main_web.STATE.phase = "battle"
    main_web.STATE.battle_system = main_web.BattleSystem(
        controller.player1.team,
        controller.player2.team,
        callbacks=None,
        first_player_team_name=controller.player1.team.team_name,
    )
    outside_hp = outside.current_hp
    selected_hp = selected.current_hp

    state = post("/api/battle/skill", {
        "general_id": zhang_fei.general_id,
        "area_row": 1,
        "area_col": 2,
    })

    assert "轮枪战术" in state["event"]
    assert outside.current_hp == outside_hp
    assert selected.current_hp < selected_hp


def setup_web_speed_judgment_battle(effect_type):
    main_web.STATE.reset()
    controller = main_web.STATE.controller
    attacker = get_general_by_name("公孙瓒")
    target = get_general_by_name("张飞")
    controller.player1.add_general_to_team(attacker)
    controller.player2.add_general_to_team(target)
    controller.player1.team.position_general(attacker, 0, 0)
    controller.player2.team.position_general(target, 0, 0)
    if effect_type == "bonus_attack":
        attacker.add_buff("attack_speed_judgment", 1, 1)
    else:
        attacker.add_debuff("attack_speed_required", 1, 1)
    main_web.STATE.phase = "battle"
    main_web.STATE.battle_system = main_web.BattleSystem(
        controller.player1.team,
        controller.player2.team,
        callbacks=None,
        first_player_team_name=controller.player1.team.team_name,
    )
    return attacker, target


def test_web_attack_returns_successful_speed_judgment_for_animation():
    attacker, target = setup_web_speed_judgment_battle("bonus_attack")
    hp_before = target.current_hp

    with patch("src.models.general.random.randint", return_value=3):
        state = post("/api/battle/attack", {
            "attacker_id": attacker.general_id,
            "target_id": target.general_id,
            "guess": "奇",
        })

    assert state["speed_judgment"] == {
        "guess": "odd",
        "dice": 3,
        "parity": "odd",
        "success": True,
        "mode": "bonus_attack",
        "message": "判定成功，获得追加普攻",
    }
    assert state["attack_result"]["performed"] is True
    assert state["attack_result"]["damage"] == hp_before - target.current_hp
    assert state["p1"]["generals"][0]["_hasExtraAttack"] is True
    assert "可重新选择目标的追加普攻" in state["event"]

    state = post("/api/battle/attack", {
        "attacker_id": attacker.general_id,
        "target_id": target.general_id,
    })

    assert state["attack_result"]["performed"] is True
    assert state["p1"]["generals"][0]["_hasExtraAttack"] is False
    assert state["p1"]["generals"][0]["_hasAttacked"] is True


def test_web_failed_required_speed_judgment_cancels_attack():
    attacker, target = setup_web_speed_judgment_battle("attack_required")
    hp_before = target.current_hp

    with patch("src.models.general.random.randint", return_value=2):
        state = post("/api/battle/attack", {
            "attacker_id": attacker.general_id,
            "target_id": target.general_id,
            "guess": "奇",
        })

    assert state["speed_judgment"]["dice"] == 2
    assert state["speed_judgment"]["success"] is False
    assert state["speed_judgment"]["mode"] == "attack_required"
    assert state["speed_judgment"]["message"] == "判定失败，本次普攻被取消"
    assert state["attack_result"]["performed"] is False
    assert target.current_hp == hp_before
    assert "掷出2点（偶），失败" in state["event"]


def test_web_bravery_and_charisma_use_explicit_guesses_and_keep_defeated_card_position():
    main_web.STATE.reset()
    controller = main_web.STATE.controller
    attacker = get_general_by_name("张飞")
    target = get_general_by_name("蔡文姬")
    controller.player1.add_general_to_team(attacker)
    controller.player2.add_general_to_team(target)
    controller.player1.team.position_general(attacker, 0, 0)
    controller.player2.team.position_general(target, 0, 0)
    attacker.take_damage(attacker.max_hp - 1)
    target.take_damage(target.max_hp - 1)
    main_web.STATE.phase = "battle"
    main_web.STATE.battle_system = main_web.BattleSystem(
        controller.player1.team,
        controller.player2.team,
        callbacks=None,
        first_player_team_name=controller.player1.team.team_name,
    )

    with patch("src.game_data.passive_skills_config.random.choice", return_value="even"), \
         patch("src.game_data.passive_skills_config.random.randint", side_effect=[3, 2]):
        state = post("/api/battle/attack", {
            "attacker_id": attacker.general_id,
            "target_id": target.general_id,
            "bravery_guess": "奇",
            "charisma_guess": "偶",
        })

    events = state["attack_result"]["events"]
    bravery = next(event for event in events if event["type"] == "bravery_judgment")
    charisma = next(event for event in events if event["type"] == "charisma_judgment")
    assert bravery["judgment"]["guess"] == "odd"
    assert bravery["judgment"]["success"] is True
    assert charisma["judgment"]["guess"] == "even"
    assert charisma["judgment"]["success"] is True
    assert charisma["attacker_id"] == attacker.general_id
    assert state["p2"]["generals"][0]["alive"] is False
    assert state["p2"]["generals"][0]["row"] == 0
    assert state["p2"]["generals"][0]["col"] == 0

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


class FakePVEController:
    available = True
    load_errors = []

    def choose_draft(self, pool, enemy_generals, cost_limit):
        selected = []
        for general in sorted(pool, key=lambda item: item.cost):
            if sum(item.cost for item in selected) + general.cost <= cost_limit:
                selected.append(general)
        return selected

    def choose_formation(self, generals, enemy_player):
        return [
            {"general_id": general.general_id, "row": index % 3, "col": index // 3}
            for index, general in enumerate(generals)
        ]

    def step_battle_turn(self, state, ai_team, enemy_team, subphase="skill"):
        if subphase == "skill":
            return {
                "kind": "end_skill", "success": True,
                "next_subphase": "attack", "done": False,
            }
        turn_result = state.ensure_rules().end_turn()
        state.turn_count = state.battle_system.turn_count
        morale_event = turn_result["morale_event"]
        morale_event["team"] = "p2"
        state.last_event = f"电脑已完成行动，第{state.turn_count}回合轮到玩家1"
        return {
            "kind": "end_attack", "success": True,
            "next_subphase": "skill", "done": False,
            "turn_events": [morale_event],
        }

    def run_battle_turn(self, state, ai_team, enemy_team):
        return []


def test_web_pve_skips_ai_draft_and_formation_screens():
    state = post("/api/new", {"mode": "pve"})
    assert state["mode"] == "pve"
    assert state["ai_team"] == "p2"
    main_web.STATE.pve_controller = FakePVEController()

    legal_pick = next(g for g in main_web.STATE.pool_p1 if g.cost <= state["cost_limit"])
    selected = post("/api/select", {"general_ids": [legal_pick.general_id]})
    assert selected["phase"] == "formation_p1"
    assert selected["p2"]["generals"]

    placed = post("/api/place", {
        "positions": [{"general_id": legal_pick.general_id, "row": 0, "col": 0}],
    })
    assert placed["phase"] == "dice"
    ai_positions = {
        (general["row"], general["col"])
        for general in placed["p2"]["generals"]
    }
    assert len(ai_positions) == len(placed["p2"]["generals"])


def test_web_pve_exposes_computer_turn_one_action_at_a_time():
    state = post("/api/new", {"mode": "pve"})
    main_web.STATE.pve_controller = FakePVEController()
    legal_pick = next(g for g in main_web.STATE.pool_p1 if g.cost <= state["cost_limit"])
    post("/api/select", {"general_ids": [legal_pick.general_id]})
    post("/api/place", {
        "positions": [{"general_id": legal_pick.general_id, "row": 0, "col": 0}],
    })

    with patch("main_web.random.randint", side_effect=[1, 6]):
        battle = post("/api/dice")

    assert battle["current_team"] == "p2"
    assert battle["ai_thinking"] is True
    assert "ai_action" not in battle

    skill_phase = post("/api/pve/step")
    assert skill_phase["ai_action"]["kind"] == "end_skill"
    assert skill_phase["current_team"] == "p2"

    attack_phase = post("/api/pve/step")
    assert attack_phase["ai_action"]["kind"] == "end_attack"
    assert attack_phase["current_team"] == "p1"
    assert attack_phase["ai_thinking"] is False


def test_web_pve_conceals_enemy_ambush_identity_until_reveal():
    post("/api/new", {"mode": "pve"})
    ambush = get_general_by_name("张任")
    ai = main_web.STATE.controller.player2
    ai.add_general_to_team(ambush)
    assert ai.team.position_general(ambush, 1, 2)
    main_web.STATE.phase = "dice"

    concealed = main_web.STATE.to_json()["p2"]["generals"][0]
    assert concealed["id"] == ambush.general_id
    assert concealed["name"] == "未知伏兵"
    assert concealed["image"] == ""
    assert concealed["attributes"] == []
    assert concealed["skill"] == ""
    assert concealed["_targetType"] == ""
    assert concealed["skill_cost"] == 0
    assert concealed["_ambushConcealed"] is True

    ambush.get_passive_skill("伏兵").trigger_counter()
    revealed = main_web.STATE.to_json()["p2"]["generals"][0]
    assert revealed["name"] == "张任"
    assert revealed["attributes"] == ["伏兵"]
    assert revealed["_ambushConcealed"] is False
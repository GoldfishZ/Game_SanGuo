"""回合恢复与前端表现事件契约测试。"""

import json

import main_web
from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleSystem
from src.models.team import Team


def post(path, body=None):
    response = main_web.handle_api(path, body or {}, None)
    return response if isinstance(response, dict) else json.loads(response)


def test_end_turn_restores_two_morale_without_exceeding_maximum():
    team1 = Team("甲军")
    team2 = Team("乙军")
    team1.current_morale = 9
    battle = BattleSystem(team1, team2, callbacks=None,
                          first_player_team_name=team1.team_name)

    event = battle._end_turn_cleanup()

    assert team1.current_morale == 11
    assert event["type"] == "morale_restore"
    assert event["amount"] == 2

    team1.current_morale = 11
    event = battle._end_turn_cleanup()
    assert team1.current_morale == 12
    assert event["amount"] == 1


def test_turn_start_returns_recruit_heal_event():
    team = Team("魏军")
    xu_chu = get_general_by_name("许褚")
    team.add_general(xu_chu)
    xu_chu.current_hp -= 3

    events = team.update_effects()

    assert xu_chu.current_hp == xu_chu.max_hp - 2
    assert events == [{
        "type": "recruit_heal",
        "general_id": xu_chu.general_id,
        "target": "许褚",
        "amount": 1,
        "hp": xu_chu.current_hp,
    }]


def test_damage_records_fence_and_shield_events():
    defender = get_general_by_name("诸葛亮")
    attacker = get_general_by_name("张飞")
    defender.take_damage(5, attacker, "basic_attack")
    fence_events = defender.drain_combat_events()
    assert fence_events[0]["type"] == "fence_block"
    assert fence_events[0]["blocked"] == 5

    defender.add_buff("damage_shield", 3, 1)
    actual = defender.take_damage(5, attacker, "skill")
    shield_events = defender.drain_combat_events()
    assert actual == 2
    assert shield_events[0]["type"] == "shield_absorb"
    assert shield_events[0]["absorbed"] == 3


def test_web_skip_returns_morale_and_recruit_events():
    main_web.STATE.reset()
    controller = main_web.STATE.controller
    p1_general = get_general_by_name("张飞")
    p2_general = get_general_by_name("许褚")
    controller.player1.add_general_to_team(p1_general)
    controller.player2.add_general_to_team(p2_general)
    controller.player1.team.position_general(p1_general, 0, 0)
    controller.player2.team.position_general(p2_general, 0, 0)
    controller.player1.team.current_morale = 7
    p2_general.current_hp -= 2
    main_web.STATE.phase = "battle"
    main_web.STATE.battle_system = BattleSystem(
        controller.player1.team,
        controller.player2.team,
        callbacks=None,
        first_player_team_name=controller.player1.team.team_name,
    )

    state = post("/api/battle/skip")
    events = state["turn_events"]

    assert controller.player1.team.current_morale == 9
    assert events[0]["type"] == "morale_restore"
    assert events[0]["team"] == "p1"
    assert any(event["type"] == "recruit_heal" and event["team"] == "p2"
               for event in events)


def test_web_serializes_damage_shield_capacity():
    main_web.STATE.reset()
    player = main_web.STATE.controller.player1
    xu_chu = get_general_by_name("许褚")
    player.add_general_to_team(xu_chu)
    xu_chu.add_buff("damage_shield", 3, 1)

    data = main_web.STATE._team_json(player)["generals"][0]

    assert data["buffs"] == [{"type": "damage_shield", "duration": 1, "value": 3}]

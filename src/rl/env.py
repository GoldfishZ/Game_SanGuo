"""本地、单进程、子动作级三国战斗强化学习环境。"""
from __future__ import annotations

import random
from itertools import combinations
from typing import Optional

from src.battle.battle_system import BattleSystem
from src.battle.rules_service import BattleRulesService
from src.game_data.generals_config import create_general_from_data
from src.game_data.generals_data import GENERALS_DATA
from src.models.game_flow import GameFlowController
from src.rl import actions
from src.rl.observation import build_debug_dict, build_observation
from src.rl.opponents import RandomOpponent
from src.rl.reward import RewardHandler


class SanguoEnv:
    """控制一方的 masked-discrete 环境；另一方完整回合由 opponent 自动执行。"""
    action_size = actions.ACTION_SIZE

    def __init__(self, opponent=None, *, team_size=3, cost_limit=8.0, max_turns=200, reward_config=None):
        self.opponent = opponent or RandomOpponent()
        self.team_size = team_size
        self.cost_limit = cost_limit
        self.max_turns = max_turns
        self.reward_handler = RewardHandler(reward_config)
        self.rng = random.Random()
        self.seed_value = None
        self.controller = None
        self.battle_system = None
        self.rules = None
        self.learning_team = None
        self.enemy_team = None
        self.subphase = "skill"
        self.done = False

    def reset(self, seed: Optional[int] = None, rosters=None, mirror=False):
        """重置一局；``rosters`` 可为两个武将 ID 列表，供受控平衡评估使用。"""
        if seed is not None:
            self.seed_value = seed
            self.rng = random.Random(seed)
            random.seed(seed)
        self.controller = GameFlowController()
        p1, p2 = self.controller.player1, self.controller.player2
        roster = list(GENERALS_DATA)
        self.rng.shuffle(roster)
        if rosters is not None:
            first_ids, second_ids = rosters
            self._populate_ids(p1, first_ids)
            self._populate_ids(p2, second_ids)
        elif mirror:
            selection = self._choose_selection(roster)
            self._populate_data(p1, selection)
            self._populate_data(p2, selection)
        else:
            self._populate_player(p1, roster[:len(roster)//2])
            self._populate_player(p2, roster[len(roster)//2:])
        self._place_randomly(p1)
        self._place_randomly(p2)
        d1 = d2 = 0
        while d1 == d2:
            d1, d2 = self.rng.randint(1, 6), self.rng.randint(1, 6)
        first, second = (p1, p2) if d1 > d2 else (p2, p1)
        second.team.max_morale += 2
        second.team.current_morale += 2
        self.controller.first_player, self.controller.second_player = first, second
        self.battle_system = BattleSystem(p1.team, p2.team, None, first.team.team_name, max_turns=self.max_turns)
        self.rules = BattleRulesService(self.battle_system)
        self.battle_system.turn_count = 1
        self.battle_system.current_side.update_effects()
        # 随机决定学习方身份，观察编码始终将其置于 self 侧。
        self.learning_team = p1.team if self.rng.randrange(2) == 0 else p2.team
        self.enemy_team = p2.team if self.learning_team is p1.team else p1.team
        self.subphase = "skill"
        self.done = False
        self.reward_handler.reset(self.learning_team, self.enemy_team)
        if self.battle_system.current_side is not self.learning_team:
            self._run_opponent_turn()
        return self.observation(), self.info()

    def _choose_selection(self, source):
        affordable = [combo for combo in combinations(source, self.team_size) if sum(item["cost"] for item in combo) <= self.cost_limit]
        return self.rng.choice(affordable) if affordable else (min(source, key=lambda item: item["cost"]),)

    def _populate_data(self, player, selection):
        for data in selection:
            player.add_general_to_team(create_general_from_data(data))

    def _populate_player(self, player, source):
        self._populate_data(player, self._choose_selection(source))

    def _populate_ids(self, player, ids):
        by_id = {data["id"]: data for data in GENERALS_DATA}
        selection = [by_id[general_id] for general_id in ids if general_id in by_id]
        if not selection:
            raise ValueError("受控阵容必须至少包含一名有效武将")
        if sum(data["cost"] for data in selection) > self.cost_limit:
            raise ValueError("受控阵容超过费用上限")
        self._populate_data(player, selection)

    def _place_randomly(self, player):
        cells = self.rng.sample([(r, c) for r in range(3) for c in range(4)], len(player.selected_generals))
        for general, (row, col) in zip(player.selected_generals, cells):
            player.team.position_general(general, row, col)
        player.team.complete_formation_setup()

    def observation(self):
        return build_observation(self)

    def info(self, action=None, result=None):
        data = build_debug_dict(self)
        data.update({"seed": self.seed_value, "action_mask": self.action_mask(), "action": action, "result": result})
        return data

    def action_mask(self):
        return actions.action_mask(self)

    def legal_actions(self):
        return actions.legal_actions(self)

    def decode_action(self, action_id):
        return actions.decode(action_id)

    def attack_target_hp(self, action_id):
        action = self.decode_action(action_id)
        target = actions.general_at(self.enemy_team, action.target_slot)
        return target.current_hp if target else float("inf")

    def step(self, action_id: int):
        if self.done:
            raise RuntimeError("本 episode 已结束，请先 reset")
        mask = self.action_mask()
        if not 0 <= action_id < self.action_size or mask[action_id]:
            raise ValueError(f"非法动作: {action_id}")
        action = self.decode_action(action_id)
        result = self._apply_learning_action(action)
        self._finalize_if_over()
        if not self.done and action.kind == "end_attack":
            self.rules.end_turn()
            self._run_opponent_turn()
            self._finalize_if_over()
        outcome = self.rules.outcome()
        reward = self.reward_handler.step(
            self.learning_team, self.enemy_team, action_success=bool(result.get("success")),
            done=self.done, winner=outcome.winner, timeout=outcome.timeout,
        )
        response_info = self.info(action_id, result)
        response_info["no_progress"] = self.reward_handler.last_no_progress
        return self.observation(), reward, self.done, response_info

    def _apply_learning_action(self, action):
        if action.kind == "end_skill":
            self.subphase = "attack"
            return {"success": True, "type": "end_skill"}
        if action.kind == "end_attack":
            return {"success": True, "type": "end_attack"}
        if action.kind.startswith("skill"):
            caster = actions.general_at(self.learning_team, action.actor_slot)
            if caster is None:
                return {"success": False, "message": "施法者阵位为空"}
            target_team = self.learning_team if "ALLY" in caster.active_skill.target_type.name else self.enemy_team
            target = actions.general_at(target_team, action.target_slot)
            result = self.rules.skill(
                caster, target=target, row=action.row if action.kind == "skill_area" else None,
                col=action.col if action.kind == "skill_area" else None, skill_row=action.row if action.kind == "skill_area" else None,
                guess=action.guess,
            )
            return result
        attacker = actions.general_at(self.learning_team, action.actor_slot)
        target = actions.general_at(self.enemy_team, action.target_slot)
        if attacker is None or target is None:
            return {"success": False, "message": "攻击者或目标阵位为空"}
        return self.rules.attack(attacker, target, guess=action.guess)

    def _run_opponent_turn(self):
        if self.battle_system._is_game_over():
            return
        # The action code is side-relative. Temporarily flip the env perspective so the
        # same action encoder and opponent policy work for either physical team.
        self.learning_team, self.enemy_team = self.enemy_team, self.learning_team
        self.subphase = "skill"
        # 对手策略若持续选择无进展动作，必须有小而明确的回合上限。
        # 耗尽后仍会在下方 advance_turn，保证战斗回合能够推进。
        guard = 64
        while guard and not self.battle_system._is_game_over():
            guard -= 1
            action_id = self.opponent.choose_action(self)
            action = self.decode_action(action_id)
            self._apply_learning_action(action)
            if action.kind == "end_attack":
                break
        if not self.battle_system._is_game_over():
            self.rules.end_turn()
        self.learning_team, self.enemy_team = self.enemy_team, self.learning_team
        self.subphase = "skill"

    def _finalize_if_over(self):
        if self.battle_system._is_game_over() or self.battle_system.turn_count >= self.battle_system.max_turns:
            self.done = True

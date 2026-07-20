"""固定离散动作编码与合法动作掩码。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from src.battle.turn_actions import resolve_skill_targets
from src.skills.skill_base import TargetType

GRID_SIZE = 12
END_SKILL = 0
END_ATTACK = 1
SKILL_BASE = 2
SKILL_TARGET_COUNT = GRID_SIZE * GRID_SIZE
SKILL_AREA_BASE = SKILL_BASE + SKILL_TARGET_COUNT
SKILL_AREA_COUNT = GRID_SIZE * GRID_SIZE
ATTACK_BASE = SKILL_AREA_BASE + SKILL_AREA_COUNT
ATTACK_COUNT = GRID_SIZE * GRID_SIZE * 3
ACTION_SIZE = ATTACK_BASE + ATTACK_COUNT
GUESSES = (None, "奇", "偶")


@dataclass(frozen=True)
class Action:
    kind: str
    actor_slot: int = -1
    target_slot: int = -1
    row: int = -1
    col: int = -1
    guess: str | None = None


def slot_for(team, general) -> int:
    pos = team.get_general_position(general)
    return pos[0] * 4 + pos[1] if pos else -1


def general_at(team, slot: int):
    if not 0 <= slot < GRID_SIZE:
        return None
    return team.formation[slot // 4][slot % 4]


def encode(action: Action) -> int:
    if action.kind == "end_skill": return END_SKILL
    if action.kind == "end_attack": return END_ATTACK
    if action.kind == "skill_target": return SKILL_BASE + action.actor_slot * GRID_SIZE + action.target_slot
    if action.kind == "skill_area": return SKILL_AREA_BASE + action.actor_slot * GRID_SIZE + action.row * 4 + action.col
    if action.kind == "attack":
        return ATTACK_BASE + (action.actor_slot * GRID_SIZE + action.target_slot) * 3 + GUESSES.index(action.guess)
    raise ValueError(f"未知动作类型: {action.kind}")


def decode(action_id: int) -> Action:
    if action_id == END_SKILL: return Action("end_skill")
    if action_id == END_ATTACK: return Action("end_attack")
    if SKILL_BASE <= action_id < SKILL_AREA_BASE:
        value = action_id - SKILL_BASE
        return Action("skill_target", value // GRID_SIZE, value % GRID_SIZE)
    if SKILL_AREA_BASE <= action_id < ATTACK_BASE:
        value = action_id - SKILL_AREA_BASE
        return Action("skill_area", value // GRID_SIZE, row=(value % GRID_SIZE) // 4, col=value % 4)
    if ATTACK_BASE <= action_id < ACTION_SIZE:
        value = action_id - ATTACK_BASE
        pair, guess_index = divmod(value, 3)
        return Action("attack", pair // GRID_SIZE, pair % GRID_SIZE, guess=GUESSES[guess_index])
    raise ValueError(f"动作编号超出范围: {action_id}")


def action_mask(env) -> np.ndarray:
    """返回 0=合法、1=非法的固定长度动作掩码。"""
    mask = np.ones(ACTION_SIZE, dtype=np.int8)
    team, enemy, bs = env.learning_team, env.enemy_team, env.battle_system
    if env.subphase == "skill":
        mask[END_SKILL] = 0
        for caster in team.get_alive_generals():
            if not (caster.can_use_active_skill() and caster.can_use_skill() and team.current_morale >= caster.active_skill.morale_cost):
                continue
            actor = slot_for(team, caster)
            tt = caster.active_skill.target_type
            if tt in (TargetType.AREA_ENEMY, TargetType.AREA_ALLY) or caster.active_skill.skill_id == "stone_sentinel_maze":
                for area in range(GRID_SIZE):
                    mask[encode(Action("skill_area", actor, row=area // 4, col=area % 4))] = 0
            elif tt in (TargetType.SINGLE_ENEMY, TargetType.SINGLE_ALLY, TargetType.FRONT_ROW_ENEMY, TargetType.BACK_ROW_ENEMY, TargetType.FRONT_ROW_ALLY, TargetType.BACK_ROW_ALLY):
                target_team = team if "ALLY" in tt.name else enemy
                for target in target_team.get_alive_generals():
                    # A target is legal only when target resolution preserves it rather
                    # than falling back to a default first target.
                    resolved = resolve_skill_targets(env.battle_system, caster, target=target)
                    if resolved == [target]:
                        target_slot = slot_for(target_team, target)
                        if target_slot >= 0:
                            mask[encode(Action("skill_target", actor, target_slot))] = 0
            else:
                mask[encode(Action("skill_target", actor, 0))] = 0
    elif env.subphase == "attack":
        mask[END_ATTACK] = 0
        for attacker in team.get_alive_generals():
            if not attacker.can_attack():
                continue
            actor = slot_for(team, attacker)
            for target in bs._get_attack_targets_for_attacker(attacker):
                target_slot = slot_for(enemy, target)
                for guess in GUESSES:
                    mask[encode(Action("attack", actor, target_slot, guess=guess))] = 0
    return mask


def legal_actions(env) -> List[int]:
    return np.flatnonzero(action_mask(env) == 0).tolist()

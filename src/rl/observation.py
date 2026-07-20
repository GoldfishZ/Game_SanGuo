"""玩家可见战场状态的固定维度编码。"""
from __future__ import annotations

import numpy as np

from src.rl.actions import GRID_SIZE, slot_for

# alive, hp, force, int, effective force/int, cooldown, skill cost, used skill,
# attacked, can attack, position row/col, public buff/debuff counts, camp code
GENERAL_FEATURES = 15
OBSERVATION_SIZE = 5 + GRID_SIZE * GENERAL_FEATURES * 2
CAMP_CODES = {"魏": 0, "蜀": 1, "吴": 2, "袁": 3, "群": 4}


def _encode_team(vector, offset, team):
    for general in team.generals:
        slot = slot_for(team, general)
        if slot < 0:
            continue
        base = offset + slot * GENERAL_FEATURES
        if not general.is_alive:
            continue
        pos = team.get_general_position(general)
        vector[base:base + GENERAL_FEATURES] = (
            1.0,
            general.current_hp / max(1, general.max_hp),
            general.force / 20.0,
            general.intelligence / 20.0,
            general.get_effective_force() / 20.0,
            general.get_effective_intelligence() / 20.0,
            general.active_skill_cooldown / 8.0,
            (general.active_skill.morale_cost if general.active_skill else 0) / 12.0,
            float(general._has_used_skill_this_turn),
            float(general._has_attacked_this_turn),
            float(general.can_attack()),
            pos[0] / 2.0,
            pos[1] / 3.0,
            min(len(general.buffs), 4) / 4.0,
            CAMP_CODES.get(general.camp.value, 5) / 5.0,
        )


def build_observation(env) -> np.ndarray:
    """构建学习方固定为 self 侧的部分可观测向量。"""
    vector = np.zeros(OBSERVATION_SIZE, dtype=np.float32)
    vector[0] = env.battle_system.turn_count / env.battle_system.max_turns
    vector[1] = float(env.battle_system.current_side is env.learning_team)
    vector[2] = float(env.subphase == "skill")
    vector[3] = env.learning_team.current_morale / max(1, env.learning_team.max_morale)
    vector[4] = env.enemy_team.current_morale / max(1, env.enemy_team.max_morale)
    _encode_team(vector, 5, env.learning_team)
    _encode_team(vector, 5 + GRID_SIZE * GENERAL_FEATURES, env.enemy_team)
    return vector


def build_debug_dict(env):
    return {
        "turn": env.battle_system.turn_count,
        "subphase": env.subphase,
        "learning_team": env.learning_team.team_name,
        "enemy_team": env.enemy_team.team_name,
        "learning_morale": env.learning_team.current_morale,
        "enemy_morale": env.enemy_team.current_morale,
    }

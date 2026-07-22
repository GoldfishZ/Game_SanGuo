"""公开战场状态的固定维度 observation v2。

离散身份均使用 one-hot，运行状态显式编码。这里不会写入未来随机结果，
也不会写入 Web 客户端不可获得的 analysis-only 信息。
"""
from __future__ import annotations

import numpy as np

from src.game_data.generals_data import GENERALS_DATA
from src.game_data.skills_config import ALL_SKILLS
from src.models.general import Attribute
from src.rl.actions import GRID_SIZE, slot_for
from src.skills.skill_base import SkillType, TargetType

OBSERVATION_SCHEMA = "sanguo-battle-observation-v2"

GENERAL_IDS = tuple(sorted(int(item["id"]) for item in GENERALS_DATA))
SKILL_IDS = tuple(sorted(ALL_SKILLS))
CAMPS = ("魏", "蜀", "吴", "凉", "袁", "他")
ATTRIBUTES = tuple(attribute.value for attribute in Attribute)
TARGET_TYPES = tuple(target.name for target in TargetType)
SKILL_TYPES = tuple(skill.name for skill in SkillType)

# 注册表属于 schema。新增运行效果时必须同步更新并提升 OBSERVATION_SCHEMA。
BUFF_TYPES = (
    "force_boost", "intelligence_boost", "damage_shield", "debuff_immunity",
    "ignore_fence", "front_only_attack", "attack_speed_judgment",
    "knockback_on_damage",
)
DEBUFF_TYPES = (
    "force_reduction", "intelligence_reduction", "attack_speed_required",
    "forced_attack_target",
)

EFFECT_FEATURES = 3  # presence, aggregate value, max duration/delay
TEAM_FEATURES = 9
GENERAL_SCALARS = 24
GENERAL_FEATURES = (
    GENERAL_SCALARS
    + len(GENERAL_IDS) + len(SKILL_IDS) + len(CAMPS)
    + len(ATTRIBUTES) + len(TARGET_TYPES) + len(SKILL_TYPES)
    + (len(BUFF_TYPES) + len(DEBUFF_TYPES)) * EFFECT_FEATURES * 2
    + GRID_SIZE  # forced target one-hot
)
GLOBAL_FEATURES = 3 + TEAM_FEATURES * 2
OBSERVATION_SIZE = GLOBAL_FEATURES + GRID_SIZE * GENERAL_FEATURES * 2


def _safe_number(value, default=0.0):
    return float(value) if isinstance(value, (int, float, bool)) else float(default)


def _one_hot(vector, offset, values, selected):
    try:
        vector[offset + values.index(selected)] = 1.0
    except (ValueError, TypeError):
        pass
    return offset + len(values)


def _effect_features(vector, offset, effects, effect_types, *, pending=False):
    for effect_type in effect_types:
        matching = [item for item in effects if item.get("type") == effect_type]
        if matching:
            vector[offset] = 1.0
            vector[offset + 1] = sum(
                _safe_number(item.get("value")) for item in matching
            ) / 20.0
            time_key = "delay_turns" if pending else "duration"
            vector[offset + 2] = max(
                _safe_number(item.get(time_key)) for item in matching
            ) / 8.0
        offset += EFFECT_FEATURES
    return offset


def _team_features(team):
    alive = team.get_alive_generals()
    max_hp = sum(general.max_hp for general in team.generals)
    pending = team.pending_morale_rewards
    return (
        team.current_morale / max(1, team.max_morale),
        team.max_morale / 20.0,
        team.morale_spent / 40.0,
        len(alive) / max(1, len(team.generals)),
        sum(general.current_hp for general in alive) / max(1, max_hp),
        min(len(pending), 4) / 4.0,
        sum(_safe_number(item.get("amount")) for item in pending) / 12.0,
        max((_safe_number(item.get("delay_turns")) for item in pending), default=0.0) / 8.0,
        min(len(team.temporary_formation_effects), 4) / 4.0,
    )


def _passive_state(general):
    fence = general.get_passive_skill("防栅")
    revive = general.get_passive_skill("复活")
    ambush = general.get_passive_skill("伏兵")
    chain_count = 0
    if general._team:
        chain_count = sum(
            ally.is_alive and ally.has_chain_passive()
            for ally in general._team.generals
        )
    return (
        float(bool(fence and fence.is_active)),
        float(bool(revive and not revive.has_revived)),
        float(bool(ambush and ambush.is_hidden)),
        float(bool(ambush and not ambush.triggered)),
        chain_count / 3.0,
    )


def _encode_general(vector, base, team, general):
    pos = team.get_general_position(general)
    if pos is None:
        return
    skill = general.active_skill
    forced_target = general.get_forced_attack_target()
    forced_slot = slot_for(forced_target._team, forced_target) if forced_target else -1
    fence, revive, ambush_hidden, ambush_available, chain_count = _passive_state(general)
    shield = sum(
        _safe_number(item.get("value"))
        for item in general.buffs if item.get("type") == "damage_shield"
    )
    vector[base:base + GENERAL_SCALARS] = (
        1.0, float(general.is_alive),
        general.current_hp / max(1, general.max_hp), general.max_hp / 40.0,
        general.force / 20.0, general.intelligence / 20.0,
        general.get_effective_force() / 20.0,
        general.get_effective_intelligence() / 20.0,
        general.cost / 8.0,
        general.active_skill_cooldown / 8.0,
        (skill.cooldown if skill else 0) / 8.0,
        (skill.morale_cost if skill else 0) / 12.0,
        float(general._has_used_skill_this_turn),
        float(general._has_attacked_this_turn),
        float(general._extra_attack_available),
        float(general.can_attack()),
        pos[0] / 2.0, pos[1] / 3.0,
        fence, revive, ambush_hidden, ambush_available, chain_count,
        min(shield, 20.0) / 20.0,
    )
    offset = base + GENERAL_SCALARS
    offset = _one_hot(vector, offset, GENERAL_IDS, general.general_id)
    offset = _one_hot(vector, offset, SKILL_IDS, skill.skill_id if skill else None)
    offset = _one_hot(vector, offset, CAMPS, general.camp.value)
    attributes = {attribute.value for attribute in general.attribute}
    for index, attribute in enumerate(ATTRIBUTES):
        vector[offset + index] = float(attribute in attributes)
    offset += len(ATTRIBUTES)
    offset = _one_hot(vector, offset, TARGET_TYPES, skill.target_type.name if skill else None)
    offset = _one_hot(vector, offset, SKILL_TYPES, skill.skill_type.name if skill else None)
    offset = _effect_features(vector, offset, general.buffs, BUFF_TYPES)
    offset = _effect_features(vector, offset, general.debuffs, DEBUFF_TYPES)
    offset = _effect_features(vector, offset, general.pending_buffs, BUFF_TYPES, pending=True)
    offset = _effect_features(vector, offset, general.pending_debuffs, DEBUFF_TYPES, pending=True)
    if 0 <= forced_slot < GRID_SIZE:
        vector[offset + forced_slot] = 1.0


def _encode_team(vector, offset, team):
    for general in team.generals:
        slot = slot_for(team, general)
        if slot >= 0:
            _encode_general(vector, offset + slot * GENERAL_FEATURES, team, general)


def build_observation(env) -> np.ndarray:
    vector = np.zeros(OBSERVATION_SIZE, dtype=np.float32)
    vector[0] = env.battle_system.turn_count / env.battle_system.max_turns
    vector[1] = float(env.battle_system.current_side is env.learning_team)
    vector[2] = float(env.subphase == "skill")
    vector[3:3 + TEAM_FEATURES] = _team_features(env.learning_team)
    vector[3 + TEAM_FEATURES:GLOBAL_FEATURES] = _team_features(env.enemy_team)
    self_offset = GLOBAL_FEATURES
    enemy_offset = self_offset + GRID_SIZE * GENERAL_FEATURES
    _encode_team(vector, self_offset, env.learning_team)
    _encode_team(vector, enemy_offset, env.enemy_team)
    return vector


def build_debug_dict(env):
    return {
        "turn": env.battle_system.turn_count,
        "subphase": env.subphase,
        "learning_team": env.learning_team.team_name,
        "enemy_team": env.enemy_team.team_name,
        "learning_morale": env.learning_team.current_morale,
        "enemy_morale": env.enemy_team.current_morale,
        "observation_schema": OBSERVATION_SCHEMA,
    }

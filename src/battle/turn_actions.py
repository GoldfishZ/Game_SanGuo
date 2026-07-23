"""共享的逐动作战斗结算工具。

Web API、离线训练环境及未来 PvE 均应通过本模块调用核心模型，避免各自
复制目标选择、普攻判定和回合切换规则。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.battle.battle_system import BattleSystem
from src.models.general import General
from src.models.team import Team
from src.skills.skill_base import TargetType


def get_team_for_general(battle_system: BattleSystem, general: General) -> Optional[Team]:
    """返回武将所属队伍，未知武将返回 ``None``。"""
    if general in battle_system.team1.generals:
        return battle_system.team1
    if general in battle_system.team2.generals:
        return battle_system.team2
    return None


def get_enemy_team(battle_system: BattleSystem, team: Team) -> Team:
    """返回 ``team`` 的敌方队伍。"""
    return battle_system.team2 if team is battle_system.team1 else battle_system.team1


def resolve_skill_targets(
    battle_system: BattleSystem,
    caster: General,
    *,
    target: Optional[General] = None,
    row: Optional[int] = None,
    col: Optional[int] = None,
    orientation: Optional[str] = None,
    mode: Optional[str] = None,
    timing: Optional[str] = None,
    skill_row: Optional[int] = None,
) -> List[Any]:
    """按 Web 战斗语义将一次技能选择转换为 ``use_active_skill`` 的 targets。

    对单体技能，调用者给出明确目标；为兼容旧 Web 客户端，未给出目标时沿用
    当前第一目标/最高武力友军的默认选择。区域技能收到一个选区字典，由技能
    本身解释尺寸与方向。
    """
    if not caster.active_skill:
        return []

    own_team = get_team_for_general(battle_system, caster)
    if own_team is None:
        return []
    enemy_team = get_enemy_team(battle_system, own_team)
    target_type = caster.active_skill.target_type
    options: Dict[str, Any] = {}
    if row is not None:
        options["row"] = row
    if col is not None:
        options["col"] = col
    if orientation in ("horizontal", "vertical"):
        options["orientation"] = orientation
    if mode:
        options["mode"] = mode
    if timing:
        options["timing"] = timing

    if target_type == TargetType.SELF:
        # 石兵八阵的区域由一个 SELF 技能的特殊输入表达。
        if caster.active_skill.skill_id == "stone_sentinel_maze" and options:
            return [options]
        return [caster]
    if target_type == TargetType.ALL_ALLIES:
        return own_team.get_alive_generals()
    if target_type == TargetType.ALL_ENEMIES:
        return enemy_team.get_alive_generals()
    if target_type == TargetType.AREA_ALLY:
        # 部分范围友军技能（如“人马大号令”）会根据施法者位置自动确定
        # 生效竖列，不需要额外选择区域。以施法者作为非空占位目标，让共享
        # 校验层能够继续结算；需要手选范围的技能仍优先收到 options。
        return [options] if options else [caster]
    if target_type == TargetType.AREA_ENEMY:
        if caster.active_skill.skill_id == "meteor_rite":
            return [{"row": skill_row}] if skill_row in range(3) else []
        return [options] if options else []

    if target_type == TargetType.SINGLE_ALLY:
        legal = own_team.get_alive_generals()
        if target in legal:
            return [target]
        return [max(legal, key=lambda general: general.get_effective_force())] if legal else []

    if target_type == TargetType.FRONT_ROW_ALLY:
        legal = own_team.get_front_row_generals()
        return [target] if target in legal else legal[:1]
    if target_type == TargetType.BACK_ROW_ALLY:
        legal = [g for g in own_team.get_alive_generals() if g not in own_team.get_front_row_generals()]
        return [target] if target in legal else legal[:1]

    legal = enemy_team.get_alive_generals()
    if target_type == TargetType.FRONT_ROW_ENEMY:
        legal = enemy_team.get_front_row_generals()
    elif target_type == TargetType.BACK_ROW_ENEMY:
        legal = [g for g in legal if g not in enemy_team.get_front_row_generals()]
    # RANDOM_ENEMY remains random inside its skill implementation; a selected target is
    # intentionally not injected to preserve its original behavior.
    if target_type == TargetType.RANDOM_ENEMY:
        return legal[:1]
    return [target] if target in legal else legal[:1]


def apply_skill_action(
    battle_system: BattleSystem,
    caster: General,
    *,
    target: Optional[General] = None,
    row: Optional[int] = None,
    col: Optional[int] = None,
    orientation: Optional[str] = None,
    mode: Optional[str] = None,
    timing: Optional[str] = None,
    skill_row: Optional[int] = None,
    guess: Optional[str] = None,
) -> Dict[str, Any]:
    """解析目标并结算一次主动技能，返回稳定的结果对象。"""
    targets = resolve_skill_targets(
        battle_system, caster, target=target, row=row, col=col,
        orientation=orientation, mode=mode, timing=timing, skill_row=skill_row,
    )
    return apply_resolved_skill_action(
        battle_system, caster, targets, guess=guess,
    )


def apply_resolved_skill_action(
    battle_system: BattleSystem,
    caster: General,
    targets: List[Any],
    *,
    guess: Optional[str] = None,
) -> Dict[str, Any]:
    """结算调用方已按公开协议解析好的目标；Web/RL 共用同一验证路径。"""
    team = get_team_for_general(battle_system, caster)
    if team is None or team is not battle_system.current_side:
        return {"success": False, "message": "当前不是该武将的行动回合"}
    if not caster.can_use_active_skill() or not caster.can_use_skill():
        return {"success": False, "message": "该武将当前无法使用技能"}

    if not targets:
        return {"success": False, "message": "未选择合法技能目标"}
    all_generals = battle_system.team1.generals + battle_system.team2.generals
    hp_before = {general.general_id: general.current_hp for general in all_generals}
    result = caster.use_active_skill(targets, battle_system.battle_context, team, guess=guess)
    damage_by_target = {
        general.general_id: max(0, hp_before[general.general_id] - general.current_hp)
        for general in all_generals
        if general.current_hp < hp_before[general.general_id]
    }
    result.setdefault("caster_id", caster.general_id)
    result.setdefault("skill_id", caster.active_skill.skill_id if caster.active_skill else "")
    result["damage_by_target_id"] = damage_by_target
    result["damage"] = sum(damage_by_target.values())
    return result


def apply_attack_action(
    battle_system: BattleSystem,
    attacker: General,
    target: General,
    *,
    guess: Optional[str] = None,
    bravery_guess: Optional[str] = None,
    charisma_guess: Optional[str] = None,
) -> Dict[str, Any]:
    """验证并结算一次普攻（含攻速判定、反伤与阵亡）。"""
    if attacker not in battle_system.current_side.get_alive_generals():
        return {"success": False, "message": "当前不是该武将的行动回合"}
    if not attacker.can_attack():
        return {"success": False, "message": "该武将本回合不能普攻"}
    legal_targets = battle_system._get_attack_targets_for_attacker(attacker)
    if target not in legal_targets:
        return {"success": False, "message": "目标不是合法普攻目标"}

    attacker_hp_before = attacker.current_hp
    target_hp_before = target.current_hp
    required = attacker.has_debuff_type("attack_speed_required")
    attacker.last_attack_speed_judgment = None
    damage = attacker.attack(
        target, guess, bravery_guess=bravery_guess, charisma_guess=charisma_guess,
    )
    judgment = getattr(attacker, "last_attack_speed_judgment", None)
    # 攻速限制判定失败时，attack 会消耗该状态并标记本回合已攻击。
    performed = not (required and judgment and not judgment.get("success"))
    if not target.is_alive:
        target._team.remove_general_from_formation(target)
    if not attacker.is_alive:
        attacker._team.remove_general_from_formation(attacker)
    return {
        "success": True,
        "damage": damage,
        "performed": performed,
        "attacker_id": attacker.general_id,
        "target_id": target.general_id,
        "attacker_hp_before": attacker_hp_before,
        "attacker_hp_after": attacker.current_hp,
        "target_hp_before": target_hp_before,
        "target_hp_after": target.current_hp,
        "speed_judgment": dict(judgment) if judgment else None,
        "attack_required": required,
    }


def advance_turn(battle_system: BattleSystem) -> Dict[str, Any]:
    """结束当前行动方回合，切换队伍并处理新回合开始效果。"""
    ending_team = battle_system.current_side
    morale_event = battle_system._end_turn_cleanup()
    battle_system._switch_to_next_player()
    battle_system.turn_count += 1
    turn_events = battle_system.current_side.update_effects()
    return {
        "ending_team": ending_team.team_name,
        "current_team": battle_system.current_side.team_name,
        "turn_count": battle_system.turn_count,
        "morale_event": morale_event,
        "turn_events": turn_events,
    }

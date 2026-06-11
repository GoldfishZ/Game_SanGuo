"""
技能配置文件
包含游戏中需要的所有主动技能定义
"""

from src.skills.skill_base import DamageSkill, EnhanceWeakenSkill, TargetType


# ==================== 现有技能 ====================

# 强化战术 - 自身武力+4，本回合结束后失效
STRENGTH_TACTICS = EnhanceWeakenSkill(
    skill_id="strength_tactics",
    name="强化战术",
    description="使自己在本回合内武力+4，回合结束后失效",
    target_type=TargetType.SELF,
    effect_type="force_boost",
    effect_value=4,
    duration=1,
    cooldown=0,
    morale_cost=4
)

# 同盟缔结 - 己方士气最大值+2
ALLIANCE_PACT = EnhanceWeakenSkill(
    skill_id="alliance_pact",
    name="同盟缔结",
    description="己方士气最大值+2，从本回合开始生效",
    target_type=TargetType.SELF,
    effect_type="morale_max_boost",
    effect_value=2,
    duration=999,
    cooldown=0,
    morale_cost=2
)

# ==================== 新增技能 ====================

# 猛攻 - 对单体敌人造成1.5倍伤害
FIERCE_ATTACK = DamageSkill(
    skill_id="fierce_attack",
    name="猛攻",
    description="对一名敌人造成1.5倍普攻伤害",
    target_type=TargetType.SINGLE_ENEMY,
    damage_multiplier=1.5,
    cooldown=2,
    morale_cost=3
)

# 鼓舞 - 己方全体武力+2
RALLY = EnhanceWeakenSkill(
    skill_id="rally",
    name="鼓舞",
    description="己方全体武将武力+2，持续1回合",
    target_type=TargetType.ALL_ALLIES,
    effect_type="force_boost",
    effect_value=2,
    duration=1,
    cooldown=2,
    morale_cost=3
)

# 火计 - 对单体敌人造成2倍伤害
FIRE_ATTACK = DamageSkill(
    skill_id="fire_attack",
    name="火计",
    description="对一名敌人造成2倍普攻伤害",
    target_type=TargetType.SINGLE_ENEMY,
    damage_multiplier=2.0,
    cooldown=3,
    morale_cost=5
)

# 威压 - 降低敌方单体武力
INTIMIDATE = EnhanceWeakenSkill(
    skill_id="intimidate",
    name="威压",
    description="使一名敌方武将武力-3，持续1回合",
    target_type=TargetType.SINGLE_ENEMY,
    effect_type="force_reduction",
    effect_value=3,
    duration=1,
    cooldown=2,
    morale_cost=3
)

# ==================== 技能字典 ====================

ALL_SKILLS = {
    "strength_tactics": STRENGTH_TACTICS,
    "alliance_pact": ALLIANCE_PACT,
    "fierce_attack": FIERCE_ATTACK,
    "rally": RALLY,
    "fire_attack": FIRE_ATTACK,
    "intimidate": INTIMIDATE,
}


def get_skill_by_id(skill_id: str):
    """根据技能ID获取技能对象"""
    return ALL_SKILLS.get(skill_id)

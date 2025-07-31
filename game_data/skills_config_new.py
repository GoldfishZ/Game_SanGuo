"""
技能配置文件
包含游戏中需要的技能定义
"""

from src.skills.skill_base import EnhanceWeakenSkill, TargetType


# ==================== 武将技能 ====================

# 强化战术 - 自身武力+4，本回合结束后失效
STRENGTH_TACTICS = EnhanceWeakenSkill(
    skill_id="strength_tactics",
    name="强化战术",
    description="使自己在本回合内武力+4，回合结束后失效",
    target_type=TargetType.SELF,
    effect_type="force_boost",
    effect_value=4,
    duration=1,  # 1回合持续
    cooldown=0,  # 无冷却
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
    duration=999,  # 永久效果
    cooldown=0,  # 无冷却
    morale_cost=2
)

# 技能字典，方便查找
ALL_SKILLS = {
    "strength_tactics": STRENGTH_TACTICS,
    "alliance_pact": ALLIANCE_PACT
}

def get_skill_by_id(skill_id: str):
    """根据技能ID获取技能对象"""
    return ALL_SKILLS.get(skill_id)

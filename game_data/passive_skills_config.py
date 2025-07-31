"""
三国武将被动技能配置
基于武将属性的被动技能
"""

from src.skills.skill_base import PassiveSkill
from src.models.general import Attribute


# ==================== 被动技能定义 ====================

# 勇猛被动技能
BRAVERY_PASSIVE = PassiveSkill(
    skill_id="bravery_passive",
    name="勇猛",
    description="战斗中永不畏惧，攻击时有概率造成额外伤害",
    attribute_type="BRAVERY"
)

# 魅力被动技能
CHARISMA_PASSIVE = PassiveSkill(
    skill_id="charisma_passive",
    name="魅力",
    description="以个人魅力影响战局，每回合为队伍恢复少量士气",
    attribute_type="CHARISMA"
)

# 募兵被动技能
RECRUIT_PASSIVE = PassiveSkill(
    skill_id="recruit_passive",
    name="募兵",
    description="善于招募士兵，战斗开始时获得额外生命值",
    attribute_type="RECRUIT"
)

# 防栅被动技能
FENCE_PASSIVE = PassiveSkill(
    skill_id="fence_passive",
    name="防栅",
    description="善于构筑防御，受到攻击时有概率减免伤害",
    attribute_type="FENCE"
)

# 连环被动技能
CHAIN_PASSIVE = PassiveSkill(
    skill_id="chain_passive",
    name="连环",
    description="攻击时有概率触发连锁反应，对相邻敌人造成伤害",
    attribute_type="CHAIN"
)

# 复活被动技能
REVIVE_PASSIVE = PassiveSkill(
    skill_id="revive_passive",
    name="复活",
    description="首次阵亡时有概率以少量生命值复活",
    attribute_type="REVIVE"
)

# 伏兵被动技能
AMBUSH_PASSIVE = PassiveSkill(
    skill_id="ambush_passive",
    name="伏兵",
    description="战斗开始时有概率获得先手攻击机会",
    attribute_type="AMBUSH"
)

# 属性到被动技能的映射
ATTRIBUTE_TO_PASSIVE = {
    Attribute.BRAVERY: BRAVERY_PASSIVE,
    Attribute.CHARISMA: CHARISMA_PASSIVE,
    Attribute.RECRUIT: RECRUIT_PASSIVE,
    Attribute.FENCE: FENCE_PASSIVE,
    Attribute.CHAIN: CHAIN_PASSIVE,
    Attribute.REVIVE: REVIVE_PASSIVE,
    Attribute.AMBUSH: AMBUSH_PASSIVE
}

def get_passive_skills_for_attributes(attributes):
    """根据武将属性获取对应的被动技能列表"""
    passive_skills = []
    for attr in attributes:
        if attr in ATTRIBUTE_TO_PASSIVE:
            passive_skills.append(ATTRIBUTE_TO_PASSIVE[attr])
    return passive_skills

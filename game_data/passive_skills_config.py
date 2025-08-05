"""
三国武将被动技能配置
基于武将属性的被动技能
"""

from src.skills.skill_base import PassiveSkill
from src.models.general import Attribute
import random


class BraveryPassive(PassiveSkill):
    """勇猛被动技能"""
    
    def __init__(self):
        super().__init__(
            skill_id="bravery_passive",
            name="勇猛",
            description="在普攻对敌方造成伤害时，若自身生命小于等于最大生命值的一半，那么可以进行一次判定，若判定成功，那么本次造成的伤害值*1.5（四舍五入到整数）",
            attribute_type="BRAVERY"
        )
    
    def trigger_on_attack(self, caster, target, original_damage) -> int:
        """在攻击时触发"""
        # 检查生命值条件：小于等于最大生命值的一半
        if caster.current_hp <= caster.max_hp // 2:
            # 进行判定（先留白，后续完成）
            if self.judgment_check(caster):
                # 伤害*1.5，四舍五入到整数
                enhanced_damage = round(original_damage * 1.5)
                return enhanced_damage
        return original_damage
    
    def judgment_check(self, caster) -> bool:
        """判定检查（先留白）"""
        # TODO: 实现具体判定逻辑
        return True  # 临时返回True


class CharismaPassive(PassiveSkill):
    """魅力被动技能"""
    
    def __init__(self):
        super().__init__(
            skill_id="charisma_passive",
            name="魅力",
            description="被击杀后可以进行一次判定，若判定成功则可以返还自身受到致死伤害的一半给攻击者",
            attribute_type="CHARISMA"
        )
    
    def trigger_on_death(self, caster, attacker, fatal_damage) -> int:
        """在被击杀时触发"""
        if self.judgment_check(caster):
            # 返还致死伤害的一半给攻击者
            return_damage = fatal_damage // 2
            return return_damage
        return 0
    
    def judgment_check(self, caster) -> bool:
        """判定检查（先留白）"""
        # TODO: 实现具体判定逻辑
        return True  # 临时返回True


class RecruitPassive(PassiveSkill):
    """募兵被动技能"""
    
    def __init__(self):
        super().__init__(
            skill_id="recruit_passive",
            name="募兵",
            description="若有生命损失，则每回合可以回复一点生命",
            attribute_type="RECRUIT"
        )
    
    def trigger_on_turn_start(self, caster) -> int:
        """在回合开始时触发"""
        # 检查是否有生命损失
        if caster.current_hp < caster.max_hp:
            # 回复一点生命
            heal_amount = caster.heal(1)
            return heal_amount
        return 0


class FencePassive(PassiveSkill):
    """防栅被动技能"""
    
    def __init__(self):
        super().__init__(
            skill_id="fence_passive",
            name="防栅",
            description="可以抵挡一次攻击，防御后失效",
            attribute_type="FENCE"
        )
        self.is_active = True  # 防栅状态
    
    def trigger_on_receive_damage(self, caster, damage) -> int:
        """在受到伤害时触发"""
        if self.is_active:
            # 抵挡一次攻击
            self.is_active = False  # 防御后失效
            return 0  # 伤害完全抵挡
        return damage  # 防栅失效，正常受到伤害


class ChainPassive(PassiveSkill):
    """连环被动技能"""
    
    def __init__(self):
        super().__init__(
            skill_id="chain_passive",
            name="连环",
            description="己方所有拥有连环的武将共享buff、debuff以及伤害",
            attribute_type="CHAIN"
        )
    
    def share_effects(self, chain_generals):
        """在拥有连环的武将之间共享效果"""
        # 收集所有buff和debuff
        all_buffs = []
        all_debuffs = []
        
        for general in chain_generals:
            all_buffs.extend(general.buffs)
            all_debuffs.extend(general.debuffs)
        
        # 为所有连环武将应用相同的效果
        for general in chain_generals:
            general.buffs = all_buffs.copy()
            general.debuffs = all_debuffs.copy()
    
    def share_damage(self, chain_generals, damage) -> int:
        """在连环武将之间平均分配伤害"""
        alive_chain_generals = [g for g in chain_generals if g.is_alive]
        if len(alive_chain_generals) > 1:
            # 伤害平均分配
            shared_damage = damage // len(alive_chain_generals)
            return shared_damage
        return damage


class RevivePassive(PassiveSkill):
    """复活被动技能"""
    
    def __init__(self):
        super().__init__(
            skill_id="revive_passive",
            name="复活",
            description="可以复活一次，复活后拥有50%的生命",
            attribute_type="REVIVE"
        )
        self.has_revived = False  # 复活状态标记
    
    def trigger_on_death(self, caster) -> bool:
        """在死亡时触发复活"""
        if not self.has_revived:
            self.has_revived = True
            # 复活后拥有50%的生命
            revive_hp = caster.max_hp // 2
            caster.current_hp = revive_hp
            caster.is_alive = True
            return True  # 复活成功
        return False  # 已经复活过


class AmbushPassive(PassiveSkill):
    """伏兵被动技能"""
    
    def __init__(self):
        super().__init__(
            skill_id="ambush_passive",
            name="伏兵",
            description="在使用技能之前不会被敌方选中，若己方只剩下拥有伏兵的武将存活，伏兵自动破隐",
            attribute_type="AMBUSH"
        )
        self.is_hidden = True  # 隐藏状态
    
    def check_auto_reveal(self, team_generals):
        """检查是否需要自动破隐"""
        # 检查己方存活武将
        alive_allies = [g for g in team_generals if g.is_alive]
        non_ambush_alive = [g for g in alive_allies if not self.has_ambush_attribute(g)]
        
        # 如果只剩下伏兵武将存活，自动破隐
        if len(non_ambush_alive) == 0:
            self.is_hidden = False
    
    def has_ambush_attribute(self, general):
        """检查武将是否有伏兵属性"""
        from src.models.general import Attribute
        return Attribute.AMBUSH in general.attribute
    
    def can_be_targeted(self, caster, team_generals) -> bool:
        """检查是否可以被选中"""
        self.check_auto_reveal(team_generals)
        return not self.is_hidden
    
    def reveal_after_skill_use(self):
        """使用技能后破隐"""
        self.is_hidden = False


# ==================== 被动技能实例 ====================

BRAVERY_PASSIVE = BraveryPassive()
CHARISMA_PASSIVE = CharismaPassive()
RECRUIT_PASSIVE = RecruitPassive()
FENCE_PASSIVE = FencePassive()
CHAIN_PASSIVE = ChainPassive()
REVIVE_PASSIVE = RevivePassive()
AMBUSH_PASSIVE = AmbushPassive()

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

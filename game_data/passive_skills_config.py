"""
三国武将被动技能配置
基于武将属性的被动技能
"""

from src.skills.skill_base import PassiveSkill
from src.models.general import Attribute
import random


def round_half_up(value: float) -> int:
    """四舍五入到整数，避免 Python round 的银行家舍入。"""
    return int(value + 0.5)


def odd_even_judgment(guess: str = None) -> dict:
    """抛一枚六面骰并判定猜奇偶是否成功。

    guess 传入 "odd"/"even" 或 "奇"/"偶"。未传入时自动随机猜测，
    方便当前 CLI/测试自动流程在没有玩家交互入口时也能完成判定。
    """
    normalized_guess = guess
    if normalized_guess in ("奇", "odd", "ODD"):
        normalized_guess = "odd"
    elif normalized_guess in ("偶", "even", "EVEN"):
        normalized_guess = "even"
    else:
        normalized_guess = random.choice(["odd", "even"])

    dice = random.randint(1, 6)
    parity = "odd" if dice % 2 else "even"
    return {
        "guess": normalized_guess,
        "dice": dice,
        "parity": parity,
        "success": normalized_guess == parity,
    }


class BraveryPassive(PassiveSkill):
    """勇猛被动技能"""
    
    def __init__(self):
        super().__init__(
            skill_id="bravery_passive",
            name="勇猛",
            description="血量低于一半时，普攻可以猜奇偶判定。成功则本次伤害*1.5（四舍五入）",
            attribute_type="BRAVERY"
        )
        self.last_judgment = None
    
    def trigger_on_attack(self, caster, target, original_damage, guess: str = None) -> int:
        """在攻击时触发"""
        # 检查生命值条件：严格低于最大生命值的一半
        if caster.current_hp < caster.max_hp / 2:
            if self.judgment_check(caster, guess):
                return round_half_up(original_damage * 1.5)
        return original_damage
    
    def judgment_check(self, caster, guess: str = None) -> bool:
        """判定检查：抛骰子猜奇偶。"""
        self.last_judgment = odd_even_judgment(guess)
        return self.last_judgment["success"]


class CharismaPassive(PassiveSkill):
    """魅力被动技能"""
    
    def __init__(self):
        super().__init__(
            skill_id="charisma_passive",
            name="魅力",
            description="受到致命伤害时猜奇偶判定。成功则对攻击者造成所受伤害一半（四舍五入）",
            attribute_type="CHARISMA"
        )
        self.last_judgment = None
    
    def trigger_on_death(self, caster, attacker, fatal_damage, guess: str = None) -> int:
        """在被击杀时触发"""
        if self.judgment_check(caster, guess):
            return round_half_up(fatal_damage / 2)
        return 0
    
    def judgment_check(self, caster, guess: str = None) -> bool:
        """判定检查：抛骰子猜奇偶。"""
        self.last_judgment = odd_even_judgment(guess)
        return self.last_judgment["success"]


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
    """防栅被动技能（一次性，破碎后不再重建）"""

    def __init__(self):
        super().__init__(
            skill_id="fence_passive",
            name="防栅",
            description="抵挡一次普攻，破碎后不再重建",
            attribute_type="FENCE"
        )
        self.is_active = True  # 防栅状态

    def trigger_on_receive_damage(self, caster, damage, damage_source: str = "basic_attack") -> int:
        """在受到伤害时触发"""
        if damage_source == "basic_attack" and self.is_active:
            self.is_active = False
            return 0  # 伤害完全抵挡
        return damage  # 防栅失效，正常受到伤害

    def update_rebuild(self, caster) -> None:
        """回合开始时空操作（不再重建防栅）"""
        pass


class ChainPassive(PassiveSkill):
    """连计被动技能"""
    
    def __init__(self):
        super().__init__(
            skill_id="chain_passive",
            name="连计",
            description="己方所有拥有连计的武将共享技能效果（增益/减益）与伤害",
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
    """伏兵被动技能

    机制（重构版）：
    - 隐藏状态下不可被普攻直接选中
    - 相邻格子的友军被普攻时，攻击者受到伤害一半的反击伤害
    - 每局只能触发一次
    - 使用主动技能后破隐（失去伏兵效果）
    - 若所有队友阵亡时仍未触发，效果自动丧失
    """

    def __init__(self):
        super().__init__(
            skill_id="ambush_passive",
            name="伏兵",
            description="不可被普攻选中；邻格友军被攻时反击伤害的一半，每局一次",
            attribute_type="AMBUSH"
        )
        self.is_hidden = True  # 隐藏状态（不可被普攻选中）
        self.triggered = False  # 是否已触发反击（每局一次）

    def check_auto_reveal(self, team_generals):
        """检查是否需要自动破隐（队友全灭则失效）"""
        if not self.triggered and not self.is_hidden:
            return
        # 检查是否还有其他存活的友军
        alive_allies = [g for g in team_generals
                       if g.is_alive and g.has_passive_skill("伏兵") is not self]
        if not alive_allies:
            self.is_hidden = False  # 队友死光，自动失去效果

    def has_ambush_attribute(self, general):
        """检查武将是否有伏兵属性"""
        from src.models.general import Attribute
        return Attribute.AMBUSH in general.attribute

    def can_be_targeted(self, caster, team_generals) -> bool:
        """检查是否可以被选中（隐藏时不可直接选中）"""
        return not self.is_hidden

    def can_counter(self):
        """是否可以触发反击"""
        return self.is_hidden and not self.triggered

    def trigger_counter(self):
        """触发反击，标记为已使用"""
        self.triggered = True
        self.is_hidden = False  # 反击后破隐

    def reveal_after_skill_use(self):
        """使用主动技能后破隐（失去伏兵保护）"""
        self.is_hidden = False


# ==================== 被动技能实例 ====================

BRAVERY_PASSIVE = BraveryPassive()
CHARISMA_PASSIVE = CharismaPassive()
RECRUIT_PASSIVE = RecruitPassive()
FENCE_PASSIVE = FencePassive()
CHAIN_PASSIVE = ChainPassive()
REVIVE_PASSIVE = RevivePassive()
AMBUSH_PASSIVE = AmbushPassive()

# 属性到被动技能类的映射（每次调用 get_passive_skills_for_attributes 创建新实例）
ATTRIBUTE_TO_PASSIVE_CLASS = {
    Attribute.BRAVERY: BraveryPassive,
    Attribute.CHARISMA: CharismaPassive,
    Attribute.RECRUIT: RecruitPassive,
    Attribute.FENCE: FencePassive,
    Attribute.CHAIN: ChainPassive,
    Attribute.REVIVE: RevivePassive,
    Attribute.AMBUSH: AmbushPassive
}

def get_passive_skills_for_attributes(attributes):
    """根据武将属性获取对应的被动技能列表（每次创建新的技能实例，避免状态共享）"""
    passive_skills = []
    for attr in attributes:
        if attr in ATTRIBUTE_TO_PASSIVE_CLASS:
            passive_skills.append(ATTRIBUTE_TO_PASSIVE_CLASS[attr]())
    return passive_skills

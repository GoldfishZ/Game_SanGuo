"""
武将模型类
定义武将的基本属性和行为
"""

from typing import List, Dict, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from ..skills.skill_base import Skill, PassiveSkill


class Camp(Enum):
    """阵营枚举"""
    WEI = "魏"
    SHU = "蜀" 
    WU = "吴"
    LIANG = "凉"
    YUAN = "袁"
    TA = "他"


class Rarity(Enum):
    """稀有度枚举"""
    COMMON = 1      # 普通卡
    RARE = 2        # 黑卡
    EPIC = 3        # 色卡
    LEGENDARY = 4   # 闪色卡


class Position(Enum):
    """位置枚举"""
    FRONT = "前排"
    MIDDLE = "中排"
    BACK = "后排"

class Attribute(Enum):
    """武将属性枚举"""
    BRAVERY = "勇猛"      # 勇猛
    CHARISMA = "魅力"     # 魅力
    RECRUIT = "募兵"      # 募兵
    FENCE = "防栅"        # 防栅
    CHAIN = "连环"        # 连环
    REVIVE = "复活"       # 复活
    AMBUSH = "伏兵"       # 伏兵
    
    def __str__(self):
        return self.value


class General:
    """武将类"""
    
    def __init__(self, 
                 general_id: int,
                 name: str,
                 camp: Camp,
                 rarity: Rarity,
                 cost: float,
                 force: int,
                 intelligence: int,
                 attribute: List[Attribute] = None,
                 active_skill: 'Skill' = None,
                 passive_skills: List['PassiveSkill'] = None):
        """
        初始化武将
        
        Args:
            general_id: 武将ID
            name: 武将姓名
            camp: 所属阵营
            rarity: 稀有度
            cost: 费用
            force: 武力
            intelligence: 智力
            attribute: 属性列表（对应被动技能）
            active_skill: 主动技能（只能有一个）
            passive_skills: 被动技能列表（基于attribute）
        """
        self.general_id = general_id
        self.name = name
        self.camp = camp
        self.rarity = rarity
        self.cost = cost
        self.force = force
        self.intelligence = intelligence
        # 最大生命值 = 武力 + 智力
        self.max_hp = force + intelligence
        self.current_hp = self.max_hp
        self.attribute = attribute or []
        self.active_skill = active_skill
        self.passive_skills = passive_skills or []
        
        # 战斗状态
        self.position: Optional[Position] = None
        self.is_alive = True
        self.buffs: List[Dict] = []  # 增益效果
        self.debuffs: List[Dict] = []  # 减益效果
        
        # 技能冷却管理
        self.active_skill_cooldown = 0  # 主动技能当前冷却时间
        
    def take_damage(self, damage: int, attacker: 'General' = None) -> int:
        """
        受到伤害
        
        Args:
            damage: 伤害值
            attacker: 攻击者（用于触发被动技能）
            
        Returns:
            实际受到的伤害
        """
        original_damage = damage
        actual_damage = max(0, damage)
        
        # 触发防栅被动技能
        if self.has_passive_skill("防栅"):
            fence_passive = self.get_passive_skill("防栅")
            actual_damage = fence_passive.trigger_on_receive_damage(self, actual_damage)
        
        # 触发连环被动技能（伤害分担）
        if self.has_passive_skill("连环"):
            # TODO: 需要传入团队信息来实现连环伤害分担
            pass
        
        # 记录是否是致死伤害
        is_fatal = (self.current_hp - actual_damage) <= 0
        fatal_damage = actual_damage if is_fatal else 0
        
        self.current_hp = max(0, self.current_hp - actual_damage)
        
        if self.current_hp <= 0:
            self.is_alive = False
            
            # 触发复活被动技能
            if self.has_passive_skill("复活"):
                revive_passive = self.get_passive_skill("复活")
                if revive_passive.trigger_on_death(self):
                    # 复活成功，记录日志
                    pass
            
            # 触发魅力被动技能（反弹伤害）
            if self.has_passive_skill("魅力") and attacker:
                charisma_passive = self.get_passive_skill("魅力")
                return_damage = charisma_passive.trigger_on_death(self, attacker, fatal_damage)
                if return_damage > 0:
                    attacker.take_damage(return_damage)
                    
        return actual_damage
    
    def heal(self, amount: int) -> int:
        """
        治疗
        
        Args:
            amount: 治疗量
            
        Returns:
            实际治疗量
        """
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp - old_hp
    
    def get_effective_force(self) -> int:
        """获取当前有效武力值（包含buff/debuff）"""
        effective_force = self.force
        
        # 计算buff效果
        for buff in self.buffs:
            if buff['type'] == 'force_boost':
                effective_force += buff['value']
                
        # 计算debuff效果
        for debuff in self.debuffs:
            if debuff['type'] == 'force_reduction':
                effective_force -= debuff['value']
                
        return max(0, effective_force)
    
    def get_effective_intelligence(self) -> int:
        """获取当前有效智力值（包含buff/debuff）"""
        effective_intelligence = self.intelligence
        
        # 计算buff效果
        for buff in self.buffs:
            if buff['type'] == 'intelligence_boost':
                effective_intelligence += buff['value']
                
        # 计算debuff效果
        for debuff in self.debuffs:
            if debuff['type'] == 'intelligence_reduction':
                effective_intelligence -= debuff['value']
                
        return max(0, effective_intelligence)
    
    def calculate_damage_to(self, target: 'General') -> int:
        """
        计算对目标武将的伤害值
        
        Args:
            target: 目标武将
            
        Returns:
            造成的伤害值
        """
        # 获取攻击方的有效武力和智力
        attacker_force = self.get_effective_force()
        attacker_intelligence = self.get_effective_intelligence()
        
        # 获取目标的有效武力和智力
        target_force = target.get_effective_force()
        target_intelligence = target.get_effective_intelligence()
        
        # 按照战斗逻辑计算伤害
        if attacker_force > target_force:
            # 武力大于目标武力：伤害 = 攻击方武力 - 目标武力
            damage = attacker_force - target_force
        else:
            # 武力小于等于目标武力：伤害 = (攻击方武力+智力) - (目标武力+智力)
            damage = (attacker_force + attacker_intelligence) - (target_force + target_intelligence)
            # 武力低于对方的情况下，确保伤害不超过3
            if damage >= 3:
              damage = 3
        
        # 确保伤害大于0
        return max(1, damage)
    
    def attack(self, target: 'General') -> int:
        """
        攻击目标武将
        
        Args:
            target: 目标武将
            
        Returns:
            实际造成的伤害
        """
        if not self.is_alive or not target.is_alive:
            return 0
        
        damage = self.calculate_damage_to(target)
        
        # 触发勇猛被动技能
        if self.has_passive_skill("勇猛"):
            bravery_passive = self.get_passive_skill("勇猛")
            damage = bravery_passive.trigger_on_attack(self, target, damage)
        
        # 触发伏兵破隐（使用技能后）
        if self.has_passive_skill("伏兵"):
            ambush_passive = self.get_passive_skill("伏兵")
            ambush_passive.reveal_after_skill_use()
        
        actual_damage = target.take_damage(damage, self)
        
        return actual_damage
    
    def add_buff(self, buff_type: str, value: int, duration: int):
        """添加增益效果"""
        self.buffs.append({
            'type': buff_type,
            'value': value,
            'duration': duration
        })
    
    def add_debuff(self, debuff_type: str, value: int, duration: int):
        """添加减益效果"""
        self.debuffs.append({
            'type': debuff_type,
            'value': value,
            'duration': duration
        })
    
    def update_effects(self):
        """更新效果持续时间和技能冷却"""
        self.buffs = [buff for buff in self.buffs if buff['duration'] > 1]
        self.debuffs = [debuff for debuff in self.debuffs if debuff['duration'] > 1]
        
        # 减少持续时间
        for buff in self.buffs:
            buff['duration'] -= 1
        for debuff in self.debuffs:
            debuff['duration'] -= 1
            
        # 更新主动技能冷却
        if self.active_skill_cooldown > 0:
            self.active_skill_cooldown -= 1
    
    def trigger_turn_start_passives(self):
        """触发回合开始时的被动技能"""
        # 触发募兵被动技能
        if self.has_passive_skill("募兵"):
            recruit_passive = self.get_passive_skill("募兵")
            heal_amount = recruit_passive.trigger_on_turn_start(self)
            if heal_amount > 0:
                # 记录治疗日志
                pass
    
    def has_passive_skill(self, skill_name: str) -> bool:
        """检查是否拥有指定的被动技能"""
        return any(skill.name == skill_name for skill in self.passive_skills)
    
    def get_passive_skill(self, skill_name: str):
        """获取指定的被动技能实例"""
        for skill in self.passive_skills:
            if skill.name == skill_name:
                return skill
        return None
    
    def can_be_targeted_by_enemy(self, team_generals=None) -> bool:
        """检查是否可以被敌方选中（考虑伏兵等效果）"""
        if not self.is_alive:
            return False
        
        # 检查伏兵被动技能
        if self.has_passive_skill("伏兵"):
            ambush_passive = self.get_passive_skill("伏兵")
            if team_generals:
                return ambush_passive.can_be_targeted(self, team_generals)
            else:
                return not ambush_passive.is_hidden
        
        return True
    
    def can_use_active_skill(self) -> bool:
        """检查是否可以使用主动技能"""
        if not self.is_alive:
            return False
        if not self.active_skill:
            return False
        if self.active_skill_cooldown > 0:
            return False
        return True
    
    def use_active_skill(self, targets: List['General'], battle_context, team=None) -> Dict:
        """
        使用主动技能
        
        Args:
            targets: 目标列表
            battle_context: 战斗上下文
            team: 队伍对象（用于管理士气）
            
        Returns:
            技能使用结果
        """
        if not self.can_use_active_skill():
            return {"success": False, "message": "无法使用主动技能"}
        
        if not self.active_skill:
            return {"success": False, "message": "没有主动技能"}
        
        # 如果有队伍对象，检查并消耗士气
        if team is not None:
            if team.current_morale < self.active_skill.morale_cost:
                return {"success": False, "message": "士气不足"}
            if not team.consume_morale(self.active_skill.morale_cost):
                return {"success": False, "message": "士气消耗失败"}
        
        # 设置冷却时间
        self.active_skill_cooldown = self.active_skill.cooldown
        
        # 执行技能效果
        result = self.active_skill.execute(self, targets, battle_context)
        result["skill_name"] = self.active_skill.name
        result["caster"] = self.name
        result["morale_consumed"] = self.active_skill.morale_cost
        if team:
            result["remaining_morale"] = team.current_morale
        
        return result
    
    def __str__(self) -> str:
        """字符串表示"""
        status = "存活" if self.is_alive else "阵亡"
        attrs = "/".join([attr.value for attr in self.attribute]) if self.attribute else "无"
        return f"{self.name}({self.camp.value}) [{attrs}] - HP:{self.current_hp}/{self.max_hp} 武力:{self.force} 智力:{self.intelligence} [{status}]"
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'general_id': self.general_id,
            'name': self.name,
            'camp': self.camp.value,
            'rarity': self.rarity.value,
            'max_hp': self.max_hp,
            'current_hp': self.current_hp,
            'cost': self.cost,
            'force': self.force,
            'intelligence': self.intelligence,
            'attribute': [attr.value for attr in self.attribute],
            'active_skill': self.active_skill.name if self.active_skill else None,
            'active_skill_cooldown': self.active_skill_cooldown,
            'passive_skills': [skill.name for skill in self.passive_skills],
            'is_alive': self.is_alive
        }

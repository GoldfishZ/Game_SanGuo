"""
武将模型类
定义武将的基本属性和行为
"""

from typing import List, Dict, Optional
from enum import Enum


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
                 max_hp: int,
                 force: int,
                 intelligence: int,
                 attribute: List[Attribute] = None,
                 skills: List[str] = None):
        """
        初始化武将
        
        Args:
            general_id: 武将ID
            name: 武将姓名
            camp: 所属阵营
            rarity: 稀有度
            max_hp: 最大生命值
            force: 武力
            intelligence: 智力
            attribute:属性
            skills: 技能列表
        """
        self.general_id = general_id
        self.name = name
        self.camp = camp
        self.rarity = rarity
        self.max_hp = max_hp
        self.current_hp = max_hp
        self.force = force
        self.intelligence = intelligence
        self.attribute = attribute or []
        self.skills = skills or []
        
        # 战斗状态
        self.position: Optional[Position] = None
        self.is_alive = True
        self.buffs: List[Dict] = []  # 增益效果
        self.debuffs: List[Dict] = []  # 减益效果
        
    def take_damage(self, damage: int) -> int:
        """
        受到伤害
        
        Args:
            damage: 伤害值
            
        Returns:
            实际受到的伤害
        """
        actual_damage = max(0, damage)
        self.current_hp = max(0, self.current_hp - actual_damage)
        
        if self.current_hp <= 0:
            self.is_alive = False
            
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
        actual_damage = target.take_damage(damage)
        
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
        """更新效果持续时间"""
        self.buffs = [buff for buff in self.buffs if buff['duration'] > 1]
        self.debuffs = [debuff for debuff in self.debuffs if debuff['duration'] > 1]
        
        # 减少持续时间
        for buff in self.buffs:
            buff['duration'] -= 1
        for debuff in self.debuffs:
            debuff['duration'] -= 1
    
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
            'force': self.force,
            'intelligence': self.intelligence,
            'attribute': [attr.value for attr in self.attribute],
            'skills': self.skills,
            'is_alive': self.is_alive
        }

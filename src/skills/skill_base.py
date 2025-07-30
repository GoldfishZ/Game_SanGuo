"""
技能系统基类
定义技能的基本结构和行为
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum


class SkillType(Enum):
    """技能类型"""
    ACTIVE = "主动技能"      # 需要手动释放
    PASSIVE = "被动技能"     # 自动触发
    COMBO = "组合技能"       # 多人配合技能


class TargetType(Enum):
    """目标类型"""
    SELF = "自身"
    SINGLE_ENEMY = "单体敌人"
    ALL_ENEMIES = "全体敌人"
    SINGLE_ALLY = "单体友军"
    ALL_ALLIES = "全体友军"
    RANDOM_ENEMY = "随机敌人"
    FRONT_ROW = "前排"
    BACK_ROW = "后排"


class Skill(ABC):
    """技能基类"""
    
    def __init__(self,
                 skill_id: str,
                 name: str,
                 description: str,
                 skill_type: SkillType,
                 target_type: TargetType,
                 cooldown: int = 0,
                 energy_cost: int = 0):
        """
        初始化技能
        
        Args:
            skill_id: 技能ID
            name: 技能名称
            description: 技能描述
            skill_type: 技能类型
            target_type: 目标类型
            cooldown: 冷却回合数
            energy_cost: 能量消耗
        """
        self.skill_id = skill_id
        self.name = name
        self.description = description
        self.skill_type = skill_type
        self.target_type = target_type
        self.cooldown = cooldown
        self.energy_cost = energy_cost
        self.current_cooldown = 0
    
    @abstractmethod
    def execute(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """
        执行技能
        
        Args:
            caster: 施法者
            targets: 目标列表
            battle_context: 战斗上下文
            
        Returns:
            技能执行结果
        """
        pass
    
    def can_use(self, caster) -> bool:
        """
        检查是否可以使用技能
        
        Args:
            caster: 施法者
            
        Returns:
            是否可以使用
        """
        return (self.current_cooldown <= 0 and 
                caster.is_alive and
                hasattr(caster, 'energy') and caster.energy >= self.energy_cost)
    
    def use_skill(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """
        使用技能
        
        Args:
            caster: 施法者
            targets: 目标列表
            battle_context: 战斗上下文
            
        Returns:
            技能使用结果
        """
        if not self.can_use(caster):
            return {"success": False, "message": "技能无法使用"}
        
        # 扣除能量和设置冷却
        if hasattr(caster, 'energy'):
            caster.energy -= self.energy_cost
        self.current_cooldown = self.cooldown
        
        # 执行技能效果
        result = self.execute(caster, targets, battle_context)
        result["skill_name"] = self.name
        result["caster"] = caster.name
        
        return result
    
    def update_cooldown(self):
        """更新冷却时间"""
        if self.current_cooldown > 0:
            self.current_cooldown -= 1


class AttackSkill(Skill):
    """攻击型技能"""
    
    def __init__(self, skill_id: str, name: str, description: str, 
                 target_type: TargetType, damage_multiplier: float = 1.0,
                 cooldown: int = 0, energy_cost: int = 0):
        super().__init__(skill_id, name, description, SkillType.ACTIVE, 
                        target_type, cooldown, energy_cost)
        self.damage_multiplier = damage_multiplier
    
    def execute(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """执行攻击技能"""
        results = []
        total_damage = 0
        
        for target in targets:
            if target.is_alive:
                damage = int(caster.get_effective_attack() * self.damage_multiplier)
                actual_damage = target.take_damage(damage)
                total_damage += actual_damage
                
                results.append({
                    "target": target.name,
                    "damage": actual_damage,
                    "target_hp": target.current_hp
                })
        
        return {
            "success": True,
            "type": "attack",
            "total_damage": total_damage,
            "targets_hit": len(results),
            "details": results
        }


class HealSkill(Skill):
    """治疗型技能"""
    
    def __init__(self, skill_id: str, name: str, description: str,
                 target_type: TargetType, heal_amount: int,
                 cooldown: int = 0, energy_cost: int = 0):
        super().__init__(skill_id, name, description, SkillType.ACTIVE,
                        target_type, cooldown, energy_cost)
        self.heal_amount = heal_amount
    
    def execute(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """执行治疗技能"""
        results = []
        total_heal = 0
        
        for target in targets:
            if target.is_alive:
                actual_heal = target.heal(self.heal_amount)
                total_heal += actual_heal
                
                results.append({
                    "target": target.name,
                    "heal": actual_heal,
                    "target_hp": target.current_hp
                })
        
        return {
            "success": True,
            "type": "heal",
            "total_heal": total_heal,
            "targets_healed": len(results),
            "details": results
        }


class BuffSkill(Skill):
    """增益技能"""
    
    def __init__(self, skill_id: str, name: str, description: str,
                 target_type: TargetType, buff_type: str, buff_value: int,
                 duration: int, cooldown: int = 0, energy_cost: int = 0):
        super().__init__(skill_id, name, description, SkillType.ACTIVE,
                        target_type, cooldown, energy_cost)
        self.buff_type = buff_type
        self.buff_value = buff_value
        self.duration = duration
    
    def execute(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """执行增益技能"""
        results = []
        
        for target in targets:
            if target.is_alive:
                target.add_buff(self.buff_type, self.buff_value, self.duration)
                results.append({
                    "target": target.name,
                    "buff_type": self.buff_type,
                    "buff_value": self.buff_value,
                    "duration": self.duration
                })
        
        return {
            "success": True,
            "type": "buff",
            "targets_buffed": len(results),
            "details": results
        }

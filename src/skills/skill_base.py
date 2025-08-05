"""
技能系统基类
定义技能的基本结构和行为
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum


class SkillType(Enum):
    """技能类型"""
    ENHANCE_WEAKEN = "强化/虚弱技能"  # 强化自身或虚弱对方
    DAMAGE = "伤害技能"              # 对敌方造成伤害
    PASSIVE = "被动技能"             # 武将属性技能


class TargetType(Enum):
    """目标类型"""
    SELF = "自身"
    SINGLE_ENEMY = "单体敌人"
    ALL_ENEMIES = "全体敌人"
    SINGLE_ALLY = "单体友军"
    ALL_ALLIES = "全体友军"
    RANDOM_ENEMY = "随机敌人"
    FRONT_ROW_ENEMY = "敌方前排"
    BACK_ROW_ENEMY = "敌方后排"
    FRONT_ROW_ALLY = "友方前排"
    BACK_ROW_ALLY = "友方后排"
    AREA_ENEMY = "区域敌人"  # 区域内的敌人
    AREA_ALLY = "区域友军"  # 区域内的友军


class Skill(ABC):
    """技能基类"""
    
    def __init__(self,
                 skill_id: str,
                 name: str,
                 description: str,
                 skill_type: SkillType,
                 target_type: TargetType,
                 cooldown: int = 0,
                 morale_cost: int = 0):
        """
        初始化技能
        
        Args:
            skill_id: 技能ID
            name: 技能名称
            description: 技能描述
            skill_type: 技能类型
            target_type: 目标类型
            cooldown: 冷却回合数
            morale_cost: 士气消耗
        """
        self.skill_id = skill_id
        self.name = name
        self.description = description
        self.skill_type = skill_type
        self.target_type = target_type
        self.cooldown = cooldown
        self.morale_cost = morale_cost
    
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
    
    def can_use(self, caster, team=None) -> bool:
        """
        检查是否可以使用技能
        
        Args:
            caster: 施法者
            team: 队伍对象（用于检查士气）
            
        Returns:
            是否可以使用
        """
        if not caster.is_alive:
            return False
        
        # 检查施法者的技能冷却（而不是技能对象的冷却）
        if hasattr(caster, 'active_skill_cooldown') and caster.active_skill_cooldown > 0:
            return False
        
        # 如果提供了队伍对象，检查士气
        if team is not None:
            return team.current_morale >= self.morale_cost
        
        return True
    
    def use_skill(self, caster, targets: List, battle_context, team=None) -> Dict[str, Any]:
        """
        使用技能
        
        Args:
            caster: 施法者
            targets: 目标列表
            battle_context: 战斗上下文
            team: 队伍对象（用于管理士气）
            
        Returns:
            技能使用结果
        """
        if not self.can_use(caster, team):
            return {"success": False, "message": "技能无法使用"}
        
        # 如果有队伍对象，通过队伍消耗士气
        if team is not None:
            if not team.consume_morale(self.morale_cost):
                return {"success": False, "message": "士气不足"}
        
        # 设置施法者的技能冷却（而不是技能对象的冷却）
        if hasattr(caster, 'active_skill_cooldown'):
            caster.active_skill_cooldown = self.cooldown
        
        # 执行技能效果
        result = self.execute(caster, targets, battle_context)
        result["skill_name"] = self.name
        result["caster"] = caster.name
        result["morale_consumed"] = self.morale_cost
        if team:
            result["remaining_morale"] = team.current_morale
        
        return result
    
    # 移除 update_cooldown 方法，因为冷却现在由武将管理
    # def update_cooldown(self):


class DamageSkill(Skill):
    """伤害技能"""
    
    def __init__(self, skill_id: str, name: str, description: str, 
                 target_type: TargetType, damage_multiplier: float = 1.0,
                 cooldown: int = 0, morale_cost: int = 0):
        super().__init__(skill_id, name, description, SkillType.DAMAGE, 
                        target_type, cooldown, morale_cost)
        self.damage_multiplier = damage_multiplier
    
    def execute(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """
        执行伤害技能
        Args:
            caster: 施法者
            targets: 目标列表
            battle_context: 战斗上下文
        """
        results = []
        total_damage = 0
        
        for target in targets:
            if target.is_alive:
                # 使用新的伤害计算逻辑
                damage = int(caster.calculate_damage_to(target) * self.damage_multiplier)
                actual_damage = target.take_damage(damage)
                total_damage += actual_damage
                
                results.append({
                    "target": target.name,
                    "damage": actual_damage,
                    "target_hp": target.current_hp
                })
        
        return {
            "success": True,
            "type": "damage",
            "total_damage": total_damage,
            "targets_hit": len(results),
            "details": results
        }


class EnhanceWeakenSkill(Skill):
    """强化/虚弱技能"""
    
    def __init__(self, skill_id: str, name: str, description: str,
                 target_type: TargetType, effect_type: str, effect_value: int,
                 duration: int, cooldown: int = 0, morale_cost: int = 0):
        super().__init__(skill_id, name, description, SkillType.ENHANCE_WEAKEN,
                        target_type, cooldown, morale_cost)
        self.effect_type = effect_type  # 如: 'force_boost', 'intelligence_reduction' 等
        self.effect_value = effect_value
        self.duration = duration
    
    def execute(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """执行强化/虚弱技能"""
        results = []
        
        # 检查是否是队伍效果（士气相关）
        if "morale" in self.effect_type and hasattr(battle_context, 'get_team_for_general'):
            # 队伍级别的效果
            team = battle_context.get_team_for_general(caster)
            if team and self.effect_type == "morale_max_boost":
                old_max = team.max_morale
                team.max_morale += self.effect_value
                # 当前士气也增加相同数值（立即生效）
                team.current_morale += self.effect_value
                
                results.append({
                    "target": "队伍",
                    "effect_type": "最大士气增加",
                    "old_max_morale": old_max,
                    "new_max_morale": team.max_morale,
                    "morale_gained": self.effect_value,
                    "current_morale": team.current_morale
                })
        else:
            # 武将个体效果
            for target in targets:
                if target.is_alive:
                    # 判断是增益还是减益
                    if "boost" in self.effect_type or "enhance" in self.effect_type:
                        target.add_buff(self.effect_type, self.effect_value, self.duration)
                        effect_name = "强化技能"
                    else:
                        target.add_debuff(self.effect_type, self.effect_value, self.duration)
                        effect_name = "虚弱技能"
                    
                    results.append({
                        "target": target.name,
                        "effect_type": self.effect_type,
                        "effect_value": self.effect_value,
                        "duration": self.duration,
                        "effect_name": effect_name
                    })
        
        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": len(results),
            "details": results
        }

class TeamEffectSkill(Skill):
    """队伍效果技能 - 影响整个队伍的技能"""
    
    def __init__(self, skill_id: str, name: str, description: str,
                 target_type: TargetType, effect_type: str, effect_value: int,
                 cooldown: int = 0, morale_cost: int = 0):
        super().__init__(skill_id, name, description, SkillType.ENHANCE_WEAKEN,
                        target_type, cooldown, morale_cost)
        self.effect_type = effect_type
        self.effect_value = effect_value
    
    def execute(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """执行队伍效果技能"""
        results = []
        
        # 获取施法者的队伍
        team = battle_context.get_team_for_general(caster)
        
        if self.effect_type == "max_morale_boost":
            # 增加队伍最大士气值
            old_max = team.max_morale
            team.max_morale += self.effect_value
            # 当前士气也增加相同数值
            team.current_morale += self.effect_value
            
            results.append({
                "effect": "最大士气增加",
                "old_max_morale": old_max,
                "new_max_morale": team.max_morale,
                "morale_gained": self.effect_value
            })
        
        return {
            "success": True,
            "type": "team_effect", 
            "effect_type": self.effect_type,
            "effect_value": self.effect_value,
            "details": results
        }

class PassiveSkill(Skill):
    """被动技能（基于武将属性）"""
    
    def __init__(self, skill_id: str, name: str, description: str, 
                 attribute_type: str):
        # 被动技能不需要目标类型、冷却和士气消耗
        super().__init__(skill_id, name, description, SkillType.PASSIVE, 
                        TargetType.SELF, 0, 0)
        self.attribute_type = attribute_type  # 对应武将的某个attribute
    
    def execute(self, caster, targets: List, battle_context) -> Dict[str, Any]:
        """被动技能的执行（通常在特定时机触发）"""
        return {
            "success": True,
            "type": "passive",
            "attribute_type": self.attribute_type,
            "message": f"{caster.name}的{self.name}被动技能触发"
        }
    
    def can_use(self, caster, team=None) -> bool:
        """被动技能总是可以使用（在满足触发条件时）"""
        return caster.is_alive

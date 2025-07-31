"""
队伍类
管理武将队伍和士气系统
"""

from typing import List, Dict, Optional, TYPE_CHECKING
from .general import General, Camp

if TYPE_CHECKING:
    pass


class Team:
    """队伍类"""
    
    def __init__(self, team_name: str = "", camp: Camp = None, max_morale: int = 12):
        """
        初始化队伍
        
        Args:
            team_name: 队伍名称
            camp: 队伍阵营
            max_morale: 最大士气值（固定为12）
        """
        self.team_name = team_name
        self.camp = camp
        self.generals: List[General] = []
        self.max_morale = 12  # 固定士气上限为12
        self.current_morale = 12
        
    def add_general(self, general: General) -> bool:
        """
        添加武将到队伍
        
        Args:
            general: 要添加的武将
            
        Returns:
            是否添加成功
        """
        if general not in self.generals:
            self.generals.append(general)
            return True
        return False
    
    def remove_general(self, general: General) -> bool:
        """
        从队伍中移除武将
        
        Args:
            general: 要移除的武将
            
        Returns:
            是否移除成功
        """
        if general in self.generals:
            self.generals.remove(general)
            return True
        return False
    
    def consume_morale(self, amount: int) -> bool:
        """
        消耗队伍士气
        
        Args:
            amount: 消耗的士气值
            
        Returns:
            是否成功消耗
        """
        if self.current_morale >= amount:
            self.current_morale -= amount
            return True
        return False
    
    def restore_morale(self, amount: int):
        """
        恢复队伍士气
        
        Args:
            amount: 恢复的士气值
        """
        self.current_morale = min(self.max_morale, self.current_morale + amount)
    
    def get_living_generals(self) -> List[General]:
        """获取存活的武将列表"""
        return [general for general in self.generals if general.is_alive]
    
    def get_dead_generals(self) -> List[General]:
        """获取阵亡的武将列表"""
        return [general for general in self.generals if not general.is_alive]
    
    def is_defeated(self) -> bool:
        """检查队伍是否全军覆没"""
        return len(self.get_living_generals()) == 0
    
    def get_total_cost(self) -> float:
        """获取队伍总费用"""
        return sum(general.cost for general in self.generals)
    
    def can_use_skill(self, general: General) -> bool:
        """
        检查武将是否可以使用主动技能
        
        Args:
            general: 要检查的武将
            
        Returns:
            是否可以使用技能
        """
        if not general.is_alive or general not in self.generals:
            return False
        
        if not general.active_skill:
            return False
        
        # 检查士气是否足够
        if self.current_morale < general.active_skill.morale_cost:
            return False
        
        # 检查武将的技能冷却
        if general.active_skill_cooldown > 0:
            return False
        
        return True
    
    def use_skill(self, general: General, targets: List[General], battle_context) -> Dict:
        """
        使用武将的主动技能
        
        Args:
            general: 施法武将
            targets: 目标列表
            battle_context: 战斗上下文
            
        Returns:
            技能使用结果
        """
        if not self.can_use_skill(general):
            return {"success": False, "message": "无法使用技能"}
        
        # 通过武将对象使用技能，让武将管理自己的冷却
        return general.use_active_skill(targets, battle_context, self)
    
    def update_effects(self):
        """更新所有武将的效果和技能冷却"""
        for general in self.generals:
            general.update_effects()  # 武将的update_effects现在会处理技能冷却
    
    def start_turn_restore_morale(self, amount: int = 10):
        """每回合开始时恢复一定士气"""
        self.restore_morale(amount)
    
    def get_team_status(self) -> Dict:
        """获取队伍状态信息"""
        return {
            "team_name": self.team_name,
            "morale": {
                "current": self.current_morale,
                "max": self.max_morale,
                "percentage": (self.current_morale / self.max_morale) * 100
            },
            "generals": {
                "total": len(self.generals),
                "living": len(self.get_living_generals()),
                "dead": len(self.get_dead_generals())
            },
            "total_cost": self.get_total_cost(),
            "is_defeated": self.is_defeated()
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        living = len(self.get_living_generals())
        total = len(self.generals)
        return f"{self.team_name} - 士气:{self.current_morale}/{self.max_morale} 武将:{living}/{total}"

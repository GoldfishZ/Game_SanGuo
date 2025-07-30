"""
战斗系统核心类
管理回合制战斗逻辑
"""

from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import random

from ..models.general import General
from ..battle.formation import Formation
from ..skills.skill_base import Skill, TargetType


class BattlePhase(Enum):
    """战斗阶段"""
    PREPARATION = "准备阶段"
    COMBAT = "战斗阶段"
    END = "结束阶段"


class ActionType(Enum):
    """行动类型"""
    ATTACK = "攻击"
    SKILL = "技能"
    DEFEND = "防御"
    MOVE = "移动"


class BattleAction:
    """战斗行动"""
    
    def __init__(self, actor: General, action_type: ActionType, 
                 target: Optional[General] = None, skill: Optional[Skill] = None):
        self.actor = actor
        self.action_type = action_type
        self.target = target
        self.skill = skill


class BattleSystem:
    """战斗系统"""
    
    def __init__(self, player_formation: Formation, enemy_formation: Formation):
        """
        初始化战斗系统
        
        Args:
            player_formation: 玩家阵型
            enemy_formation: 敌方阵型
        """
        self.player_formation = player_formation
        self.enemy_formation = enemy_formation
        self.current_phase = BattlePhase.PREPARATION
        self.turn_counter = 0
        self.battle_log: List[str] = []
        self.turn_order: List[General] = []
        
    def start_battle(self) -> Dict[str, Any]:
        """开始战斗"""
        self.current_phase = BattlePhase.PREPARATION
        self.turn_counter = 0
        self.battle_log.clear()
        
        # 计算行动顺序（按速度排序）
        self._calculate_turn_order()
        
        self.log_message("=== 战斗开始 ===")
        self.log_message(f"玩家阵容: {len(self.player_formation.get_living_generals())}人")
        self.log_message(f"敌方阵容: {len(self.enemy_formation.get_living_generals())}人")
        
        self.current_phase = BattlePhase.COMBAT
        
        return {
            "status": "battle_started",
            "turn_order": [g.name for g in self.turn_order],
            "message": "战斗开始！"
        }
    
    def execute_turn(self) -> Dict[str, Any]:
        """执行一个回合"""
        if self.current_phase != BattlePhase.COMBAT:
            return {"status": "error", "message": "战斗未进行中"}
        
        self.turn_counter += 1
        self.log_message(f"\n=== 第{self.turn_counter}回合 ===")
        
        # 执行每个武将的行动
        for general in self.turn_order:
            if not general.is_alive:
                continue
                
            # 更新武将效果
            general.update_effects()
            
            # AI决策或玩家操作
            if self._is_player_general(general):
                action = self._get_player_action(general)
            else:
                action = self._get_ai_action(general)
            
            # 执行行动
            if action:
                self._execute_action(action)
            
            # 检查战斗是否结束
            if self._check_battle_end():
                break
        
        # 检查战斗结果
        battle_result = self._check_battle_end()
        if battle_result:
            self.current_phase = BattlePhase.END
            return battle_result
        
        return {
            "status": "turn_completed",
            "turn": self.turn_counter,
            "player_alive": len(self.player_formation.get_living_generals()),
            "enemy_alive": len(self.enemy_formation.get_living_generals())
        }
    
    def _calculate_turn_order(self):
        """计算行动顺序"""
        all_generals = (self.player_formation.get_living_generals() + 
                       self.enemy_formation.get_living_generals())
        
        # 按速度降序排序
        self.turn_order = sorted(all_generals, key=lambda g: g.speed, reverse=True)
    
    def _is_player_general(self, general: General) -> bool:
        """判断是否为玩家武将"""
        return general in self.player_formation.get_all_generals()
    
    def _get_player_action(self, general: General) -> Optional[BattleAction]:
        """获取玩家行动（简化版，实际应该由UI处理）"""
        # 这里简化为AI行动，实际游戏中应该等待玩家输入
        return self._get_ai_action(general)
    
    def _get_ai_action(self, general: General) -> Optional[BattleAction]:
        """AI决策"""
        # 简单的AI逻辑：优先使用技能，否则攻击
        
        # 确定敌方阵营
        if self._is_player_general(general):
            enemy_formation = self.enemy_formation
        else:
            enemy_formation = self.player_formation
        
        enemy_targets = enemy_formation.get_living_generals()
        if not enemy_targets:
            return None
        
        # 随机选择一个敌人作为目标
        target = random.choice(enemy_targets)
        
        # 简单攻击行动
        return BattleAction(general, ActionType.ATTACK, target)
    
    def _execute_action(self, action: BattleAction):
        """执行行动"""
        actor = action.actor
        
        if action.action_type == ActionType.ATTACK:
            self._execute_attack(actor, action.target)
        elif action.action_type == ActionType.SKILL:
            self._execute_skill(actor, action.skill, action.target)
        elif action.action_type == ActionType.DEFEND:
            self._execute_defend(actor)
    
    def _execute_attack(self, attacker: General, target: General):
        """执行攻击"""
        if not target.is_alive:
            return
        
        damage = attacker.get_effective_attack()
        actual_damage = target.take_damage(damage)
        
        self.log_message(f"{attacker.name} 攻击 {target.name}，造成 {actual_damage} 点伤害")
        
        if not target.is_alive:
            self.log_message(f"{target.name} 被击败！")
    
    def _execute_skill(self, caster: General, skill: Skill, target: General):
        """执行技能"""
        if not skill or not skill.can_use(caster):
            return
        
        targets = self._get_skill_targets(skill, caster, target)
        result = skill.use_skill(caster, targets, self)
        
        if result.get("success"):
            self.log_message(f"{caster.name} 使用技能 {skill.name}")
            # 根据技能结果添加详细日志
            self._log_skill_result(result)
    
    def _execute_defend(self, defender: General):
        """执行防御"""
        # 防御行动：临时提升防御力
        defender.add_buff("defense_boost", defender.defense // 2, 1)
        self.log_message(f"{defender.name} 进入防御状态")
    
    def _get_skill_targets(self, skill: Skill, caster: General, primary_target: General) -> List[General]:
        """根据技能目标类型获取目标列表"""
        targets = []
        
        if skill.target_type == TargetType.SELF:
            targets = [caster]
        elif skill.target_type == TargetType.SINGLE_ENEMY:
            targets = [primary_target] if primary_target else []
        elif skill.target_type == TargetType.ALL_ENEMIES:
            if self._is_player_general(caster):
                targets = self.enemy_formation.get_living_generals()
            else:
                targets = self.player_formation.get_living_generals()
        elif skill.target_type == TargetType.SINGLE_ALLY:
            targets = [primary_target] if primary_target else []
        elif skill.target_type == TargetType.ALL_ALLIES:
            if self._is_player_general(caster):
                targets = self.player_formation.get_living_generals()
            else:
                targets = self.enemy_formation.get_living_generals()
        
        return targets
    
    def _log_skill_result(self, result: Dict[str, Any]):
        """记录技能结果"""
        if result.get("type") == "attack":
            self.log_message(f"  造成总伤害: {result.get('total_damage', 0)}")
        elif result.get("type") == "heal":
            self.log_message(f"  总治疗量: {result.get('total_heal', 0)}")
        elif result.get("type") == "buff":
            self.log_message(f"  为 {result.get('targets_buffed', 0)} 个目标施加增益效果")
    
    def _check_battle_end(self) -> Optional[Dict[str, Any]]:
        """检查战斗是否结束"""
        player_alive = len(self.player_formation.get_living_generals())
        enemy_alive = len(self.enemy_formation.get_living_generals())
        
        if player_alive == 0:
            self.log_message("\n=== 战斗失败 ===")
            return {
                "status": "defeat",
                "message": "全军覆没，战斗失败！",
                "turns": self.turn_counter
            }
        elif enemy_alive == 0:
            self.log_message("\n=== 战斗胜利 ===")
            return {
                "status": "victory",
                "message": "敌军全灭，战斗胜利！",
                "turns": self.turn_counter
            }
        
        return None
    
    def log_message(self, message: str):
        """记录战斗日志"""
        self.battle_log.append(message)
        print(message)  # 同时输出到控制台
    
    def get_battle_state(self) -> Dict[str, Any]:
        """获取当前战斗状态"""
        return {
            "phase": self.current_phase.value,
            "turn": self.turn_counter,
            "player_formation": {
                "living_count": len(self.player_formation.get_living_generals()),
                "generals": [g.to_dict() for g in self.player_formation.get_all_generals()]
            },
            "enemy_formation": {
                "living_count": len(self.enemy_formation.get_living_generals()),
                "generals": [g.to_dict() for g in self.enemy_formation.get_all_generals()]
            },
            "turn_order": [g.name for g in self.turn_order if g.is_alive],
            "recent_logs": self.battle_log[-10:]  # 最近10条日志
        }

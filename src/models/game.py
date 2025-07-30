"""
游戏主控制器
管理整个游戏的状态和流程
"""

from typing import Dict, List, Any, Optional
from ..models.general import General, Camp, Rarity
from ..battle.formation import Formation, FormationType
from ..battle.battle_system import BattleSystem
from ..skills.skill_base import AttackSkill, HealSkill, BuffSkill, TargetType


class GameState:
    """游戏状态枚举"""
    MENU = "主菜单"
    FORMATION_SETUP = "阵容设置"
    BATTLE = "战斗中"
    VICTORY = "胜利"
    DEFEAT = "失败"


class Game:
    """游戏主控制器"""
    
    def __init__(self):
        """初始化游戏"""
        self.state = GameState.MENU
        self.player_generals: List[General] = []
        self.player_formation = Formation(FormationType.BALANCED)
        self.current_battle: Optional[BattleSystem] = None
        
        # 初始化游戏数据
        self._initialize_game_data()
    
    def _initialize_game_data(self):
        """初始化游戏数据"""
        # 创建一些示例武将
        self._create_sample_generals()
    
    def _create_sample_generals(self):
        """创建示例武将"""
        # 蜀国武将
        liu_bei = General(
            general_id=1,
            name="刘备",
            camp=Camp.SHU,
            rarity=Rarity.LEGENDARY,
            max_hp=120,
            attack=80,
            defense=70,
            speed=60,
            skills=["仁德", "激励"]
        )
        
        guan_yu = General(
            general_id=2,
            name="关羽",
            camp=Camp.SHU,
            rarity=Rarity.EPIC,
            max_hp=100,
            attack=95,
            defense=80,
            speed=70,
            skills=["青龙偃月", "义薄云天"]
        )
        
        zhang_fei = General(
            general_id=3,
            name="张飞",
            camp=Camp.SHU,
            rarity=Rarity.EPIC,
            max_hp=110,
            attack=90,
            defense=85,
            speed=65,
            skills=["咆哮", "猛攻"]
        )
        
        # 魏国武将
        cao_cao = General(
            general_id=4,
            name="曹操",
            camp=Camp.WEI,
            rarity=Rarity.LEGENDARY,
            max_hp=115,
            attack=85,
            defense=75,
            speed=80,
            skills=["奸雄", "挟天子"]
        )
        
        xiahou_dun = General(
            general_id=5,
            name="夏侯惇",
            camp=Camp.WEI,
            rarity=Rarity.RARE,
            max_hp=95,
            attack=88,
            defense=82,
            speed=68,
            skills=["拔矢啖睛", "猛攻"]
        )
        
        # 添加到玩家武将列表
        self.player_generals = [liu_bei, guan_yu, zhang_fei]
        
        # 默认设置玩家阵型
        self.player_formation.place_general(liu_bei, 1, 1)  # 中排中间
        self.player_formation.place_general(guan_yu, 0, 0)  # 前排左
        self.player_formation.place_general(zhang_fei, 0, 2)  # 前排右
    
    def start_new_battle(self) -> Dict[str, Any]:
        """开始新战斗"""
        # 创建敌方阵型（简单AI）
        enemy_formation = self._create_enemy_formation()
        
        # 创建战斗系统
        self.current_battle = BattleSystem(self.player_formation, enemy_formation)
        
        # 开始战斗
        result = self.current_battle.start_battle()
        self.state = GameState.BATTLE
        
        return result
    
    def _create_enemy_formation(self) -> Formation:
        """创建敌方阵型"""
        enemy_formation = Formation(FormationType.OFFENSIVE)
        
        # 创建敌方武将
        enemy1 = General(
            general_id=101,
            name="敌将甲",
            camp=Camp.WEI,
            rarity=Rarity.COMMON,
            max_hp=80,
            attack=70,
            defense=60,
            speed=55
        )
        
        enemy2 = General(
            general_id=102,
            name="敌将乙",
            camp=Camp.WEI,
            rarity=Rarity.RARE,
            max_hp=90,
            attack=75,
            defense=65,
            speed=60
        )
        
        enemy3 = General(
            general_id=103,
            name="敌将丙",
            camp=Camp.WEI,
            rarity=Rarity.COMMON,
            max_hp=85,
            attack=68,
            defense=70,
            speed=50
        )
        
        # 放置敌方武将
        enemy_formation.place_general(enemy1, 0, 1)  # 前排中间
        enemy_formation.place_general(enemy2, 1, 0)  # 中排左
        enemy_formation.place_general(enemy3, 1, 2)  # 中排右
        
        return enemy_formation
    
    def execute_battle_turn(self) -> Dict[str, Any]:
        """执行战斗回合"""
        if not self.current_battle or self.state != GameState.BATTLE:
            return {"status": "error", "message": "当前没有进行中的战斗"}
        
        result = self.current_battle.execute_turn()
        
        # 检查战斗结果
        if result.get("status") == "victory":
            self.state = GameState.VICTORY
        elif result.get("status") == "defeat":
            self.state = GameState.DEFEAT
        
        return result
    
    def get_game_state(self) -> Dict[str, Any]:
        """获取游戏状态"""
        base_state = {
            "current_state": self.state,
            "player_generals_count": len(self.player_generals),
            "player_formation_info": self.player_formation.get_formation_info()
        }
        
        if self.current_battle:
            base_state["battle_state"] = self.current_battle.get_battle_state()
        
        return base_state
    
    def setup_formation(self, general_id: int, row: int, col: int) -> bool:
        """设置阵型"""
        if self.state != GameState.FORMATION_SETUP:
            return False
        
        # 找到指定武将
        general = None
        for g in self.player_generals:
            if g.general_id == general_id:
                general = g
                break
        
        if not general:
            return False
        
        return self.player_formation.place_general(general, row, col)
    
    def get_available_generals(self) -> List[Dict[str, Any]]:
        """获取可用武将列表"""
        return [general.to_dict() for general in self.player_generals]
    
    def reset_game(self):
        """重置游戏"""
        self.state = GameState.MENU
        self.current_battle = None
        
        # 重置武将状态
        for general in self.player_generals:
            general.current_hp = general.max_hp
            general.is_alive = True
            general.buffs.clear()
            general.debuffs.clear()
    
    def save_game(self) -> Dict[str, Any]:
        """保存游戏（返回可序列化的游戏数据）"""
        return {
            "state": self.state,
            "player_generals": [g.to_dict() for g in self.player_generals],
            "formation_type": self.player_formation.formation_type.value
        }
    
    def load_game(self, save_data: Dict[str, Any]) -> bool:
        """加载游戏"""
        try:
            # 这里应该实现从保存数据恢复游戏状态的逻辑
            # 简化版本
            self.state = save_data.get("state", GameState.MENU)
            return True
        except Exception as e:
            print(f"加载游戏失败: {e}")
            return False

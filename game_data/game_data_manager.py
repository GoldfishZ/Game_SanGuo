"""
游戏数据管理器
统一管理游戏中的武将和技能数据
"""

from typing import List, Dict, Optional
from src.models.general import General, Camp, Rarity
from .generals_config import get_all_generals, get_general_by_name, get_generals_by_camp
from .skills_config import ALL_SKILLS


class GameDataManager:
    """游戏数据管理器"""
    
    def __init__(self):
        """初始化游戏数据管理器"""
        self._all_generals = None
        self._generals_by_camp = {}
        self._generals_by_rarity = {}
    
    def get_all_generals(self) -> Dict[str, General]:
        """获取所有武将"""
        if self._all_generals is None:
            self._all_generals = get_all_generals()
        return self._all_generals
    
    def get_general_list(self) -> List[General]:
        """获取武将列表"""
        return list(self.get_all_generals().values())
    
    def get_general_by_name(self, name: str) -> Optional[General]:
        """根据名称获取武将"""
        return get_general_by_name(name)
    
    def create_general(self, name: str) -> Optional[General]:
        """根据名称创建武将实例（返回新的对象）"""
        # 导入创建函数
        from .generals_config import (
            create_zhang_ren, create_jinhuan_sanjie, create_lu_su
        )
        
        # 武将创建函数映射
        general_creators = {
            "zhang_ren": create_zhang_ren,
            "jinhuan_sanjie": create_jinhuan_sanjie,
            "lu_su": create_lu_su
        }
        
        creator_func = general_creators.get(name.lower())
        if creator_func:
            return creator_func()
        return None
    
    def get_generals_by_camp(self, camp: Camp) -> List[General]:
        """根据阵营获取武将列表"""
        if camp not in self._generals_by_camp:
            self._generals_by_camp[camp] = get_generals_by_camp(camp)
        return self._generals_by_camp[camp]
    
    def get_generals_by_rarity(self, rarity: Rarity) -> List[General]:
        """根据稀有度获取武将列表"""
        if rarity not in self._generals_by_rarity:
            generals = []
            for general in self.get_general_list():
                if general.rarity == rarity:
                    generals.append(general)
            self._generals_by_rarity[rarity] = generals
        return self._generals_by_rarity[rarity]
    
    def get_all_skills(self) -> Dict[str, any]:
        """获取所有技能"""
        return ALL_SKILLS
    
    def search_generals(self, **criteria) -> List[General]:
        """
        搜索武将
        
        Args:
            **criteria: 搜索条件，如 camp=Camp.SHU, rarity=Rarity.LEGENDARY 等
        
        Returns:
            符合条件的武将列表
        """
        generals = self.get_general_list()
        
        for key, value in criteria.items():
            if hasattr(General, key):
                generals = [g for g in generals if getattr(g, key) == value]
        
        return generals
    
    def get_generals_info(self) -> Dict:
        """获取武将统计信息"""
        all_generals = self.get_general_list()
        
        # 按阵营统计
        camp_counts = {}
        for camp in Camp:
            camp_counts[camp.value] = len(self.get_generals_by_camp(camp))
        
        # 按稀有度统计
        rarity_counts = {}
        for rarity in Rarity:
            rarity_counts[rarity.name] = len(self.get_generals_by_rarity(rarity))
        
        return {
            "total_generals": len(all_generals),
            "camp_distribution": camp_counts,
            "rarity_distribution": rarity_counts,
            "total_skills": len(ALL_SKILLS)
        }
    
    def print_all_generals(self):
        """打印所有武将信息"""
        print("=== 三国武将卡牌游戏 - 武将图鉴 ===\n")
        
        for camp in Camp:
            generals = self.get_generals_by_camp(camp)
            if generals:
                print(f"【{camp.value}】阵营武将:")
                for general in generals:
                    print(f"  ⭐ {general.name}")
                    print(f"     稀有度: {general.rarity.name}")
                    print(f"     费用: {general.cost}")
                    print(f"     生命: {general.max_hp}")
                    print(f"     武力: {general.force}")
                    print(f"     智力: {general.intelligence}")
                    print(f"     属性: {', '.join([attr.value for attr in general.attribute])}")
                    if general.active_skill:
                        print(f"     主动技能: {general.active_skill.name}")
                        print(f"       - {general.active_skill.description}")
                        print(f"       - 士气消耗: {general.active_skill.morale_cost}")
                        print(f"       - 冷却: {general.active_skill.cooldown}回合")
                    if general.passive_skills:
                        print(f"     被动技能: {', '.join([skill.name for skill in general.passive_skills])}")
                    print()
                print()


# 全局游戏数据管理器实例
game_data_manager = GameDataManager()

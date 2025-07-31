"""
游戏数据包初始化
"""

from .game_data_manager import game_data_manager
from .generals_config import get_all_generals, get_general_by_name, get_generals_by_camp
from .skills_config import ALL_SKILLS, get_skill_by_id
from .passive_skills_config import get_passive_skills_for_attributes

__all__ = [
    'game_data_manager',
    'get_all_generals',
    'get_general_by_name', 
    'get_generals_by_camp',
    'ALL_SKILLS',
    'get_skill_by_id',
    'get_passive_skills_for_attributes'
]

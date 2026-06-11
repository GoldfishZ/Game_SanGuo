"""
三国武将配置
从 generals_data.py 数据文件读取，自动创建所有武将实例
"""

from src.models.general import General, Camp, Rarity, Attribute
from .skills_config import get_skill_by_id
from .passive_skills_config import get_passive_skills_for_attributes
from .generals_data import GENERALS_DATA


# ==================== 数据 → 武将 映射 ====================

CAMP_MAP = {
    "魏": Camp.WEI, "蜀": Camp.SHU, "吴": Camp.WU,
    "凉": Camp.LIANG, "袁": Camp.YUAN, "他": Camp.TA,
}

RARITY_MAP = {
    "COMMON": Rarity.COMMON, "RARE": Rarity.RARE,
    "EPIC": Rarity.EPIC, "LEGENDARY": Rarity.LEGENDARY,
}

ATTR_MAP = {
    "勇猛": Attribute.BRAVERY, "魅力": Attribute.CHARISMA,
    "募兵": Attribute.RECRUIT, "防栅": Attribute.FENCE,
    "连环": Attribute.CHAIN, "复活": Attribute.REVIVE,
    "伏兵": Attribute.AMBUSH,
}


def create_general_from_data(data: dict) -> General:
    """根据数据字典创建一个武将实例"""
    attributes = [ATTR_MAP[a] for a in data.get("attributes", [])]

    general = General(
        general_id=data["id"],
        name=data["name"],
        camp=CAMP_MAP[data["camp"]],
        rarity=RARITY_MAP[data["rarity"]],
        cost=data["cost"],
        force=data["force"],
        intelligence=data["intelligence"],
        attribute=attributes,
        active_skill=get_skill_by_id(data["skill_id"]),
        image_file=data.get("image_file"),
    )
    # 根据属性自动装配被动技能
    general.passive_skills = get_passive_skills_for_attributes(general.attribute)
    return general


# ==================== 武将创建函数字典 ====================

# 懒加载：第一次使用时从数据文件创建
_cache: dict = {}

GENERAL_CREATORS = {}


def _init_creators():
    """初始化武将创建器（仅执行一次）"""
    global GENERAL_CREATORS
    if GENERAL_CREATORS:
        return
    for data in GENERALS_DATA:
        general_id = data["id"]
        # 使用英文名作为 key（方便命令行输入和引用）
        import re
        import unicodedata
        # 简单的拼音转换：用 general_id 作为唯一 key
        key = f"general_{general_id}"
        # 同时添加中文名映射
        name_key = data["name"]

        # 工厂函数（每次调用创建新实例，保证被动技能独立）
        def make_general(d=data):
            return create_general_from_data(d)

        GENERAL_CREATORS[key] = make_general
        GENERAL_CREATORS[name_key] = make_general


_init_creators()


def get_all_generals():
    """获取所有武将实例（返回新对象字典）"""
    return {data["name"]: create_general_from_data(data) for data in GENERALS_DATA}


def get_general_by_name(name: str):
    """根据中文名创建武将实例"""
    for data in GENERALS_DATA:
        if data["name"] == name:
            return create_general_from_data(data)
    return None


def get_generals_by_camp(camp: Camp):
    """根据阵营获取武将列表"""
    generals = []
    for data in GENERALS_DATA:
        if CAMP_MAP[data["camp"]] == camp:
            generals.append(create_general_from_data(data))
    return generals

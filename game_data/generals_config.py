"""
三国武将配置
定义游戏中所有可用的武将
"""

from src.models.general import General, Camp, Rarity, Attribute
from .skills_config import get_skill_by_id
from .passive_skills_config import get_passive_skills_for_attributes


# ==================== 武将创建函数 ====================

def create_zhang_ren():
    """创建张任"""
    attributes = [Attribute.AMBUSH]  # 伏兵属性
    zhang_ren = General(
        general_id=1001,
        name="张任",
        camp=Camp.TA,  # 他阵营
        rarity=Rarity.COMMON,  # 普通卡
        cost=1.5,
        force=6,
        intelligence=6,  # 最大生命 = 6+6 = 12
        attribute=attributes,
        active_skill=get_skill_by_id("strength_tactics")  # 强化战术
    )
    zhang_ren.passive_skills = get_passive_skills_for_attributes(zhang_ren.attribute)
    return zhang_ren


def create_jinhuan_sanjie():
    """创建金环三结"""
    jinhuan_sanjie = General(
        general_id=1002,
        name="金环三结",
        camp=Camp.TA,  # 他阵营
        rarity=Rarity.COMMON,  # 普通卡
        cost=1.0,
        force=3,
        intelligence=1,  # 最大生命 = 3+1 = 4
        attribute=[],  # 没有属性
        active_skill=get_skill_by_id("strength_tactics")  # 强化战术
    )
    jinhuan_sanjie.passive_skills = []
    return jinhuan_sanjie


def create_lu_su():
    """创建鲁肃"""
    attributes = [Attribute.FENCE]  # 防栅属性
    lu_su = General(
        general_id=1003,
        name="鲁肃",
        camp=Camp.WU,  # 吴阵营
        rarity=Rarity.RARE,  # 黑卡
        cost=1.5,
        force=4,
        intelligence=8,  # 最大生命 = 4+8 = 12
        attribute=attributes,
        active_skill=get_skill_by_id("alliance_pact")  # 同盟缔结
    )
    lu_su.passive_skills = get_passive_skills_for_attributes(lu_su.attribute)
    return lu_su


# ==================== 武将创建函数字典 ====================

GENERAL_CREATORS = {
    "zhang_ren": create_zhang_ren,
    "jinhuan_sanjie": create_jinhuan_sanjie,
    "lu_su": create_lu_su
}

def get_all_generals():
    """获取所有武将实例"""
    return {name: creator() for name, creator in GENERAL_CREATORS.items()}

def get_general_by_name(name: str):
    """根据名称创建武将实例"""
    creator = GENERAL_CREATORS.get(name)
    if creator:
        return creator()
    return None

def get_generals_by_camp(camp: Camp):
    """根据阵营获取武将列表"""
    generals = []
    for creator in GENERAL_CREATORS.values():
        general = creator()
        if general.camp == camp:
            generals.append(general)
    return generals

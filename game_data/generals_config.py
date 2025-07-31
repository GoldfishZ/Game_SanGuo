"""
三国武将配置
定义游戏中所有可用的武将
"""

from src.models.general import General, Camp, Rarity, Attribute
from .skills_config import get_skill_by_id
from .passive_skills_config import get_passive_skills_for_attributes


# ==================== 蜀国武将 ====================

def create_liu_bei():
    """创建刘备"""
    attributes = [Attribute.CHARISMA, Attribute.RECRUIT]
    liu_bei = General(
        general_id=1001,
        name="刘备",
        camp=Camp.SHU,
        rarity=Rarity.LEGENDARY,
        cost=3.5,
        max_hp=120,
        force=75,
        intelligence=85,
        attribute=attributes,
        active_skill=get_skill_by_id("rende"),
        passive_skills=get_passive_skills_for_attributes(attributes)
    )
    return liu_bei

def create_guan_yu():
    """创建关羽"""
    attributes = [Attribute.BRAVERY, Attribute.CHARISMA]
    guan_yu = General(
        general_id=1002,
        name="关羽",
        camp=Camp.SHU,
        rarity=Rarity.EPIC,
        cost=3.0,
        max_hp=100,
        force=95,
        intelligence=75,
        attribute=attributes,
        active_skill=get_skill_by_id("qinglong_yanyue"),
        passive_skills=get_passive_skills_for_attributes(attributes)
    )
    return guan_yu

def create_zhang_fei():
    """创建张飞"""
    attributes = [Attribute.BRAVERY, Attribute.FENCE]
    zhang_fei = General(
        general_id=1003,
        name="张飞",
        camp=Camp.SHU,
        rarity=Rarity.EPIC,
        cost=2.5,
        max_hp=110,
        force=90,
        intelligence=60,
        attribute=attributes,
        active_skill=get_skill_by_id("paoxiao"),
        passive_skills=get_passive_skills_for_attributes(attributes)
    )
    return zhang_fei

def create_zhuge_liang():
    """创建诸葛亮"""
    attributes = [Attribute.CHARISMA, Attribute.AMBUSH]
    zhuge_liang = General(
        general_id=1004,
        name="诸葛亮",
        camp=Camp.SHU,
        rarity=Rarity.LEGENDARY,
        cost=3.5,
        max_hp=80,
        force=45,
        intelligence=100,
        attribute=attributes,
        active_skill=get_skill_by_id("bagua_zhen"),
        passive_skills=get_passive_skills_for_attributes(attributes)
    )
    return zhuge_liang

def create_zhao_yun():
    """创建赵云"""
    attributes = [Attribute.BRAVERY, Attribute.REVIVE]
    zhao_yun = General(
        general_id=1005,
        name="赵云",
        camp=Camp.SHU,
        rarity=Rarity.EPIC,
        cost=2.5,
        max_hp=95,
        force=88,
        intelligence=78,
        attribute=attributes,
        active_skill=get_skill_by_id("longdan"),
        passive_skills=get_passive_skills_for_attributes(attributes)
    )
    return zhao_yun

# ==================== 魏国武将 ====================

def create_cao_cao():
    """创建曹操"""
    attributes = [Attribute.CHARISMA, Attribute.RECRUIT, Attribute.AMBUSH]
    cao_cao = General(
        general_id=2001,
        name="曹操",
        camp=Camp.WEI,
        rarity=Rarity.LEGENDARY,
        cost=4.0,
        max_hp=115,
        force=80,
        intelligence=95,
        attribute=attributes,
        active_skill=get_skill_by_id("jianxiong"),
        passive_skills=get_passive_skills_for_attributes(attributes)
    )
    return cao_cao

def create_xiahou_dun():
    """创建夏侯惇"""
    attributes = [Attribute.BRAVERY, Attribute.REVIVE]
    xiahou_dun = General(
        general_id=2002,
        name="夏侯惇",
        camp=Camp.WEI,
        rarity=Rarity.RARE,
        cost=2.0,
        max_hp=95,
        force=88,
        intelligence=65,
        attribute=attributes,
        active_skill=get_skill_by_id("bashi_danqing"),
        passive_skills=get_passive_skills_for_attributes(attributes)
    )
    return xiahou_dun

def create_xu_chu():
    """创建许褚"""
    attributes = [Attribute.BRAVERY, Attribute.FENCE]
    xu_chu = General(
        general_id=2003,
        name="许褚",
        camp=Camp.WEI,
        rarity=Rarity.RARE,
        cost=2.0,
        max_hp=105,
        force=92,
        intelligence=55,
        attribute=attributes,
        active_skill=get_skill_by_id("luoyi_zhan"),
        passive_skills=get_passive_skills_for_attributes(attributes)
    )
    return xu_chu

def create_sima_yi():
    """创建司马懿"""
    attributes = [Attribute.AMBUSH, Attribute.CHARISMA]
    sima_yi = General(
        general_id=2004,
        name="司马懿",
        camp=Camp.WEI,
        rarity=Rarity.LEGENDARY,
        cost=3.5,
        max_hp=85,
        force=60,
        intelligence=98,
        attribute=attributes,
        active_skill=get_skill_by_id("yingshi_langgu"),
        passive_skills=get_passive_skills_for_attributes(attributes)
    )
    return sima_yi

# ==================== 吴国武将 ====================

def create_sun_quan():
    """创建孙权"""
    attributes = [Attribute.CHARISMA, Attribute.RECRUIT]
    sun_quan = General(
        general_id=3001,
        name="孙权",
        camp=Camp.WU,
        rarity=Rarity.LEGENDARY,
        cost=3.0,
        max_hp=110,
        force=70,
        intelligence=85,
        attribute=attributes,
        active_skill=get_skill_by_id("zhiheng"),
        passive_skills=get_passive_skills_for_attributes(attributes)
    )
    return sun_quan

def create_zhou_yu():
    """创建周瑜"""
    attributes = [Attribute.CHARISMA, Attribute.CHAIN]
    zhou_yu = General(
        general_id=3002,
        name="周瑜",
        camp=Camp.WU,
        rarity=Rarity.EPIC,
        cost=3.0,
        max_hp=85,
        force=75,
        intelligence=95,
        attribute=attributes,
        active_skill=get_skill_by_id("chibi_huoji"),
        passive_skills=get_passive_skills_for_attributes(attributes)
    )
    return zhou_yu

def create_gan_ning():
    """创建甘宁"""
    attributes = [Attribute.BRAVERY, Attribute.AMBUSH]
    gan_ning = General(
        general_id=3003,
        name="甘宁",
        camp=Camp.WU,
        rarity=Rarity.RARE,
        cost=2.0,
        max_hp=90,
        force=85,
        intelligence=70,
        attribute=attributes,
        active_skill=get_skill_by_id("qixi"),
        passive_skills=get_passive_skills_for_attributes(attributes)
    )
    return gan_ning

# ==================== 群雄武将 ====================

def create_lu_bu():
    """创建吕布"""
    attributes = [Attribute.BRAVERY, Attribute.CHAIN]
    lu_bu = General(
        general_id=4001,
        name="吕布",
        camp=Camp.TA,
        rarity=Rarity.LEGENDARY,
        cost=4.5,
        max_hp=105,
        force=100,
        intelligence=50,
        attribute=attributes,
        active_skill=get_skill_by_id("wushuang"),
        passive_skills=get_passive_skills_for_attributes(attributes)
    )
    return lu_bu

def create_dong_zhuo():
    """创建董卓"""
    attributes = [Attribute.RECRUIT, Attribute.FENCE]
    dong_zhuo = General(
        general_id=4002,
        name="董卓",
        camp=Camp.TA,
        rarity=Rarity.EPIC,
        cost=3.0,
        force=65,
        intelligence=75,  # 最大生命 = 65+75 = 140
        attribute=attributes,
        active_skill=get_skill_by_id("eli")
    )
    dong_zhuo.passive_skills = get_passive_skills_for_attributes(attributes)
    return dong_zhuo


# ==================== 新增武将 ====================

def create_zhang_ren():
    """创建张任"""
    attributes = [Attribute.AMBUSH]  # 伏兵属性
    zhang_ren = General(
        general_id=2001,
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
        general_id=2002,
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
        general_id=2003,
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
    # 蜀国武将
    "liu_bei": create_liu_bei,
    "guan_yu": create_guan_yu,
    "zhang_fei": create_zhang_fei,
    "zhuge_liang": create_zhuge_liang,
    "zhao_yun": create_zhao_yun,
    
    # 魏国武将
    "cao_cao": create_cao_cao,
    "xiahou_dun": create_xiahou_dun,
    "xu_chu": create_xu_chu,
    "sima_yi": create_sima_yi,
    
    # 吴国武将
    "sun_quan": create_sun_quan,
    "zhou_yu": create_zhou_yu,
    "gan_ning": create_gan_ning,
    
    # 群雄武将
    "lu_bu": create_lu_bu,
    "dong_zhuo": create_dong_zhuo,
    
    # 新增武将
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

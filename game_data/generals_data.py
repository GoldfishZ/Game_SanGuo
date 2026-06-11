"""
武将数据库 —— 唯一的武将数据源
修改武将数值、添加新武将都在这个文件中操作，无需改动任何其他文件

字段说明：
  id          武将唯一ID
  name        中文名
  camp        阵营: 蜀/魏/吴/他
  rarity      稀有度: COMMON/RARE/EPIC/LEGENDARY（对应费用: 1.0/1.5/2.0/3.0）
  cost        费用
  force       武力 (影响普攻伤害)
  intelligence 智力 (影响策略伤害)
  attributes  属性列表: 勇猛/魅力/募兵/防栅/连环/复活/伏兵 (空列表=无属性)
  skill_id    主动技能ID (skills_config.py 中定义)
  image_file  武将卡图片文件名 (存放在 assets/images/generals/)
"""

GENERALS_DATA = [
    # ==================== 蜀 ====================
    {
        "id": 2001,
        "name": "刘备",
        "camp": "蜀",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 5,
        "intelligence": 7,
        "attributes": ["魅力"],
        "skill_id": "rally",
        "image_file": "liu_bei.png",
    },
    {
        "id": 2002,
        "name": "关羽",
        "camp": "蜀",
        "rarity": "EPIC",
        "cost": 2.0,
        "force": 9,
        "intelligence": 5,
        "attributes": ["勇猛"],
        "skill_id": "fierce_attack",
        "image_file": "guan_yu.png",
    },
    {
        "id": 2003,
        "name": "张飞",
        "camp": "蜀",
        "rarity": "EPIC",
        "cost": 2.0,
        "force": 10,
        "intelligence": 3,
        "attributes": ["勇猛"],
        "skill_id": "fierce_attack",
        "image_file": "zhang_fei.png",
    },
    {
        "id": 2004,
        "name": "赵云",
        "camp": "蜀",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 8,
        "intelligence": 6,
        "attributes": ["伏兵"],
        "skill_id": "strength_tactics",
        "image_file": "zhao_yun.png",
    },
    {
        "id": 2005,
        "name": "诸葛亮",
        "camp": "蜀",
        "rarity": "LEGENDARY",
        "cost": 3.0,
        "force": 3,
        "intelligence": 10,
        "attributes": ["连环"],
        "skill_id": "fire_attack",
        "image_file": "zhuge_liang.png",
    },

    # ==================== 魏 ====================
    {
        "id": 3001,
        "name": "曹操",
        "camp": "魏",
        "rarity": "LEGENDARY",
        "cost": 3.0,
        "force": 7,
        "intelligence": 9,
        "attributes": ["魅力"],
        "skill_id": "rally",
        "image_file": "cao_cao.png",
    },
    {
        "id": 3002,
        "name": "夏侯惇",
        "camp": "魏",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 8,
        "intelligence": 5,
        "attributes": ["勇猛"],
        "skill_id": "strength_tactics",
        "image_file": "xiahou_dun.png",
    },
    {
        "id": 3003,
        "name": "张辽",
        "camp": "魏",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 8,
        "intelligence": 7,
        "attributes": ["募兵"],
        "skill_id": "fierce_attack",
        "image_file": "zhang_liao.png",
    },
    {
        "id": 3004,
        "name": "司马懿",
        "camp": "魏",
        "rarity": "EPIC",
        "cost": 2.0,
        "force": 4,
        "intelligence": 9,
        "attributes": ["伏兵"],
        "skill_id": "intimidate",
        "image_file": "sima_yi.png",
    },

    # ==================== 吴 ====================
    {
        "id": 4001,
        "name": "孙坚",
        "camp": "吴",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 7,
        "intelligence": 6,
        "attributes": ["复活"],
        "skill_id": "strength_tactics",
        "image_file": "sun_jian.png",
    },
    {
        "id": 4002,
        "name": "周瑜",
        "camp": "吴",
        "rarity": "EPIC",
        "cost": 2.0,
        "force": 5,
        "intelligence": 9,
        "attributes": ["连环"],
        "skill_id": "fire_attack",
        "image_file": "zhou_yu.png",
    },
    {
        "id": 4003,
        "name": "甘宁",
        "camp": "吴",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 9,
        "intelligence": 4,
        "attributes": ["募兵"],
        "skill_id": "fierce_attack",
        "image_file": "gan_ning.png",
    },

    # ==================== 他 ====================
    {
        "id": 1001,
        "name": "张任",
        "camp": "他",
        "rarity": "COMMON",
        "cost": 1.0,
        "force": 6,
        "intelligence": 6,
        "attributes": ["伏兵"],
        "skill_id": "strength_tactics",
        "image_file": "zhang_ren.png",
    },
    {
        "id": 5001,
        "name": "吕布",
        "camp": "他",
        "rarity": "LEGENDARY",
        "cost": 3.0,
        "force": 10,
        "intelligence": 2,
        "attributes": ["勇猛"],
        "skill_id": "fierce_attack",
        "image_file": "lv_bu.png",
    },
    {
        "id": 1003,
        "name": "鲁肃",
        "camp": "吴",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 4,
        "intelligence": 8,
        "attributes": ["防栅"],
        "skill_id": "alliance_pact",
        "image_file": "lu_su.png",
    },
]

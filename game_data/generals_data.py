"""
武将数据库 —— 唯一的武将数据源
修改武将数值、添加新武将都在这个文件中操作，无需改动任何其他文件

字段说明：
  id          武将唯一ID
  name        中文名
  camp        阵营: 蜀/魏/吴/凉/袁/他
  rarity      稀有度: COMMON/RARE/EPIC/LEGENDARY（对应费用: 1.0/1.5/2.0/3.0）
  cost        费用
  force       武力 (影响普攻伤害)
  intelligence 智力 (影响策略伤害)
  attributes  属性列表: 勇猛/魅力/募兵/防栅/连计/复活/伏兵 (空列表=无属性)
  skill_id    主动技能ID (skills_config.py 中定义)
  image_file  武将卡图片文件名 (存放在 assets/images/generals/)
"""

GENERALS_DATA = [
    # ==================== 蜀 ====================
    {
        "id": 2003,
        "name": "张飞",
        "camp": "蜀",
        "rarity": "EPIC",
        "cost": 2.0,
        "force": 8,
        "intelligence": 4,
        "attributes": ["勇猛"],
        "skill_id": "spear_wheel_tactics",
        "image_file": "zhang_fei.png"
    },
    {
        "id": 2005,
        "name": "诸葛亮",
        "camp": "蜀",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 3,
        "intelligence": 10,
        "attributes": ["防栅"],
        "skill_id": "stone_sentinel_maze",
        "image_file": "zhuge_liang.png"
    },
    {
        "id": 2006,
        "name": "夏侯月姬",
        "camp": "蜀",
        "rarity": "COMMON",
        "cost": 1.0,
        "force": 2,
        "intelligence": 7,
        "attributes": ["魅力"],
        "skill_id": "thunder_strike",
        "image_file": "xiahou_yueji.png"
    },
    {
        "id": 2007,
        "name": "周仓",
        "camp": "蜀",
        "rarity": "COMMON",
        "cost": 1.0,
        "force": 4,
        "intelligence": 1,
        "attributes": ["勇猛"],
        "skill_id": "strength_tactics",
        "image_file": "zhou_cang.png"
    },
    {
        "id": 2008,
        "name": "马岱",
        "camp": "蜀",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 5,
        "intelligence": 7,
        "attributes": ["伏兵"],
        "skill_id": "steadfast",
        "image_file": "ma_dai.png"
    },
    {
        "id": 2009,
        "name": "姜维",
        "camp": "蜀",
        "rarity": "EPIC",
        "cost": 2.0,
        "force": 7,
        "intelligence": 7,
        "attributes": ["募兵"],
        "skill_id": "taunt",
        "image_file": "jiang_wei.png"
    },

    # ==================== 魏 ====================
    {
        "id": 3001,
        "name": "曹操",
        "camp": "魏",
        "rarity": "EPIC",
        "cost": 2.0,
        "force": 7,
        "intelligence": 9,
        "attributes": ["魅力"],
        "skill_id": "siege_all_army",
        "image_file": "cao_cao.png"
    },
    {
        "id": 3002,
        "name": "夏侯惇",
        "camp": "魏",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 8,
        "intelligence": 6,
        "attributes": ["勇猛"],
        "skill_id": "wei_king_guard",
        "image_file": "xiahou_dun.png"
    },
    {
        "id": 3003,
        "name": "张辽",
        "camp": "凉",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 7,
        "intelligence": 6,
        "attributes": ["连计"],
        "skill_id": "cavalry_unity",
        "image_file": "zhang_liao.png"
    },
    {
        "id": 3005,
        "name": "曹仁",
        "camp": "魏",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 5,
        "intelligence": 6,
        "attributes": [],
        "skill_id": "momentary_order",
        "image_file": "cao_ren.png"
    },
    {
        "id": 3006,
        "name": "贾诩",
        "camp": "魏",
        "rarity": "COMMON",
        "cost": 1.0,
        "force": 1,
        "intelligence": 9,
        "attributes": [],
        "skill_id": "discord_strategy",
        "image_file": "jia_xu.png"
    },
    {
        "id": 3007,
        "name": "王异",
        "camp": "魏",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 4,
        "intelligence": 8,
        "attributes": ["魅力", "防栅"],
        "skill_id": "tooth_for_tooth",
        "image_file": "wang_yi.png"
    },
    {
        "id": 3008,
        "name": "许褚",
        "camp": "魏",
        "rarity": "EPIC",
        "cost": 2.0,
        "force": 8,
        "intelligence": 2,
        "attributes": ["募兵"],
        "skill_id": "guard_tactics",
        "image_file": "xu_chu.png"
    },
    {
        "id": 3009,
        "name": "夏侯渊",
        "camp": "魏",
        "rarity": "EPIC",
        "cost": 2.0,
        "force": 8,
        "intelligence": 4,
        "attributes": ["募兵"],
        "skill_id": "divine_speed_tactics",
        "image_file": "xiahou_yuan.png"
    },
    {
        "id": 3010,
        "name": "郭皇后",
        "camp": "魏",
        "rarity": "COMMON",
        "cost": 1.0,
        "force": 2,
        "intelligence": 7,
        "attributes": ["魅力"],
        "skill_id": "weakening_chain",
        "image_file": "guo_huanghou.png"
    },
    {
        "id": 3011,
        "name": "蔡文姬",
        "camp": "魏",
        "rarity": "COMMON",
        "cost": 1.0,
        "force": 1,
        "intelligence": 7,
        "attributes": ["魅力"],
        "skill_id": "flying_dance",
        "image_file": "cai_wenji.png"
    },
    {
        "id": 3012,
        "name": "于禁",
        "camp": "魏",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 5,
        "intelligence": 6,
        "attributes": ["连计"],
        "skill_id": "wei_elite",
        "image_file": "yu_jin.png"
    },

    # ==================== 吴 ====================
    {
        "id": 4003,
        "name": "甘宁",
        "camp": "吴",
        "rarity": "EPIC",
        "cost": 2.5,
        "force": 8,
        "intelligence": 6,
        "attributes": ["勇猛"],
        "skill_id": "strength_tactics",
        "image_file": "gan_ning.png"
    },
    {
        "id": 4004,
        "name": "大乔",
        "camp": "吴",
        "rarity": "COMMON",
        "cost": 1.0,
        "force": 2,
        "intelligence": 4,
        "attributes": ["募兵", "魅力"],
        "skill_id": "jiangdong_beauty",
        "image_file": "da_qiao.png"
    },
    {
        "id": 4005,
        "name": "太史慈",
        "camp": "吴",
        "rarity": "EPIC",
        "cost": 2.0,
        "force": 8,
        "intelligence": 4,
        "attributes": [],
        "skill_id": "flawless",
        "image_file": "taishi_ci.png"
    },
    {
        "id": 4006,
        "name": "朱然",
        "camp": "吴",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 4,
        "intelligence": 6,
        "attributes": ["防栅", "募兵"],
        "skill_id": "fence_rebuild",
        "image_file": "zhu_ran.png"
    },
    {
        "id": 4007,
        "name": "小乔",
        "camp": "吴",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 2,
        "intelligence": 5,
        "attributes": ["防栅", "魅力"],
        "skill_id": "meteor_rite",
        "image_file": "xiao_qiao.png"
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
        "image_file": "zhang_ren.png"
    },
    {
        "id": 1004,
        "name": "汉献帝",
        "camp": "他",
        "rarity": "COMMON",
        "cost": 1.0,
        "force": 1,
        "intelligence": 5,
        "attributes": ["魅力", "防栅"],
        "skill_id": "imperial_edict",
        "image_file": "han_xian_di.png"
    },
    {
        "id": 1005,
        "name": "司马徽",
        "camp": "他",
        "rarity": "COMMON",
        "cost": 1.0,
        "force": 1,
        "intelligence": 8,
        "attributes": ["防栅", "募兵"],
        "skill_id": "master_teaching",
        "image_file": "sima_hui.png"
    },
    {
        "id": 1006,
        "name": "张角",
        "camp": "他",
        "rarity": "COMMON",
        "cost": 1.0,
        "force": 2,
        "intelligence": 8,
        "attributes": ["魅力"],
        "skill_id": "taiping_arts",
        "image_file": "zhang_jiao.png"
    },
    {
        "id": 1007,
        "name": "皇甫嵩",
        "camp": "他",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 5,
        "intelligence": 5,
        "attributes": ["募兵"],
        "skill_id": "bandit_suppression_order",
        "image_file": "huangfu_song.png"
    },
    {
        "id": 1008,
        "name": "公孙瓒",
        "camp": "他",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 5,
        "intelligence": 5,
        "attributes": ["魅力", "募兵"],
        "skill_id": "white_horse_formation",
        "image_file": "gong_sun_zan.png"
    },
    {
        "id": 1009,
        "name": "带来洞主",
        "camp": "他",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 5,
        "intelligence": 3,
        "attributes": ["复活"],
        "skill_id": "knockback_tactics",
        "image_file": "dailai_dongzhu.png"
    },
    {
        "id": 1010,
        "name": "王允",
        "camp": "他",
        "rarity": "COMMON",
        "cost": 1.0,
        "force": 2,
        "intelligence": 8,
        "attributes": [],
        "skill_id": "small_chain_plot",
        "image_file": "wang_yun.png"
    },
    {
        "id": 5001,
        "name": "吕布",
        "camp": "凉",
        "rarity": "LEGENDARY",
        "cost": 3.0,
        "force": 10,
        "intelligence": 1,
        "attributes": ["勇猛"],
        "skill_id": "peerless_under_heaven",
        "image_file": "lv_bu.png"
    },
    {
        "id": 5002,
        "name": "董卓",
        "camp": "凉",
        "rarity": "EPIC",
        "cost": 2.5,
        "force": 8,
        "intelligence": 7,
        "attributes": ["魅力"],
        "skill_id": "grand_cavalry_order",
        "image_file": "dong_zhuo.png"
    },
    {
        "id": 5003,
        "name": "陈宫",
        "camp": "凉",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 4,
        "intelligence": 7,
        "attributes": ["防栅"],
        "skill_id": "destructive_advice",
        "image_file": "chen_gong.png"
    },
    {
        "id": 5004,
        "name": "邹氏",
        "camp": "凉",
        "rarity": "COMMON",
        "cost": 1.0,
        "force": 2,
        "intelligence": 7,
        "attributes": ["伏兵", "魅力"],
        "skill_id": "corrupt_dance",
        "image_file": "zou_shi.png"
    },
    {
        "id": 5005,
        "name": "李傕和郭汜",
        "camp": "凉",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 6,
        "intelligence": 3,
        "attributes": [],
        "skill_id": "vile_raid",
        "image_file": "li_jue_guo_si.png"
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
        "image_file": "lu_su.png"
    },

    # ==================== 袁 ====================
    {
        "id": 6001,
        "name": "田丰",
        "camp": "袁",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 4,
        "intelligence": 9,
        "attributes": ["伏兵"],
        "skill_id": "meticulous_offense",
        "image_file": "tian_feng.png"
    },
    {
        "id": 6002,
        "name": "于夫罗",
        "camp": "袁",
        "rarity": "COMMON",
        "cost": 1.0,
        "force": 3,
        "intelligence": 3,
        "attributes": ["连计"],
        "skill_id": "united_siege",
        "image_file": "yu_fuluo.png"
    },
    {
        "id": 6003,
        "name": "张郃",
        "camp": "袁",
        "rarity": "RARE",
        "cost": 1.5,
        "force": 6,
        "intelligence": 5,
        "attributes": [],
        "skill_id": "first_merit",
        "image_file": "zhang_he.png"
    },
    {
        "id": 6004,
        "name": "文丑",
        "camp": "袁",
        "rarity": "EPIC",
        "cost": 2.0,
        "force": 8,
        "intelligence": 3,
        "attributes": ["勇猛"],
        "skill_id": "high_morale",
        "image_file": "wen_chou.png"
    },
]

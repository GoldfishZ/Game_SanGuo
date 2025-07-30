"""
三国武将数据
包含武将的基本信息和技能配置
"""

from typing import Dict, List, Any
from ..models.general import Camp, Rarity


# 武将数据配置
GENERALS_DATA: Dict[int, Dict[str, Any]] = {
    # 蜀国武将
    1: {
        "name": "刘备",
        "camp": Camp.SHU,
        "rarity": Rarity.LEGENDARY,
        "max_hp": 120,
        "attack": 80,
        "defense": 70,
        "speed": 60,
        "skills": ["仁德", "激励", "桃园结义"],
        "description": "蜀汉皇帝，仁德之君，擅长团队协作和治疗技能"
    },
    2: {
        "name": "关羽",
        "camp": Camp.SHU,
        "rarity": Rarity.EPIC,
        "max_hp": 100,
        "attack": 95,
        "defense": 80,
        "speed": 70,
        "skills": ["青龙偃月", "义薄云天", "单骑救主"],
        "description": "武圣关羽，忠义无双，拥有强大的单体攻击能力"
    },
    3: {
        "name": "张飞",
        "camp": Camp.SHU,
        "rarity": Rarity.EPIC,
        "max_hp": 110,
        "attack": 90,
        "defense": 85,
        "speed": 65,
        "skills": ["咆哮", "猛攻", "长坂坡"],
        "description": "燕人张飞，勇猛无畏，擅长范围攻击和震慑敌人"
    },
    4: {
        "name": "诸葛亮",
        "camp": Camp.SHU,
        "rarity": Rarity.LEGENDARY,
        "max_hp": 80,
        "attack": 60,
        "defense": 50,
        "speed": 90,
        "skills": ["八卦阵", "火计", "空城计", "七星灯"],
        "description": "卧龙先生，智谋超群，拥有多种策略技能和辅助能力"
    },
    5: {
        "name": "赵云",
        "camp": Camp.SHU,
        "rarity": Rarity.EPIC,
        "max_hp": 95,
        "attack": 88,
        "defense": 78,
        "speed": 85,
        "skills": ["龙胆", "冲锋", "救主"],
        "description": "常山赵子龙，胆识过人，攻守兼备的全能武将"
    },
    
    # 魏国武将
    101: {
        "name": "曹操",
        "camp": Camp.WEI,
        "rarity": Rarity.LEGENDARY,
        "max_hp": 115,
        "attack": 85,
        "defense": 75,
        "speed": 80,
        "skills": ["奸雄", "挟天子", "望梅止渴"],
        "description": "魏武帝曹操，治世之能臣，乱世之奸雄"
    },
    102: {
        "name": "夏侯惇",
        "camp": Camp.WEI,
        "rarity": Rarity.RARE,
        "max_hp": 95,
        "attack": 88,
        "defense": 82,
        "speed": 68,
        "skills": ["拔矢啖睛", "猛攻", "忠勇"],
        "description": "曹操麾下猛将，忠勇无双，越战越勇"
    },
    103: {
        "name": "许褚",
        "camp": Camp.WEI,
        "rarity": Rarity.RARE,
        "max_hp": 105,
        "attack": 92,
        "defense": 88,
        "speed": 55,
        "skills": ["裸衣战马超", "虎痴", "护主"],
        "description": "虎痴许褚，力大无穷，曹操的贴身护卫"
    },
    104: {
        "name": "司马懿",
        "camp": Camp.WEI,
        "rarity": Rarity.LEGENDARY,
        "max_hp": 85,
        "attack": 65,
        "defense": 60,
        "speed": 95,
        "skills": ["鹰视狼顾", "反间", "忍耐", "篡权"],
        "description": "司马仲达，深谋远虑，善于隐忍和策反"
    },
    
    # 吴国武将
    201: {
        "name": "孙权",
        "camp": Camp.WU,
        "rarity": Rarity.LEGENDARY,
        "max_hp": 110,
        "attack": 75,
        "defense": 80,
        "speed": 75,
        "skills": ["制衡", "救援", "江东基业"],
        "description": "吴大帝孙权，善于平衡和统筹，江东之主"
    },
    202: {
        "name": "周瑜",
        "camp": Camp.WU,
        "rarity": Rarity.EPIC,
        "max_hp": 85,
        "attack": 70,
        "defense": 65,
        "speed": 88,
        "skills": ["反间", "火攻", "英姿", "赤壁"],
        "description": "美周郎，雄姿英发，火烧赤壁的英雄"
    },
    203: {
        "name": "甘宁",
        "camp": Camp.WU,
        "rarity": Rarity.RARE,
        "max_hp": 90,
        "attack": 90,
        "defense": 70,
        "speed": 80,
        "skills": ["奇袭", "锦帆贼", "勇猛"],
        "description": "锦帆贼甘宁，勇猛果敢，善于奇袭"
    },
    
    # 群雄武将
    301: {
        "name": "吕布",
        "camp": Camp.QUN,
        "rarity": Rarity.LEGENDARY,
        "max_hp": 105,
        "attack": 105,
        "defense": 75,
        "speed": 88,
        "skills": ["无双", "方天画戟", "辕门射戟"],
        "description": "飞将吕布，武力无双，人中吕布马中赤兔"
    },
    302: {
        "name": "董卓",
        "camp": Camp.QUN,
        "rarity": Rarity.EPIC,
        "max_hp": 120,
        "attack": 70,
        "defense": 85,
        "speed": 45,
        "skills": ["酒池肉林", "恶逆", "威压"],
        "description": "西凉董卓，残暴专横，拥有强大的压制能力"
    },
    303: {
        "name": "袁绍",
        "camp": Camp.QUN,
        "rarity": Rarity.RARE,
        "max_hp": 100,
        "attack": 75,
        "defense": 70,
        "speed": 65,
        "skills": ["血裔", "召集", "四世三公"],
        "description": "四世三公袁本初，出身名门，善于召集援军"
    }
}

# 技能数据配置
SKILLS_DATA: Dict[str, Dict[str, Any]] = {
    # 攻击技能
    "青龙偃月": {
        "type": "attack",
        "description": "关羽的招牌技能，对敌人造成150%攻击力伤害",
        "damage_multiplier": 1.5,
        "target_type": "single_enemy",
        "cooldown": 2,
        "energy_cost": 3
    },
    "咆哮": {
        "type": "attack",
        "description": "张飞怒吼，对前排所有敌人造成120%攻击力伤害",
        "damage_multiplier": 1.2,
        "target_type": "front_row",
        "cooldown": 1,
        "energy_cost": 2
    },
    "猛攻": {
        "type": "attack",
        "description": "普通的强力攻击，造成130%攻击力伤害",
        "damage_multiplier": 1.3,
        "target_type": "single_enemy",
        "cooldown": 1,
        "energy_cost": 2
    },
    "方天画戟": {
        "type": "attack",
        "description": "吕布的无双攻击，对敌方全体造成110%攻击力伤害",
        "damage_multiplier": 1.1,
        "target_type": "all_enemies",
        "cooldown": 3,
        "energy_cost": 4
    },
    
    # 治疗技能
    "仁德": {
        "type": "heal",
        "description": "刘备的仁德之心，为友军恢复生命值",
        "heal_amount": 30,
        "target_type": "single_ally",
        "cooldown": 2,
        "energy_cost": 2
    },
    "救援": {
        "type": "heal",
        "description": "为生命值最低的友军恢复大量生命值",
        "heal_amount": 50,
        "target_type": "single_ally",
        "cooldown": 3,
        "energy_cost": 3
    },
    
    # 增益技能
    "激励": {
        "type": "buff",
        "description": "激励友军，提升攻击力",
        "buff_type": "attack_boost",
        "buff_value": 20,
        "duration": 3,
        "target_type": "all_allies",
        "cooldown": 4,
        "energy_cost": 3
    },
    "义薄云天": {
        "type": "buff",
        "description": "关羽的忠义激励队友，提升防御力",
        "buff_type": "defense_boost",
        "buff_value": 25,
        "duration": 2,
        "target_type": "all_allies",
        "cooldown": 3,
        "energy_cost": 2
    },
    "英姿": {
        "type": "buff",
        "description": "周瑜的英姿飒爽，提升全队速度",
        "buff_type": "speed_boost",
        "buff_value": 15,
        "duration": 4,
        "target_type": "all_allies",
        "cooldown": 4,
        "energy_cost": 3
    },
    
    # 特殊技能
    "火计": {
        "type": "special",
        "description": "诸葛亮的火计，对敌方全体造成持续伤害",
        "effect": "burn",
        "damage_per_turn": 20,
        "duration": 3,
        "target_type": "all_enemies",
        "cooldown": 5,
        "energy_cost": 4
    },
    "空城计": {
        "type": "special",
        "description": "诸葛亮的空城计，免疫下次攻击",
        "effect": "immunity",
        "duration": 1,
        "target_type": "self",
        "cooldown": 6,
        "energy_cost": 3
    },
    "反间": {
        "type": "special",
        "description": "离间敌人，使其攻击自己人",
        "effect": "confusion",
        "duration": 2,
        "target_type": "single_enemy",
        "cooldown": 4,
        "energy_cost": 3
    }
}

# 阵型数据配置
FORMATION_DATA: Dict[str, Dict[str, Any]] = {
    "锋矢阵": {
        "description": "前锋突出的攻击阵型，提升前排攻击力",
        "type": "offensive",
        "bonuses": {
            "front_attack": 1.3,
            "middle_attack": 1.1,
            "back_attack": 1.0,
            "front_defense": 0.9,
            "middle_defense": 1.0,
            "back_defense": 1.1
        }
    },
    "鱼鳞阵": {
        "description": "层层递进的防御阵型，提升整体防御力",
        "type": "defensive",
        "bonuses": {
            "front_defense": 1.4,
            "middle_defense": 1.2,
            "back_defense": 1.1,
            "front_attack": 0.8,
            "middle_attack": 0.9,
            "back_attack": 1.0
        }
    },
    "雁行阵": {
        "description": "灵活机动的速度阵型，提升行动速度",
        "type": "speed",
        "bonuses": {
            "front_speed": 1.3,
            "middle_speed": 1.4,
            "back_speed": 1.2,
            "front_defense": 0.8,
            "middle_defense": 0.7,
            "back_defense": 0.9
        }
    },
    "方圆阵": {
        "description": "攻守兼备的均衡阵型，全面小幅提升",
        "type": "balanced",
        "bonuses": {
            "all_attack": 1.1,
            "all_defense": 1.1,
            "all_speed": 1.1
        }
    },
    "八卦阵": {
        "description": "诸葛亮的神秘阵法，随机给予强大效果",
        "type": "special",
        "bonuses": {
            "random_effect": True,
            "effect_power": 1.5
        }
    }
}

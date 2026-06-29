"""
技能配置文件
包含游戏中需要的所有主动技能定义
"""

from src.models.general import odd_even_judgment
from src.skills.skill_base import DamageSkill, EnhanceWeakenSkill, Skill, SkillType, TargetType


class SiegeRowSkill(Skill):
    """全军攻城：强化曹操所在行的己方武将。"""

    def __init__(self):
        super().__init__(
            skill_id="siege_all_army",
            name="全军攻城",
            description="我方与曹操同一排的武将武力+3，本回合普攻无视栅栏防御，但只能攻击正前方武将",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SELF,
            cooldown=0,
            morale_cost=6,
        )
        self.effect_value = 3
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到曹操所属队伍",
                "details": [],
            }

        caster_position = team.get_general_position(caster)
        if caster_position is None:
            affected_generals = [caster]
            row = None
        else:
            row, _ = caster_position
            affected_generals = [
                general for general in team.generals
                if general.is_alive and team.get_general_position(general)
                and team.get_general_position(general)[0] == row
            ]

        details = []
        for general in affected_generals:
            general.add_buff("force_boost", self.effect_value, self.duration)
            general.add_buff("ignore_fence", 1, self.duration)
            general.add_buff("front_only_attack", 1, self.duration)
            details.append({
                "target": general.name,
                "row": row,
                "effect": "武力+3，无视栅栏，只能攻击正前方",
                "duration": self.duration,
            })

        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": len(details),
            "details": details,
        }


class StoneSentinelMazeSkill(Skill):
    """石兵八阵：临时重排敌方 2x2 方格内的武将。"""

    def __init__(self):
        super().__init__(
            skill_id="stone_sentinel_maze",
            name="石兵八阵",
            description="一回合内任意排列敌方2x2方格内的武将，回合结束后返回原位",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SELF,
            cooldown=0,
            morale_cost=4,
        )

    def execute(self, caster, targets, battle_context):
        caster_team = battle_context.get_team_for_general(caster)
        if caster_team is None:
            return {
                "success": False,
                "type": "formation",
                "message": "无法找到诸葛亮所属队伍",
                "details": [],
            }

        enemy_team = (
            battle_context.team2
            if caster_team == battle_context.team1
            else battle_context.team1
        )
        result = enemy_team.apply_temporary_2x2_rearrangement()
        if not result.get("success"):
            return {
                "success": False,
                "type": "formation",
                "message": result.get("message", "石兵八阵发动失败"),
                "details": [],
            }

        return {
            "success": True,
            "type": "formation",
            "targets_affected": len(result["moves"]),
            "details": [{
                "target": move["general"],
                "from": move["from"],
                "to": move["to"],
            } for move in result["moves"]],
        }


class PeerlessUnderHeavenSkill(Skill):
    """天下无双：吕布进入鬼神般的爆发状态。"""

    def __init__(self):
        super().__init__(
            skill_id="peerless_under_heaven",
            name="天下无双",
            description="自身武力+6，持续3回合；生命上限和当前生命+2",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SELF,
            cooldown=0,
            morale_cost=6,
        )
        self.force_boost = 6
        self.hp_boost = 2
        self.duration = 3

    def execute(self, caster, targets, battle_context):
        old_max_hp = caster.max_hp
        old_current_hp = caster.current_hp

        caster.add_buff("force_boost", self.force_boost, self.duration)
        caster.max_hp += self.hp_boost
        caster.current_hp += self.hp_boost

        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": 1,
            "details": [{
                "target": caster.name,
                "effect": "武力+6持续3回合，生命上限和当前生命+2",
                "old_max_hp": old_max_hp,
                "new_max_hp": caster.max_hp,
                "old_current_hp": old_current_hp,
                "new_current_hp": caster.current_hp,
                "duration": self.duration,
            }],
        }


class SpearWheelTacticsSkill(Skill):
    """轮枪战术：以敌方 2x2 方格内最弱武力者结算伤害，再由全体平摊。"""

    def __init__(self):
        super().__init__(
            skill_id="spear_wheel_tactics",
            name="轮枪战术",
            description="对敌方2x2方格内武力最低者计算伤害，伤害由方格内所有武将平摊",
            skill_type=SkillType.DAMAGE,
            target_type=TargetType.AREA_ENEMY,
            cooldown=0,
            morale_cost=4,
        )

    def execute(self, caster, targets, battle_context):
        caster_team = battle_context.get_team_for_general(caster)
        if caster_team is None:
            return {
                "success": False,
                "type": "damage",
                "message": "无法找到张飞所属队伍",
                "details": [],
            }

        enemy_team = (
            battle_context.team2
            if caster_team == battle_context.team1
            else battle_context.team1
        )
        block_positions, block_generals = self._select_target_block(enemy_team)
        if not block_generals:
            return {
                "success": False,
                "type": "damage",
                "message": "目标2x2方格内没有可攻击武将",
                "details": [],
            }

        weakest = min(
            block_generals,
            key=lambda general: (
                general.get_effective_force(),
                general.current_hp,
                general.name,
            )
        )
        base_damage = caster.calculate_damage_to(weakest)
        shared_damage = max(1, base_damage // len(block_generals))

        details = []
        total_damage = 0
        for target in block_generals:
            actual_damage = target.take_damage(shared_damage, caster, "skill")
            total_damage += actual_damage
            details.append({
                "target": target.name,
                "damage": actual_damage,
                "target_hp": target.current_hp,
            })

        return {
            "success": True,
            "type": "damage",
            "block": block_positions,
            "damage_basis_target": weakest.name,
            "base_damage": base_damage,
            "shared_damage": shared_damage,
            "total_damage": total_damage,
            "targets_hit": len(details),
            "details": details,
        }

    def _select_target_block(self, enemy_team):
        best_positions = []
        best_generals = []

        for row in range(2):
            for col in range(3):
                positions = [
                    (row, col), (row, col + 1),
                    (row + 1, col), (row + 1, col + 1),
                ]
                generals = [
                    enemy_team.formation[r][c]
                    for r, c in positions
                    if enemy_team.formation[r][c] is not None
                    and enemy_team.formation[r][c].is_alive
                ]
                if len(generals) > len(best_generals):
                    best_positions = positions
                    best_generals = generals

        return best_positions, best_generals


class WeiKingGuardSkill(Skill):
    """魏王的卫兵：夏侯惇获得一次连击判定。"""

    def __init__(self):
        super().__init__(
            skill_id="wei_king_guard",
            name="魏王的卫兵",
            description="自身武力+3；获得一次攻速判定，成功则普攻连续输出两次",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SELF,
            cooldown=0,
            morale_cost=4,
        )
        self.force_boost = 3
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        caster.add_buff("force_boost", self.force_boost, self.duration)
        caster.add_buff("attack_speed_judgment", 1, self.duration)

        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": 1,
            "details": [{
                "target": caster.name,
                "effect": "武力+3，获得一次攻速判定",
                "duration": self.duration,
            }],
        }


class CavalryUnitySkill(Skill):
    """人马一体：张辽进入骑战突击状态。"""

    def __init__(self):
        super().__init__(
            skill_id="cavalry_unity",
            name="人马一体",
            description="自身武力+2；获得一次攻速判定，成功则普攻连续输出两次",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SELF,
            cooldown=0,
            morale_cost=3,
        )
        self.force_boost = 2
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        caster.add_buff("force_boost", self.force_boost, self.duration)
        caster.add_buff("attack_speed_judgment", 1, self.duration)

        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": 1,
            "details": [{
                "target": caster.name,
                "effect": "武力+2，获得一次攻速判定",
                "duration": self.duration,
            }],
        }


class WeiEliteSkill(Skill):
    """魏武精英：于禁稳定强化自身两回合。"""

    def __init__(self):
        super().__init__(
            skill_id="wei_elite",
            name="魏武精英",
            description="自身武力+2，持续两回合",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SELF,
            cooldown=0,
            morale_cost=3,
        )
        self.force_boost = 2
        self.duration = 2

    def execute(self, caster, targets, battle_context):
        caster.add_buff("force_boost", self.force_boost, self.duration)
        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": 1,
            "details": [{
                "target": caster.name,
                "effect": "武力+2",
                "duration": self.duration,
            }],
        }


class KnockbackTacticsSkill(Skill):
    """击飞战术：强化自身，造成普攻伤害后击退敌方前排。"""

    def __init__(self):
        super().__init__(
            skill_id="knockback_tactics",
            name="击飞战术",
            description="自身武力+2；造成伤害时使目标与其后排武将换位",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SELF,
            cooldown=0,
            morale_cost=3,
        )
        self.force_boost = 2
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        caster.add_buff("force_boost", self.force_boost, self.duration)
        caster.add_buff("knockback_on_damage", 1, self.duration)
        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": 1,
            "details": [{
                "target": caster.name,
                "effect": "武力+2，造成伤害后击飞换位",
                "duration": self.duration,
            }],
        }


class DivineSpeedTacticsSkill(Skill):
    """神速战术：夏侯渊发动高速突击。"""

    def __init__(self):
        super().__init__(
            skill_id="divine_speed_tactics",
            name="神速战术",
            description="自身武力+2；获得一次攻速判定，成功则普攻连续输出两次",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SELF,
            cooldown=0,
            morale_cost=4,
        )
        self.force_boost = 2
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        caster.add_buff("force_boost", self.force_boost, self.duration)
        caster.add_buff("attack_speed_judgment", 1, self.duration)

        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": 1,
            "details": [{
                "target": caster.name,
                "effect": "武力+2，获得一次攻速判定",
                "duration": self.duration,
            }],
        }


class GrandCavalryOrderSkill(Skill):
    """人马大号令：强化董卓所在横排的己方武将。"""

    def __init__(self):
        super().__init__(
            skill_id="grand_cavalry_order",
            name="人马大号令",
            description="我方一横排武将武力+4，并获得一次攻速判定",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.AREA_ALLY,
            cooldown=0,
            morale_cost=7,
        )
        self.force_boost = 4
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到董卓所属队伍",
                "details": [],
            }

        caster_position = team.get_general_position(caster)
        if caster_position is None:
            affected_generals = [caster]
            row = None
        else:
            row, _ = caster_position
            affected_generals = [
                general for general in team.generals
                if general.is_alive and team.get_general_position(general)
                and team.get_general_position(general)[0] == row
            ]

        details = []
        for general in affected_generals:
            general.add_buff("force_boost", self.force_boost, self.duration)
            general.add_buff("attack_speed_judgment", 1, self.duration)
            details.append({
                "target": general.name,
                "row": row,
                "effect": "武力+4，获得一次攻速判定",
                "duration": self.duration,
            })

        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": len(details),
            "details": details,
        }


class BanditSuppressionOrderSkill(Skill):
    """贼军讨伐令：按对面同排敌军数量强化己方横排。"""

    def __init__(self):
        super().__init__(
            skill_id="bandit_suppression_order",
            name="贼军讨伐令",
            description="自身所在横排友军武力上升，上升点数等于敌方同排存活武将数量",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.AREA_ALLY,
            cooldown=0,
            morale_cost=5,
        )
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到皇甫嵩所属队伍",
                "details": [],
            }

        enemy_team = (
            battle_context.team2
            if team == battle_context.team1
            else battle_context.team1
        )
        caster_position = team.get_general_position(caster)
        if caster_position is None:
            row = None
            affected_generals = [caster] if caster.is_alive else []
            enemy_count = len([general for general in enemy_team.generals if general.is_alive])
        else:
            row, _ = caster_position
            affected_generals = [
                general for general in team.generals
                if general.is_alive and team.get_general_position(general)
                and team.get_general_position(general)[0] == row
            ]
            enemy_count = sum(
                1 for general in enemy_team.formation[row]
                if general is not None and general.is_alive
            )

        if not affected_generals:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "我方横排没有可被讨伐令强化的存活武将",
                "details": [],
            }

        details = []
        for general in affected_generals:
            general.add_buff("force_boost", enemy_count, self.duration)
            details.append({
                "target": general.name,
                "row": row,
                "effect": f"武力+{enemy_count}",
                "duration": self.duration,
            })

        return {
            "success": True,
            "type": "enhance_weaken",
            "row": row,
            "enemy_count": enemy_count,
            "targets_affected": len(details),
            "details": details,
        }


class WhiteHorseFormationSkill(Skill):
    """白马阵：公孙瓒所在横排友军获得攻速判定。"""

    def __init__(self):
        super().__init__(
            skill_id="white_horse_formation",
            name="白马阵",
            description="自身所在横排的我方武将获得一次攻速判定",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.AREA_ALLY,
            cooldown=0,
            morale_cost=5,
        )
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到公孙瓒所属队伍",
                "details": [],
            }

        caster_position = team.get_general_position(caster)
        if caster_position is None:
            row = None
            affected_generals = [caster] if caster.is_alive else []
        else:
            row, _ = caster_position
            affected_generals = [
                general for general in team.generals
                if general.is_alive and team.get_general_position(general)
                and team.get_general_position(general)[0] == row
            ]

        if not affected_generals:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "我方横排没有可进入白马阵的存活武将",
                "details": [],
            }

        details = []
        for general in affected_generals:
            general.add_buff("attack_speed_judgment", 1, self.duration)
            details.append({
                "target": general.name,
                "row": row,
                "effect": "获得一次攻速判定",
                "duration": self.duration,
            })

        return {
            "success": True,
            "type": "enhance_weaken",
            "row": row,
            "targets_affected": len(details),
            "details": details,
        }


class ImperialEdictSkill(Skill):
    """敕命：强化我方当前武力最高的武将。"""

    def __init__(self):
        super().__init__(
            skill_id="imperial_edict",
            name="敕命",
            description="使我方武力最高的武将武力+5",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SINGLE_ALLY,
            cooldown=0,
            morale_cost=4,
        )
        self.force_boost = 5
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到汉献帝所属队伍",
                "details": [],
            }

        alive_generals = [general for general in team.generals if general.is_alive]
        if not alive_generals:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "我方没有可被敕命的存活武将",
                "details": [],
            }

        target = max(
            alive_generals,
            key=lambda general: (
                general.get_effective_force(),
                general.get_effective_intelligence(),
                general.current_hp,
            ),
        )
        target.add_buff("force_boost", self.force_boost, self.duration)

        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": 1,
            "details": [{
                "target": target.name,
                "effect": "武力+5",
                "duration": self.duration,
            }],
        }


class DestructiveAdviceSkill(Skill):
    """破坏性的献策：强化己方最强武将，陈宫自身付出血量代价。"""

    def __init__(self):
        super().__init__(
            skill_id="destructive_advice",
            name="破坏性的献策",
            description="使我方武力最高的武将武力+5，自身受到4点伤害；目标为吕布时效果加倍",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SINGLE_ALLY,
            cooldown=0,
            morale_cost=3,
        )
        self.force_boost = 5
        self.self_damage = 4
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到陈宫所属队伍",
                "details": [],
            }

        alive_generals = [general for general in team.generals if general.is_alive]
        if not alive_generals:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "我方没有可被破坏性献策强化的存活武将",
                "details": [],
            }

        target = max(
            alive_generals,
            key=lambda general: (
                general.get_effective_force(),
                general.get_effective_intelligence(),
                general.current_hp,
            ),
        )
        boost = self.force_boost * 2 if target.name == "吕布" else self.force_boost
        target.add_buff("force_boost", boost, self.duration)
        actual_self_damage = caster.take_damage(self.self_damage, caster, "skill")

        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": 1,
            "self_damage": actual_self_damage,
            "details": [{
                "target": target.name,
                "effect": f"武力+{boost}",
                "duration": self.duration,
            }, {
                "target": caster.name,
                "effect": f"自身受到{actual_self_damage}点伤害",
                "duration": 0,
            }],
        }


class UnitedSiegeSkill(Skill):
    """联合围攻：于夫罗依靠己方人数提升自身武力。"""

    def __init__(self):
        super().__init__(
            skill_id="united_siege",
            name="联合围攻",
            description="自身武力上升，上升数量等于当前场上我方存活武将数",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SELF,
            cooldown=0,
            morale_cost=4,
        )
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到于夫罗所属队伍",
                "details": [],
            }

        ally_count = len([general for general in team.generals if general.is_alive])
        if ally_count <= 0:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "我方没有可用于联合围攻的存活武将",
                "details": [],
            }

        caster.add_buff("force_boost", ally_count, self.duration)
        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": 1,
            "ally_count": ally_count,
            "details": [{
                "target": caster.name,
                "effect": f"武力+{ally_count}",
                "duration": self.duration,
            }],
        }


class VileRaidSkill(Skill):
    """卑劣的奇袭：李傕和郭汜根据敌方已消耗士气提升武力。"""

    def __init__(self):
        super().__init__(
            skill_id="vile_raid",
            name="卑劣的奇袭",
            description="自身武力上升，上升值为敌方已消耗士气的一半，最少2点",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SELF,
            cooldown=0,
            morale_cost=3,
        )
        self.minimum_boost = 2
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到李傕和郭汜所属队伍",
                "details": [],
            }

        enemy_team = (
            battle_context.team2
            if team == battle_context.team1
            else battle_context.team1
        )
        enemy_morale_spent = max(0, int(getattr(enemy_team, "morale_spent", 0)))
        force_boost = max(self.minimum_boost, (enemy_morale_spent + 1) // 2)
        caster.add_buff("force_boost", force_boost, self.duration)

        return {
            "success": True,
            "type": "enhance_weaken",
            "enemy_morale_spent": enemy_morale_spent,
            "force_boost": force_boost,
            "targets_affected": 1,
            "details": [{
                "target": caster.name,
                "effect": f"武力+{force_boost}",
                "duration": self.duration,
            }],
        }


class HighMoraleSkill(Skill):
    """士气旺盛：文丑按队伍士气上限提升武力。"""

    def __init__(self):
        super().__init__(
            skill_id="high_morale",
            name="士气旺盛",
            description="若士气上限为初始值则武力+4；上限每增加2点，额外武力+1",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SELF,
            cooldown=0,
            morale_cost=4,
        )
        self.initial_max_morale = 12
        self.base_boost = 4
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到文丑所属队伍",
                "details": [],
            }

        morale_bonus_steps = max(0, (team.max_morale - self.initial_max_morale) // 2)
        force_boost = self.base_boost + morale_bonus_steps
        caster.add_buff("force_boost", force_boost, self.duration)

        return {
            "success": True,
            "type": "enhance_weaken",
            "max_morale": team.max_morale,
            "initial_max_morale": self.initial_max_morale,
            "force_boost": force_boost,
            "targets_affected": 1,
            "details": [{
                "target": caster.name,
                "effect": f"武力+{force_boost}",
                "duration": self.duration,
            }],
        }


class FirstMeritSkill(Skill):
    """率先立功：张郃先行突击，并在存活时带回士气。"""

    def __init__(self):
        super().__init__(
            skill_id="first_merit",
            name="率先立功",
            description="自身武力+2；下一回合若自身仍存活则士气+2",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SELF,
            cooldown=0,
            morale_cost=3,
        )
        self.force_boost = 2
        self.morale_reward = 2
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到张郃所属队伍",
                "details": [],
            }

        caster.add_buff("force_boost", self.force_boost, self.duration)
        team.add_pending_morale_reward(
            self.morale_reward,
            1,
            required_alive_generals=[caster],
        )

        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": 1,
            "pending_morale_reward": self.morale_reward,
            "details": [{
                "target": caster.name,
                "effect": f"武力+{self.force_boost}，下回合存活则士气+{self.morale_reward}",
                "duration": self.duration,
            }],
        }


class MomentaryOrderSkill(Skill):
    """刹那的号令：短时间强化曹仁周围 2x2 范围内的友军。"""

    def __init__(self):
        super().__init__(
            skill_id="momentary_order",
            name="刹那的号令",
            description="包括自己在内2x2范围内的我方武将武力+2，下回合无法使用",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.AREA_ALLY,
            cooldown=2,
            morale_cost=3,
        )
        self.force_boost = 2
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到曹仁所属队伍",
                "details": [],
            }

        affected_generals, block_positions = self._get_affected_generals(caster, team)
        details = []
        for general in affected_generals:
            general.add_buff("force_boost", self.force_boost, self.duration)
            details.append({
                "target": general.name,
                "effect": "武力+2",
                "duration": self.duration,
            })

        return {
            "success": True,
            "type": "enhance_weaken",
            "block": block_positions,
            "targets_affected": len(details),
            "details": details,
        }

    def _get_affected_generals(self, caster, team):
        caster_position = team.get_general_position(caster)
        if caster_position is None:
            return ([caster] if caster.is_alive else []), []

        caster_row, caster_col = caster_position
        candidate_blocks = []
        for row_start in range(max(0, caster_row - 1), min(caster_row, 1) + 1):
            for col_start in range(max(0, caster_col - 1), min(caster_col, 2) + 1):
                positions = [
                    (row_start, col_start),
                    (row_start, col_start + 1),
                    (row_start + 1, col_start),
                    (row_start + 1, col_start + 1),
                ]
                generals = [
                    team.formation[row][col]
                    for row, col in positions
                    if team.formation[row][col] is not None
                    and team.formation[row][col].is_alive
                ]
                candidate_blocks.append((positions, generals))

        best_positions, best_generals = max(
            candidate_blocks,
            key=lambda item: (len(item[1]), -item[0][0][0], -item[0][0][1]),
        )
        return best_generals, best_positions


class MeticulousOffenseSkill(Skill):
    """缜密的攻势：强化前方 2x2 武将，并筹划下回合士气。"""

    def __init__(self):
        super().__init__(
            skill_id="meticulous_offense",
            name="缜密的攻势",
            description="前方2x2方格的我方武将武力+3；下回合士气+3，若受益武将阵亡则不加士气",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.AREA_ALLY,
            cooldown=0,
            morale_cost=5,
        )
        self.force_boost = 3
        self.morale_reward = 3
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到田丰所属队伍",
                "details": [],
            }

        affected_generals, block_positions = self._get_affected_generals(caster, team)
        if not affected_generals:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "前方2x2方格内没有可强化的我方武将",
                "details": [],
            }

        details = []
        for general in affected_generals:
            general.add_buff("force_boost", self.force_boost, self.duration)
            details.append({
                "target": general.name,
                "effect": "武力+3",
                "duration": self.duration,
            })

        team.add_pending_morale_reward(
            self.morale_reward,
            delay_turns=1,
            required_alive_generals=affected_generals,
        )

        return {
            "success": True,
            "type": "enhance_weaken",
            "block": block_positions,
            "targets_affected": len(details),
            "pending_morale_reward": self.morale_reward,
            "details": details,
        }

    def _get_affected_generals(self, caster, team):
        caster_position = team.get_general_position(caster)
        if caster_position is None:
            return ([caster] if caster.is_alive else []), []

        caster_row, caster_col = caster_position
        row_starts = sorted({
            max(0, min(1, caster_row - 2)),
            max(0, min(1, caster_row - 1)),
            max(0, min(1, caster_row)),
        })
        col_starts = sorted({
            max(0, min(2, caster_col - 1)),
            max(0, min(2, caster_col)),
        })

        candidate_blocks = []
        for row_start in row_starts:
            for col_start in col_starts:
                positions = [
                    (row_start, col_start),
                    (row_start, col_start + 1),
                    (row_start + 1, col_start),
                    (row_start + 1, col_start + 1),
                ]
                if not any(row < caster_row for row, _ in positions):
                    continue
                generals = [
                    team.formation[row][col]
                    for row, col in positions
                    if team.formation[row][col] is not None
                    and team.formation[row][col].is_alive
                ]
                candidate_blocks.append((positions, generals))

        if not candidate_blocks:
            return ([caster] if caster.is_alive else []), [caster_position]

        best_positions, best_generals = max(
            candidate_blocks,
            key=lambda item: (
                len(item[1]),
                -item[0][0][0],
                -abs(item[0][0][1] - caster_col),
            ),
        )
        return best_generals, best_positions


class ThunderStrikeSkill(Skill):
    """雷击：在敌方 2x2 区域内降下两道需要判定的雷。"""

    def __init__(self):
        super().__init__(
            skill_id="thunder_strike",
            name="雷击",
            description="敌方2x2方格内打下两道闪电；目标猜错奇偶则受到2倍智力差伤害",
            skill_type=SkillType.DAMAGE,
            target_type=TargetType.AREA_ENEMY,
            cooldown=0,
            morale_cost=6,
        )
        self.strike_count = 2

    def execute(self, caster, targets, battle_context, guess=None):
        caster_team = battle_context.get_team_for_general(caster)
        if caster_team is None:
            return {
                "success": False,
                "type": "damage",
                "message": "无法找到夏侯月姬所属队伍",
                "details": [],
            }

        enemy_team = (
            battle_context.team2
            if caster_team == battle_context.team1
            else battle_context.team1
        )
        # 如果前端传入了已选区域目标，直接使用；否则自动选择最佳2x2块
        if targets and len(targets) > 0 and all(hasattr(t, 'is_alive') for t in targets):
            block_generals = [t for t in targets if t.is_alive and t._team == enemy_team]
            block_positions = [(0, 0)]  # 前端传入时不需要block info
        else:
            block_positions, block_generals = self._select_target_block(enemy_team)
        if not block_generals:
            return {
                "success": False,
                "type": "damage",
                "message": "目标2x2方格内没有可雷击武将",
                "details": [],
            }

        details = []
        total_damage = 0
        for target in self._select_strike_targets(block_generals):
            judgment = odd_even_judgment(guess)  # 使用玩家选择的奇偶
            damage = 0
            if not judgment["success"]:
                damage = self._calculate_thunder_damage(caster, target)
                damage = target.take_damage(damage, caster, "skill")
                total_damage += damage

            details.append({
                "target": target.name,
                "judgment": judgment,
                "damage": damage,
                "target_hp": target.current_hp,
            })

        return {
            "success": True,
            "type": "damage",
            "block": block_positions,
            "strike_count": len(details),
            "total_damage": total_damage,
            "details": details,
        }

    def _calculate_thunder_damage(self, caster, target):
        intelligence_diff = (
            caster.get_effective_intelligence()
            - target.get_effective_intelligence()
        )
        return max(1, intelligence_diff * 2)

    def _select_target_block(self, enemy_team):
        best_positions = []
        best_generals = []

        for row in range(2):
            for col in range(3):
                positions = [
                    (row, col), (row, col + 1),
                    (row + 1, col), (row + 1, col + 1),
                ]
                generals = [
                    enemy_team.formation[r][c]
                    for r, c in positions
                    if enemy_team.formation[r][c] is not None
                    and enemy_team.formation[r][c].is_alive
                ]
                if len(generals) > len(best_generals):
                    best_positions = positions
                    best_generals = generals

        return best_positions, best_generals

    def _select_strike_targets(self, block_generals):
        targets = sorted(
            block_generals,
            key=lambda general: (
                general.get_effective_intelligence(),
                general.current_hp,
                general.name,
            ),
        )
        if len(targets) == 1:
            return targets * self.strike_count
        return targets[:self.strike_count]


class JiangdongBeautySkill(Skill):
    """江东的大美人：净化并滋养大乔周围的友军。"""

    def __init__(self):
        super().__init__(
            skill_id="jiangdong_beauty",
            name="江东的大美人",
            description="清除自身所在3x3方格内友军减益；若无减益则回复1点生命，满血则生命上限+1",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.AREA_ALLY,
            cooldown=0,
            morale_cost=4,
        )

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到大乔所属队伍",
                "details": [],
            }

        affected_generals = self._get_affected_generals(caster, team)
        details = []

        for general in affected_generals:
            if general.debuffs:
                cleared_count = len(general.debuffs)
                general.debuffs.clear()
                effect = "清除debuff"
                details.append({
                    "target": general.name,
                    "effect": effect,
                    "cleared_debuffs": cleared_count,
                    "current_hp": general.current_hp,
                    "max_hp": general.max_hp,
                })
            elif general.current_hp < general.max_hp:
                healed = general.heal(1)
                details.append({
                    "target": general.name,
                    "effect": "回复生命",
                    "healed": healed,
                    "current_hp": general.current_hp,
                    "max_hp": general.max_hp,
                })
            else:
                general.max_hp += 1
                general.current_hp += 1
                details.append({
                    "target": general.name,
                    "effect": "生命上限+1",
                    "current_hp": general.current_hp,
                    "max_hp": general.max_hp,
                })

        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": len(details),
            "details": details,
        }

    def _get_affected_generals(self, caster, team):
        caster_position = team.get_general_position(caster)
        if caster_position is None:
            return [caster] if caster.is_alive else []

        center_row, center_col = caster_position
        affected = []
        for row in range(center_row - 1, center_row + 2):
            for col in range(center_col - 1, center_col + 2):
                if 0 <= row < 3 and 0 <= col < 4:
                    general = team.formation[row][col]
                    if general is not None and general.is_alive:
                        affected.append(general)
        return affected


class FlawlessSkill(Skill):
    """天衣无缝：太史慈在蓄势与速攻之间二选一。"""

    def __init__(self):
        super().__init__(
            skill_id="flawless",
            name="天衣无缝",
            description="二选一：保存武智合计+6的未来增益；或武力+4并获得一次攻速判定",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SELF,
            cooldown=0,
            morale_cost=6,
        )
        self.speed_force_boost = 4
        self.saved_total_boost = 6
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        options = self._get_options(targets, battle_context)
        mode = options.get("mode") or options.get("taishi_ci_mode") or "speed"
        if mode in ("saved", "delayed", "reserve", "蓄势", "保存"):
            return self._execute_saved_boost(caster, options)
        return self._execute_speed_boost(caster)

    def _execute_speed_boost(self, caster):
        caster.add_buff("force_boost", self.speed_force_boost, self.duration)
        caster.add_buff("attack_speed_judgment", 1, self.duration)
        return {
            "success": True,
            "type": "enhance_weaken",
            "mode": "speed",
            "targets_affected": 1,
            "details": [{
                "target": caster.name,
                "effect": "武力+4，获得一次攻速判定",
                "duration": self.duration,
            }],
        }

    def _execute_saved_boost(self, caster, options):
        force_boost = int(options.get("force_boost", 3))
        force_boost = max(0, min(self.saved_total_boost, force_boost))
        intelligence_boost = self.saved_total_boost - force_boost
        delay_turns = int(options.get("delay_turns", 1))
        duration = int(options.get("duration", self.duration))

        if delay_turns <= 0:
            caster.add_buff("force_boost", force_boost, duration)
            caster.add_buff("intelligence_boost", intelligence_boost, duration)
            effect = "武智合计+6立即生效"
        else:
            caster.add_pending_buff("force_boost", force_boost, duration, delay_turns)
            caster.add_pending_buff("intelligence_boost", intelligence_boost, duration, delay_turns)
            effect = f"武智合计+6延迟{delay_turns}回合生效"

        return {
            "success": True,
            "type": "enhance_weaken",
            "mode": "saved",
            "targets_affected": 1,
            "details": [{
                "target": caster.name,
                "effect": effect,
                "force_boost": force_boost,
                "intelligence_boost": intelligence_boost,
                "delay_turns": max(0, delay_turns),
                "duration": duration,
            }],
        }

    def _get_options(self, targets, battle_context):
        options = {}
        context_options = getattr(battle_context, "skill_options", None)
        if isinstance(context_options, dict):
            options.update(context_options)
        if targets and isinstance(targets[0], dict):
            options.update(targets[0])
        return options


class MasterTeachingSkill(Skill):
    """夫子的教诲：提升司马徽所在横排友军智力。"""

    def __init__(self):
        super().__init__(
            skill_id="master_teaching",
            name="夫子的教诲",
            description="使自身所在横排的我方武将智力+2，持续1回合",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.AREA_ALLY,
            cooldown=0,
            morale_cost=3,
        )
        self.intelligence_boost = 2
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到司马徽所属队伍",
                "details": [],
            }

        affected_generals, row = self._get_affected_generals(caster, team)
        details = []
        for general in affected_generals:
            general.add_buff("intelligence_boost", self.intelligence_boost, self.duration)
            details.append({
                "target": general.name,
                "row": row,
                "effect": "智力+2",
                "duration": self.duration,
            })

        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": len(details),
            "details": details,
        }

    def _get_affected_generals(self, caster, team):
        caster_position = team.get_general_position(caster)
        if caster_position is None:
            return ([caster] if caster.is_alive else []), None

        row, _ = caster_position
        affected_generals = [
            general for general in team.generals
            if general.is_alive and team.get_general_position(general)
            and team.get_general_position(general)[0] == row
        ]
        return affected_generals, row


class FenceRebuildSkill(Skill):
    """防栅重建：立即修复己方所有存活武将的防栅。"""

    def __init__(self):
        super().__init__(
            skill_id="fence_rebuild",
            name="防栅重建",
            description="重建己方所有存活武将的防栅",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.ALL_ALLIES,
            cooldown=0,
            morale_cost=6,
        )

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到朱然所属队伍",
                "details": [],
            }

        details = []
        for general in team.generals:
            if not general.is_alive or not general.has_passive_skill("防栅"):
                continue
            fence = general.get_passive_skill("防栅")
            was_active = fence.is_active
            fence.is_active = True
            fence.rebuild_turns_remaining = 0
            details.append({
                "target": general.name,
                "effect": "防栅重建" if not was_active else "防栅保持",
                "is_active": fence.is_active,
            })

        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": len(details),
            "details": details,
        }


class TaipingArtsSkill(Skill):
    """太平要术：每局最多两次，复活己方全部阵亡武将。"""

    def __init__(self):
        super().__init__(
            skill_id="taiping_arts",
            name="太平要术",
            description="复活我方所有阵亡武将，复活后生命值为半血；每局最多使用两次",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.ALL_ALLIES,
            cooldown=0,
            morale_cost=6,
        )
        self.max_uses_per_game = 2

    def can_use(self, caster, team=None) -> bool:
        if not super().can_use(caster, team):
            return False
        return self._get_use_count(caster) < self.max_uses_per_game

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到张角所属队伍",
                "details": [],
            }

        details = []
        for general in team.generals:
            if general.is_alive:
                continue
            revive_hp = max(1, general.max_hp // 2)
            general.is_alive = True
            general.current_hp = revive_hp
            details.append({
                "target": general.name,
                "effect": "复活",
                "current_hp": general.current_hp,
                "max_hp": general.max_hp,
            })

        self._increment_use_count(caster)
        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": len(details),
            "uses_remaining": self.max_uses_per_game - self._get_use_count(caster),
            "details": details,
        }

    def _get_use_count(self, caster) -> int:
        counts = getattr(caster, "active_skill_usage_counts", {})
        return counts.get(self.skill_id, 0)

    def _increment_use_count(self, caster) -> None:
        if not hasattr(caster, "active_skill_usage_counts"):
            caster.active_skill_usage_counts = {}
        caster.active_skill_usage_counts[self.skill_id] = self._get_use_count(caster) + 1


class DiscordStrategySkill(Skill):
    """离间谋略：指定敌方2x2区域，在选定进攻时机削弱武智。"""

    def __init__(self):
        super().__init__(
            skill_id="discord_strategy",
            name="离间谋略",
            description="指定敌方2x2方格武将武力和智力-2，可选择我方进攻或对方进攻时生效",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.AREA_ENEMY,
            cooldown=0,
            morale_cost=6,
        )
        self.reduction = 2
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        caster_team = battle_context.get_team_for_general(caster)
        if caster_team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到贾诩所属队伍",
                "details": [],
            }

        enemy_team = (
            battle_context.team2
            if caster_team == battle_context.team1
            else battle_context.team1
        )
        options = self._get_options(targets, battle_context)
        timing = self._normalize_timing(options.get("timing") or options.get("mode"))
        block_positions, block_generals = self._select_target_block(enemy_team, options)
        if not block_generals:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "目标2x2方格内没有可离间武将",
                "details": [],
            }

        details = []
        for target in block_generals:
            if timing == "enemy_attack":
                target.add_pending_debuff("force_reduction", self.reduction, self.duration, 1)
                target.add_pending_debuff("intelligence_reduction", self.reduction, self.duration, 1)
                effect = "对方进攻时武力-2、智力-2"
            else:
                target.add_debuff("force_reduction", self.reduction, self.duration)
                target.add_debuff("intelligence_reduction", self.reduction, self.duration)
                effect = "我方进攻时武力-2、智力-2"
            details.append({
                "target": target.name,
                "effect": effect,
                "timing": timing,
                "duration": self.duration,
            })

        return {
            "success": True,
            "type": "enhance_weaken",
            "mode": timing,
            "block": block_positions,
            "targets_affected": len(details),
            "details": details,
        }

    def _get_options(self, targets, battle_context):
        options = {}
        context_options = getattr(battle_context, "skill_options", None)
        if isinstance(context_options, dict):
            options.update(context_options)
        if targets and isinstance(targets[0], dict):
            options.update(targets[0])
        return options

    def _normalize_timing(self, timing):
        if timing in ("enemy_attack", "enemy", "opponent", "对方进攻", "敌方进攻"):
            return "enemy_attack"
        return "ally_attack"

    def _select_target_block(self, enemy_team, options):
        row = options.get("row")
        col = options.get("col")
        if row is None or col is None:
            origin = options.get("origin") or options.get("block_origin")
            if isinstance(origin, (tuple, list)) and len(origin) >= 2:
                row, col = origin[0], origin[1]

        if row is not None and col is not None:
            row = max(0, min(1, int(row)))
            col = max(0, min(2, int(col)))
            positions = [
                (row, col), (row, col + 1),
                (row + 1, col), (row + 1, col + 1),
            ]
            generals = [
                enemy_team.formation[r][c]
                for r, c in positions
                if enemy_team.formation[r][c] is not None
                and enemy_team.formation[r][c].is_alive
            ]
            return positions, generals

        best_positions = []
        best_generals = []
        for row in range(2):
            for col in range(3):
                positions = [
                    (row, col), (row, col + 1),
                    (row + 1, col), (row + 1, col + 1),
                ]
                generals = [
                    enemy_team.formation[r][c]
                    for r, c in positions
                    if enemy_team.formation[r][c] is not None
                    and enemy_team.formation[r][c].is_alive
                ]
                if len(generals) > len(best_generals):
                    best_positions = positions
                    best_generals = generals
        return best_positions, best_generals


class ToothForToothSkill(Skill):
    """以牙还牙：王异在大范围削弱和重点反制之间二选一。"""

    def __init__(self):
        super().__init__(
            skill_id="tooth_for_tooth",
            name="以牙还牙",
            description="二选一：敌方2x2武力-3；或敌方2x1武力-3且下回合普攻需攻速判定",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.AREA_ENEMY,
            cooldown=0,
            morale_cost=5,
        )
        self.force_reduction = 3
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        caster_team = battle_context.get_team_for_general(caster)
        if caster_team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到王异所属队伍",
                "details": [],
            }

        enemy_team = (
            battle_context.team2
            if caster_team == battle_context.team1
            else battle_context.team1
        )
        options = self._get_options(targets, battle_context)
        mode = self._normalize_mode(options.get("mode") or options.get("wang_yi_mode"))
        if mode == "focused":
            block_positions, block_generals = self._select_2x1_block(enemy_team, options)
        else:
            block_positions, block_generals = self._select_2x2_block(enemy_team, options)

        if not block_generals:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "目标方格内没有可施加以牙还牙的武将",
                "details": [],
            }

        details = []
        for target in block_generals:
            target.add_debuff("force_reduction", self.force_reduction, self.duration)
            effect = "武力-3"
            if mode == "focused":
                target.add_pending_debuff("attack_speed_required", 1, self.duration, 1)
                effect = "武力-3，下回合普攻需攻速判定"
            details.append({
                "target": target.name,
                "effect": effect,
                "mode": mode,
                "duration": self.duration,
            })

        return {
            "success": True,
            "type": "enhance_weaken",
            "mode": mode,
            "block": block_positions,
            "targets_affected": len(details),
            "details": details,
        }

    def _get_options(self, targets, battle_context):
        options = {}
        context_options = getattr(battle_context, "skill_options", None)
        if isinstance(context_options, dict):
            options.update(context_options)
        if targets and isinstance(targets[0], dict):
            options.update(targets[0])
        return options

    def _normalize_mode(self, mode):
        if mode in ("focused", "narrow", "2x1", "二", "反制"):
            return "focused"
        return "wide"

    def _select_2x2_block(self, enemy_team, options):
        row, col = self._read_origin(options)
        if row is not None and col is not None:
            row = max(0, min(1, int(row)))
            col = max(0, min(2, int(col)))
            positions = [
                (row, col), (row, col + 1),
                (row + 1, col), (row + 1, col + 1),
            ]
            return positions, self._generals_at(enemy_team, positions)
        return self._best_block(enemy_team, 2, 2)

    def _select_2x1_block(self, enemy_team, options):
        row, col = self._read_origin(options)
        orientation = options.get("orientation", "vertical")
        if row is not None and col is not None:
            row = int(row)
            col = int(col)
            if orientation in ("horizontal", "1x2", "横"):
                row = max(0, min(2, row))
                col = max(0, min(2, col))
                positions = [(row, col), (row, col + 1)]
            else:
                row = max(0, min(1, row))
                col = max(0, min(3, col))
                positions = [(row, col), (row + 1, col)]
            return positions, self._generals_at(enemy_team, positions)
        return self._best_block(enemy_team, 2, 1)

    def _read_origin(self, options):
        row = options.get("row")
        col = options.get("col")
        if row is None or col is None:
            origin = options.get("origin") or options.get("block_origin")
            if isinstance(origin, (tuple, list)) and len(origin) >= 2:
                row, col = origin[0], origin[1]
        return row, col

    def _best_block(self, enemy_team, height, width):
        best_positions = []
        best_generals = []
        for row in range(0, 3 - height + 1):
            for col in range(0, 4 - width + 1):
                positions = [
                    (r, c)
                    for r in range(row, row + height)
                    for c in range(col, col + width)
                ]
                generals = self._generals_at(enemy_team, positions)
                if len(generals) > len(best_generals):
                    best_positions = positions
                    best_generals = generals
        return best_positions, best_generals

    def _generals_at(self, team, positions):
        return [
            team.formation[row][col]
            for row, col in positions
            if team.formation[row][col] is not None
            and team.formation[row][col].is_alive
        ]


class TauntSkill(Skill):
    """挑衅：姜维强制敌方2x2区域武将只能普攻自己。"""

    def __init__(self):
        super().__init__(
            skill_id="taunt",
            name="挑衅",
            description="使敌方2x2方格内的武将本回合普攻只能攻击自己",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.AREA_ENEMY,
            cooldown=0,
            morale_cost=3,
        )
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        caster_team = battle_context.get_team_for_general(caster)
        if caster_team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到姜维所属队伍",
                "details": [],
            }

        enemy_team = (
            battle_context.team2
            if caster_team == battle_context.team1
            else battle_context.team1
        )
        options = self._get_options(targets, battle_context)
        block_positions, block_generals = self._select_2x2_block(enemy_team, options)

        if not block_generals:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "目标方格内没有可被挑衅的武将",
                "details": [],
            }

        details = []
        for target in block_generals:
            target.add_debuff("forced_attack_target", caster, self.duration)
            details.append({
                "target": target.name,
                "effect": "普攻只能攻击姜维",
                "duration": self.duration,
            })

        return {
            "success": True,
            "type": "enhance_weaken",
            "block": block_positions,
            "targets_affected": len(details),
            "details": details,
        }

    def _get_options(self, targets, battle_context):
        options = {}
        context_options = getattr(battle_context, "skill_options", None)
        if isinstance(context_options, dict):
            options.update(context_options)
        if targets and isinstance(targets[0], dict):
            options.update(targets[0])
        return options

    def _select_2x2_block(self, enemy_team, options):
        row = options.get("row")
        col = options.get("col")
        if row is None or col is None:
            origin = options.get("origin") or options.get("block_origin")
            if isinstance(origin, (tuple, list)) and len(origin) >= 2:
                row, col = origin[0], origin[1]

        if row is not None and col is not None:
            row = max(0, min(1, int(row)))
            col = max(0, min(2, int(col)))
            positions = [
                (row, col), (row, col + 1),
                (row + 1, col), (row + 1, col + 1),
            ]
            return positions, self._generals_at(enemy_team, positions)

        return self._best_block(enemy_team)

    def _best_block(self, enemy_team):
        best_positions = []
        best_generals = []
        for row in range(2):
            for col in range(3):
                positions = [
                    (row, col), (row, col + 1),
                    (row + 1, col), (row + 1, col + 1),
                ]
                generals = self._generals_at(enemy_team, positions)
                if len(generals) > len(best_generals):
                    best_positions = positions
                    best_generals = generals
        return best_positions, best_generals

    def _generals_at(self, team, positions):
        return [
            team.formation[row][col]
            for row, col in positions
            if team.formation[row][col] is not None
            and team.formation[row][col].is_alive
        ]


class CorruptDanceSkill(Skill):
    """堕落之舞：邹氏对敌方全体造成固定伤害。"""

    def __init__(self):
        super().__init__(
            skill_id="corrupt_dance",
            name="堕落之舞",
            description="对敌方全体存活武将造成1点伤害",
            skill_type=SkillType.DAMAGE,
            target_type=TargetType.ALL_ENEMIES,
            cooldown=0,
            morale_cost=5,
        )
        self.damage = 1

    def execute(self, caster, targets, battle_context):
        caster_team = battle_context.get_team_for_general(caster)
        if caster_team is None:
            return {
                "success": False,
                "type": "damage",
                "message": "无法找到邹氏所属队伍",
                "details": [],
            }

        enemy_team = (
            battle_context.team2
            if caster_team == battle_context.team1
            else battle_context.team1
        )
        affected_generals = enemy_team.get_alive_generals()
        if not affected_generals:
            return {
                "success": False,
                "type": "damage",
                "message": "敌方没有可受到堕落之舞伤害的存活武将",
                "details": [],
            }

        details = []
        total_damage = 0
        for target in affected_generals:
            actual_damage = target.take_damage(self.damage, caster, "skill")
            total_damage += actual_damage
            details.append({
                "target": target.name,
                "damage": actual_damage,
            })

        return {
            "success": True,
            "type": "damage",
            "damage_per_target": self.damage,
            "targets_affected": len(details),
            "total_damage": total_damage,
            "details": details,
        }


class MeteorRiteSkill(Skill):
    """流星的仪式：小乔对敌方一横排造成固定伤害。"""

    def __init__(self):
        super().__init__(
            skill_id="meteor_rite",
            name="流星的仪式",
            description="对敌方一横排存活武将直接造成2点伤害",
            skill_type=SkillType.DAMAGE,
            target_type=TargetType.AREA_ENEMY,
            cooldown=0,
            morale_cost=5,
        )
        self.damage = 2

    def execute(self, caster, targets, battle_context):
        caster_team = battle_context.get_team_for_general(caster)
        if caster_team is None:
            return {
                "success": False,
                "type": "damage",
                "message": "无法找到小乔所属队伍",
                "details": [],
            }

        enemy_team = (
            battle_context.team2
            if caster_team == battle_context.team1
            else battle_context.team1
        )
        row = self._select_row(enemy_team, targets, battle_context)
        row_generals = [
            general
            for general in enemy_team.formation[row]
            if general is not None and general.is_alive
        ]

        if not row_generals:
            return {
                "success": False,
                "type": "damage",
                "message": "目标横排没有可受到流星的仪式伤害的武将",
                "row": row,
                "details": [],
            }

        details = []
        total_damage = 0
        for target in row_generals:
            actual_damage = target.take_damage(self.damage, caster, "skill")
            total_damage += actual_damage
            details.append({
                "target": target.name,
                "damage": actual_damage,
            })

        return {
            "success": True,
            "type": "damage",
            "row": row,
            "damage_per_target": self.damage,
            "targets_affected": len(details),
            "total_damage": total_damage,
            "details": details,
        }

    def _select_row(self, enemy_team, targets, battle_context):
        options = {}
        context_options = getattr(battle_context, "skill_options", None)
        if isinstance(context_options, dict):
            options.update(context_options)
        if targets and isinstance(targets[0], dict):
            options.update(targets[0])

        row = options.get("row")
        if row is not None:
            return max(0, min(2, int(row)))

        best_row = 0
        best_count = -1
        for candidate_row in range(3):
            count = sum(
                1
                for general in enemy_team.formation[candidate_row]
                if general is not None and general.is_alive
            )
            if count > best_count:
                best_row = candidate_row
                best_count = count
        return best_row


class SmallChainPlotSkill(Skill):
    """小连环计：王允让敌方2x1区域武将下回合普攻受限。"""

    def __init__(self):
        super().__init__(
            skill_id="small_chain_plot",
            name="小连环计",
            description="使敌方2x1方格内的武将下回合无法稳定普攻",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.AREA_ENEMY,
            cooldown=0,
            morale_cost=5,
        )
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        caster_team = battle_context.get_team_for_general(caster)
        if caster_team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到王允所属队伍",
                "details": [],
            }

        enemy_team = (
            battle_context.team2
            if caster_team == battle_context.team1
            else battle_context.team1
        )
        options = self._get_options(targets, battle_context)
        block_positions, block_generals = self._select_2x1_block(enemy_team, options)

        if not block_generals:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "目标方格内没有可施加小连环计的武将",
                "details": [],
            }

        details = []
        for target in block_generals:
            target.add_pending_debuff("attack_speed_required", 1, self.duration, 1)
            details.append({
                "target": target.name,
                "effect": "下回合普攻需攻速判定，失败则无法普攻",
                "duration": self.duration,
            })

        return {
            "success": True,
            "type": "enhance_weaken",
            "block": block_positions,
            "targets_affected": len(details),
            "details": details,
        }

    def _get_options(self, targets, battle_context):
        options = {}
        context_options = getattr(battle_context, "skill_options", None)
        if isinstance(context_options, dict):
            options.update(context_options)
        if targets and isinstance(targets[0], dict):
            options.update(targets[0])
        return options

    def _select_2x1_block(self, enemy_team, options):
        row = options.get("row")
        col = options.get("col")
        if row is None or col is None:
            origin = options.get("origin") or options.get("block_origin")
            if isinstance(origin, (tuple, list)) and len(origin) >= 2:
                row, col = origin[0], origin[1]

        orientation = options.get("orientation", "vertical")
        if row is not None and col is not None:
            row = int(row)
            col = int(col)
            if orientation in ("horizontal", "1x2", "横向"):
                row = max(0, min(2, row))
                col = max(0, min(2, col))
                positions = [(row, col), (row, col + 1)]
            else:
                row = max(0, min(1, row))
                col = max(0, min(3, col))
                positions = [(row, col), (row + 1, col)]
            return positions, self._generals_at(enemy_team, positions)

        return self._best_block(enemy_team)

    def _best_block(self, enemy_team):
        best_positions = []
        best_generals = []
        for row in range(2):
            for col in range(4):
                positions = [(row, col), (row + 1, col)]
                generals = self._generals_at(enemy_team, positions)
                if len(generals) > len(best_generals):
                    best_positions = positions
                    best_generals = generals
        return best_positions, best_generals

    def _generals_at(self, team, positions):
        return [
            team.formation[row][col]
            for row, col in positions
            if team.formation[row][col] is not None
            and team.formation[row][col].is_alive
        ]


class WeakeningChainSkill(Skill):
    """衰弱的连计：按我方连计武将数量扩大削弱目标数。"""

    def __init__(self):
        super().__init__(
            skill_id="weakening_chain",
            name="衰弱的连计",
            description="指定敌方武将武力-3；我方多位连计武将时，每多一位额外削弱一名敌将",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SINGLE_ENEMY,
            cooldown=0,
            morale_cost=4,
        )
        self.force_reduction = 3
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        caster_team = battle_context.get_team_for_general(caster)
        if caster_team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到郭皇后所属队伍",
                "details": [],
            }

        enemy_team = (
            battle_context.team2
            if caster_team == battle_context.team1
            else battle_context.team1
        )
        chain_count = sum(
            1 for general in caster_team.generals
            if general.is_alive and general.has_chain_passive()
        )
        target_count = 1 + max(0, chain_count - 1)
        selected_targets = self._select_targets(targets, enemy_team, target_count)

        if not selected_targets:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "没有可施加衰弱的敌方武将",
                "details": [],
            }

        details = []
        for target in selected_targets:
            target.add_debuff("force_reduction", self.force_reduction, self.duration)
            details.append({
                "target": target.name,
                "effect": "武力-3",
                "duration": self.duration,
            })

        return {
            "success": True,
            "type": "enhance_weaken",
            "chain_count": chain_count,
            "target_limit": target_count,
            "targets_affected": len(details),
            "details": details,
        }

    def _select_targets(self, targets, enemy_team, target_count):
        alive_enemies = [general for general in enemy_team.generals if general.is_alive]
        selected = []

        for target in targets or []:
            if target in alive_enemies and target not in selected:
                selected.append(target)
                if len(selected) >= target_count:
                    return selected

        remaining = [general for general in alive_enemies if general not in selected]
        remaining.sort(
            key=lambda general: (
                general.get_effective_force(),
                general.get_effective_intelligence(),
                general.current_hp,
            ),
            reverse=True,
        )
        selected.extend(remaining[:max(0, target_count - len(selected))])
        return selected


class FlyingDanceSkill(Skill):
    """飞天之舞：为己方全体存活武将赋予一次攻速判定。"""

    def __init__(self):
        super().__init__(
            skill_id="flying_dance",
            name="飞天之舞",
            description="我方全体存活武将获得一次攻速判定",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.ALL_ALLIES,
            cooldown=0,
            morale_cost=5,
        )
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        team = battle_context.get_team_for_general(caster)
        if team is None:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "无法找到蔡文姬所属队伍",
                "details": [],
            }

        affected_generals = team.get_alive_generals()
        if not affected_generals:
            return {
                "success": False,
                "type": "enhance_weaken",
                "message": "没有可获得飞天之舞效果的己方武将",
                "details": [],
            }

        details = []
        for general in affected_generals:
            general.add_buff("attack_speed_judgment", 1, self.duration)
            details.append({
                "target": general.name,
                "effect": "获得一次攻速判定",
                "duration": self.duration,
            })

        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": len(details),
            "details": details,
        }


class SteadfastSkill(Skill):
    """质实刚健：强化自身并免疫本回合减益。"""

    def __init__(self):
        super().__init__(
            skill_id="steadfast",
            name="质实刚健",
            description="自身武力+2，并清除和免疫本回合减益效果",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SELF,
            cooldown=0,
            morale_cost=3,
        )
        self.force_boost = 2
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        caster.debuffs.clear()
        caster.add_buff("force_boost", self.force_boost, self.duration)
        caster.add_buff("debuff_immunity", 1, self.duration)
        return {
            "success": True,
            "type": "enhance_weaken",
            "targets_affected": 1,
            "details": [{
                "target": caster.name,
                "effect": "武力+2，清除并免疫减益",
                "duration": self.duration,
            }],
        }


class GuardTacticsSkill(Skill):
    """防护战术：许褚给自己套上一次减伤护盾。"""

    def __init__(self):
        super().__init__(
            skill_id="guard_tactics",
            name="防护战术",
            description="自身获得护盾，下一次受到伤害时减免3点伤害",
            skill_type=SkillType.ENHANCE_WEAKEN,
            target_type=TargetType.SELF,
            cooldown=0,
            morale_cost=4,
        )
        self.shield_value = 3
        self.duration = 1

    def execute(self, caster, targets, battle_context):
        caster.add_buff("damage_shield", self.shield_value, self.duration)
        return {
            "success": True,
            "type": "enhance_weaken",
            "caster": caster.name,
            "effect": "damage_shield",
            "shield_value": self.shield_value,
            "duration": self.duration,
            "details": [{
                "target": caster.name,
                "effect": f"下一次受到伤害减免{self.shield_value}点",
                "duration": self.duration,
            }],
        }


# ==================== 现有技能 ====================

# 强化战术 - 自身武力+4，本回合结束后失效
STRENGTH_TACTICS = EnhanceWeakenSkill(
    skill_id="strength_tactics",
    name="强化战术",
    description="使自己在本回合内武力+4，回合结束后失效",
    target_type=TargetType.SELF,
    effect_type="force_boost",
    effect_value=4,
    duration=1,
    cooldown=0,
    morale_cost=4
)

# 同盟缔结 - 己方士气最大值+2
ALLIANCE_PACT = EnhanceWeakenSkill(
    skill_id="alliance_pact",
    name="同盟缔结",
    description="己方士气最大值+2，从本回合开始生效",
    target_type=TargetType.SELF,
    effect_type="morale_max_boost",
    effect_value=2,
    duration=999,
    cooldown=0,
    morale_cost=2
)

# ==================== 新增技能 ====================

# 猛攻 - 对单体敌人造成1.5倍伤害
FIERCE_ATTACK = DamageSkill(
    skill_id="fierce_attack",
    name="猛攻",
    description="对一名敌人造成1.5倍普攻伤害",
    target_type=TargetType.SINGLE_ENEMY,
    damage_multiplier=1.5,
    cooldown=2,
    morale_cost=3
)

# 鼓舞 - 己方全体武力+2
RALLY = EnhanceWeakenSkill(
    skill_id="rally",
    name="鼓舞",
    description="己方全体武将武力+2，持续1回合",
    target_type=TargetType.ALL_ALLIES,
    effect_type="force_boost",
    effect_value=2,
    duration=1,
    cooldown=2,
    morale_cost=3
)

# 火计 - 对单体敌人造成2倍伤害
FIRE_ATTACK = DamageSkill(
    skill_id="fire_attack",
    name="火计",
    description="对一名敌人造成2倍普攻伤害",
    target_type=TargetType.SINGLE_ENEMY,
    damage_multiplier=2.0,
    cooldown=3,
    morale_cost=5
)

# 威压 - 降低敌方单体武力
INTIMIDATE = EnhanceWeakenSkill(
    skill_id="intimidate",
    name="威压",
    description="使一名敌方武将武力-3，持续1回合",
    target_type=TargetType.SINGLE_ENEMY,
    effect_type="force_reduction",
    effect_value=3,
    duration=1,
    cooldown=2,
    morale_cost=3
)

# 全军攻城 - 曹操专属技能
SIEGE_ALL_ARMY = SiegeRowSkill()

# 石兵八阵 - 诸葛亮专属技能
STONE_SENTINEL_MAZE = StoneSentinelMazeSkill()

# 天下无双 - 吕布专属技能
PEERLESS_UNDER_HEAVEN = PeerlessUnderHeavenSkill()

# 轮枪战术 - 张飞专属技能
SPEAR_WHEEL_TACTICS = SpearWheelTacticsSkill()

# 挑衅 - 姜维专属技能
TAUNT = TauntSkill()

# 魏王的卫兵 - 夏侯惇专属技能
WEI_KING_GUARD = WeiKingGuardSkill()

# 人马一体 - 张辽专属技能
CAVALRY_UNITY = CavalryUnitySkill()

# 魏武精英 - 于禁专属技能
WEI_ELITE = WeiEliteSkill()

# 击飞战术 - 带来洞主专属技能
KNOCKBACK_TACTICS = KnockbackTacticsSkill()

# 神速战术 - 夏侯渊专属技能
DIVINE_SPEED_TACTICS = DivineSpeedTacticsSkill()

# 人马大号令 - 董卓专属技能
GRAND_CAVALRY_ORDER = GrandCavalryOrderSkill()

# 贼军讨伐令 - 皇甫嵩专属技能
BANDIT_SUPPRESSION_ORDER = BanditSuppressionOrderSkill()

# 白马阵 - 公孙瓒专属技能
WHITE_HORSE_FORMATION = WhiteHorseFormationSkill()

# 敕命 - 汉献帝专属技能
IMPERIAL_EDICT = ImperialEdictSkill()

# 破坏性的献策 - 陈宫专属技能
DESTRUCTIVE_ADVICE = DestructiveAdviceSkill()

# 联合围攻 - 于夫罗专属技能
UNITED_SIEGE = UnitedSiegeSkill()

# 卑劣的奇袭 - 李傕和郭汜专属技能
VILE_RAID = VileRaidSkill()

# 士气旺盛 - 文丑专属技能
HIGH_MORALE = HighMoraleSkill()

# 率先立功 - 张郃专属技能
FIRST_MERIT = FirstMeritSkill()

# 刹那的号令 - 曹仁专属技能
MOMENTARY_ORDER = MomentaryOrderSkill()

# 缜密的攻势 - 田丰专属技能
METICULOUS_OFFENSE = MeticulousOffenseSkill()

# 雷击 - 夏侯月姬专属技能
THUNDER_STRIKE = ThunderStrikeSkill()

# 江东的大美人 - 大乔专属技能
JIANGDONG_BEAUTY = JiangdongBeautySkill()

# 天衣无缝 - 太史慈专属技能
FLAWLESS = FlawlessSkill()

# 夫子的教诲 - 司马徽专属技能
MASTER_TEACHING = MasterTeachingSkill()

# 防栅重建 - 朱然专属技能
FENCE_REBUILD = FenceRebuildSkill()

# 流星的仪式 - 小乔专属技能
METEOR_RITE = MeteorRiteSkill()

# 堕落之舞 - 邹氏专属技能
CORRUPT_DANCE = CorruptDanceSkill()

# 太平要术 - 张角专属技能
TAIPING_ARTS = TaipingArtsSkill()

# 离间谋略 - 贾诩专属技能
DISCORD_STRATEGY = DiscordStrategySkill()

# 以牙还牙 - 王异专属技能
TOOTH_FOR_TOOTH = ToothForToothSkill()

# 小连环计 - 王允专属技能
SMALL_CHAIN_PLOT = SmallChainPlotSkill()

# 衰弱的连计 - 郭皇后专属技能
WEAKENING_CHAIN = WeakeningChainSkill()

# 飞天之舞 - 蔡文姬专属技能
FLYING_DANCE = FlyingDanceSkill()

# 质实刚健 - 马岱专属技能
STEADFAST = SteadfastSkill()

# 防护战术 - 许褚专属技能
GUARD_TACTICS = GuardTacticsSkill()

# ==================== 技能字典 ====================

ALL_SKILLS = {
    "strength_tactics": STRENGTH_TACTICS,
    "alliance_pact": ALLIANCE_PACT,
    "fierce_attack": FIERCE_ATTACK,
    "rally": RALLY,
    "fire_attack": FIRE_ATTACK,
    "intimidate": INTIMIDATE,
    "siege_all_army": SIEGE_ALL_ARMY,
    "stone_sentinel_maze": STONE_SENTINEL_MAZE,
    "peerless_under_heaven": PEERLESS_UNDER_HEAVEN,
    "spear_wheel_tactics": SPEAR_WHEEL_TACTICS,
    "taunt": TAUNT,
    "wei_king_guard": WEI_KING_GUARD,
    "cavalry_unity": CAVALRY_UNITY,
    "wei_elite": WEI_ELITE,
    "knockback_tactics": KNOCKBACK_TACTICS,
    "divine_speed_tactics": DIVINE_SPEED_TACTICS,
    "grand_cavalry_order": GRAND_CAVALRY_ORDER,
    "bandit_suppression_order": BANDIT_SUPPRESSION_ORDER,
    "white_horse_formation": WHITE_HORSE_FORMATION,
    "imperial_edict": IMPERIAL_EDICT,
    "destructive_advice": DESTRUCTIVE_ADVICE,
    "united_siege": UNITED_SIEGE,
    "vile_raid": VILE_RAID,
    "high_morale": HIGH_MORALE,
    "first_merit": FIRST_MERIT,
    "momentary_order": MOMENTARY_ORDER,
    "meticulous_offense": METICULOUS_OFFENSE,
    "thunder_strike": THUNDER_STRIKE,
    "jiangdong_beauty": JIANGDONG_BEAUTY,
    "flawless": FLAWLESS,
    "master_teaching": MASTER_TEACHING,
    "fence_rebuild": FENCE_REBUILD,
    "meteor_rite": METEOR_RITE,
    "corrupt_dance": CORRUPT_DANCE,
    "taiping_arts": TAIPING_ARTS,
    "discord_strategy": DISCORD_STRATEGY,
    "tooth_for_tooth": TOOTH_FOR_TOOTH,
    "small_chain_plot": SMALL_CHAIN_PLOT,
    "weakening_chain": WEAKENING_CHAIN,
    "flying_dance": FLYING_DANCE,
    "steadfast": STEADFAST,
    "guard_tactics": GUARD_TACTICS,
}


def get_skill_by_id(skill_id: str):
    """根据技能ID获取技能对象"""
    return ALL_SKILLS.get(skill_id)

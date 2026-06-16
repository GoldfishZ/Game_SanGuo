"""
技能配置文件
包含游戏中需要的所有主动技能定义
"""

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

# 魏王的卫兵 - 夏侯惇专属技能
WEI_KING_GUARD = WeiKingGuardSkill()

# 人马一体 - 张辽专属技能
CAVALRY_UNITY = CavalryUnitySkill()

# 人马大号令 - 董卓专属技能
GRAND_CAVALRY_ORDER = GrandCavalryOrderSkill()

# 敕命 - 汉献帝专属技能
IMPERIAL_EDICT = ImperialEdictSkill()

# 刹那的号令 - 曹仁专属技能
MOMENTARY_ORDER = MomentaryOrderSkill()

# 缜密的攻势 - 田丰专属技能
METICULOUS_OFFENSE = MeticulousOffenseSkill()

# 江东的大美人 - 大乔专属技能
JIANGDONG_BEAUTY = JiangdongBeautySkill()

# 天衣无缝 - 太史慈专属技能
FLAWLESS = FlawlessSkill()

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
    "wei_king_guard": WEI_KING_GUARD,
    "cavalry_unity": CAVALRY_UNITY,
    "grand_cavalry_order": GRAND_CAVALRY_ORDER,
    "imperial_edict": IMPERIAL_EDICT,
    "momentary_order": MOMENTARY_ORDER,
    "meticulous_offense": METICULOUS_OFFENSE,
    "jiangdong_beauty": JIANGDONG_BEAUTY,
    "flawless": FLAWLESS,
}


def get_skill_by_id(skill_id: str):
    """根据技能ID获取技能对象"""
    return ALL_SKILLS.get(skill_id)

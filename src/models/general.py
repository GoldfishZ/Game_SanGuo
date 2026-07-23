"""
武将模型类
定义武将的基本属性和行为
"""

from typing import List, Dict, Optional, TYPE_CHECKING
from enum import Enum
import random

if TYPE_CHECKING:
    from ..skills.skill_base import Skill, PassiveSkill


def round_half_up(value: float) -> int:
    """四舍五入到整数。"""
    return int(value + 0.5)


def odd_even_judgment(guess: str = None) -> dict:
    """抛一枚六面骰并判定猜奇偶是否成功。"""
    normalized_guess = guess
    if normalized_guess in ("奇", "odd", "ODD"):
        normalized_guess = "odd"
    elif normalized_guess in ("偶", "even", "EVEN"):
        normalized_guess = "even"
    else:
        normalized_guess = random.choice(["odd", "even"])

    dice = random.randint(1, 6)
    parity = "odd" if dice % 2 else "even"
    return {
        "guess": normalized_guess,
        "dice": dice,
        "parity": parity,
        "success": normalized_guess == parity,
    }


class Camp(Enum):
    """阵营枚举"""
    WEI = "魏"
    SHU = "蜀" 
    WU = "吴"
    LIANG = "凉"
    YUAN = "袁"
    TA = "他"


class Rarity(Enum):
    """稀有度枚举"""
    COMMON = 1      # 普通卡
    RARE = 2        # 黑卡
    EPIC = 3        # 色卡
    LEGENDARY = 4   # 闪色卡


class Position(Enum):
    """位置枚举"""
    FRONT = "前排"
    MIDDLE = "中排"
    BACK = "后排"

class Attribute(Enum):
    """武将属性枚举"""
    BRAVERY = "勇猛"      # 勇猛
    CHARISMA = "魅力"     # 魅力
    RECRUIT = "募兵"      # 募兵
    FENCE = "防栅"        # 防栅
    CHAIN = "连计"        # 连计
    REVIVE = "复活"       # 复活
    AMBUSH = "伏兵"       # 伏兵
    
    def __str__(self):
        return self.value


class General:
    """武将类"""
    
    def __init__(self,
                 general_id: int,
                 name: str,
                 camp: Camp,
                 rarity: Rarity,
                 cost: float,
                 force: int,
                 intelligence: int,
                 attribute: List[Attribute] = None,
                 active_skill: 'Skill' = None,
                 passive_skills: List['PassiveSkill'] = None,
                 image_file: str = None):
        """
        初始化武将

        Args:
            general_id: 武将ID
            name: 武将姓名
            camp: 所属阵营
            rarity: 稀有度
            cost: 费用
            force: 武力
            intelligence: 智力
            attribute: 属性列表（对应被动技能）
            active_skill: 主动技能（只能有一个）
            passive_skills: 被动技能列表（基于attribute）
            image_file: 武将卡图片文件名（相对于 assets/images/generals/）
        """
        self.general_id = general_id
        self.name = name
        self.camp = camp
        self.rarity = rarity
        self.cost = cost
        self.force = force
        self.intelligence = intelligence
        # 最大生命值 = 武力 + 智力
        self.max_hp = force + intelligence
        self.current_hp = self.max_hp
        self.attribute = attribute or []
        self.active_skill = active_skill
        self.passive_skills = passive_skills or []
        self.image_file = image_file  # 武将卡图片文件名
        
        # 战斗状态
        self.position: Optional[Position] = None
        self.is_alive = True
        self.buffs: List[Dict] = []  # 增益效果
        self.debuffs: List[Dict] = []  # 减益效果
        self.pending_buffs: List[Dict] = []  # 延迟生效的增益效果
        self.pending_debuffs: List[Dict] = []  # 延迟生效的减益效果
        
        # 技能冷却管理
        self.active_skill_cooldown = 0  # 主动技能当前冷却时间
        self.active_skill_usage_counts = {}  # 主动技能使用次数（按武将实例记录）
        self.last_attack_speed_judgment = None
        self._has_attacked_this_turn = False  # 本回合是否已普攻
        self._extra_attack_available = False  # 攻速判定成功后可用的一次追加普攻
        self._has_used_skill_this_turn = False  # 本回合是否已使用技能
        # 仅用于表现层的短期事件队列。战斗规则仍由模型本身结算，Web 前端
        # 消费这些事件来按真实顺序播放防栅、护盾、复活等反馈。
        self._combat_events: List[Dict] = []

        # 所属队伍弱引用（由 Team.add_general 设置，用于连环等需要团队信息的被动技能）
        self._team = None

    def record_combat_event(self, event_type: str, **payload) -> None:
        """记录一次可视化战斗事件，不参与任何数值结算。"""
        event = {
            "type": event_type,
            "general_id": self.general_id,
            "target": self.name,
        }
        event.update(payload)
        self._combat_events.append(event)

    def drain_combat_events(self) -> List[Dict]:
        """取出并清空尚未被表现层消费的战斗事件。"""
        events = list(self._combat_events)
        self._combat_events.clear()
        return events
        
    def take_damage(self, damage: int, attacker: 'General' = None,
                    damage_source: str = "basic_attack",
                    charisma_guess: str = None) -> int:
        """
        受到伤害
        
        Args:
            damage: 伤害值
            attacker: 攻击者（用于触发被动技能）
            
        Returns:
            实际受到的伤害
        """
        original_damage = damage
        actual_damage = max(0, damage)
        
        ignores_fence = (
            damage_source == "basic_attack"
            and attacker is not None
            and attacker.has_buff_type("ignore_fence")
        )

        if damage_source != "guard_share":
            actual_damage = self.share_damage_with_cao_guard(actual_damage, attacker)

        # 触发防栅被动技能（仅普攻，攻城状态可无视）
        if self.has_passive_skill("防栅") and not ignores_fence:
            fence_passive = self.get_passive_skill("防栅")
            fence_was_active = fence_passive.is_active
            actual_damage = fence_passive.trigger_on_receive_damage(
                self, actual_damage, damage_source
            )
            if fence_was_active and not fence_passive.is_active:
                self.record_combat_event(
                    "fence_block", attacker=getattr(attacker, "name", ""),
                    blocked=original_damage,
                )

        # 护盾在防栅之后结算，避免被完全抵挡的普攻消耗护盾。
        if actual_damage > 0:
            for index, buff in enumerate(self.buffs):
                if buff.get("type") == "damage_shield":
                    shield_value = max(0, int(buff.get("value", 0)))
                    absorbed = min(actual_damage, shield_value)
                    actual_damage = max(0, actual_damage - shield_value)
                    del self.buffs[index]
                    self.record_combat_event(
                        "shield_absorb", attacker=getattr(attacker, "name", ""),
                        absorbed=absorbed, remaining=0,
                    )
                    break
        
        # 触发连环被动技能（伤害分担）
        if self.has_chain_passive():
            chain_passive = self.get_chain_passive()
            # 找到己方所有拥有连计的存活武将，分担伤害
            chain_generals = []
            if self._team:
                for g in self._team.generals:
                    if g.is_alive and g.has_chain_passive():
                        chain_generals.append(g)
            if len(chain_generals) > 1:
                actual_damage = chain_passive.share_damage(chain_generals, actual_damage)
                self.record_combat_event(
                    "chain_share", damage=actual_damage,
                    linked=[g.name for g in chain_generals],
                )
                # 将分担后的伤害应用到每个连计武将（跳过自己，已经算过了）
                for g in chain_generals:
                    if g != self:
                        g.current_hp = max(0, g.current_hp - actual_damage)
                        if g.current_hp <= 0:
                            g.is_alive = False
        
        # 记录是否是致死伤害
        is_fatal = (self.current_hp - actual_damage) <= 0
        fatal_damage = actual_damage if is_fatal else 0
        
        self.current_hp = max(0, self.current_hp - actual_damage)
        
        if self.current_hp <= 0:
            self.is_alive = False
            
            # 触发复活被动技能
            if self.has_passive_skill("复活"):
                revive_passive = self.get_passive_skill("复活")
                if revive_passive.trigger_on_death(self):
                    self.record_combat_event("revive", hp=self.current_hp)
            
            # 复活优先于魅力；只有最终仍然阵亡时才进行魅力判定。
            if not self.is_alive and self.has_passive_skill("魅力") and attacker:
                charisma_passive = self.get_passive_skill("魅力")
                return_damage = charisma_passive.trigger_on_death(
                    self, attacker, fatal_damage, guess=charisma_guess,
                )
                judgment = getattr(charisma_passive, "last_judgment", None)
                self.record_combat_event(
                    "charisma_judgment", attacker=attacker.name,
                    attacker_id=attacker.general_id,
                    judgment=dict(judgment) if judgment else None,
                    reflected=return_damage, fatal_damage=fatal_damage,
                )
                if return_damage > 0:
                    attacker.take_damage(return_damage, self, "passive")
                    
        return actual_damage
    
    def heal(self, amount: int) -> int:
        """
        治疗
        
        Args:
            amount: 治疗量
            
        Returns:
            实际治疗量
        """
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp - old_hp
    
    def get_effective_force(self) -> int:
        """获取当前有效武力值（包含buff/debuff）"""
        effective_force = self.force
        
        # 计算buff效果
        for buff in self.buffs:
            if buff['type'] == 'force_boost':
                effective_force += buff['value']
                
        # 计算debuff效果
        for debuff in self.debuffs:
            if debuff['type'] == 'force_reduction':
                effective_force -= debuff['value']
                
        return max(0, effective_force)
    
    def get_effective_intelligence(self) -> int:
        """获取当前有效智力值（包含buff/debuff）"""
        effective_intelligence = self.intelligence
        
        # 计算buff效果
        for buff in self.buffs:
            if buff['type'] == 'intelligence_boost':
                effective_intelligence += buff['value']
                
        # 计算debuff效果
        for debuff in self.debuffs:
            if debuff['type'] == 'intelligence_reduction':
                effective_intelligence -= debuff['value']
                
        return max(0, effective_intelligence)
    
    def calculate_damage_to(self, target: 'General') -> int:
        """
        计算对目标武将的伤害值
        
        Args:
            target: 目标武将
            
        Returns:
            造成的伤害值
        """
        # 获取攻击方的有效武力和智力
        attacker_force = self.get_effective_force()
        attacker_intelligence = self.get_effective_intelligence()
        
        # 获取目标的有效武力和智力
        target_force = target.get_effective_force()
        target_intelligence = target.get_effective_intelligence()
        
        # 按照游戏规则计算伤害：武力占优时取武力差，否则综合差最多 3 点。
        if attacker_force > target_force:
            damage = attacker_force - target_force
        else:
            damage = (attacker_force + attacker_intelligence) - (target_force + target_intelligence)
            damage = min(3, damage)

        return max(1, damage)
    
    def attack(self, target: 'General', guess: str = None,
               bravery_guess: str = None, charisma_guess: str = None) -> int:
        """
        攻击目标武将（每回合每名武将只能调用一次）

        Args:
            target: 目标武将
            guess: 攻速判定时的奇偶猜测
            bravery_guess: 勇猛判定的奇偶猜测
            charisma_guess: 目标受到致命伤害时的魅力判定猜测

        Returns:
            实际造成的伤害
        """
        if not self.is_alive or not target.is_alive:
            return 0
        if self._has_attacked_this_turn and not self._extra_attack_available:
            return 0  # 本回合普攻与追加普攻均已用完
        forced_target = self.get_forced_attack_target()
        if forced_target is not None and target is not forced_target:
            return 0
        if forced_target is None and self.has_buff_type("front_only_attack") and not self.can_attack_front_target(target):
            return 0

        # 攻速判定成功后获得的追加普攻不再触发第二次判定。
        if self._extra_attack_available:
            self._extra_attack_available = False
            return self._perform_basic_attack_once(
                target, bravery_guess=bravery_guess, charisma_guess=charisma_guess,
            )

        # 攻速限制判定（debuff：必须猜对才能普攻）
        if self.has_debuff_type("attack_speed_required"):
            self.consume_debuff_type("attack_speed_required")
            judgment = odd_even_judgment(guess)
            self.last_attack_speed_judgment = judgment
            if not judgment["success"]:
                self._has_attacked_this_turn = True
                return 0

        actual_damage = self._perform_basic_attack_once(
            target, bravery_guess=bravery_guess, charisma_guess=charisma_guess,
        )
        self._has_attacked_this_turn = True

        # 攻速判定（buff：猜对则获得一次可自行选目标的追加普攻）。
        if self.has_buff_type("attack_speed_judgment"):
            self.consume_buff_type("attack_speed_judgment")
            judgment = odd_even_judgment(guess)
            self.last_attack_speed_judgment = judgment
            if judgment["success"] and self.is_alive:
                self._extra_attack_available = True

        return actual_damage

    def _perform_basic_attack_once(self, target: 'General', *,
                                   bravery_guess: str = None,
                                   charisma_guess: str = None) -> int:
        """执行一次基础普攻结算。"""
        damage = self.calculate_damage_to(target)
        
        # 触发勇猛被动技能
        if self.has_passive_skill("勇猛"):
            bravery_passive = self.get_passive_skill("勇猛")
            before_damage = damage
            bravery_passive.last_judgment = None
            damage = bravery_passive.trigger_on_attack(
                self, target, damage, guess=bravery_guess,
            )
            judgment = getattr(bravery_passive, "last_judgment", None)
            if self.current_hp < self.max_hp / 2 and judgment:
                self.record_combat_event(
                    "bravery_judgment", target=target.name,
                    judgment=dict(judgment), bonus=max(0, damage - before_damage),
                )
        
        # 伏兵反击：相邻隐藏伏兵可对攻击者造成反击伤害
        if target._team:
            target._team.resolve_ambush_interception(
                self, target, damage
            )
        
        actual_damage = target.take_damage(
            damage, self, "basic_attack", charisma_guess=charisma_guess,
        )
        if (
            actual_damage > 0
            and self.has_buff_type("knockback_on_damage")
            and target.is_alive
            and target._team
        ):
            target._team.knock_back_with_rear_general(target)
        
        return actual_damage
    
    def add_buff(self, buff_type: str, value: int, duration: int):
        """添加增益效果"""
        self.buffs.append({
            'type': buff_type,
            'value': value,
            'duration': duration
        })
        self.sync_chain_effects()

    def add_pending_buff(self, buff_type: str, value: int, duration: int, delay_turns: int):
        """添加一个延迟生效的增益效果。"""
        self.pending_buffs.append({
            'type': buff_type,
            'value': value,
            'duration': duration,
            'delay_turns': max(1, delay_turns),
        })

    def add_pending_debuff(self, debuff_type: str, value: int, duration: int, delay_turns: int):
        """添加一个延迟生效的减益效果。"""
        self.pending_debuffs.append({
            'type': debuff_type,
            'value': value,
            'duration': duration,
            'delay_turns': max(1, delay_turns),
        })
    
    def add_debuff(self, debuff_type: str, value: int, duration: int):
        """添加减益效果"""
        if self.has_buff_type("debuff_immunity"):
            return
        self.debuffs.append({
            'type': debuff_type,
            'value': value,
            'duration': duration
        })
        self.sync_chain_effects()

    def has_buff_type(self, buff_type: str) -> bool:
        """检查当前是否拥有指定类型的增益状态。"""
        return any(buff.get('type') == buff_type for buff in self.buffs)

    def consume_buff_type(self, buff_type: str) -> bool:
        """消耗一个指定类型的增益状态。"""
        for index, buff in enumerate(self.buffs):
            if buff.get('type') == buff_type:
                del self.buffs[index]
                return True
        return False

    def has_debuff_type(self, debuff_type: str) -> bool:
        """检查当前是否拥有指定类型的减益状态。"""
        return any(debuff.get('type') == debuff_type for debuff in self.debuffs)

    def consume_debuff_type(self, debuff_type: str) -> bool:
        """消耗一个指定类型的减益状态。"""
        for index, debuff in enumerate(self.debuffs):
            if debuff.get('type') == debuff_type:
                del self.debuffs[index]
                return True
        return False

    def share_damage_with_cao_guard(self, damage: int, attacker: 'General' = None) -> int:
        """曹操受伤时，由同队存活的夏侯惇常驻承担一半伤害。"""
        if self.name != "曹操" or not self._team or damage <= 0:
            return damage

        for general in self._team.get_alive_generals():
            if general is self:
                continue
            if general.name == "夏侯惇":
                guard_damage = min(damage, round_half_up(damage / 2))
                remaining_damage = max(0, damage - guard_damage)
                general.take_damage(guard_damage, attacker, "guard_share")
                return remaining_damage

        return damage

    def get_forced_attack_target(self):
        """Return the living target this general must attack, if taunted."""
        for debuff in self.debuffs:
            if debuff.get("type") == "forced_attack_target":
                target = debuff.get("value")
                if target is not None and getattr(target, "is_alive", False):
                    return target
        return None

    def can_attack_front_target(self, target: 'General') -> bool:
        """攻城状态下只能攻击正前方同列且可被普攻选中的武将。"""
        if not self._team or not target._team:
            return True
        attacker_pos = self._team.get_general_position(self)
        target_pos = target._team.get_general_position(target)
        if attacker_pos is None or target_pos is None:
            return True
        if attacker_pos[1] != target_pos[1]:
            return False
        return target in target._team.get_attackable_targets()
    
    def update_effects(self):
        """更新效果持续时间和技能冷却（每回合开始时调用）"""
        # 重置本回合攻击和技能状态
        self._has_attacked_this_turn = False
        self._extra_attack_available = False
        self._has_used_skill_this_turn = False

        self.buffs = [buff for buff in self.buffs if buff['duration'] > 1]
        self.debuffs = [debuff for debuff in self.debuffs if debuff['duration'] > 1]

        # 减少持续时间
        for buff in self.buffs:
            buff['duration'] -= 1
        for debuff in self.debuffs:
            debuff['duration'] -= 1

        self.activate_pending_buffs()
        self.activate_pending_debuffs()

        # 更新主动技能冷却
        if self.active_skill_cooldown > 0:
            self.active_skill_cooldown -= 1

        # 防栅：被攻破后两回合重建
        if self.has_passive_skill("防栅"):
            fence_passive = self.get_passive_skill("防栅")
            fence_passive.update_rebuild(self)

        # 连计：同步效果到所有连计武将
        self.sync_chain_effects()

    def activate_pending_buffs(self):
        """将到期的延迟增益加入当前增益列表。"""
        remaining_pending_buffs = []
        for pending in self.pending_buffs:
            pending['delay_turns'] -= 1
            if pending['delay_turns'] <= 0:
                self.add_buff(
                    pending['type'],
                    pending['value'],
                    pending['duration'],
                )
            else:
                remaining_pending_buffs.append(pending)
        self.pending_buffs = remaining_pending_buffs

    def activate_pending_debuffs(self):
        """将到期的延迟减益加入当前减益列表。"""
        remaining_pending_debuffs = []
        for pending in self.pending_debuffs:
            pending['delay_turns'] -= 1
            if pending['delay_turns'] <= 0:
                self.add_debuff(
                    pending['type'],
                    pending['value'],
                    pending['duration'],
                )
            else:
                remaining_pending_debuffs.append(pending)
        self.pending_debuffs = remaining_pending_debuffs
    
    def trigger_turn_start_passives(self):
        """触发回合开始时的被动技能"""
        events = []
        # 触发募兵被动技能
        if self.has_passive_skill("募兵"):
            recruit_passive = self.get_passive_skill("募兵")
            heal_amount = recruit_passive.trigger_on_turn_start(self)
            if heal_amount > 0:
                event = {
                    "type": "recruit_heal",
                    "general_id": self.general_id,
                    "target": self.name,
                    "amount": heal_amount,
                    "hp": self.current_hp,
                }
                self._combat_events.append(event)
                events.append(event)
        return events
    
    def has_passive_skill(self, skill_name: str) -> bool:
        """检查是否拥有指定的被动技能"""
        names = [skill_name]
        if skill_name == "连环":
            names.append("连计")
        elif skill_name == "连计":
            names.append("连环")
        return any(skill.name in names for skill in self.passive_skills)
    
    def get_passive_skill(self, skill_name: str):
        """获取指定的被动技能实例"""
        for skill in self.passive_skills:
            if skill.name == skill_name:
                return skill
            if skill_name in ("连环", "连计") and skill.name in ("连环", "连计"):
                return skill
        return None

    def has_chain_passive(self) -> bool:
        """兼容旧名“连环”和新名“连计”。"""
        return self.has_passive_skill("连计")

    def get_chain_passive(self):
        """获取连计被动实例。"""
        return self.get_passive_skill("连计")

    def sync_chain_effects(self):
        """同步己方连计武将的增益和减益效果。"""
        if not self.has_chain_passive() or not self._team:
            return
        chain_generals = [
            g for g in self._team.generals
            if g.is_alive and g.has_chain_passive()
        ]
        if len(chain_generals) <= 1:
            return

        # 取每种相同效果在单个武将上的最大叠加数，而不是把每个已同步副本
        # 再次相加。否则每次 update_effects 都会令列表指数增长。
        def merge_effects(attribute):
            merged = []
            for general in chain_generals:
                seen_on_general = []
                for effect in getattr(general, attribute):
                    occurrence = sum(1 for item in seen_on_general if item == effect) + 1
                    seen_on_general.append(effect)
                    existing = sum(1 for item in merged if item == effect)
                    if existing < occurrence:
                        merged.append(effect.copy())
            return merged

        all_buffs = merge_effects("buffs")
        all_debuffs = merge_effects("debuffs")
        for g in chain_generals:
            g.buffs = [b.copy() for b in all_buffs]
            g.debuffs = [d.copy() for d in all_debuffs]
    
    def can_be_targeted_by_enemy(self, team_generals=None) -> bool:
        """检查是否可以被敌方选中（考虑伏兵等效果）"""
        if not self.is_alive:
            return False
        
        # 检查伏兵被动技能
        if self.has_passive_skill("伏兵"):
            ambush_passive = self.get_passive_skill("伏兵")
            if team_generals:
                return ambush_passive.can_be_targeted(self, team_generals)
            else:
                return not ambush_passive.is_hidden
        
        return True
    
    def can_attack(self) -> bool:
        """检查本回合是否还可以普攻（含攻速判定成功后的追加普攻）。"""
        return self.is_alive and (
            not self._has_attacked_this_turn or self._extra_attack_available
        )

    def can_use_skill(self) -> bool:
        """检查本回合是否还可以使用技能"""
        return self.is_alive and not self._has_used_skill_this_turn

    def can_use_active_skill(self) -> bool:
        """检查是否可以使用主动技能"""
        if not self.is_alive:
            return False
        if not self.active_skill:
            return False
        if self.active_skill_cooldown > 0:
            return False
        return True
    
    def use_active_skill(self, targets: List['General'], battle_context, team=None, guess=None) -> Dict:
        """
        使用主动技能
        
        Args:
            targets: 目标列表
            battle_context: 战斗上下文
            team: 队伍对象（用于管理士气）
            
        Returns:
            技能使用结果
        """
        if not self.can_use_active_skill():
            return {"success": False, "message": "无法使用主动技能"}
        
        if not self.active_skill:
            return {"success": False, "message": "没有主动技能"}

        if hasattr(self.active_skill, "can_use") and not self.active_skill.can_use(self, team):
            return {"success": False, "message": "技能无法使用"}
        
        # 如果有队伍对象，检查并消耗士气
        if team is not None:
            if team.current_morale < self.active_skill.morale_cost:
                return {"success": False, "message": "士气不足"}
            if not team.consume_morale(self.active_skill.morale_cost):
                return {"success": False, "message": "士气消耗失败"}
        
        # 设置冷却时间
        self.active_skill_cooldown = self.active_skill.cooldown
        
        # 执行技能效果
        if guess is not None and hasattr(self.active_skill, 'execute'):
            import inspect
            sig = inspect.signature(self.active_skill.execute)
            if 'guess' in sig.parameters:
                result = self.active_skill.execute(self, targets, battle_context, guess=guess)
            else:
                result = self.active_skill.execute(self, targets, battle_context)
        else:
            result = self.active_skill.execute(self, targets, battle_context)
        if result.get("success") and self.has_passive_skill("伏兵"):
            ambush_passive = self.get_passive_skill("伏兵")
            if ambush_passive.is_hidden:
                self.record_combat_event(
                    "ambush_reveal", reason="skill", skill=self.active_skill.name,
                )
            ambush_passive.reveal_after_skill_use()
        result["skill_name"] = self.active_skill.name
        result["caster"] = self.name
        result["morale_consumed"] = self.active_skill.morale_cost
        if result.get("success"):
            self._has_used_skill_this_turn = True
        if team:
            result["remaining_morale"] = team.current_morale
        
        return result
    
    def __str__(self) -> str:
        """字符串表示"""
        status = "存活" if self.is_alive else "阵亡"
        attrs = "/".join([attr.value for attr in self.attribute]) if self.attribute else "无"
        return f"{self.name}({self.camp.value}) [{attrs}] - HP:{self.current_hp}/{self.max_hp} 武力:{self.force} 智力:{self.intelligence} [{status}]"
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'general_id': self.general_id,
            'name': self.name,
            'camp': self.camp.value,
            'rarity': self.rarity.value,
            'max_hp': self.max_hp,
            'current_hp': self.current_hp,
            'cost': self.cost,
            'force': self.force,
            'intelligence': self.intelligence,
            'attribute': [attr.value for attr in self.attribute],
            'active_skill': self.active_skill.name if self.active_skill else None,
            'active_skill_cooldown': self.active_skill_cooldown,
            'passive_skills': [skill.name for skill in self.passive_skills],
            'is_alive': self.is_alive,
            'image_file': self.image_file,
        }

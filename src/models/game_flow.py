"""
游戏主流程控制器
管理整个游戏的流程和状态
"""

import random
from typing import List, Dict, Optional, Tuple
from src.models.general import General
from src.models.team import Team, Camp
from game_data.generals_config import get_all_generals, GENERAL_CREATORS


class GamePhase:
    """游戏阶段枚举"""
    MENU = "主菜单"
    GENERAL_SELECTION = "选将阶段"
    FORMATION_SETUP = "阵型布置阶段"
    DICE_ROLL = "抛骰子决定先手"
    BATTLE = "战斗阶段"
    SKILL_PHASE = "技能使用阶段"
    ATTACK_PHASE = "普攻阶段"
    GAME_OVER = "游戏结束"


class Player:
    """玩家类"""
    
    def __init__(self, player_id: int, name: str):
        self.player_id = player_id
        self.name = name
        self.team = Team(f"{name}的队伍")
        self.selected_generals: List[General] = []
    
    def add_general_to_team(self, general: General):
        """添加武将到队伍"""
        self.selected_generals.append(general)
        self.team.add_general(general)
    
    def is_defeated(self) -> bool:
        """检查是否败北（所有武将阵亡）"""
        return self.team.is_defeated()


class GameFlowController:
    """游戏流程控制器"""
    
    def __init__(self):
        self.current_phase = GamePhase.MENU
        self.player1 = Player(1, "玩家1")
        self.player2 = Player(2, "玩家2")
        self.current_player: Optional[Player] = None
        self.turn_count = 0
        self.general_pool: List[General] = []
        self.first_player: Optional[Player] = None
        self.second_player: Optional[Player] = None
        
    def start_game(self):
        """开始游戏主流程"""
        print("🎮 开始三国武将卡牌游戏！")
        print("=" * 50)
        
        # 1. 选将流程
        self._enter_general_selection()
        
        # 2. 阵型布置阶段
        self._enter_formation_setup()
        
        # 3. 抛骰子决定先手
        self._roll_dice_for_first_player()
        
        # 4. 进入回合制战斗
        self._enter_battle_phase()
    
    def _enter_general_selection(self):
        """进入选将阶段"""
        print("\n📋 进入选将阶段")
        print("=" * 30)
        
        self.current_phase = GamePhase.GENERAL_SELECTION
        
        # 从武将池中随机抽取15位武将
        self._generate_general_pool()
        
        # 显示武将池
        self._display_general_pool()
        
        # 玩家1选将
        self._player_select_generals(self.player1)
        
        # 玩家2选将
        self._player_select_generals(self.player2)
        
        print("\n✅ 选将阶段完成！")
        self._display_teams()
    
    def _enter_formation_setup(self):
        """进入阵型布置阶段"""
        print("\n🛡️ 进入阵型布置阶段")
        print("=" * 30)
        print("阵型说明：3行4列的方格，玩家只能攻击敌方最前排的武将")
        print("位置说明：行(0-2)，列(0-3)，第0行为最前排")
        
        # 玩家1布置阵型
        self._player_setup_formation(self.player1)
        
        # 玩家2布置阵型
        self._player_setup_formation(self.player2)
        
        print("\n✅ 阵型布置完成！")
        self._display_formations()
    
    def _player_setup_formation(self, player: Player):
        """玩家布置阵型"""
        print(f"\n🎯 {player.name} 开始布置阵型")
        print(f"你有 {len(player.selected_generals)} 位武将需要布置")
        
        # 开始阵型布置
        player.team.setup_formation_phase()
        
        # 显示武将列表
        print("你的武将：")
        for i, general in enumerate(player.selected_generals):
            print(f"  {i+1}. {general.name} (武力:{general.force} 智力:{general.intelligence})")
        
        # 逐个布置武将
        for i, general in enumerate(player.selected_generals):
            print(f"\n正在布置: {general.name}")
            self._position_general_interactive(player.team, general)
        
        # 完成布置
        success = player.team.complete_formation_setup()
        if success:
            print(f"✅ {player.name} 阵型布置完成")
        else:
            print(f"❌ {player.name} 阵型布置失败，重新布置")
            self._player_setup_formation(player)
    
    def _position_general_interactive(self, team: Team, general: General):
        """交互式武将布置"""
        while True:
            print(f"当前阵型：\n{team.get_formation_display()}")
            try:
                row = int(input(f"请输入 {general.name} 的行位置 (0-2): "))
                col = int(input(f"请输入 {general.name} 的列位置 (0-3): "))
                
                success = team.position_general(general, row, col)
                if success:
                    print(f"✅ {general.name} 成功放置到位置 ({row}, {col})")
                    break
                else:
                    print("❌ 放置失败，位置无效或已被占用，请重新选择")
            except ValueError:
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n游戏中断")
                return
    
    def _display_formations(self):
        """显示双方阵型"""
        print("\n📋 双方阵型展示")
        print("=" * 40)
        print(self.player1.team.get_formation_display())
        print(self.player2.team.get_formation_display())
    
    def _generate_general_pool(self):
        """生成15位武将的选择池"""
        print("🎲 正在生成武将池...")
        
        # 获取所有可用武将
        all_generals_creators = list(GENERAL_CREATORS.values())
        
        # 随机选择15位武将（有重复的话就扩展池子）
        selected_creators = []
        for _ in range(15):
            creator = random.choice(all_generals_creators)
            selected_creators.append(creator)
        
        # 创建武将实例
        self.general_pool = []
        for i, creator in enumerate(selected_creators):
            general = creator()
            general.pool_index = i + 1  # 添加池子中的编号
            self.general_pool.append(general)
        
        print(f"✅ 已生成包含{len(self.general_pool)}位武将的选择池")
    
    def _display_general_pool(self):
        """显示武将池"""
        print("\n🏛️ 可选武将池：")
        print("-" * 60)
        
        for general in self.general_pool:
            status = "✅可选" if hasattr(general, 'pool_index') else "❌已选"
            print(f"{general.pool_index:2d}. {general.name:8s} "
                  f"({general.camp.value}) "
                  f"武力:{general.force:2d} 智力:{general.intelligence:2d} "
                  f"生命:{general.max_hp:2d} [{status}]")
    
    def _player_select_generals(self, player: Player):
        """玩家选择武将"""
        print(f"\n🎯 {player.name} 开始选将")
        print("请选择你的武将（输入编号，选择完成后输入0）：")
        
        available_generals = [g for g in self.general_pool if hasattr(g, 'pool_index')]
        
        while True:
            try:
                choice = input(f"{player.name} 请选择武将编号 (1-15, 输入0完成选择): ").strip()
                
                if choice == "0":
                    if len(player.selected_generals) > 0:
                        break
                    else:
                        print("❌ 至少需要选择一位武将！")
                        continue
                
                choice_num = int(choice)
                if 1 <= choice_num <= 15:
                    # 找到对应的武将
                    selected_general = None
                    for general in available_generals:
                        if general.pool_index == choice_num:
                            selected_general = general
                            break
                    
                    if selected_general:
                        # 添加到玩家队伍
                        player.add_general_to_team(selected_general)
                        # 从可选列表中移除
                        available_generals.remove(selected_general)
                        delattr(selected_general, 'pool_index')  # 移除池子编号标记
                        
                        print(f"✅ {player.name} 选择了 {selected_general.name}")
                        print(f"当前队伍：{[g.name for g in player.selected_generals]}")
                    else:
                        print("❌ 该武将已被选择或不存在！")
                else:
                    print("❌ 请输入1-15之间的数字！")
                    
            except ValueError:
                print("❌ 请输入有效的数字！")
            except KeyboardInterrupt:
                print("\n游戏被中断")
                return
    
    def _display_teams(self):
        """显示双方队伍"""
        print("\n👥 队伍总览")
        print("=" * 40)
        
        for player in [self.player1, self.player2]:
            print(f"\n{player.name} 的队伍：")
            for general in player.selected_generals:
                print(f"  • {general.name} ({general.camp.value}) "
                      f"武力:{general.force} 智力:{general.intelligence} "
                      f"生命:{general.max_hp}")
    
    def _roll_dice_for_first_player(self):
        """抛骰子决定先手玩家"""
        print("\n🎲 抛骰子决定先手玩家")
        print("=" * 30)

        self.current_phase = GamePhase.DICE_ROLL

        # 玩家1抛骰子
        dice1 = random.randint(1, 6)
        print(f"{self.player1.name} 抛出了：{dice1}")

        # 玩家2抛骰子
        dice2 = random.randint(1, 6)
        print(f"{self.player2.name} 抛出了：{dice2}")

        # 决定先手
        if dice1 > dice2:
            self.first_player = self.player1
            self.second_player = self.player2
            print(f"🎯 {self.player1.name} 点数更大，获得先手！")
        elif dice2 > dice1:
            self.first_player = self.player2
            self.second_player = self.player1
            print(f"🎯 {self.player2.name} 点数更大，获得先手！")
        else:
            # 平局重新抛
            print("🎲 点数相同，重新抛骰子！")
            self._roll_dice_for_first_player()
            return

        # 设置当前玩家
        self.current_player = self.first_player

        # 后手补偿：后手玩家初始士气上限+2，当前士气也+2
        compensation = 2
        self.second_player.team.max_morale += compensation
        self.second_player.team.current_morale += compensation
        print(f"🎁 后手补偿：{self.second_player.name} 初始士气上限+{compensation}（当前 {self.second_player.team.current_morale}/{self.second_player.team.max_morale}）")
    
    def _enter_battle_phase(self):
        """进入战斗阶段"""
        print("\n⚔️ 进入战斗阶段")
        print("=" * 30)
        
        self.current_phase = GamePhase.BATTLE
        
        # 开始回合制战斗
        while not self._is_game_over():
            self._execute_turn()
        
        # 游戏结束
        self._handle_game_over()
    
    def _execute_turn(self):
        """执行一个回合"""
        self.turn_count += 1
        
        print(f"\n🎯 第{self.turn_count}回合 - {self.current_player.name}的回合")
        print("-" * 40)
        
        # 显示当前状态
        self._display_battle_status()
        
        # 技能使用阶段
        self._execute_skill_phase()
        
        # 普攻阶段
        self._execute_attack_phase()
        
        # 检查游戏是否结束
        if self._is_game_over():
            return
        
        # 切换到下一个玩家
        self._switch_to_next_player()
    
    def _execute_skill_phase(self):
        """执行技能使用阶段"""
        print(f"\n✨ {self.current_player.name} - 技能使用阶段")
        self.current_phase = GamePhase.SKILL_PHASE
        
        # 显示可用技能
        available_generals = self.current_player.team.get_alive_generals()
        
        if not available_generals:
            print("❌ 没有存活的武将可以使用技能")
            return
        
        print("可使用技能的武将：")
        for i, general in enumerate(available_generals):
            skill_name = general.active_skill.name if general.active_skill else "无技能"
            cooldown_info = f"(冷却:{general.active_skill_cooldown})" if general.active_skill_cooldown > 0 else ""
            can_use = "✅" if general.can_use_active_skill() else "❌"
            print(f"  {i+1}. {general.name} - {skill_name} {cooldown_info} {can_use}")
        
        # 玩家选择是否使用技能
        while True:
            try:
                choice = input(f"\n{self.current_player.name} 选择使用技能的武将编号 (1-{len(available_generals)}, 输入0跳过): ").strip()
                
                if choice == "0":
                    print("⏭️ 跳过技能使用阶段")
                    break
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(available_generals):
                    selected_general = available_generals[choice_num - 1]
                    
                    if selected_general.can_use_active_skill():
                        # 选择目标并使用技能
                        self._use_skill(selected_general)
                        break
                    else:
                        print("❌ 该武将无法使用技能（冷却中或没有技能）")
                else:
                    print(f"❌ 请输入1-{len(available_generals)}之间的数字！")
                    
            except ValueError:
                print("❌ 请输入有效的数字！")
            except KeyboardInterrupt:
                print("\n技能阶段被中断")
                break
    
    def _use_skill(self, caster: General):
        """使用技能"""
        if not caster.active_skill:
            print(f"❌ {caster.name} 没有可用技能")
            return
        
        print(f"🔥 {caster.name} 准备使用技能：{caster.active_skill.name}")
        
        # 根据技能目标类型选择目标
        targets = self._select_skill_targets(caster)
        
        if targets:
            # 创建战斗上下文
            battle_context = BattleContext(self)
            
            # 使用技能
            result = caster.use_active_skill(targets, battle_context, self.current_player.team)
            
            # 显示结果
            self._display_skill_result(result)
    
    def _select_skill_targets(self, caster: General) -> List[General]:
        """选择技能目标"""
        from src.skills.skill_base import TargetType
        
        target_type = caster.active_skill.target_type
        
        if target_type == TargetType.SELF:
            return [caster]
        elif target_type == TargetType.ALL_ALLIES:
            return self.current_player.team.get_alive_generals()
        elif target_type == TargetType.SINGLE_ENEMY:
            # 让玩家选择敌方目标
            enemy_player = self.player2 if self.current_player == self.player1 else self.player1
            enemy_generals = enemy_player.team.get_alive_generals()
            
            if not enemy_generals:
                print("❌ 没有可攻击的敌方武将")
                return []
            
            print("选择攻击目标：")
            for i, general in enumerate(enemy_generals):
                print(f"  {i+1}. {general.name} (生命:{general.current_hp}/{general.max_hp})")
            
            try:
                choice = int(input("请选择目标编号: ")) - 1
                if 0 <= choice < len(enemy_generals):
                    return [enemy_generals[choice]]
            except ValueError:
                pass
            
            print("❌ 无效选择")
            return []
        
        return []
    
    def _display_skill_result(self, result: dict):
        """显示技能使用结果"""
        if result.get("success"):
            print(f"✅ 技能使用成功！")
            if "details" in result:
                for detail in result["details"]:
                    print(f"   {detail}")
        else:
            print(f"❌ 技能使用失败：{result.get('message', '未知错误')}")
    
    def _execute_attack_phase(self):
        """执行普攻阶段"""
        print(f"\n⚔️ {self.current_player.name} - 普攻阶段")
        self.current_phase = GamePhase.ATTACK_PHASE
        
        # 获取存活的武将
        available_generals = self.current_player.team.get_alive_generals()
        enemy_player = self.player2 if self.current_player == self.player1 else self.player1
        
        if not available_generals:
            print("❌ 没有存活的武将可以攻击")
            return
        
        # 获取敌方可攻击的目标（只有前排武将）
        attackable_targets = enemy_player.team.get_attackable_targets()
        
        if not attackable_targets:
            print("❌ 没有可攻击的敌方武将")
            return
        
        # 选择攻击的武将
        print("选择攻击的武将：")
        for i, general in enumerate(available_generals):
            pos = self.current_player.team.get_general_position(general)
            print(f"  {i+1}. {general.name} 位置{pos} (生命:{general.current_hp}/{general.max_hp})")
        
        try:
            choice = int(input("请选择攻击武将编号: ")) - 1
            if 0 <= choice < len(available_generals):
                attacker = available_generals[choice]
                
                # 显示可攻击的目标（前排武将）
                print("可攻击的目标（前排武将）：")
                for i, general in enumerate(attackable_targets):
                    pos = enemy_player.team.get_general_position(general)
                    print(f"  {i+1}. {general.name} 位置{pos} (生命:{general.current_hp}/{general.max_hp})")
                
                target_choice = int(input("请选择攻击目标编号: ")) - 1
                if 0 <= target_choice < len(attackable_targets):
                    target = attackable_targets[target_choice]
                    
                    # 执行攻击
                    damage = attacker.attack(target)
                    print(f"⚔️ {attacker.name} 攻击 {target.name}，造成 {damage} 点伤害")
                    print(f"   {target.name} 剩余生命：{target.current_hp}/{target.max_hp}")
                    
                    if not target.is_alive():
                        print(f"💀 {target.name} 已阵亡！")
                        # 从阵型中移除阵亡的武将
                        enemy_player.team.remove_general_from_formation(target)
                        print(f"   {target.name} 已从阵型中移除")
                        
                        # 显示更新后的阵型
                        print(f"更新后的阵型：\n{enemy_player.team.get_formation_display()}")
                
        except (ValueError, IndexError):
            print("❌ 无效选择，跳过攻击")
    
    def _display_battle_status(self):
        """显示战斗状态"""
        print("\n📊 当前战斗状态：")

        for player in [self.player1, self.player2]:
            print(f"\n{player.name} (士气:{player.team.current_morale}/{player.team.max_morale}):")
            living_generals = player.team.get_alive_generals()
            dead_generals = player.team.get_defeated_generals()
            
            print("  存活武将:")
            for general in living_generals:
                print(f"    {general.name} (生命:{general.current_hp}/{general.max_hp})")
            
            if dead_generals:
                print("  阵亡武将:")
                for general in dead_generals:
                    print(f"    {general.name} (已阵亡)")
    
    def _switch_to_next_player(self):
        """切换到下一个玩家（A-B-A-B交替，后手已获得初始士气补偿）"""
        self.current_player = self.player2 if self.current_player == self.player1 else self.player1
    
    def _is_game_over(self) -> bool:
        """检查游戏是否结束"""
        return self.player1.is_defeated() or self.player2.is_defeated()
    
    def _handle_game_over(self):
        """处理游戏结束"""
        print("\n🎉 游戏结束！")
        print("=" * 30)
        
        self.current_phase = GamePhase.GAME_OVER
        
        if self.player1.is_defeated():
            print(f"🏆 {self.player2.name} 获得胜利！")
        elif self.player2.is_defeated():
            print(f"🏆 {self.player1.name} 获得胜利！")
        
        print(f"\n📊 游戏统计：")
        print(f"总回合数：{self.turn_count}")
        print(f"先手玩家：{self.first_player.name}")


class BattleContext:
    """战斗上下文，为技能提供必要信息"""
    
    def __init__(self, game_controller: GameFlowController):
        self.game_controller = game_controller
    
    def get_team_for_general(self, general: General) -> Team:
        """根据武将获取所属队伍"""
        if general in self.game_controller.player1.team.generals:
            return self.game_controller.player1.team
        elif general in self.game_controller.player2.team.generals:
            return self.game_controller.player2.team
        return None

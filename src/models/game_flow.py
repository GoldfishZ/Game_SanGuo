"""
游戏主流程控制器
管理整个游戏的流程和状态（选将、布阵、掷骰子），战斗委托给 BattleSystem
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
    """游戏流程控制器（战前/战后逻辑，战斗委托给 BattleSystem）"""

    def __init__(self, battle_callbacks=None):
        self.current_phase = GamePhase.MENU
        self.player1 = Player(1, "玩家1")
        self.player2 = Player(2, "玩家2")
        self.current_player: Optional[Player] = None
        self.turn_count = 0
        self.general_pool: List[General] = []
        self.first_player: Optional[Player] = None
        self.second_player: Optional[Player] = None
        self._battle_system = None  # 战斗结束后保留引用
        self._battle_callbacks = battle_callbacks  # None = 使用 CLI

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
        """生成15位武将的选择池（不重复）"""
        print("🎲 正在生成武将池...")

        all_generals_creators = list(GENERAL_CREATORS.values())
        n = min(15, len(all_generals_creators))
        selected_creators = random.sample(all_generals_creators, n)

        self.general_pool = []
        for i, creator in enumerate(selected_creators):
            general = creator()
            general.pool_index = i + 1
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

    # ==================== 战斗阶段（委托给 BattleSystem） ====================

    def _enter_battle_phase(self):
        """进入战斗阶段，委托给 BattleSystem"""
        gui_mode = self._battle_callbacks is not None

        if not gui_mode:
            print("\n⚔️ 进入战斗阶段")
            print("=" * 30)

        self.current_phase = GamePhase.BATTLE

        from src.battle.battle_system import BattleSystem
        from src.ui.cli_callbacks import CLIBattleCallbacks

        callbacks = self._battle_callbacks or CLIBattleCallbacks()
        self._battle_system = BattleSystem(
            team1=self.player1.team,
            team2=self.player2.team,
            callbacks=callbacks,
            first_player_team_name=self.first_player.team.team_name,
        )
        try:
            winner_team_name = self._battle_system.run()
        except Exception as e:
            import traceback
            traceback.print_exc()
            # GUI 模式用 Pygame 显示错误
            if gui_mode:
                try:
                    import pygame
                    if pygame.get_init():
                        callbacks.on_skill_failed("系统", f"战斗异常: {e}")
                except:
                    pass
            raise

        self.turn_count = self._battle_system.turn_count
        self._handle_game_over_with_winner(winner_team_name)

    def _handle_game_over_with_winner(self, winner_team_name: str):
        """根据战斗系统返回的胜者队伍名处理游戏结束"""
        gui_mode = self._battle_callbacks is not None

        if not gui_mode:
            print("\n🎉 游戏结束！")
            print("=" * 30)

        self.current_phase = GamePhase.GAME_OVER

        if winner_team_name == self.player1.team.team_name:
            if not gui_mode:
                print(f"🏆 {self.player1.name} 获得胜利！")
        elif winner_team_name == self.player2.team.team_name:
            if not gui_mode:
                print(f"🏆 {self.player2.name} 获得胜利！")
        else:
            if self.player1.is_defeated():
                if not gui_mode:
                    print(f"🏆 {self.player2.name} 获得胜利！")
            elif self.player2.is_defeated():
                if not gui_mode:
                    print(f"🏆 {self.player1.name} 获得胜利！")

        if not gui_mode:
            print(f"\n📊 游戏统计：")
            print(f"总回合数：{self.turn_count}")
            print(f"先手玩家：{self.first_player.name}")

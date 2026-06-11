"""
CLI 战斗回调实现
用 print()/input() 实现 BattleCallbacks，保持与原命令行体验完全一致
"""

from typing import List, Tuple
from src.battle.battle_system import BattleCallbacks, BattleEvent, BattleStatusData


class CLIBattleCallbacks(BattleCallbacks):
    """命令行版本的战斗UI回调"""

    # ---- 显示 / 通知方法 ----

    def display_battle_status(self, data: BattleStatusData) -> None:
        """显示当前战斗状态"""
        print("\n📊 当前战斗状态：")

        teams = [
            (data.team1_name, data.team1_morale, data.team1_max_morale, data.team1_generals),
            (data.team2_name, data.team2_morale, data.team2_max_morale, data.team2_generals),
        ]

        for name, morale, max_morale, generals in teams:
            player_name = name.split("的队伍")[0] if "的队伍" in name else name
            print(f"\n{player_name} (士气:{morale}/{max_morale}):")
            alive = [g for g in generals if g["is_alive"]]
            dead = [g for g in generals if not g["is_alive"]]

            print("  存活武将:")
            for g in alive:
                cooldown = f" [冷却:{g['active_skill_cooldown']}]" if g['active_skill_cooldown'] > 0 else ""
                print(f"    {g['name']} (生命:{g['current_hp']}/{g['max_hp']}){cooldown}")

            if dead:
                print("  阵亡武将:")
                for g in dead:
                    print(f"    {g['name']} (已阵亡)")

    def on_turn_start(self, turn_count: int, player_name: str) -> None:
        """回合开始"""
        print(f"\n🎯 第{turn_count}回合 - {player_name}的回合")
        print("-" * 40)

    def on_skill_used(self, event: BattleEvent) -> None:
        """技能使用成功"""
        print(f"✅ 技能使用成功！")
        for detail in event.details:
            print(f"   {detail}")

    def on_skill_failed(self, skill_name: str, reason: str) -> None:
        """技能使用失败"""
        print(f"❌ 技能使用失败：{reason}")

    def on_attack(self, event: BattleEvent) -> None:
        """攻击结果"""
        print(f"⚔️ {event.source_name} 攻击 {event.target_name}，造成 {event.damage} 点伤害")
        print(f"   {event.target_name} 剩余生命：{event.target_hp}/{event.target_max_hp}")

    def on_general_defeated(self, event: BattleEvent) -> None:
        """武将阵亡"""
        print(f"💀 {event.target_name} 已阵亡！")
        print(f"   {event.target_name} 已从阵型中移除")

    def on_battle_end(self, winner_name: str, turn_count: int) -> None:
        """战斗结束——此方法由 GameFlowController 的 _handle_game_over 替代，
           这里只做简单标记"""
        pass

    # ---- 请求玩家输入的方法 ----

    def request_skill_use(self, available_generals: list, player_name: str) -> int:
        """请求选择使用技能的武将"""
        print(f"\n✨ {player_name} - 技能使用阶段")
        print("可使用技能的武将：")

        for i, name, skill_name, cooldown, can_use in available_generals:
            cooldown_info = f"(冷却:{cooldown})" if cooldown > 0 else ""
            status = "✅" if can_use else "❌"
            print(f"  {i+1}. {name} - {skill_name} {cooldown_info} {status}")

        while True:
            try:
                choice = input(
                    f"\n{player_name} 选择使用技能的武将编号 "
                    f"(1-{len(available_generals)}, 输入0跳过): "
                ).strip()

                if choice == "0":
                    print("⏭️ 跳过技能使用阶段")
                    return -1

                choice_num = int(choice)
                if 1 <= choice_num <= len(available_generals):
                    idx = choice_num - 1
                    if available_generals[idx][4]:  # can_use
                        return idx
                    else:
                        print("❌ 该武将无法使用技能（冷却中或没有技能）")
                else:
                    print(f"❌ 请输入1-{len(available_generals)}之间的数字！")

            except ValueError:
                print("❌ 请输入有效的数字！")
            except KeyboardInterrupt:
                print("\n技能阶段被中断")
                return -1

    def request_skill_target(self, caster_name: str, skill_name: str,
                             possible_targets: list) -> int:
        """请求选择技能目标"""
        print(f"🔥 {caster_name} 准备使用技能：{skill_name}")

        if not possible_targets:
            print("❌ 没有可攻击的敌方武将")
            return -1

        print("选择攻击目标：")
        for i, name, hp, max_hp in possible_targets:
            print(f"  {i+1}. {name} (生命:{hp}/{max_hp})")

        try:
            choice = int(input("请选择目标编号: ")) - 1
            if 0 <= choice < len(possible_targets):
                return choice
        except ValueError:
            pass

        print("❌ 无效选择")
        return -1

    def request_attack_action(self, attackers: list, targets: list,
                              player_name: str) -> Tuple[int, int]:
        """请求选择攻击者和目标"""
        print(f"\n⚔️ {player_name} - 普攻阶段")

        print("选择攻击的武将：")
        for i, name, hp, max_hp, pos in attackers:
            print(f"  {i+1}. {name} 位置{pos} (生命:{hp}/{max_hp})")

        try:
            choice = int(input("请选择攻击武将编号: ")) - 1
            if not (0 <= choice < len(attackers)):
                raise ValueError()
            a_idx = choice

            # 显示可攻击目标
            print("可攻击的目标（前排武将）：")
            for i, name, hp, max_hp, pos in targets:
                print(f"  {i+1}. {name} 位置{pos} (生命:{hp}/{max_hp})")

            target_choice = int(input("请选择攻击目标编号: ")) - 1
            if 0 <= target_choice < len(targets):
                return (a_idx, target_choice)

        except (ValueError, IndexError):
            print("❌ 无效选择，跳过攻击")

        return (-1, -1)

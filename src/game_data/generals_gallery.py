"""
武将图鉴演示
展示游戏中所有可用的武将和技能
"""

from .game_data_manager import game_data_manager
from src.models.general import Camp, Rarity


def show_generals_gallery():
    """显示武将图鉴"""
    print("🎮" * 20)
    print("   三国武将卡牌游戏 - 武将图鉴")
    print("🎮" * 20)
    
    # 显示游戏统计信息
    info = game_data_manager.get_generals_info()
    print(f"\n📊 游戏数据统计:")
    print(f"  总武将数: {info['total_generals']}")
    print(f"  总技能数: {info['total_skills']}")
    print("\n📈 阵营分布:")
    for camp, count in info['camp_distribution'].items():
        print(f"  {camp}: {count}名武将")
    print("\n⭐ 稀有度分布:")
    for rarity, count in info['rarity_distribution'].items():
        print(f"  {rarity}: {count}名武将")
    
    print("\n" + "="*60)
    
    # 显示所有武将详细信息
    game_data_manager.print_all_generals()


def show_camp_generals(camp: Camp):
    """显示指定阵营的武将"""
    generals = game_data_manager.get_generals_by_camp(camp)
    print(f"\n=== {camp.value}阵营武将 ===")
    
    for general in generals:
        print(f"\n🏛️ {general.name} (ID: {general.general_id})")
        print(f"   💎 稀有度: {general.rarity.name}")
        print(f"   💰 费用: {general.cost}")
        print(f"   ❤️  生命: {general.max_hp}")
        print(f"   ⚔️  武力: {general.force}")
        print(f"   🧠 智力: {general.intelligence}")
        print(f"   🏷️  属性: {', '.join([attr.value for attr in general.attribute])}")
        
        if general.active_skill:
            skill = general.active_skill
            print(f"   🔥 主动技能: {skill.name}")
            print(f"      📝 描述: {skill.description}")
            print(f"      ⚡ 士气消耗: {skill.morale_cost}")
            print(f"      ⏰ 冷却时间: {skill.cooldown}回合")
            print(f"      🎯 目标类型: {skill.target_type.value}")
        
        if general.passive_skills:
            print(f"   🛡️  被动技能:")
            for passive in general.passive_skills:
                print(f"      • {passive.name}: {passive.description}")


def interactive_gallery():
    """交互式武将图鉴"""
    while True:
        print("\n" + "="*50)
        print("🎯 三国武将卡牌游戏 - 交互式图鉴")
        print("="*50)
        print("1. 查看所有武将")
        print("2. 按阵营查看武将")
        print("3. 按稀有度查看武将")
        print("4. 搜索武将")
        print("5. 退出")
        
        choice = input("\n请选择操作 (1-5): ").strip()
        
        if choice == "1":
            show_generals_gallery()
        
        elif choice == "2":
            print("\n选择阵营:")
            camps = list(Camp)
            for i, camp in enumerate(camps, 1):
                print(f"{i}. {camp.value}")
            
            try:
                camp_choice = int(input("请输入阵营编号: ")) - 1
                if 0 <= camp_choice < len(camps):
                    show_camp_generals(camps[camp_choice])
                else:
                    print("❌ 无效的阵营编号!")
            except ValueError:
                print("❌ 请输入有效的数字!")
        
        elif choice == "3":
            print("\n选择稀有度:")
            rarities = list(Rarity)
            for i, rarity in enumerate(rarities, 1):
                print(f"{i}. {rarity.name}")
            
            try:
                rarity_choice = int(input("请输入稀有度编号: ")) - 1
                if 0 <= rarity_choice < len(rarities):
                    selected_rarity = rarities[rarity_choice]
                    generals = game_data_manager.get_generals_by_rarity(selected_rarity)
                    print(f"\n=== {selected_rarity.name}稀有度武将 ===")
                    for general in generals:
                        print(f"• {general.name} ({general.camp.value})")
                else:
                    print("❌ 无效的稀有度编号!")
            except ValueError:
                print("❌ 请输入有效的数字!")
        
        elif choice == "4":
            name = input("\n请输入武将名称 (如: 张任): ").strip()
            general = game_data_manager.get_general_by_name(name.lower().replace(" ", "_"))
            if general:
                show_camp_generals(general.camp)
            else:
                print(f"❌ 未找到武将: {name}")
        
        elif choice == "5":
            print("👋 感谢使用武将图鉴!")
            break
        
        else:
            print("❌ 无效的选择，请重新输入!")


if __name__ == "__main__":
    # 可以直接运行显示所有武将，或者使用交互式模式
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_gallery()
    else:
        show_generals_gallery()

"""
测试武将系统
验证15武将数据加载、技能独立冷却、士气上限
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.game_data_manager import game_data_manager
from game_data.generals_data import GENERALS_DATA
from game_data.generals_config import get_general_by_name
from src.models.team import Team
from src.models.general import Camp, Rarity


def test_all_generals():
    """测试所有武将数据加载"""
    print("🧹" * 20)
    print("   测试武将系统（15人）")
    print("🧹" * 20)

    all_generals = game_data_manager.get_general_list()
    print(f"\n📊 系统武将统计:")
    print(f"   总武将数量: {len(all_generals)} (应为{len(GENERALS_DATA)})")
    assert len(all_generals) == len(GENERALS_DATA), \
        f"武将数量不匹配: {len(all_generals)} != {len(GENERALS_DATA)}"

    # 列出所有武将
    print(f"\n📋 所有武将列表:")
    for general in all_generals:
        attrs = [attr.value for attr in general.attribute] if general.attribute else ["无"]
        print(f"   • {general.name} ({general.camp.value}, {general.rarity.name})")
        print(f"     {general.force}武 {general.intelligence}智 HP:{general.max_hp} "
              f"技能:{general.active_skill.name if general.active_skill else '无'} "
              f"属性:{attrs}")

    info = game_data_manager.get_generals_info()
    print(f"\n📈 详细统计:")
    print(f"   总武将数: {info['total_generals']}")
    print(f"   总技能数: {info['total_skills']}")
    print(f"   阵营分布: {info['camp_distribution']}")
    print(f"   稀有度分布: {info['rarity_distribution']}")

    # 验证每个阵营都有武将
    for camp, count in info['camp_distribution'].items():
        if camp in ('蜀', '魏', '吴', '他'):
            assert count > 0, f"{camp}阵营应有武将"


def test_specific_generals():
    """测试具体武将数据正确性"""
    print("\n🎯" * 20)
    print("   测试具体武将数据")
    print("🎯" * 20)

    checks = [
        ("张任", "他", "COMMON", 6, 6, "伏兵", "强化战术"),
        ("刘备", "蜀", "RARE", 5, 7, "魅力", "鼓舞"),
        ("关羽", "蜀", "EPIC", 9, 5, "勇猛", "猛攻"),
        ("曹操", "魏", "LEGENDARY", 7, 9, "魅力", "鼓舞"),
        ("吕布", "他", "LEGENDARY", 10, 2, "勇猛", "猛攻"),
        ("诸葛亮", "蜀", "LEGENDARY", 3, 10, "连环", "火计"),
        ("鲁肃", "吴", "RARE", 4, 8, "防栅", "同盟缔结"),
    ]

    for name, camp, rarity, force, intelligence, attr, skill in checks:
        g = get_general_by_name(name)
        assert g is not None, f"{name} 创建失败"
        assert g.camp.value == camp, f"{name} 阵营: 期望{camp} 实际{g.camp.value}"
        assert g.rarity.name == rarity, f"{name} 稀有度: 期望{rarity} 实际{g.rarity.name}"
        assert g.force == force, f"{name} 武力: 期望{force} 实际{g.force}"
        assert g.intelligence == intelligence, f"{name} 智力: 期望{intelligence} 实际{g.intelligence}"
        assert g.max_hp == force + intelligence, f"{name} 生命: 期望{force+intelligence} 实际{g.max_hp}"
        if attr:
            assert attr in [a.value for a in g.attribute], f"{name} 应有属性{attr}"
        assert g.active_skill is not None, f"{name} 应有主动技能"
        assert g.active_skill.name == skill, f"{name} 技能: 期望{skill} 实际{g.active_skill.name}"
        print(f"   ✅ {name}: {force}武 {intelligence}智 [{attr}] {skill}")


def test_skill_independence():
    """测试技能独立冷却"""
    print("\n⚔️" * 20)
    print("   测试技能独立冷却")
    print("⚔️" * 20)

    zhang_ren = get_general_by_name("张任")
    zhao_yun = get_general_by_name("赵云")
    assert zhang_ren and zhao_yun, "武将创建失败"
    assert zhang_ren.active_skill.name == zhao_yun.active_skill.name == "强化战术"

    team = Team("测试队伍", Camp.TA)
    team.add_general(zhang_ren)
    team.add_general(zhao_yun)

    print(f"\n   队伍士气: {team.current_morale}/{team.max_morale}")
    print(f"   {zhang_ren.name} 冷却: {zhang_ren.active_skill_cooldown}")
    print(f"   {zhao_yun.name} 冷却: {zhao_yun.active_skill_cooldown}")

    r1 = team.use_skill(zhang_ren, [zhang_ren], {"battle_phase": "main"})
    print(f"\n   {zhang_ren.name} 使用技能: {'成功' if r1.get('success') else '失败'}")
    print(f"   士气: {team.current_morale}/{team.max_morale}")

    r2 = team.use_skill(zhao_yun, [zhao_yun], {"battle_phase": "main"})
    print(f"   {zhao_yun.name} 使用技能: {'成功' if r2.get('success') else '失败'}")
    print(f"   士气: {team.current_morale}/{team.max_morale}")

    assert r1.get("success") and r2.get("success"), "两个武将应都能使用技能"
    print("\n   ✅ 同技能不同武将独立冷却正常")


def test_team_morale_limit():
    """测试队伍士气固定上限"""
    print("\n⚡" * 20)
    print("   测试队伍士气固定上限")
    print("⚡" * 20)

    teams = [
        Team("默认队伍"),
        Team("指定阵营", Camp.WU),
        Team("尝试自定义士气", Camp.TA, max_morale=50),
    ]

    for i, team in enumerate(teams, 1):
        print(f"   队伍{i}: max={team.max_morale}, current={team.current_morale} (均应为12)")
        assert team.max_morale == 12, f"队伍{i}士气上限不是12"
        assert team.current_morale == 12, f"队伍{i}当前士气不是12"

    print("\n   ✅ 士气上限固定12")


def test_chain_integration():
    """测试连环被动技能：伤害分担"""
    print("\n🔗" * 20)
    print("   测试连环被动技能集成")
    print("🔗" * 20)

    # 诸葛亮有连环属性
    zhuge_liang_1 = get_general_by_name("诸葛亮")
    zhuge_liang_2 = get_general_by_name("诸葛亮")
    assert zhuge_liang_1 and zhuge_liang_2

    team = Team("测试连环队伍", Camp.SHU)
    team.add_general(zhuge_liang_1)
    team.add_general(zhuge_liang_2)

    # 放置到阵型
    team.position_general(zhuge_liang_1, 0, 0)
    team.position_general(zhuge_liang_2, 0, 1)

    # 两人都有连环
    assert zhuge_liang_1.has_passive_skill("连环")
    assert zhuge_liang_2.has_passive_skill("连环")

    hp_before = zhuge_liang_2.current_hp
    print(f"   攻击前: 诸葛亮1 HP={zhuge_liang_1.current_hp}/{zhuge_liang_1.max_hp}, "
          f"诸葛亮2 HP={zhuge_liang_2.current_hp}/{zhuge_liang_2.max_hp}")

    # 创建攻击者
    from src.models.general import General, Attribute
    attacker = General(9999, "测试攻击者", Camp.WEI, Rarity.COMMON, 1.0, 10, 5)
    attacker.attack(zhuge_liang_1)

    print(f"   攻击后: 诸葛亮1 HP={zhuge_liang_1.current_hp}/{zhuge_liang_1.max_hp}, "
          f"诸葛亮2 HP={zhuge_liang_2.current_hp}/{zhuge_liang_2.max_hp}")

    # 诸葛亮2 也应该受到伤害（连环分担）
    assert zhuge_liang_2.current_hp < hp_before, \
        f"连环分担失败：诸葛亮2 HP应由{hp_before}减少"
    print("   ✅ 连环伤害分担成功！")


if __name__ == "__main__":
    print("🎮 武将系统完整测试")

    test_all_generals()
    test_specific_generals()
    test_skill_independence()
    test_team_morale_limit()
    test_chain_integration()

    print(f"\n✅ 测试完成！")
    print(f"   📋 武将: {len(GENERALS_DATA)}人，覆盖4个阵营")
    print(f"   🔥 技能: 6个主动技能 + 7个被动技能")
    print(f"   ⚡ 士气: 固定上限12")
    print(f"   💚 生命: 武力+智力")
    print(f"   🎯 冷却: 每个武将独立管理")
    print(f"   🔗 连环: 伤害分担+效果同步已集成")

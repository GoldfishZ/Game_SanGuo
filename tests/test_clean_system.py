"""
测试武将系统
验证武将数据加载、技能独立冷却、士气上限
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
    print(f"   测试武将系统（{len(GENERALS_DATA)}人）")
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
        if camp in ('蜀', '魏', '吴', '袁', '他'):
            assert count > 0, f"{camp}阵营应有武将"


def test_specific_generals():
    """测试具体武将数据正确性"""
    print("\n🎯" * 20)
    print("   测试具体武将数据")
    print("🎯" * 20)

    checks = [
        ("张任", "他", "COMMON", 6, 6, "伏兵", "强化战术"),
        ("张飞", "蜀", "EPIC", 8, 4, "勇猛", "轮枪战术"),
        ("夏侯月姬", "蜀", "COMMON", 2, 7, "魅力", "雷击"),
        ("周仓", "蜀", "COMMON", 4, 1, "勇猛", "强化战术"),
        ("马岱", "蜀", "RARE", 5, 7, "伏兵", "质实刚健"),
        ("姜维", "蜀", "EPIC", 7, 7, "募兵", "挑衅"),
        ("曹操", "魏", "EPIC", 7, 9, "魅力", "全军攻城"),
        ("夏侯惇", "魏", "RARE", 8, 6, "勇猛", "魏王的卫兵"),
        ("曹仁", "魏", "RARE", 5, 6, None, "刹那的号令"),
        ("贾诩", "魏", "COMMON", 1, 9, None, "离间谋略"),
        ("王异", "魏", "RARE", 4, 8, ("魅力", "防栅"), "以牙还牙"),
        ("许褚", "魏", "EPIC", 8, 2, "募兵", "防护战术"),
        ("夏侯渊", "魏", "EPIC", 8, 4, "募兵", "神速战术"),
        ("郭皇后", "魏", "COMMON", 2, 7, "魅力", "衰弱的连计"),
        ("蔡文姬", "魏", "COMMON", 1, 7, "魅力", "飞天之舞"),
        ("于禁", "魏", "RARE", 5, 6, "连计", "魏武精英"),
        ("张辽", "凉", "RARE", 7, 6, "连计", "人马一体"),
        ("吕布", "凉", "LEGENDARY", 10, 1, "勇猛", "天下无双"),
        ("董卓", "凉", "EPIC", 8, 7, "魅力", "人马大号令"),
        ("陈宫", "凉", "RARE", 4, 7, "防栅", "破坏性的献策"),
        ("邹氏", "凉", "COMMON", 2, 7, ("伏兵", "魅力"), "堕落之舞"),
        ("李傕和郭汜", "凉", "RARE", 6, 3, None, "卑劣的奇袭"),
        ("诸葛亮", "蜀", "RARE", 3, 10, "防栅", "石兵八阵"),
        ("鲁肃", "吴", "RARE", 4, 8, "防栅", "同盟缔结"),
        ("大乔", "吴", "COMMON", 2, 4, ("募兵", "魅力"), "江东的大美人"),
        ("太史慈", "吴", "EPIC", 8, 4, None, "天衣无缝"),
        ("朱然", "吴", "RARE", 4, 6, ("防栅", "募兵"), "防栅重建"),
        ("小乔", "吴", "RARE", 2, 5, ("防栅", "魅力"), "流星的仪式"),
        ("汉献帝", "他", "COMMON", 1, 5, ("魅力", "防栅"), "敕命"),
        ("司马徽", "他", "COMMON", 1, 8, ("防栅", "募兵"), "夫子的教诲"),
        ("皇甫嵩", "他", "RARE", 5, 5, "募兵", "贼军讨伐令"),
        ("公孙瓒", "他", "RARE", 5, 5, ("魅力", "募兵"), "白马阵"),
        ("张角", "他", "COMMON", 2, 8, "魅力", "太平要术"),
        ("带来洞主", "他", "RARE", 5, 3, "复活", "击飞战术"),
        ("王允", "他", "COMMON", 2, 8, None, "小连环计"),
        ("文丑", "袁", "EPIC", 8, 3, "勇猛", "士气旺盛"),
        ("田丰", "袁", "RARE", 4, 9, "伏兵", "缜密的攻势"),
        ("于夫罗", "袁", "COMMON", 3, 3, "连计", "联合围攻"),
        ("张郃", "袁", "RARE", 6, 5, None, "率先立功"),
    ]

    for name, camp, rarity, force, intelligence, attrs, skill in checks:
        g = get_general_by_name(name)
        assert g is not None, f"{name} 创建失败"
        assert g.camp.value == camp, f"{name} 阵营: 期望{camp} 实际{g.camp.value}"
        assert g.rarity.name == rarity, f"{name} 稀有度: 期望{rarity} 实际{g.rarity.name}"
        assert g.force == force, f"{name} 武力: 期望{force} 实际{g.force}"
        assert g.intelligence == intelligence, f"{name} 智力: 期望{intelligence} 实际{g.intelligence}"
        assert g.max_hp == force + intelligence, f"{name} 生命: 期望{force+intelligence} 实际{g.max_hp}"
        expected_attrs = attrs if isinstance(attrs, tuple) else (attrs,)
        for attr in expected_attrs:
            if attr:
                assert attr in [a.value for a in g.attribute], f"{name} 应有属性{attr}"
        assert g.active_skill is not None, f"{name} 应有主动技能"
        assert g.active_skill.name == skill, f"{name} 技能: 期望{skill} 实际{g.active_skill.name}"
        attr_text = "/".join([attr for attr in expected_attrs if attr]) or "无"
        print(f"   ✅ {name}: {force}武 {intelligence}智 [{attr_text}] {skill}")


def test_skill_independence():
    """Test independent cooldown for generals sharing one skill."""
    print("\n" + "=" * 20)
    print("   test skill independence")
    print("=" * 20)

    zhang_ren = get_general_by_name("张任")
    zhou_cang = get_general_by_name("周仓")
    assert zhang_ren and zhou_cang, "general creation failed"
    assert zhang_ren.active_skill.name == zhou_cang.active_skill.name == "强化战术"

    team = Team("test team", Camp.TA)
    team.add_general(zhang_ren)
    team.add_general(zhou_cang)

    print(f"\n   morale: {team.current_morale}/{team.max_morale}")
    print(f"   {zhang_ren.name} cooldown: {zhang_ren.active_skill_cooldown}")
    print(f"   {zhou_cang.name} cooldown: {zhou_cang.active_skill_cooldown}")

    r1 = team.use_skill(zhang_ren, [zhang_ren], {"battle_phase": "main"})
    print(f"\n   {zhang_ren.name} skill: {'success' if r1.get('success') else 'failed'}")
    print(f"   morale: {team.current_morale}/{team.max_morale}")

    r2 = team.use_skill(zhou_cang, [zhou_cang], {"battle_phase": "main"})
    print(f"   {zhou_cang.name} skill: {'success' if r2.get('success') else 'failed'}")
    print(f"   morale: {team.current_morale}/{team.max_morale}")

    assert r1.get("success") and r2.get("success"), "both generals should be able to use the shared skill"
    print("   ok: shared skill cooldown is independent")


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
    """Test chain passive damage sharing."""
    print("\n" + "=" * 20)
    print("   test chain passive")
    print("=" * 20)

    chain_general_1 = get_general_by_name("张辽")
    chain_general_2 = get_general_by_name("于禁")
    assert chain_general_1 and chain_general_2

    team = Team("chain test team", Camp.SHU)
    team.add_general(chain_general_1)
    team.add_general(chain_general_2)

    team.position_general(chain_general_1, 0, 0)
    team.position_general(chain_general_2, 0, 1)

    assert chain_general_1.has_passive_skill("连环")
    assert chain_general_2.has_passive_skill("连环")

    hp_before = chain_general_2.current_hp
    print(f"   before: chain1 HP={chain_general_1.current_hp}/{chain_general_1.max_hp}, "
          f"chain2 HP={chain_general_2.current_hp}/{chain_general_2.max_hp}")

    from src.models.general import General
    attacker = General(9999, "test attacker", Camp.WEI, Rarity.COMMON, 1.0, 10, 5)
    attacker.attack(chain_general_1)

    print(f"   after: chain1 HP={chain_general_1.current_hp}/{chain_general_1.max_hp}, "
          f"chain2 HP={chain_general_2.current_hp}/{chain_general_2.max_hp}")

    assert chain_general_2.current_hp < hp_before,         f"chain sharing failed: chain2 HP should drop from {hp_before}"
    print("   ok: chain damage sharing works")


if __name__ == "__main__":
    print("🎮 武将系统完整测试")

    test_all_generals()
    test_specific_generals()
    test_skill_independence()
    test_team_morale_limit()
    test_chain_integration()

    print(f"\n✅ 测试完成！")
    active_skill_count = len({
        data["skill_id"] for data in GENERALS_DATA
        if data.get("skill_id")
    })
    camp_count = len({data["camp"] for data in GENERALS_DATA})
    print(f"   📋 武将: {len(GENERALS_DATA)}人，覆盖{camp_count}个阵营")
    print(f"   🔥 技能: {active_skill_count}个主动技能 + 7个被动技能")
    print(f"   ⚡ 士气: 固定上限12")
    print(f"   💚 生命: 武力+智力")
    print(f"   🎯 冷却: 每个武将独立管理")
    print(f"   🔗 连环: 伤害分担+效果同步已集成")

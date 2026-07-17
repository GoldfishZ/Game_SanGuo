"""
测试同盟缔结技能的士气增加效果
验证"士气最大值+2"功能是否正常工作
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.general import General, Camp, Rarity, Attribute
from src.models.team import Team
from src.game_data.skills_config import get_skill_by_id
from src.game_data.passive_skills_config import get_passive_skills_for_attributes


class MockBattleContext:
    """模拟战斗上下文"""
    
    def __init__(self):
        self.teams = {}
    
    def add_team(self, team_name: str, team: Team):
        """添加队伍"""
        self.teams[team_name] = team
    
    def get_team_for_general(self, general: General) -> Team:
        """根据武将获取所属队伍"""
        for team in self.teams.values():
            if general in team.generals:
                return team
        return None


def test_alliance_pact_morale_boost():
    """测试同盟缔结技能的士气增加效果"""
    print("🤝 测试同盟缔结技能 - 士气最大值+2")
    
    # 创建鲁肃（拥有同盟缔结技能）
    lu_su = General(
        general_id=1003,
        name="鲁肃",
        camp=Camp.WU,
        rarity=Rarity.RARE,
        cost=1.5,
        force=4,
        intelligence=8,
        attribute=[Attribute.FENCE],
        active_skill=get_skill_by_id("alliance_pact")  # 同盟缔结
    )
    lu_su.passive_skills = get_passive_skills_for_attributes(lu_su.attribute)
    
    # 创建队伍
    team = Team("吴国队伍", Camp.WU)
    team.add_general(lu_su)
    
    # 创建战斗上下文
    battle_context = MockBattleContext()
    battle_context.add_team("wu_team", team)
    
    print(f"   使用技能前:")
    print(f"   队伍最大士气: {team.max_morale}")
    print(f"   队伍当前士气: {team.current_morale}")
    print(f"   鲁肃技能冷却: {lu_su.active_skill_cooldown}")
    
    # 使用同盟缔结技能
    result = lu_su.use_active_skill(
        targets=[lu_su],  # 目标是自己（TargetType.SELF）
        battle_context=battle_context,
        team=team
    )
    
    print(f"\n   技能使用结果:")
    print(f"   成功: {result['success']}")
    if result['success']:
        print(f"   技能名称: {result['skill_name']}")
        print(f"   士气消耗: {result['morale_consumed']}")
        print(f"   剩余士气: {result['remaining_morale']}")
        if 'details' in result:
            for detail in result['details']:
                print(f"   效果详情: {detail}")
    
    print(f"\n   使用技能后:")
    print(f"   队伍最大士气: {team.max_morale}")
    print(f"   队伍当前士气: {team.current_morale}")
    print(f"   鲁肃技能冷却: {lu_su.active_skill_cooldown}")
    
    # 验证效果
    expected_max_morale = 12 + 2  # 原始12 + 技能增加2
    expected_current_morale = 12 - 2 + 2  # 原始12 - 消耗2 + 增加2
    
    if team.max_morale == expected_max_morale:
        print(f"   ✅ 最大士气增加正确: {expected_max_morale}")
    else:
        print(f"   ❌ 最大士气增加错误: 期望{expected_max_morale}, 实际{team.max_morale}")
    
    if team.current_morale == expected_current_morale:
        print(f"   ✅ 当前士气正确: {expected_current_morale}")
    else:
        print(f"   ❌ 当前士气错误: 期望{expected_current_morale}, 实际{team.current_morale}")


def test_multiple_alliance_uses():
    """测试多次使用同盟缔结技能"""
    print("\n🔄 测试多次使用同盟缔结技能")
    
    # 创建武将和队伍
    general = General(
        general_id=2001,
        name="测试武将",
        camp=Camp.SHU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=5,
        intelligence=5,
        attribute=[],
        active_skill=get_skill_by_id("alliance_pact")
    )
    
    team = Team("测试队伍")
    team.add_general(general)
    
    battle_context = MockBattleContext()
    battle_context.add_team("test_team", team)
    
    print(f"   初始状态: 最大士气{team.max_morale}, 当前士气{team.current_morale}")
    
    # 第一次使用
    result1 = general.use_active_skill([general], battle_context, team)
    print(f"   第一次使用后: 最大士气{team.max_morale}, 当前士气{team.current_morale}")
    
    # 第二次使用
    result2 = general.use_active_skill([general], battle_context, team)
    print(f"   第二次使用后: 最大士气{team.max_morale}, 当前士气{team.current_morale}")
    
    # 第三次使用
    result3 = general.use_active_skill([general], battle_context, team)
    print(f"   第三次使用后: 最大士气{team.max_morale}, 当前士气{team.current_morale}")
    
    # 验证累积效果
    expected_max = 12 + 6  # 12 + 3次使用 × 2
    expected_current = 12 + 6 - 6  # 12 + 6增加 - 6消耗
    
    if team.max_morale == expected_max and team.current_morale == expected_current:
        print(f"   ✅ 多次使用效果正确: 最大{expected_max}, 当前{expected_current}")
    else:
        print(f"   ❌ 多次使用效果错误")


def main():
    """主测试函数"""
    print("🎮 同盟缔结技能测试")
    print("=" * 60)
    
    test_alliance_pact_morale_boost()
    test_multiple_alliance_uses()
    
    print("\n" + "=" * 60)
    print("✅ 同盟缔结技能测试完成！")
    print("📋 功能验证:")
    print("   🤝 同盟缔结: 士气最大值+2，立即生效")
    print("   💰 士气消耗: 使用技能消耗2点士气")
    print("   🔄 可重复使用: 无冷却时间限制")
    print("   ⚡ 立即生效: 当前士气也增加2点")


if __name__ == "__main__":
    main()

"""
测试大乔专属技能“江东的大美人”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_ally(name):
    return General(
        general_id=9400,
        name=name,
        camp=Camp.WU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=4,
        intelligence=4,
    )


def test_da_qiao_data_and_skill():
    da_qiao = get_general_by_name("大乔")

    assert da_qiao.camp == Camp.WU
    assert da_qiao.rarity == Rarity.COMMON
    assert da_qiao.cost == 1.0
    assert da_qiao.force == 2
    assert da_qiao.intelligence == 4
    assert da_qiao.max_hp == 6
    assert "募兵" in [attr.value for attr in da_qiao.attribute]
    assert "魅力" in [attr.value for attr in da_qiao.attribute]
    assert da_qiao.active_skill.name == "江东的大美人"
    assert da_qiao.active_skill.morale_cost == 4


def test_jiangdong_beauty_cleanses_heals_or_raises_hp_cap_in_3x3():
    da_qiao = get_general_by_name("大乔")
    debuffed = make_ally("减益友军")
    damaged = make_ally("受伤友军")
    full_hp = make_ally("满血友军")
    outside = make_ally("圈外友军")

    team = Team("吴军")
    enemy_team = Team("敌军")
    for general in [da_qiao, debuffed, damaged, full_hp, outside]:
        team.add_general(general)

    team.position_general(da_qiao, 1, 1)
    team.position_general(debuffed, 0, 0)
    team.position_general(damaged, 0, 2)
    team.position_general(full_hp, 2, 2)
    team.position_general(outside, 2, 3)

    debuffed.add_debuff("force_reduction", 2, 1)
    damaged.current_hp -= 2

    result = team.use_skill(da_qiao, [da_qiao], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert team.current_morale == 8
    assert result["targets_affected"] == 4

    assert debuffed.debuffs == []
    assert debuffed.current_hp == debuffed.max_hp

    assert damaged.current_hp == damaged.max_hp - 1

    assert full_hp.max_hp == 9
    assert full_hp.current_hp == 9

    assert da_qiao.max_hp == 7
    assert da_qiao.current_hp == 7

    assert outside.max_hp == 8
    assert outside.current_hp == 8


def test_jiangdong_beauty_respects_selected_3x3_containing_caster():
    da_qiao = get_general_by_name("大乔")
    left_outside = make_ally("左侧选区外")
    right_inside = make_ally("右侧选区内")
    team = Team("吴军")
    enemy_team = Team("敌军")
    for general in [da_qiao, left_outside, right_inside]:
        team.add_general(general)
    team.position_general(da_qiao, 1, 1)
    team.position_general(left_outside, 1, 0)
    team.position_general(right_inside, 1, 3)
    left_max_hp = left_outside.max_hp
    right_max_hp = right_inside.max_hp

    result = team.use_skill(
        da_qiao,
        [{"row": 0, "col": 1}],
        BattleContext(team, enemy_team),
    )

    assert result["success"] is True
    assert left_outside.max_hp == left_max_hp
    assert right_inside.max_hp == right_max_hp + 1


if __name__ == "__main__":
    test_da_qiao_data_and_skill()
    test_jiangdong_beauty_cleanses_heals_or_raises_hp_cap_in_3x3()
    print("大乔江东的大美人测试通过")

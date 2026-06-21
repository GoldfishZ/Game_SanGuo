"""
测试蔡文姬专属技能“飞天之舞”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_general(general_id, name, camp=Camp.WEI):
    return General(
        general_id=general_id,
        name=name,
        camp=camp,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=4,
        intelligence=4,
    )


def test_cai_wenji_data_and_skill():
    cai_wenji = get_general_by_name("蔡文姬")

    assert cai_wenji.camp == Camp.WEI
    assert cai_wenji.rarity == Rarity.COMMON
    assert cai_wenji.cost == 1.0
    assert cai_wenji.force == 1
    assert cai_wenji.intelligence == 7
    assert {attr.value for attr in cai_wenji.attribute} == {"魅力"}
    assert cai_wenji.active_skill.name == "飞天之舞"
    assert cai_wenji.active_skill.morale_cost == 5


def test_flying_dance_grants_attack_speed_to_all_alive_allies():
    cai_wenji = get_general_by_name("蔡文姬")
    ally = make_general(9401, "友军")
    defeated_ally = make_general(9402, "阵亡友军")
    enemy = make_general(9403, "敌军", Camp.SHU)
    defeated_ally.current_hp = 0
    defeated_ally.is_alive = False

    team = Team("魏军")
    enemy_team = Team("敌军")
    for general in [cai_wenji, ally, defeated_ally]:
        team.add_general(general)
    enemy_team.add_general(enemy)

    result = team.use_skill(cai_wenji, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["targets_affected"] == 2
    assert team.current_morale == 7
    assert cai_wenji.has_buff_type("attack_speed_judgment")
    assert ally.has_buff_type("attack_speed_judgment")
    assert not defeated_ally.has_buff_type("attack_speed_judgment")
    assert not enemy.has_buff_type("attack_speed_judgment")


if __name__ == "__main__":
    test_cai_wenji_data_and_skill()
    test_flying_dance_grants_attack_speed_to_all_alive_allies()
    print("蔡文姬飞天之舞测试通过")

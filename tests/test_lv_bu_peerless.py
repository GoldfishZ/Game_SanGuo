"""
测试吕布专属技能“天下无双”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.models.general import Camp
from src.models.team import Team


class DummyBattleContext:
    def __init__(self, team):
        self.team = team

    def get_team_for_general(self, general):
        return self.team if general in self.team.generals else None


def test_lv_bu_peerless_under_heaven_boosts_force_and_hp_cap():
    lv_bu = get_general_by_name("吕布")
    team = Team("西凉军", Camp.LIANG)
    team.add_general(lv_bu)
    context = DummyBattleContext(team)

    assert lv_bu.camp == Camp.LIANG
    assert lv_bu.force == 10
    assert lv_bu.intelligence == 1
    assert lv_bu.max_hp == 11
    assert lv_bu.current_hp == 11
    assert lv_bu.active_skill.name == "天下无双"
    assert team.current_morale == 12

    result = lv_bu.use_active_skill([lv_bu], context, team)

    assert result["success"] is True
    assert team.current_morale == 6
    assert lv_bu.get_effective_force() == 16
    assert lv_bu.max_hp == 13
    assert lv_bu.current_hp == 13

    assert result["details"][0]["duration"] == 3

    lv_bu.update_effects()
    assert lv_bu.get_effective_force() == 16
    assert lv_bu.max_hp == 13
    assert lv_bu.current_hp == 13

    lv_bu.update_effects()
    assert lv_bu.get_effective_force() == 16
    assert lv_bu.max_hp == 13
    assert lv_bu.current_hp == 13

    lv_bu.update_effects()
    assert lv_bu.get_effective_force() == 10
    assert lv_bu.max_hp == 13
    assert lv_bu.current_hp == 13


if __name__ == "__main__":
    test_lv_bu_peerless_under_heaven_boosts_force_and_hp_cap()
    print("吕布天下无双测试通过")

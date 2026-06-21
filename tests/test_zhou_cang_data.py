"""
测试周仓武将数据。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.models.general import Camp, Rarity


def test_zhou_cang_data_and_skill():
    zhou_cang = get_general_by_name("周仓")

    assert zhou_cang.camp == Camp.SHU
    assert zhou_cang.rarity == Rarity.COMMON
    assert zhou_cang.cost == 1.0
    assert zhou_cang.force == 4
    assert zhou_cang.intelligence == 1
    assert {attr.value for attr in zhou_cang.attribute} == {"勇猛"}
    assert zhou_cang.active_skill.name == "强化战术"
    assert zhou_cang.active_skill.morale_cost == 4


if __name__ == "__main__":
    test_zhou_cang_data_and_skill()
    print("周仓数据测试通过")

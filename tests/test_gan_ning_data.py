"""
测试甘宁武将数据。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.models.general import Camp, Rarity


def test_gan_ning_data_and_skill():
    gan_ning = get_general_by_name("甘宁")

    assert gan_ning.camp == Camp.WU
    assert gan_ning.rarity == Rarity.EPIC
    assert gan_ning.cost == 2.5
    assert gan_ning.force == 8
    assert gan_ning.intelligence == 6
    assert gan_ning.max_hp == 14
    assert "勇猛" in [attr.value for attr in gan_ning.attribute]
    assert gan_ning.active_skill.name == "强化战术"
    assert gan_ning.active_skill.morale_cost == 4


if __name__ == "__main__":
    test_gan_ning_data_and_skill()
    print("甘宁数据测试通过")

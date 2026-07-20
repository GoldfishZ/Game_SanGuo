"""强化学习奖励的无进展惩罚测试。"""
from src.rl.reward import RewardHandler


class Team:
    def __init__(self, hp, alive):
        self.hp = hp
        self.alive = alive

    def get_alive_generals(self):
        return [object()] * self.alive


# RewardHandler's public helpers expect generals with HP; patch through small fake objects.
class General:
    def __init__(self, hp):
        self.current_hp = hp


class CombatTeam:
    def __init__(self, hp_values):
        self.generals = [General(hp) for hp in hp_values]

    def get_alive_generals(self):
        return [general for general in self.generals if general.current_hp > 0]


def test_no_progress_action_receives_penalty():
    learning = CombatTeam([10])
    enemy = CombatTeam([10])
    reward = RewardHandler()
    reward.reset(learning, enemy)
    value = reward.step(learning, enemy, action_success=False)
    assert value == reward.config["no_progress"]
    assert reward.last_no_progress


def test_successful_phase_action_is_not_penalized_as_no_progress():
    learning = CombatTeam([10])
    enemy = CombatTeam([10])
    reward = RewardHandler()
    reward.reset(learning, enemy)
    value = reward.step(learning, enemy, action_success=True)
    assert value == reward.config["skill_success"]
    assert not reward.last_no_progress


def test_damage_action_is_not_penalized_as_no_progress():
    learning = CombatTeam([10])
    enemy = CombatTeam([10])
    reward = RewardHandler()
    reward.reset(learning, enemy)
    enemy.generals[0].current_hp = 8
    value = reward.step(learning, enemy, action_success=False)
    assert value > 0
    assert not reward.last_no_progress

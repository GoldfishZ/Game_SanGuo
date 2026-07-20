"""学习方视角的可配置奖励。"""
from __future__ import annotations

DEFAULT_REWARD = {
    "hp_delta": 0.05,
    "kill": 0.15,
    "skill_success": 0.01,
    "no_progress": -0.02,
    "win": 1.0,
    "lose": -1.0,
    "draw": -0.2,
}


def team_hp(team):
    return sum(g.current_hp for g in team.get_alive_generals())


def alive_count(team):
    return len(team.get_alive_generals())


class RewardHandler:
    def __init__(self, config=None):
        self.config = {**DEFAULT_REWARD, **(config or {})}
        self.previous = None
        self.last_no_progress = False

    def reset(self, learning_team, enemy_team):
        self.previous = (team_hp(learning_team), team_hp(enemy_team), alive_count(learning_team), alive_count(enemy_team))

    def step(self, learning_team, enemy_team, *, action_success=False, done=False, winner=None, timeout=False):
        current = (team_hp(learning_team), team_hp(enemy_team), alive_count(learning_team), alive_count(enemy_team))
        old_self, old_enemy, old_alive, old_enemy_alive = self.previous
        self_hp, enemy_hp, self_alive, enemy_alive = current
        hp_delta = (old_enemy - enemy_hp) - (old_self - self_hp)
        kill_delta = (old_enemy_alive - enemy_alive) - (old_alive - self_alive)
        reward = self.config["hp_delta"] * hp_delta
        reward += self.config["kill"] * kill_delta
        no_progress = not action_success and hp_delta == 0 and kill_delta == 0
        if no_progress and not done:
            reward += self.config["no_progress"]
        if action_success:
            reward += self.config["skill_success"]
        if done:
            if timeout and winner is None:
                reward += self.config["draw"]
            elif winner == learning_team.team_name:
                reward += self.config["win"]
            else:
                reward += self.config["lose"]
        self.previous = current
        self.last_no_progress = no_progress
        return float(reward)

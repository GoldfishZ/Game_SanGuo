"""PvE 战术导向、双方对称的 potential-delta 奖励 v3。"""
from __future__ import annotations

DEFAULT_REWARD = {
    "hp_delta": 0.05,
    "kill": 0.15,
    "action_success": 0.005,
    "no_progress": -0.02,
    "fence_delta": 0.10,
    "shield_delta": 0.02,
    "effect_delta": 0.01,
    "win": 1.0,
    "lose": -1.0,
    "draw": 0.0,
}


def _alive(team):
    return list(team.get_alive_generals())


def _fence_count(team):
    count = 0
    for general in _alive(team):
        getter = getattr(general, "get_passive_skill", None)
        fence = getter("防栅") if getter else None
        count += int(bool(fence and getattr(fence, "is_active", False)))
    return count


def _shield_capacity(team):
    return sum(
        max(0.0, float(effect.get("value", 0) or 0))
        for general in _alive(team)
        for effect in getattr(general, "buffs", ())
        if effect.get("type") == "damage_shield"
    )


def _effect_mass(team):
    """效果的低权重势能；到期时会反向扣回，避免仅靠反复施法刷分。"""
    total = 0.0
    for general in _alive(team):
        for sign, attribute in ((1.0, "buffs"), (-1.0, "debuffs")):
            for effect in getattr(general, attribute, ()):
                if effect.get("type") == "damage_shield":
                    continue
                value = effect.get("value", 1)
                numeric = float(value) if isinstance(value, (int, float, bool)) else 1.0
                duration = max(1.0, float(effect.get("duration", 1) or 1))
                total += sign * max(1.0, abs(numeric)) * min(duration, 4.0) / 4.0
    return total


def _team_state(team):
    alive = _alive(team)
    return {
        "hp": sum(float(general.current_hp) for general in alive),
        "alive": len(alive),
        "fence": _fence_count(team),
        "shield": _shield_capacity(team),
        "effect": _effect_mass(team),
    }


class RewardHandler:
    def __init__(self, config=None):
        config = dict(config or {})
        # 接受 v2 checkpoint/YAML 的旧名称，但内部统一为 action_success。
        if "skill_success" in config and "action_success" not in config:
            config["action_success"] = config.pop("skill_success")
        self.config = {**DEFAULT_REWARD, **config}
        self.previous = None
        self.last_no_progress = False
        self.last_components = {}

    def reset(self, learning_team, enemy_team):
        self.previous = (_team_state(learning_team), _team_state(enemy_team))
        self.last_no_progress = False
        self.last_components = {}

    def step(self, learning_team, enemy_team, *, action_success=False,
             action_kind=None, done=False, winner=None, timeout=False):
        current_self, current_enemy = _team_state(learning_team), _team_state(enemy_team)
        old_self, old_enemy = self.previous

        def relative_delta(key):
            return ((current_self[key] - old_self[key])
                    - (current_enemy[key] - old_enemy[key]))

        components = {
            "hp": self.config["hp_delta"] * relative_delta("hp"),
            "kill": self.config["kill"] * relative_delta("alive"),
            "fence": self.config["fence_delta"] * relative_delta("fence"),
            "shield": self.config["shield_delta"] * relative_delta("shield"),
            "effect": self.config["effect_delta"] * relative_delta("effect"),
            "action": 0.0,
            "no_progress": 0.0,
            "terminal": 0.0,
        }
        is_end = action_kind in ("end_skill", "end_attack")
        if action_success and not is_end:
            components["action"] = self.config["action_success"]

        changed = any(abs(components[key]) > 1e-12 for key in ("hp", "kill", "fence", "shield", "effect"))
        self.last_no_progress = bool(not is_end and not action_success and not changed and not done)
        if self.last_no_progress:
            components["no_progress"] = self.config["no_progress"]

        if done:
            if timeout:
                components["terminal"] = self.config["draw"]
            elif winner == learning_team.team_name:
                components["terminal"] = self.config["win"]
            else:
                components["terminal"] = self.config["lose"]

        self.previous = (current_self, current_enemy)
        self.last_components = components
        return float(sum(components.values()))

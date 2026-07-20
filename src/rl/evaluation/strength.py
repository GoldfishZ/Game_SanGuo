"""武将实战表现与相对强度统计。"""
from __future__ import annotations

from collections import defaultdict
import math


class GeneralStrengthTracker:
    """以滚动/累计 episode 统计当前策略下的武将实际贡献。"""
    def __init__(self):
        self.stats = defaultdict(lambda: {
            "appearances": 0, "wins": 0, "survived": 0,
            "hp_fraction_sum": 0.0, "damage": 0.0,
        })

    def record_team(self, team, won, damage_by_id=None):
        damage_by_id = damage_by_id or {}
        for general in team.generals:
            stat = self.stats[general.name]
            stat["appearances"] += 1
            stat["wins"] += int(won)
            stat["survived"] += int(general.is_alive)
            stat["hp_fraction_sum"] += general.current_hp / max(1, general.max_hp)
            stat["damage"] += damage_by_id.get(general.general_id, 0.0)

    def record_episode(self, learning_team, enemy_team, winner_name, damage_by_id=None):
        self.record_team(learning_team, winner_name == learning_team.team_name, damage_by_id)
        self.record_team(enemy_team, winner_name == enemy_team.team_name, damage_by_id)

    def snapshot(self):
        report = {}
        for name, stat in self.stats.items():
            count = stat["appearances"]
            if not count:
                continue
            win_rate = stat["wins"] / count
            report[name] = {
                "appearances": count,
                "win_rate": win_rate,
                "survival_rate": stat["survived"] / count,
                "mean_hp_fraction": stat["hp_fraction_sum"] / count,
                "mean_damage": stat["damage"] / count,
                # Center at 0: positive is above a 50% side-win baseline.
                "practical_strength": win_rate - 0.5,
            }
        return dict(sorted(report.items(), key=lambda item: item[1]["practical_strength"], reverse=True))

    def balance_metrics(self):
        values = [item["practical_strength"] for item in self.snapshot().values()]
        if not values:
            return {"strength_std": 0.0, "strength_range": 0.0, "general_count": 0}
        mean = sum(values) / len(values)
        return {
            "strength_std": math.sqrt(sum((value - mean) ** 2 for value in values) / len(values)),
            "strength_range": max(values) - min(values),
            "general_count": len(values),
        }

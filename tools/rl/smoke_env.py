"""手动检查离线 RL 环境的最小随机对局。"""
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.rl.env import SanguoEnv


def main():
    env = SanguoEnv()
    _, _ = env.reset(7)
    rng = random.Random(3)
    done = False
    steps = 0
    total_reward = 0.0
    while not done and steps < 2000:
        action = rng.choice(env.legal_actions())
        _, reward, done, _ = env.step(action)
        total_reward += reward
        steps += 1
    print({"done": done, "steps": steps, "turn": env.battle_system.turn_count, "reward": round(total_reward, 3)})


if __name__ == "__main__":
    main()

"""带CUDA缓存回收的笔记本v3训练入口。"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.rl.training.ppo_v3_laptop import ppo_update
from tools.rl import train_ppo_v3


if __name__ == "__main__":
    train_ppo_v3.ppo_update = ppo_update
    train_ppo_v3.main()

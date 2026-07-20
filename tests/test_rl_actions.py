"""动作编解码与掩码测试。"""
from src.rl import actions
from src.rl.env import SanguoEnv


def test_rl_action_codec_round_trip():
    samples = (
        actions.Action("end_skill"),
        actions.Action("end_attack"),
        actions.Action("skill_target", 2, 5),
        actions.Action("skill_area", 3, row=1, col=2),
        actions.Action("attack", 4, 7, guess="偶"),
    )
    for action in samples:
        assert actions.decode(actions.encode(action)) == action


def test_rl_every_legal_action_decodes():
    env = SanguoEnv()
    env.reset(123)
    for action_id in env.legal_actions():
        assert actions.encode(actions.decode(action_id)) == action_id

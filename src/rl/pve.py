"""Server-side PvE bridge for draft, formation and PPO battle inference."""
from __future__ import annotations

import os
from pathlib import Path

from src.paths import PVE_MODELS_DIR
from src.rl.prebattle import PrebattlePolicy, snapshot_formation


DEFAULT_BATTLE_MODEL = PVE_MODELS_DIR / "battle_policy.pt"
DEFAULT_PREBATTLE_MODEL = PVE_MODELS_DIR / "prebattle_value.pt"


class _BattleView:
    """Minimal environment facade consumed by observation/actions/model policies."""

    def __init__(self, battle_system, learning_team, enemy_team, subphase):
        self.battle_system = battle_system
        self.learning_team = learning_team
        self.enemy_team = enemy_team
        self.subphase = subphase

    def observation(self):
        from src.rl.observation import build_observation
        return build_observation(self)

    def action_mask(self):
        from src.rl import actions
        return actions.action_mask(self)

    def legal_actions(self):
        from src.rl import actions
        return actions.legal_actions(self)

    def decode_action(self, action_id):
        from src.rl import actions
        return actions.decode(action_id)

    def attack_target_hp(self, action_id):
        from src.rl import actions
        action = actions.decode(action_id)
        target = actions.general_at(self.enemy_team, action.target_slot)
        return target.current_hp if target else float("inf")


class PVEController:
    """Lazily loaded AI components; failures degrade to safe baselines."""

    def __init__(self, battle_checkpoint=None, prebattle_checkpoint=None, *, device="cpu"):
        self.device = device
        self.battle_checkpoint = Path(
            battle_checkpoint or os.environ.get("SANGUO_PVE_BATTLE_MODEL", DEFAULT_BATTLE_MODEL)
        )
        self.prebattle_checkpoint = Path(
            prebattle_checkpoint or os.environ.get("SANGUO_PVE_PREBATTLE_MODEL", DEFAULT_PREBATTLE_MODEL)
        )
        self.battle_model = None
        self.prebattle = PrebattlePolicy(device=device)
        self.load_errors = []
        self._loaded = False

    @property
    def available(self):
        self.load()
        return self.battle_model is not None

    def load(self):
        if self._loaded:
            return self
        self._loaded = True
        try:
            import torch
            from src.rl import actions
            from src.rl.models.actor_critic_v3 import ActorCritic, MODEL_SCHEMA
            from src.rl.observation import OBSERVATION_SCHEMA, OBSERVATION_SIZE
            from src.rl.training.checkpoint import CheckpointManager
            state = torch.load(self.battle_checkpoint, map_location=self.device, weights_only=False)
            CheckpointManager.validate_schema(
                state, observation_schema=OBSERVATION_SCHEMA,
                observation_size=OBSERVATION_SIZE, action_size=actions.ACTION_SIZE,
                model_schema=MODEL_SCHEMA,
            )
            self.battle_model = ActorCritic(OBSERVATION_SIZE, actions.ACTION_SIZE)
            self.battle_model.load_state_dict(state["model"])
            self.battle_model.to(self.device).eval()
        except Exception as exc:  # Web must remain playable when an artifact is absent.
            self.load_errors.append(f"战斗模型加载失败: {exc}")
            self.battle_model = None
        try:
            self.prebattle.load(self.prebattle_checkpoint)
        except Exception as exc:
            self.load_errors.append(f"预战模型加载失败: {exc}")
        return self

    def choose_draft(self, pool, enemy_generals, cost_limit):
        self.load()
        return self.prebattle.choose_draft(pool, enemy_generals, cost_limit)

    def choose_formation(self, generals, enemy_player):
        self.load()
        return self.prebattle.choose_formation(
            generals, enemy_player.selected_generals, snapshot_formation(enemy_player.team),
        )

    def _choose_battle_action(self, view):
        if self.battle_model is None:
            legal = view.legal_actions()
            attacks = [item for item in legal if view.decode_action(item).kind == "attack"]
            if attacks:
                return min(attacks, key=view.attack_target_hp)
            skills = [item for item in legal if view.decode_action(item).kind.startswith("skill")]
            return (skills or legal)[0]
        import torch
        with torch.no_grad():
            observation = torch.as_tensor(
                view.observation(), dtype=torch.float32, device=self.device,
            ).unsqueeze(0)
            mask = torch.as_tensor(
                view.action_mask(), dtype=torch.bool, device=self.device,
            ).unsqueeze(0)
            logits, _ = self.battle_model(observation, mask)
            return int(logits.argmax(dim=-1).item())

    @staticmethod
    def _apply_action(state, view, action):
        from src.rl import actions
        if action.kind == "end_skill":
            view.subphase = "attack"
            return {"success": True, "type": "end_skill"}
        if action.kind == "end_attack":
            return {"success": True, "type": "end_attack"}
        if action.kind.startswith("skill"):
            caster = actions.general_at(view.learning_team, action.actor_slot)
            if caster is None:
                return {"success": False, "message": "AI 施法者阵位为空"}
            target_team = (
                view.learning_team if "ALLY" in caster.active_skill.target_type.name
                else view.enemy_team
            )
            target = actions.general_at(target_team, action.target_slot)
            return state.ensure_rules().skill(
                caster, target=target,
                row=action.row if action.kind == "skill_area" else None,
                col=action.col if action.kind == "skill_area" else None,
                skill_row=action.row if action.kind == "skill_area" else None,
                guess=action.guess,
            )
        attacker = actions.general_at(view.learning_team, action.actor_slot)
        target = actions.general_at(view.enemy_team, action.target_slot)
        if attacker is None or target is None:
            return {"success": False, "message": "AI 攻击者或目标阵位为空"}
        return state.ensure_rules().attack(attacker, target, guess=action.guess)

    @staticmethod
    def _position(team, general):
        position = team.get_general_position(general) if general is not None else None
        return {"row": position[0], "col": position[1]} if position else None

    def step_battle_turn(self, state, ai_team, enemy_team, subphase="skill"):
        """Execute one visible AI sub-action without hiding intermediate game state."""
        self.load()
        battle = state.battle_system
        if battle is None or battle.current_side is not ai_team:
            return {"kind": "idle", "success": False, "next_subphase": subphase}
        if battle._is_game_over() or battle.turn_count >= battle.max_turns:
            state.finish_battle()
            return {"kind": "finished", "success": True, "done": True}

        from src.rl import actions
        view = _BattleView(battle, ai_team, enemy_team, subphase)
        action_id = self._choose_battle_action(view)
        action = actions.decode(action_id)
        actor = actions.general_at(ai_team, action.actor_slot)
        target_team = enemy_team
        if action.kind.startswith("skill") and actor and "ALLY" in actor.active_skill.target_type.name:
            target_team = ai_team
        target = actions.general_at(target_team, action.target_slot)
        actor_position = self._position(ai_team, actor)
        target_position = self._position(target_team, target)

        state.clear_combat_events()
        result = self._apply_action(state, view, action)
        combat_events = state.drain_combat_events()
        if action.kind == "attack":
            result.setdefault("events", combat_events)

        trace = {
            "action_id": action_id,
            "kind": action.kind,
            "success": bool(result.get("success")),
            "actor_id": actor.general_id if actor else result.get("caster_id"),
            "actor_name": actor.name if actor else "",
            "actor_position": actor_position,
            "target_id": target.general_id if target else result.get("target_id"),
            "target_name": target.name if target else "",
            "target_position": target_position,
            "skill_id": actor.active_skill.skill_id if actor and actor.active_skill else "",
            "skill_name": actor.active_skill.name if actor and actor.active_skill else "",
            "result": result,
            "combat_events": combat_events,
            "next_subphase": subphase,
            "done": False,
        }

        if action.kind == "end_skill":
            trace["next_subphase"] = "attack"
            state.last_event = "电脑结束技能阶段，正在选择普攻"
        elif action.kind == "end_attack":
            turn_result = state.ensure_rules().end_turn()
            state.turn_count = battle.turn_count
            morale_event = turn_result["morale_event"]
            controller = state.controller
            morale_event["team"] = (
                "p1" if turn_result["ending_team"] == controller.player1.team.team_name else "p2"
            )
            trace["turn_events"] = [morale_event] + state.drain_combat_events()
            trace["next_subphase"] = "skill"
            if battle._is_game_over() or battle.turn_count >= battle.max_turns:
                state.finish_battle()
                trace["done"] = True
            else:
                state.last_event = f"电脑已完成行动，第{state.turn_count}回合轮到玩家1"
        elif action.kind.startswith("skill"):
            state.last_event = (
                f"电脑：{actor.name} 使用 {actor.active_skill.name}"
                if actor and result.get("success") else result.get("message", "电脑技能失败")
            )
        elif action.kind == "attack":
            damage = result.get("damage", 0)
            state.last_event = (
                f"电脑：{actor.name} 普攻 {target.name} [-{damage}]"
                if actor and target and result.get("success") else result.get("message", "电脑普攻失败")
            )

        if action.kind != "end_attack" and (
            battle._is_game_over() or battle.turn_count >= battle.max_turns
        ):
            state.finish_battle()
            trace["done"] = True
        return trace

    def run_battle_turn(self, state, ai_team, enemy_team):
        """Compatibility helper for headless simulations; Web uses step_battle_turn."""
        traces = []
        subphase = "skill"
        for _ in range(64):
            trace = self.step_battle_turn(state, ai_team, enemy_team, subphase)
            traces.append(trace)
            subphase = trace.get("next_subphase", subphase)
            if trace.get("done") or trace.get("kind") in ("end_attack", "idle", "finished"):
                break
        return traces

"""Four-servo rocker-foot prototype environment; runtime validation pending.

Policy inputs deliberately exclude joint position/velocity and base velocity.
The servo's simulated internal potentiometer is used only inside its plant.
All servo/contact randomization ranges are uncalibrated engineering priors.
"""
from __future__ import annotations

import json
from pathlib import Path

import torch
import isaaclab.sim as sim_utils
from isaaclab.assets import Articulation, ArticulationCfg
from isaaclab.actuators import IdealPDActuatorCfg
from isaaclab.envs import DirectRLEnv, DirectRLEnvCfg
from isaaclab.envs import mdp
from isaaclab.managers import EventTermCfg, SceneEntityCfg
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.utils import configclass

from paths import SIMULATION as HERE
INFO = json.loads((HERE / "robot_info.json").read_text())
JOINT_ORDER = INFO["joint_order"]


@configclass
class EventsCfg:
    foot_material = EventTermCfg(
        func=mdp.randomize_rigid_body_material, mode="startup",
        params={"asset_cfg": SceneEntityCfg("robot", body_names=["left_leg", "right_leg"]),
                "static_friction_range": (0.45, 1.1), "dynamic_friction_range": (0.35, 0.85),
                "restitution_range": (0.0, 0.03), "num_buckets": 32, "make_consistent": True},
    )
    mass_variation = EventTermCfg(
        func=mdp.randomize_rigid_body_mass, mode="startup",
        params={"asset_cfg": SceneEntityCfg("robot"), "mass_distribution_params": (0.9, 1.1),
                "operation": "scale", "recompute_inertia": True},
    )


@configclass
class MicroDucklingEnvCfg(DirectRLEnvCfg):
    randomize_servos = True
    decimation = 10
    episode_length_s = 12.0
    action_space = 4
    observation_space = 56  # four frames of: gyro3, gravity3, commands4, issued targets4
    state_space = 0
    sim = sim_utils.SimulationCfg(dt=0.002, render_interval=10,
        physics_material=sim_utils.RigidBodyMaterialCfg(
            static_friction=0.8, dynamic_friction=0.65, restitution=0.0,
            friction_combine_mode="average", restitution_combine_mode="min"))
    scene = InteractiveSceneCfg(num_envs=256, env_spacing=1.0, replicate_physics=True)
    events = EventsCfg()
    robot_cfg = ArticulationCfg(
        prim_path="/World/envs/env_.*/Robot",
        spawn=sim_utils.UsdFileCfg(
            usd_path=str(HERE / "usd/microduckling.usd"),
            activate_contact_sensors=True,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(disable_gravity=False, max_depenetration_velocity=0.3),
            articulation_props=sim_utils.ArticulationRootPropertiesCfg(
                enabled_self_collisions=True, solver_position_iteration_count=12, solver_velocity_iteration_count=4),
            collision_props=sim_utils.CollisionPropertiesCfg(contact_offset=0.0002, rest_offset=0.0),
        ),
        init_state=ArticulationCfg.InitialStateCfg(pos=(0.0, 0.0, INFO["root_height_m"] + 0.001),
                                                  joint_pos={".*": 0.0}, joint_vel={".*": 0.0}),
        # Explicit efforts supplied below; gains zero prevent a second hidden position controller.
        actuators={"servo_plant": IdealPDActuatorCfg(
            joint_names_expr=JOINT_ORDER, stiffness=0.0, damping=0.0,
            effort_limit=0.11, effort_limit_sim=0.11,
            velocity_limit=10.472, velocity_limit_sim=10.472)},
    )


class MicroDucklingEnv(DirectRLEnv):
    cfg: MicroDucklingEnvCfg

    def __init__(self, cfg, render_mode=None, **kwargs):
        super().__init__(cfg, render_mode, **kwargs)
        self.joint_ids, names = self.robot.find_joints(JOINT_ORDER, preserve_order=True)
        if names != JOINT_ORDER or len(self.robot.joint_names) != 4:
            raise RuntimeError(f"Joint mapping changed: {names}")
        self.limits = torch.tensor(INFO["joint_limits_rad"], device=self.device)
        self.lower, self.upper = self.limits[:, 0], self.limits[:, 1]
        self.center = (self.lower + self.upper) / 2
        self.half = (self.upper - self.lower) / 2
        shape = (self.num_envs, 4)
        self.actions = torch.zeros(shape, device=self.device)
        self.last_actions = self.actions.clone()
        self.issued = torch.zeros(shape, device=self.device)
        self.filtered = self.issued.clone()
        self.backlash_target = self.issued.clone()
        self.efforts = self.issued.clone()
        self.commands = self.issued.clone()
        self.command_queue = torch.zeros((self.num_envs, 3, 4), device=self.device)
        self.command_delay = torch.zeros((self.num_envs, 4), dtype=torch.long, device=self.device)
        self.history = torch.zeros((self.num_envs, 4, 14), device=self.device)
        self.gyro_bias = torch.zeros((self.num_envs, 3), device=self.device)
        self.gravity_bias = self.gyro_bias.clone()
        self.param = {n: torch.zeros(shape, device=self.device) for n in ("tau", "backlash", "kp", "kd", "torque", "speed")}
        self.last_pre_reset = {}

    def _setup_scene(self):
        self.robot = Articulation(self.cfg.robot_cfg)
        plane = sim_utils.GroundPlaneCfg()
        plane.func("/World/Ground", plane)
        self.scene.clone_environments(copy_from_source=False)
        self.scene.filter_collisions(global_prim_paths=["/World/Ground"])
        self.scene.articulations["robot"] = self.robot
        light = sim_utils.DomeLightCfg(intensity=1800.0)
        light.func("/World/Light", light)

    def _pre_physics_step(self, actions):
        self.last_actions.copy_(self.actions)
        self.actions = actions.clamp(-1, 1)
        requested = self.center + self.half * self.actions
        # Same 3 rad/s command slew limiter must be implemented on the microcontroller.
        self.issued += (requested - self.issued).clamp(-3.0 * self.step_dt, 3.0 * self.step_dt)
        self.command_queue[:, 2] = self.command_queue[:, 1].clone()
        self.command_queue[:, 1] = self.command_queue[:, 0].clone()
        self.command_queue[:, 0] = self.issued

    def _apply_action(self):
        delayed = self.command_queue.gather(1, self.command_delay[:, None, :]).squeeze(1)
        self.filtered += (delayed - self.filtered) * (1 - torch.exp(-self.physics_dt / self.param["tau"]))
        # Play operator: reversal must take up gear clearance before the target changes.
        delta = self.filtered - self.backlash_target
        b = self.param["backlash"]
        self.backlash_target += torch.sign(delta) * (delta.abs() - b).clamp_min(0)
        q = self.robot.data.joint_pos[:, self.joint_ids]
        dq = self.robot.data.joint_vel[:, self.joint_ids]
        raw = self.param["kp"] * (self.backlash_target - q) - self.param["kd"] * dq
        # Conservative symmetric speed envelope; actual motor braking must be identified experimentally.
        envelope = self.param["torque"] * (1 - dq.abs() / self.param["speed"]).clamp(0, 1)
        self.efforts = torch.maximum(torch.minimum(raw, envelope), -envelope)
        self.robot.set_joint_effort_target(self.efforts, joint_ids=self.joint_ids)

    def _get_observations(self):
        gyro = self.robot.data.root_ang_vel_b + self.gyro_bias + torch.randn_like(self.gyro_bias) * 0.015
        # Projected gravity approximates a body-mounted IMU attitude estimator, not perfect hardware truth.
        gravity = self.robot.data.projected_gravity_b + self.gravity_bias + torch.randn_like(self.gravity_bias) * 0.01
        gravity = gravity / gravity.norm(dim=-1, keepdim=True).clamp_min(1e-6)
        issued_normalized = (self.issued - self.center) / self.half
        frame = torch.cat((gyro * 0.25, gravity, self.commands, issued_normalized), dim=-1)
        self.history[:, :-1] = self.history[:, 1:].clone()
        self.history[:, -1] = frame
        return {"policy": self.history.reshape(self.num_envs, -1).clone()}

    def _get_rewards(self):
        # Privileged states are allowed for the reward, never sent to the deployed actor.
        data = self.robot.data
        upright = (-data.projected_gravity_b[:, 2]).clamp(0, 1)
        velocity = torch.exp(-((data.root_lin_vel_b[:, 0] - self.commands[:, 0]) / 0.045).square())
        yaw_rate = torch.exp(-((data.root_ang_vel_b[:, 2] - self.commands[:, 1]) / 0.5).square())
        q = data.joint_pos[:, self.joint_ids]
        face_error = (q[:, 2:] - self.commands[:, 2:]).square().sum(-1)
        drift = data.root_lin_vel_b[:, 1].square()
        effort = (self.efforts / 0.11).square().mean(-1)
        changes = (self.actions - self.last_actions).square().mean(-1)
        reward = upright * (1.0 + velocity + 0.25 * yaw_rate) - 0.2 * face_error - 4.0 * drift - 0.04 * effort - 0.03 * changes
        return (reward - 3.0 * self.reset_terminated.float()) * self.step_dt

    def _get_dones(self):
        z = self.robot.data.root_pos_w[:, 2] - self.scene.env_origins[:, 2]
        fallen = (self.robot.data.projected_gravity_b[:, 2] > -0.55) | (z < INFO["root_height_m"] * 0.45)
        q = self.robot.data.joint_pos[:, self.joint_ids]
        dq = self.robot.data.joint_vel[:, self.joint_ids]
        finite = (torch.isfinite(self.robot.data.root_state_w).all(dim=-1)
                  & torch.isfinite(q).all(dim=-1) & torch.isfinite(dq).all(dim=-1))
        nonfinite = ~finite
        # DirectRLEnv resets terminated environments inside step(). Capture the
        # state before that reset so smoke diagnostics cannot hide a fall/NaN.
        self.last_pre_reset = {"root_z": z.clone(), "joint_pos": q.clone(),
                               "finite": finite.clone(), "fallen": fallen.clone(),
                               "efforts": self.efforts.clone()}
        return fallen | nonfinite, self.episode_length_buf >= self.max_episode_length - 1

    def _reset_idx(self, env_ids):
        if env_ids is None:
            env_ids = torch.arange(self.num_envs, device=self.device)
        super()._reset_idx(env_ids)
        q = self.robot.data.default_joint_pos[env_ids].clone()
        dq = self.robot.data.default_joint_vel[env_ids].clone()
        root = self.robot.data.default_root_state[env_ids].clone()
        root[:, :3] += self.scene.env_origins[env_ids]
        self.robot.write_root_pose_to_sim(root[:, :7], env_ids)
        self.robot.write_root_velocity_to_sim(root[:, 7:], env_ids)
        self.robot.write_joint_state_to_sim(q, dq, env_ids=env_ids)
        count = len(env_ids)
        ranges = {"tau": (.02, .08), "backlash": (.008, .035), "kp": (.4, 1.0),
                  "kd": (.002, .006), "torque": (.06, .11), "speed": (8.0, 10.472)}
        for name, (low, high) in ranges.items():
            sample = torch.rand((count, 4), device=self.device) if self.cfg.randomize_servos else .5
            self.param[name][env_ids] = low + (high-low) * sample
        self.command_delay[env_ids] = (torch.randint(0, 3, (count, 4), device=self.device)
                                      if self.cfg.randomize_servos else 0)
        self.gyro_bias[env_ids] = ((torch.rand((count, 3), device=self.device) - .5) * .04
                                  if self.cfg.randomize_servos else 0)
        self.gravity_bias[env_ids] = ((torch.rand((count, 3), device=self.device) - .5) * .04
                                     if self.cfg.randomize_servos else 0)
        self.commands[env_ids, 0] = torch.rand(count, device=self.device) * .06
        self.commands[env_ids, 1] = (torch.rand(count, device=self.device) - .5) * .5
        self.commands[env_ids, 2] = (torch.rand(count, device=self.device) - .5) * .5
        self.commands[env_ids, 3] = torch.rand(count, device=self.device) * self.upper[3]
        for target in (self.issued, self.filtered, self.backlash_target):
            target[env_ids] = q[:, self.joint_ids]
        self.command_queue[env_ids] = q[:, None, self.joint_ids]
        self.actions[env_ids] = (q[:, self.joint_ids] - self.center) / self.half
        self.last_actions[env_ids] = self.actions[env_ids]
        self.efforts[env_ids] = 0
        self.history[env_ids] = 0

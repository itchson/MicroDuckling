"""Small PPO policy configuration, targeting Isaac Lab 2.3.2's bundled RSL-RL."""
from isaaclab.utils import configclass
from isaaclab_rl.rsl_rl import RslRlOnPolicyRunnerCfg, RslRlPpoActorCriticCfg, RslRlPpoAlgorithmCfg


@configclass
class MicroDucklingPPOCfg(RslRlOnPolicyRunnerCfg):
    seed = 42
    num_steps_per_env = 32
    max_iterations = 1500
    save_interval = 100
    experiment_name = "microduckling_prototype"
    obs_groups = {"policy": ["policy"], "critic": ["policy"]}
    clip_actions = 1.0
    policy = RslRlPpoActorCriticCfg(
        init_noise_std=0.25, actor_obs_normalization=True, critic_obs_normalization=True,
        actor_hidden_dims=[64, 32], critic_hidden_dims=[64, 32], activation="tanh",
    )
    algorithm = RslRlPpoAlgorithmCfg(
        value_loss_coef=1.0, use_clipped_value_loss=True, clip_param=0.2,
        entropy_coef=0.005, num_learning_epochs=5, num_mini_batches=4,
        learning_rate=3e-4, schedule="adaptive", gamma=0.99, lam=0.95,
        desired_kl=0.01, max_grad_norm=1.0,
    )

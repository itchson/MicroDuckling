"""Task registration only; simulator imports happen after AppLauncher starts."""
import gymnasium as gym

gym.register(
    id="MicroDuckling-Flat-v0",
    entry_point="microduckling_lab.environment:MicroDucklingEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "microduckling_lab.environment:MicroDucklingEnvCfg",
        "rsl_rl_cfg_entry_point": "microduckling_lab.ppo:MicroDucklingPPOCfg",
    },
)

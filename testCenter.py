from argparse import ArgumentParser

import cv2
import gymnasium
import gymnasium.wrappers.human_rendering
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common import evaluation, policies
import os
import wandb
from wandb.integration.sb3 import WandbCallback


import vizdoom.gymnasium_wrapper  # noqa


DEFAULT_ENV = "VizdoomDefendCenter-v0"
AVAILABLE_ENVS = [env for env in gymnasium.envs.registry.keys() if "Vizdoom" in env]
# Height and width of the resized image
IMAGE_SHAPE = (60, 80)
EVAL_FREQ = 50000

# Training parameters
TRAINING_TIMESTEPS = 1000000
N_STEPS = 1024
N_ENVS = 2
FRAME_SKIP = 4

CHECKPOINT_DIR = "./checkpoints/train/center"
LOG_DIR = "./logs/center"
MODEL_SAVE_DIR = "./final_models/center"

config = {
    "env": DEFAULT_ENV,
    "image_shape": IMAGE_SHAPE,
    "training_timesteps": TRAINING_TIMESTEPS,
    "n_steps": N_STEPS,
    "n_envs": N_ENVS,
    "frame_skip": FRAME_SKIP,
}


def main(args):
    # Create multiple environments: this speeds up training with PPO
    # We apply two wrappers on the environment:
    #  1) The above wrapper that modifies the observations (takes only the image and resizes it)
    #  2) A reward scaling wrapper. Normally the scenarios use large magnitudes for rewards (e.g., 100, -100).
    #     This may lead to unstable learning, and we scale the rewards by 1/100
    def wrap_env(env):
        # env = gymnasium.make("VizdoomBasic-v0", render_mode="human", frame_skip=4)
        # env = ObservationWrapper(env)
        env = gymnasium.wrappers.TransformReward(env, lambda r: r * 0.01)
        env = gymnasium.wrappers.HumanRendering(env)
        return env

    models = os.listdir(MODEL_SAVE_DIR)

    if models == []:
        nrModel = 0
    else:
        nrModel = len(models) + 1

    envs = make_vec_env(args.env, n_envs=N_ENVS, wrapper_class=wrap_env, env_kwargs={"frame_skip": FRAME_SKIP})

    # Initialize wandb
    run = wandb.init(
        project="vizdoom",
        name="vizdoom-Center" + str(nrModel + 1),
        group="center",
        tags=["ppo", "vizdoom", "DefendCenter"],
        config=config,
        sync_tensorboard=True,
        save_code=True,
        monitor_gym=True,
    )

    # agent = PPO(
    #     "MultiInputPolicy", envs, n_steps=N_STEPS, verbose=2, tensorboard_log=LOG_DIR
    # )
    agent = PPO(
        policies.MultiInputActorCriticPolicy, envs, n_steps=N_STEPS, verbose=1, tensorboard_log=LOG_DIR + "/" + run.id,
        learning_rate=1e-5, 
        n_epochs=10,
        batch_size=64,
    )


    # Do the actual learning
    # This will print out the results in the console.
    # If agent gets better, "ep_rew_mean" should increase steadily
    # agent.learn(total_timesteps=TRAINING_TIMESTEPS, callback=callback)
    agent.learn(
        total_timesteps=TRAINING_TIMESTEPS,
        callback=WandbCallback(
            model_save_path=f"{MODEL_SAVE_DIR}/model_{nrModel}",
            verbose=2,
        ),
    )
    
    run.finish()
    
    # agent.save(f"{MODEL_SAVE_DIR}/model_{nrModel}")


if __name__ == "__main__":
    parser = ArgumentParser("Train stable-baselines3 PPO agents on ViZDoom.")
    parser.add_argument(
        "--env",
        default=DEFAULT_ENV,
        choices=AVAILABLE_ENVS,
        help="Name of the environment to play",
    )
    args = parser.parse_args()
    main(args)

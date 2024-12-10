import random
from collections import deque
from os import path

import altair as alt
import gymnasium as gym
import numpy as np
import polars as pl
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from gymnasium.envs.registration import register
from gymnasium.wrappers import RecordVideo
from stable_baselines3 import DQN, PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import VecEnv

from simulation.envs.wrappers.display_info import DisplayInfo

alt.renderers.enable("browser")


register(
    id="CartPole-v99",
    entry_point="simulation.envs.cartpole:CartPoleEnv",
    max_episode_steps=200,
)


class ReplayBuffer:
    def __init__(self, buffer_size, batch_size):
        self.buffer = deque(maxlen=buffer_size)
        self.batch_size = batch_size

    def add(self, state, action, reward, next_state, done):
        data = (state, action, reward, next_state, done)
        self.buffer.append(data)

    def __len__(self):
        return len(self.buffer)

    def get_batch(self):
        data = random.sample(self.buffer, self.batch_size)

        state = torch.tensor(np.stack([x[0] for x in data]))
        action = torch.tensor(np.array([x[1] for x in data]).astype(np.int64))
        reward = torch.tensor(np.array([x[2] for x in data]).astype(np.float32))
        next_state = torch.tensor(np.stack([x[3] for x in data]))
        done = torch.tensor(np.array([x[4] for x in data]).astype(np.int32))
        return state, action, reward, next_state, done


class QNet(nn.Module):
    def __init__(self, action_size):
        super().__init__()
        self.l1 = nn.Linear(4, 128)
        self.l2 = nn.Linear(128, 128)
        self.l3 = nn.Linear(128, action_size)

    def forward(self, x):
        x = F.relu(self.l1(x))
        x = F.relu(self.l2(x))
        x = self.l3(x)
        return x


class DQNAgent:
    def __init__(self):
        self.gamma = 0.98
        self.lr = 0.0005
        self.epsilon = 0.1
        self.buffer_size = 10000
        self.batch_size = 32
        self.action_size = 2

        self.replay_buffer = ReplayBuffer(self.buffer_size, self.batch_size)
        self.qnet = QNet(self.action_size)
        self.qnet_target = QNet(self.action_size)
        self.optimizer = optim.Adam(self.qnet.parameters(), lr=self.lr)

    def get_action(self, state):
        if np.random.rand() < self.epsilon:
            return np.random.choice(self.action_size)
        else:
            state = torch.tensor(state[np.newaxis, :])
            qs = self.qnet(state)
            return qs.argmax().item()

    def update(self, state, action, reward, next_state, done):
        self.replay_buffer.add(state, action, reward, next_state, done)
        if len(self.replay_buffer) < self.batch_size:
            return

        state, action, reward, next_state, done = self.replay_buffer.get_batch()
        qs = self.qnet(state)
        q = qs[np.arange(self.batch_size), action]

        next_qs = self.qnet_target(next_state)
        next_q = next_qs.max(1)[0]

        next_q.detach()
        target = reward + (1 - done) * self.gamma * next_q

        loss_fn = nn.MSELoss()
        loss = loss_fn(q, target)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

    def sync_qnet(self):
        self.qnet_target.load_state_dict(self.qnet.state_dict())


def naive(env):
    episodes = 100_000
    sync_interval = 20

    agent = DQNAgent()
    reward_history = []

    for episode in range(episodes):
        obs, _ = env.reset()
        done = False
        total_reward = 0

        while not done:
            action = agent.get_action(obs)
            next_obs, reward, terminated, truncated, info = env.step(action)

            agent.update(obs, action, reward, next_obs, done)
            obs = next_obs
            total_reward += reward

            # End the episode when either truncated or terminated is true
            #  - truncated: The episode duration reaches max number of timesteps
            #  - terminated: Any of the state space values is no longer finite.
            done = terminated or truncated

        if episode % sync_interval == 0:
            agent.sync_qnet()

        reward_history.append(total_reward)
        if episode % 10 == 0:
            print("episode :{}, total reward : {}".format(episode, total_reward))

    df = pl.DataFrame(
        {
            "episode": list(range(episodes)),
            "reward": reward_history,
        }
    )
    df.plot.line(x="episode", y="reward").show()


def sb3_dqn(env):
    model = DQN("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=100_000)
    model.save("dqn_cartpole")

    del model  # remove to demonstrate saving and loading

    model = DQN.load("dqn_cartpole")

    obs, _ = env.reset()
    done = False
    total_reward = 0

    while not done:
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward

        done = terminated or truncated


def sb3_ppo(vec_env: VecEnv):
    model = PPO("MlpPolicy", vec_env, verbose=1)
    model.learn(total_timesteps=50_000)
    model.save("ppo_cartpole")

    del model  # remove to demonstrate saving and loading

    model = PPO.load("ppo_cartpole")

    obs = vec_env.reset()
    while True:
        action, _states = model.predict(obs)
        obs, rewards, dones, infos = vec_env.step(action)
        vec_env.render("human")


def _episode_trigger(episode_id: int) -> bool:
    """The default episode trigger.

    This function will trigger recordings at the episode indices 0, 1, 8, 27, ..., :math:`k^3`, ..., 729, 1000, 2000, 3000, ..., 10000, 200000, ...

    Args:
        episode_id: The episode number

    Returns:
        If to apply a video schedule number
    """
    if episode_id < 1000:
        return int(round(episode_id ** (1.0 / 3))) ** 3 == episode_id
    else:
        return episode_id % (10 ** (len(str(episode_id)) - 1)) == 0


if __name__ == "__main__":
    # env = gym.make("CartPole-v99", render_mode="human")
    # env = gym.make("CartPole-v0")
    env = RecordVideo(
        gym.make("CartPole-v0", render_mode="rgb_array"),
        video_folder=f"{path.dirname(__file__)}/../videos",
        episode_trigger=_episode_trigger,
    )
    # vec_env = gym.vector.make(
    #     "CartPole-v0",
    #     render_mode="rgb_array",
    #     num_envs=4,
    #     wrappers=lambda env: RecordVideo(
    #         env, video_folder=f"{path.dirname(__file__)}/../videos"
    #     ),
    # )
    vec_env = make_vec_env(
        "CartPole-v0",
        n_envs=4,
        env_kwargs={"render_mode": "rgb_array"},
        wrapper_class=lambda env: RecordVideo(
            env=DisplayInfo(env=env),
            video_folder=f"{path.dirname(__file__)}/../videos",
            episode_trigger=_episode_trigger,
        ),
    )

    # sb3_dqn(env)
    sb3_ppo(vec_env)

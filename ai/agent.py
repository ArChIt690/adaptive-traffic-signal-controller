"""Q-learning agent that picks the green time for each road, per traffic situation.

State  s = (dNS, dEW): traffic level 0-3 on each road -> 16 states (= the 16 ROM addresses).
Action a = (gNS, gEW): green seconds for each road, from G_CHOICES -> 49 actions.
Reward r = -(average seconds a car waits) over one simulated episode.

Each episode is a single decision (the traffic level stays fixed during it), so this is
the one-step (gamma = 0) form of Q-learning, also called a contextual bandit:
    Q[s, a] <- Q[s, a] + alpha * (r - Q[s, a])
Actions are chosen epsilon-greedily, with epsilon decaying from eps_start to eps_end.
The learned policy is argmax_a Q[s, a] for each state; it is written into the ROM.
"""
from dataclasses import dataclass

import numpy as np

from ai.traffic import SimResult, simulate
from hw.rom import LEVELS, Policy

G_CHOICES = (3, 5, 7, 9, 11, 13, 15)
ACTIONS: list[tuple[int, int]] = [(g_ns, g_ew) for g_ns in G_CHOICES for g_ew in G_CHOICES]
FIXED_GREEN = (9, 9)
CURVE_WINDOW = 500
STATES = [(d_ns, d_ew) for d_ns in LEVELS for d_ew in LEVELS]  # index = (dNS << 2) | dEW


@dataclass
class TrainResult:
    policy: Policy
    q: np.ndarray          # shape (16, 49)
    visits: np.ndarray     # shape (16, 49)
    curve: list[float]     # mean reward per CURVE_WINDOW episodes


def train(episodes: int = 20000, episode_seconds: int = 900, alpha: float = 0.1,
          eps_start: float = 1.0, eps_end: float = 0.05, seed: int = 0) -> TrainResult:
    rng = np.random.default_rng(seed)
    q = np.zeros((len(STATES), len(ACTIONS)))
    visits = np.zeros_like(q, dtype=int)
    rewards = []
    for ep in range(episodes):
        eps = eps_start + (eps_end - eps_start) * ep / max(episodes - 1, 1)
        s = int(rng.integers(len(STATES)))
        if rng.random() < eps:
            a = int(rng.integers(len(ACTIONS)))
        else:
            a = int(np.argmax(q[s]))  # untried actions keep Q = 0, which is optimistic
        d_ns, d_ew = STATES[s]
        g_ns, g_ew = ACTIONS[a]
        r = -simulate(g_ns, g_ew, d_ns, d_ew, episode_seconds, seed=int(rng.integers(2**31))).avg_wait
        visits[s, a] += 1
        # the first sample replaces the optimistic 0 outright, after that a constant step size
        step = max(alpha, 1.0 / visits[s, a])
        q[s, a] += step * (r - q[s, a])
        rewards.append(r)

    policy = {}
    for s, state in enumerate(STATES):
        tried = np.where(visits[s] > 0, q[s], -np.inf)  # never pick an action it never tried
        policy[state] = ACTIONS[int(np.argmax(tried))]
    curve = [float(np.mean(rewards[i:i + CURVE_WINDOW])) for i in range(0, len(rewards), CURVE_WINDOW)]
    return TrainResult(policy, q, visits, curve)


def fixed_policy() -> Policy:
    return {state: FIXED_GREEN for state in STATES}


def best_fixed_policy(seconds: int = 1800, seed: int = 123) -> Policy:
    """The strongest fair baseline: the equal-green fixed timer (same g on both roads, for
    every traffic level) that gives the lowest mean wait on the evaluation traffic."""
    def mean_wait(g):
        return sum(r.avg_wait for r in evaluate({s: (g, g) for s in STATES}, seconds, seed).values())
    g = min(G_CHOICES, key=mean_wait)
    return {state: (g, g) for state in STATES}


def evaluate(policy: Policy, seconds: int = 1800, seed: int = 123) -> dict[tuple[int, int], SimResult]:
    """Same random traffic (seed per state) for every policy, so comparisons are fair."""
    return {state: simulate(*policy[state], *state, seconds=seconds, seed=seed + i)
            for i, state in enumerate(STATES)}

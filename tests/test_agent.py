import pytest

from ai.agent import ACTIONS, G_CHOICES, evaluate, fixed_policy, train

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def trained():
    return train(episodes=8000, episode_seconds=600, seed=0)


def test_action_space():
    assert len(ACTIONS) == 49 and (3, 15) in ACTIONS and G_CHOICES == (3, 5, 7, 9, 11, 13, 15)


def test_policy_complete_and_valid(trained):
    assert set(trained.policy) == {(a, b) for a in range(4) for b in range(4)}
    assert all(g in G_CHOICES for pair in trained.policy.values() for g in pair)
    assert trained.q.shape == (16, 49)


def test_favours_busy_road(trained):
    ns, ew = trained.policy[(3, 0)]
    assert ns > ew
    ns, ew = trained.policy[(0, 3)]
    assert ew > ns


def test_more_green_when_saturated(trained):
    assert sum(trained.policy[(3, 3)]) > sum(trained.policy[(0, 0)])


def test_beats_fixed_timer(trained):
    ai, fx = evaluate(trained.policy), evaluate(fixed_policy())
    mean = lambda d: sum(r.avg_wait for r in d.values()) / len(d)
    assert mean(ai) < 0.9 * mean(fx)


def test_learning_curve_improves(trained):
    assert len(trained.curve) == 8000 // 500
    assert trained.curve[-1] > trained.curve[0]   # rewards are -wait, so higher is better


def test_deterministic():
    a = train(episodes=300, episode_seconds=120, seed=5)
    b = train(episodes=300, episode_seconds=120, seed=5)
    assert a.policy == b.policy


def test_best_fixed_policy_is_best_equal_split():
    from ai.agent import best_fixed_policy
    best = best_fixed_policy()
    g = set(best.values())
    assert len(g) == 1 and (gg := g.pop())[0] == gg[1]          # one equal split everywhere
    mean = lambda p: sum(r.avg_wait for r in evaluate(p).values()) / 16
    others = [{s: (x, x) for s in best} for x in G_CHOICES]
    assert all(mean(best) <= mean(o) for o in others)


def test_beats_best_fixed_timer(trained):
    from ai.agent import best_fixed_policy
    ai, fx = evaluate(trained.policy), evaluate(best_fixed_policy())
    mean = lambda d: sum(r.avg_wait for r in d.values()) / len(d)
    assert mean(ai) < 0.9 * mean(fx)

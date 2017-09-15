import numpy as np

from utils import hash_key


def beta_posterior_lower_bounds(n, s, alpha=1, beta=1):
    """
    A lower bound approximation of the posterior distribution, such
    that for our result x and unknown true parameter theta we have
    P(theta < x) = 0.05, i.e. it's 95% probable that the true theta
    is above our estimate.

    Assuming a Beta(alpha, beta) prior and a Binomial likelihood, we have
    a Beta(alpha + s, beta + n - s) posterior distribution. Rather
    than sampling or inverting the Beta CDF (hard) to find the lower bound
    we use a normal approximation taking
    mu = alpha / (alpha + beta)
    and
    sigma^2 = alpha*beta / (alpha + beta)^2*(alpha + beta + 1),
    we solve 0.05 = \Phi((x-mu) / sigma) for x
    """
    a = alpha + s
    b = beta + n - s
    z = -1.65 # normal z-score lookup given p = 0.05
    return (a / (a + b)) + z * np.sqrt((a*b) / ((a+b)**2 * (a + b + 1)))

async def posterior_estimates(redis, experiment_id, choices):
    p = np.zeros(len(choices))
    for i, choice in enumerate(choices):
        n_samples = await redis.scard('samples:%s:%s' % (experiment_id, i)) or 1
        n_successes = await redis.scard('successes:%s:%s' % (experiment_id, i)) or 0
        print('--', i, choice, n_successes, n_samples)
        p[i] = beta_posterior_lower_bounds(
            n_samples,
            n_successes
        )
    return p

async def epsilon_greedy(experiment_id, experiment, redis):
    """
    At each sample this algorithm considers whether or not to exploit vs. explore the environment. It chooses explore a random arm with probability $\epsilon$ or exploit the best performming arm with probability $1 - \epsilon$.
    """
    epsilon = experiment['parameters']['epsilon']
    choices = experiment['choices']
    p = await posterior_estimates(redis, experiment_id, choices)

    if np.random.uniform(0,1) < epsilon:
        return np.random.choice(p) # explore
    else:
        return np.argmax(p) # exploit

async def epsilon_first(experiment_id, experiment, redis):
    if samples < n:
        return np.random.choice(p) # explore
    else:
        return np.argmax(p) # exploit

async def epsilon_decreasing(experiment_id, experiment, redis):
    # TODO epsilon greedy, but updates eps over time
    pass

async def vdbe(experiment_id, experiment, redis):
    # TODO
    pass

async def contextual_epsilon_greedy(experiment_id, experiment, redis):
    # TODO
    pass

async def thompson_sampling(experiment_id, experiment, redis):
    """
    Continuously chooses based on observed successes, e.g. Polya's urn.
    """
    choices = experiment['choices']
    p = np.zeros(len(choices))
    for choice in choices:
        p[choice] = await redis.scard(
            # FIXME
            hash_key('successes', experiment_id) + ':' + choice
        )
    p /= p.sum()
    return np.random.choice(len(p), p=p)

async def pricing(experiment_id, experiment, redis):
    # TODO
    pass

async def expected_successes_lost(experiment_id, experiment, redis):
    # TODO
    pass

POLICIES = {
    'epsilon_greedy': epsilon_greedy,
    'epsilon_first': epsilon_first,
    'epsilon_decreasing': epsilon_decreasing,
    'adaptive_epsilon': vdbe,
    'contextual_epsilon': contextual_epsilon_greedy,
    'probability_matching': thompson_sampling,
    'pricing': pricing,
    'ethical': expected_successes_lost,
}

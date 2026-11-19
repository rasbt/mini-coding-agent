def choose_action(q_values, state, epsilon, rng):
    """Epsilon-greedy: random action with probability epsilon, else the best one (ties broken randomly)."""
    if state not in q_values or rng.random() < epsilon:
        # Explore: pick random action from ACTIONS
        return rng.choice(ACTIONS)
    else:
        # Exploit: find best Q-value(s)
        best_q = max(q_values[state].values())
        best_actions = [a for a, q in q_values[state].items() if q == best_q]
        return rng.choice(best_actions)


def outcome_of(reward, done):
    """Label how an episode ended, using only the observed reward."""
    if done:
        return "goal" if reward > 0 else "trap"
    return "timeout"


def q_learning(env, episodes, max_steps, alpha=ALPHA, gamma=GAMMA,
               epsilon=EPSILON, seed=0):
    """Learn action values from environment interactions. Returns (q_values, results)."""
    random.seed(seed)
    rng = random.Random(seed)
    q_values = {}
    results = []
    robot = Agent(lambda percept: None)

    for episode in range(1, episodes + 1):
        state = env.reset(robot)
        if state not in q_values:
            q_values[state] = {a: 0.0 for a in ACTIONS}
        
        total_reward = 0
        steps = 0
        done = False
        
        while not done and steps < max_steps:
            action = choose_action(q_values, state, epsilon, rng)
            next_state, reward, done = env.execute_action(robot, action)
            
            if state not in q_values:
                q_values[state] = {a: 0.0 for a in ACTIONS}
            
            old_score = q_values[state][action]
            
            if done:
                target = reward
            else:
                if next_state not in q_values:
                    q_values[next_state] = {a: 0.0 for a in ACTIONS}
                target = reward + gamma * max(q_values[next_state].values())
            
            q_values[state][action] = old_score + alpha * (target - old_score)
            
            total_reward += reward
            state = next_state
            steps += 1
        
        results.append({
            "episode": episode,
            "steps": steps,
            "reward": total_reward,
            "outcome": outcome_of(reward, done)
        })
    
    return (q_values, results)


def derive_policy(q_values):
    """Best action for each position the robot visited."""
    policy = {}
    for state, actions in q_values.items():
        best_action = max(actions, key=actions.get)
        policy[state] = best_action
    return policy


def evaluate_agent(env, q_values, episodes, max_steps, seed=1, show_paths=3):
    """Evaluate the learned policy without changing Q-values (epsilon = EVALUATION_EPSILON)."""
    random.seed(seed)
    rng = random.Random(seed)
    robot = Agent(lambda percept: None)
    
    total_reward = 0
    total_steps = 0
    goal_count = 0
    trap_count = 0
    timeout_count = 0
    
    for episode in range(episodes):
        state = env.reset(robot)
        done = False
        last_reward = 0
        steps = 0
        path = []
        
        while not done and steps < max_steps:
            action = choose_action(q_values, state, EVALUATION_EPSILON, rng)
            next_state, reward, done = env.execute_action(robot, action)
            
            if episode < show_paths:
                path.append(f"{action} -> {next_state}")
            
            total_reward += reward
            last_reward = reward
            state = next_state
            steps += 1
        
        outcome = outcome_of(last_reward, done)
        if outcome == "goal":
            goal_count += 1
        elif outcome == "trap":
            trap_count += 1
        else:
            timeout_count += 1
        
        total_steps += steps
        
        if episode < show_paths:
            print(" | ".join(path))
    
    average_reward = total_reward / episodes
    average_steps = total_steps / episodes
    success_rate = goal_count / episodes
    
    return {
        "episodes": episodes,
        "goal": goal_count,
        "trap": trap_count,
        "timeout": timeout_count,
        "average_reward": average_reward,
        "average_steps": average_steps,
        "success_rate": success_rate
    }

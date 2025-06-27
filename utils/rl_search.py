import numpy as np
from typing import List, Dict, Any, Callable, Optional

class RLSearchAlgorithm:
    """Reinforcement Learning search algorithm for content retrieval."""
    
    def __init__(self, 
                exploration_rate: float = 0.1, 
                learning_rate: float = 0.1, 
                discount_factor: float = 0.9):
        """
        Initialize the RL search algorithm.
        
        Args:
            exploration_rate: Epsilon value for exploration
            learning_rate: Alpha value for learning rate
            discount_factor: Gamma value for discounting future rewards
        """
        self.exploration_rate = exploration_rate
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.q_values = {}  # State-action value function
    
    def _get_state_key(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a state key from the query and context."""
        if context is None:
            return query
        
        # Use relevant parts of context to define state
        state_parts = [query]
        for key in sorted(context.keys()):
            if key in ['chapter_id', 'version_type']:
                state_parts.append(f"{key}={context[key]}")
        
        return "|".join(state_parts)
    
    def _get_q_value(self, state_key: str, action: str) -> float:
        """Get Q-value for a state-action pair."""
        if state_key not in self.q_values:
            self.q_values[state_key] = {}
        
        if action not in self.q_values[state_key]:
            self.q_values[state_key][action] = 0.0
        
        return self.q_values[state_key][action]
    
    def _update_q_value(self, state_key: str, action: str, reward: float, next_state_key: Optional[str] = None):
        """Update Q-value for a state-action pair."""
        if state_key not in self.q_values:
            self.q_values[state_key] = {}
        
        if action not in self.q_values[state_key]:
            self.q_values[state_key][action] = 0.0
        
        # Calculate updated Q-value using Q-learning update rule
        if next_state_key is not None and self.q_values.get(next_state_key):
            max_next_q = max(self.q_values[next_state_key].values()) if self.q_values[next_state_key] else 0
            new_q = self.q_values[state_key][action] + self.learning_rate * (
                reward + self.discount_factor * max_next_q - self.q_values[state_key][action]
            )
        else:
            new_q = self.q_values[state_key][action] + self.learning_rate * (
                reward - self.q_values[state_key][action]
            )
        
        self.q_values[state_key][action] = new_q
    
    def select_action(self, 
                    state_key: str, 
                    available_actions: List[str]) -> str:
        """
        Select an action using epsilon-greedy policy.
        
        Args:
            state_key: Key representing the current state
            available_actions: List of available actions
            
        Returns:
            Selected action
        """
        if not available_actions:
            return None
        
        # Exploration: with probability epsilon, select a random action
        if np.random.random() < self.exploration_rate:
            return np.random.choice(available_actions)
        
        # Exploitation: select the action with the highest Q-value
        state_q_values = {action: self._get_q_value(state_key, action) for action in available_actions}
        
        # If all Q-values are the same, choose randomly
        if len(set(state_q_values.values())) == 1:
            return np.random.choice(available_actions)
        
        return max(state_q_values, key=state_q_values.get)
    
    def search(self, 
              query: str, 
              items: List[Dict[str, Any]], 
              context: Optional[Dict[str, Any]] = None,
              reward_function: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        Perform RL-based search on a collection of items.
        
        Args:
            query: Search query
            items: Collection of items to search
            context: Additional search context
            reward_function: Custom function for calculating rewards
            
        Returns:
            Sorted search results
        """
        if not items:
            return []
        
        state_key = self._get_state_key(query, context)
        item_ids = [item["id"] for item in items]
        
        # Select action (item) using RL policy
        selected_id = self.select_action(state_key, item_ids)
        
        # Default reward function uses string similarity to query
        if reward_function is None:
            def reward_function(item, query):
                # Simple string matching reward
                content = item.get("content", "")
                query_terms = query.lower().split()
                matches = sum(1 for term in query_terms if term.lower() in content.lower())
                return matches / max(len(query_terms), 1)
        
        # Calculate rewards for all items and update Q-values
        results = []
        for item in items:
            reward = reward_function(item, query)
            self._update_q_value(state_key, item["id"], reward)
            
            # Add reward score to result
            results.append({
                **item,
                "rl_score": reward,
                "q_value": self._get_q_value(state_key, item["id"])
            })
        
        # Sort results by their Q-values
        sorted_results = sorted(results, key=lambda x: x.get("q_value", 0), reverse=True)
        
        return sorted_results

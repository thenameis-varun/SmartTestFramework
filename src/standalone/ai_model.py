# Copyright (c) 2025 Varun Kumar BS.
# This file contains proprietary code and/or utilities for development purposes.

import sqlite3
import json
import numpy as np

class QLearningAgent:
    def __init__(self, iterations_options=[5, 8, 10, 15], delay_options=[3, 4, 5, 6],
                alpha=0.1, gamma=0.9, epsilon=0.1):
        self.iterations_options = iterations_options
        self.delay_options = delay_options
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.q_table = {}
        self.conn = sqlite3.connect("framework.db")
        self.load_logs()

    def get_state(self, hardware_type, test_name, username=None):
        """Return state string based on hardware_type and test_name.
        For auto-detected devices, prefer username-specific state if available."""
        if hardware_type == "auto-detected" and username:
            return f"{hardware_type}_{username}_{test_name}"
        return f"{hardware_type}_{test_name}"

    def get_action(self, iterations, delay):
        return (iterations, delay)

    def load_logs(self):
        try:
            cursor = self.conn.execute("SELECT hardware_type, test_name, parameters, outcome, username FROM Logs")
            for row in cursor:
                hardware_type, test_name, params, outcome, username = row
                params = json.loads(params)
                iterations = params.get("iterations", 10)
                delay = params.get("delay", 5)

                # Prefer username-specific state for auto-detected
                state = self.get_state(hardware_type, test_name, username)
                action = self.get_action(iterations, delay)

                if state not in self.q_table:
                    self.q_table[state] = {}
                if action not in self.q_table[state]:
                    self.q_table[state][action] = 0.0

                reward = 1.0 if outcome == "success" else -1.0
                self.q_table[state][action] += self.alpha * (reward - self.q_table[state][action])
        except sqlite3.OperationalError:
            pass

    def suggest_parameters(self, hardware_type, test_name, username=None):
        self.load_logs()  # refresh with latest

        # Username-specific state if auto-detected
        state = self.get_state(hardware_type, test_name, username)

        # If no user-specific data, fallback to generic auto-detected
        if state not in self.q_table and hardware_type == "auto-detected":
            state = self.get_state(hardware_type, test_name)

        if state not in self.q_table:
            # Initialize default Q-values
            self.q_table[state] = {(i, d): 0.0 for i in self.iterations_options for d in self.delay_options}

        # Epsilon-greedy
        if np.random.rand() < self.epsilon:
            action = (np.random.choice(self.iterations_options), np.random.choice(self.delay_options))
        else:
            action = max(self.q_table[state], key=self.q_table[state].get)

        return {
            "parameters": {"iterations": int(action[0]), "delay": int(action[1])},
            "confidence": 0.8 if max(self.q_table[state].values()) > 0 else 0.7
        }

def suggest_parameters(hardware_type, test_name):
    agent = QLearningAgent()  # Create agent only when needed
    return agent.suggest_parameters(hardware_type, test_name)
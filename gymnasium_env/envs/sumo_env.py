import gymnasium as gym
from gymnasium import spaces
import numpy as np
import os
import sys
from typing import List
from statistics import mean
from dotenv import load_dotenv
from src.simulation import Simulation

load_dotenv()
root_path = os.getenv("SUMO_PROJECT_PATH")
sys.path.append(root_path)

class DemoEnv(gym.Env):
    metadata = {"render.modes": ["console"]}
    # WARN: The environment creator metadata doesn't include `render_modes`, contains: ['render.modes']
    def __init__(self, num_vehicles, num_agents, route_id):
        super().__init__()
    
        self._num_vehicles = num_vehicles
        self._num_agents = num_agents
        self._route_id = route_id
        self._simulation = Simulation(num_vehicles, num_agents, route_id)
        self._simulation.setup_sumo()
        self._simulation.get_options()
        self._simulation.start_sumo()
        self._simulation.simulation_init()
        self._vehicle_ids, self._agent_ids = self._simulation.get_ids()
        
        self.observation_space = spaces.Dict({
            "agents": spaces.Dict({
                "agent_id": spaces.Tuple((
                    spaces.Box(low=0, high=100, shape=(2,), dtype=int), # posn
                    spaces.Discrete(200) # speed
                ))
            }),
            "vehicles": spaces.Dict({
                "vehicle_id": spaces.Tuple((
                    spaces.Box(low=0, high=100, shape=(2,), dtype=int), # posn
                    spaces.Discrete(200) # speed
                ))
            }),
        })
        # (x, y, speed) for each vehicle
        high = np.array([np.inf] * self._num_vehicles * 3) 
        
        self.observation_space = spaces.Box(
            low=-high, 
            high=high,
            dtype=np.float32
        )
        # acceleration (a), where -3 < a < 1 (ms^-2)
        self.action_space = spaces.Box(
            low=np.array([-3]), 
            high=np.array([1]), 
            dtype=np.float32
        )

    def get_info(self):
        ''' todo'''
        pass
    
    def reset(self, seed=None, options=None) -> tuple[List[float], dict]:
        super().reset(seed=seed)
        
        if not hasattr(self, "_simulation") or self._simulation is None:
            self._simulation = Simulation(self._num_vehicles, self._num_agents, self._route_id)
            self._simulation.setup_sumo()
            self._simulation.get_options()
            self._simulation.start_sumo()
            self._simulation.simulation_init()
            self._vehicle_ids, self._agent_ids = self._simulation.get_ids()
        else:
            # self._simulation.simulation_reset()
            pass
        
        obs = self._simulation.get_obs() 
        
        print("Observation:", obs)
        print("Expected shape:", self.observation_space.shape)
        print("Actual shape:", obs.shape)
        
        return obs, {}
        
    def step(self, action) -> tuple[object, float, bool, object]:
        self._simulation.simulation_step()
        self._simulation.set_acceleration(action)
        
        vehicle_info = [None] * len(self._vehicle_ids)
        posns, speeds = self._simulation.get_obs()

        for id in self._vehicle_ids:
            id_index = int(id)
            vehicle_info[id_index] = (
                posns[id_index][0], 
                posns[id_index][1], 
                speeds[id_index]
            )

        padded_obs = np.pad(vehicle_info, (0, len(self._vehicle_ids) * 3))
        observation = np.array(padded_obs)
        reward = self.calculate_reward()
        done = self._simulation.get_terminated()
        info = {}

        return observation, reward, done, info

    def render(self, mode="console") -> None:
        if mode == "console":
            print("environment state...")
    
    def close(self) -> None:
        self._simulation.end_simulation()

    def calculate_reward(self) -> float:
        speeds, _ = self._simulation.get_obs()
        filtered_speeds = [x for x in speeds if x]
        return mean(filtered_speeds)

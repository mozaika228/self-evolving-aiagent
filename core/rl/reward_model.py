from typing import Dict, Any


class RewardModel:
    def __init__(
        self,
        test_weight: float = 0.4,
        efficiency_weight: float = 0.2,
        quality_weight: float = 0.2,
        iterations_weight: float = 0.1,
        innovation_weight: float = 0.1,
    ):
        self.test_weight = test_weight
        self.efficiency_weight = efficiency_weight
        self.quality_weight = quality_weight
        self.iterations_weight = iterations_weight
        self.innovation_weight = innovation_weight

    def calculate(
        self,
        test_score: float,
        iterations: int,
        code_quality: float,
        efficiency: float = 1.0,
        innovation: float = 0.5,
    ) -> float:
        reward = (
            self.test_weight * test_score
            + self.quality_weight * code_quality
            + self.efficiency_weight * efficiency
            + self.iterations_weight * (1.0 - min(iterations / 5.0, 1.0))
            + self.innovation_weight * innovation
        )
        return max(0.0, min(1.0, reward))

    def calculate_penalty(self, iterations: int, max_iterations: int = 5) -> float:
        return 1.0 - (iterations / max_iterations) * 0.1

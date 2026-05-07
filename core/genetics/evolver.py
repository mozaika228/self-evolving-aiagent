import asyncio
import random
from typing import Dict, List, Tuple, Callable
from dataclasses import dataclass


@dataclass
class Individual:
    code: str
    fitness: float
    mutations_count: int


class GeneticEvolver:
    def __init__(
        self,
        population_size: int = 10,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
    ):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.population: List[Individual] = []
        self.generation = 0

    async def initialize(
        self,
        initial_code: str,
    ) -> None:
        self.population = [
            Individual(
                code=self._mutate_code(initial_code),
                fitness=0.0,
                mutations_count=1,
            )
            for _ in range(self.population_size)
        ]

    async def evaluate(
        self,
        fitness_fn: Callable,
    ) -> None:
        for individual in self.population:
            individual.fitness = await fitness_fn(individual.code)

    async def evolve(self) -> Individual:
        self.generation += 1
        
        await self._select_and_reproduce()
        await self._mutate_population()
        
        best = max(self.population, key=lambda x: x.fitness)
        return best

    async def _select_and_reproduce(self) -> None:
        sorted_pop = sorted(self.population, key=lambda x: x.fitness, reverse=True)
        elite_size = self.population_size // 4
        elite = sorted_pop[:elite_size]
        
        new_population = elite.copy()
        
        while len(new_population) < self.population_size:
            parent1 = random.choice(elite)
            parent2 = random.choice(elite)
            
            if random.random() < self.crossover_rate:
                child_code = self._crossover(parent1.code, parent2.code)
            else:
                child_code = parent1.code
            
            new_population.append(
                Individual(
                    code=child_code,
                    fitness=0.0,
                    mutations_count=0,
                )
            )
        
        self.population = new_population[:self.population_size]

    async def _mutate_population(self) -> None:
        for individual in self.population:
            if random.random() < self.mutation_rate:
                individual.code = self._mutate_code(individual.code)
                individual.mutations_count += 1

    def _mutate_code(self, code: str) -> str:
        lines = code.split("\n")
        mutations = [
            self._swap_lines,
            self._add_comments,
            self._rename_variables,
        ]
        
        mutation_fn = random.choice(mutations)
        mutated = mutation_fn(lines)
        
        return "\n".join(mutated)

    def _crossover(self, code1: str, code2: str) -> str:
        lines1 = code1.split("\n")
        lines2 = code2.split("\n")
        
        split_point1 = random.randint(0, len(lines1))
        split_point2 = random.randint(0, len(lines2))
        
        offspring = lines1[:split_point1] + lines2[split_point2:]
        return "\n".join(offspring)

    def _swap_lines(self, lines: List[str]) -> List[str]:
        if len(lines) < 2:
            return lines
        
        idx1, idx2 = random.sample(range(len(lines)), 2)
        lines[idx1], lines[idx2] = lines[idx2], lines[idx1]
        return lines

    def _add_comments(self, lines: List[str]) -> List[str]:
        idx = random.randint(0, len(lines) - 1)
        lines.insert(idx, f"# Evolution v{self.generation}")
        return lines

    def _rename_variables(self, lines: List[str]) -> List[str]:
        mapping = {f"var_{i}": f"var_{i}_evolved" for i in range(10)}
        
        for old_name, new_name in mapping.items():
            lines = [line.replace(old_name, new_name) for line in lines]
        
        return lines

    async def get_statistics(self) -> Dict[str, any]:
        fitnesses = [ind.fitness for ind in self.population]
        return {
            "generation": self.generation,
            "avg_fitness": sum(fitnesses) / len(fitnesses),
            "max_fitness": max(fitnesses),
            "population_size": len(self.population),
        }

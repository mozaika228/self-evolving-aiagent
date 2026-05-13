"""
Integration Guide and Examples for Enhanced Agent System
Shows how to use MetaRewardModel, MultiAgentOrchestrator, and CausalMemoryStore
"""

# ============================================================================
# QUICK START - Enhanced Agent with All Features
# ============================================================================

# Example 1: Basic usage with all enhancements
async def example_enhanced_execution():
    from core.enhanced_agent import EnhancedEvolvingAgent
    
    agent = EnhancedEvolvingAgent(model="deepseek-coder:7b")
    
    result = await agent.execute_enhanced(
        task="Create a REST API for TODO management with authentication",
        language="python",
        learn=True,
        use_multi_agent=True,  # Use specialist agents
        use_causal_tracking=True,  # Track reasoning chain
    )
    
    print(f"Code:\n{result.code}")
    print(f"Test Score: {result.test_score:.1%}")
    print(f"Specialist Used: {result.specialist_used}")
    print(f"Task Category: {result.task_category}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Weights Used: {result.meta_weights_used}")


# ============================================================================
# DETAILED EXAMPLES - Individual Components
# ============================================================================

# Example 2: Meta-Reward Model in Action
async def example_meta_reward():
    from core.meta.meta_reward_model import MetaRewardModel
    
    meta_reward = MetaRewardModel()
    
    # Task 1: Performance-critical (e.g., real-time trading)
    task1 = "Implement O(log n) search with caching for high-frequency data access"
    weights1 = meta_reward.get_weights_for_task(task1)
    
    print("Performance-critical task weights:")
    print(f"  efficiency: {weights1['efficiency']}")  # Should be high
    print(f"  test_score: {weights1['test_score']}")  # Should be lower
    
    # Calculate reward with adaptive weights
    reward_result = meta_reward.calculate(
        test_score=0.92,
        iterations=2,
        code_quality=0.85,
        efficiency=0.95,
        task=task1,
    )
    
    print(f"\nAdaptive Reward: {reward_result['reward']:.3f}")
    print(f"Category Detected: {reward_result['category']}")
    print(f"Component Scores: {reward_result['component_scores']}")


# Example 3: Multi-Agent Orchestrator
async def example_multi_agent():
    from core.multi_agent.orchestrator import MultiAgentOrchestrator, AgentSpecialty
    from core.llm_engine import LLMEngine
    from core.executor import CodeExecutor
    from core.code_gen.generator import CodeGenerator
    from core.testing.test_runner import TestRunner
    
    llm = LLMEngine()
    executor = CodeExecutor()
    generator = CodeGenerator(llm)
    test_runner = TestRunner()
    
    orchestrator = MultiAgentOrchestrator(llm, executor, generator, test_runner)
    
    # Solve task with backend specialist focus
    result = await orchestrator.solve_with_specialists(
        task="Design database schema for e-commerce with denormalization",
        language="python",
        required_specialties=[AgentSpecialty.BACKEND, AgentSpecialty.OPTIMIZATION],
    )
    
    print(f"Specialist: {result['specialist']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Proposals from: {result['all_proposals']}")
    
    # Get statistics
    stats = orchestrator.get_specialist_stats()
    print(f"\nSpecialist Performance:")
    for spec, perf in stats['specialist_performance'].items():
        print(f"  {spec}: {perf['success_rate']:.1%} success rate")


# Example 4: Causal Memory & Reasoning
async def example_causal_memory():
    from core.memory.causal_store import CausalMemoryStore, CausalLink, DecisionType
    
    causal_store = CausalMemoryStore()
    
    # Simulate execution with causal decisions
    decisions = [
        CausalLink(
            cause="Use async/await for I/O operations",
            decision_type=DecisionType.OPTIMIZATION_DECISION,
            reasoning="Database queries are I/O bound, async will improve throughput",
            alternatives=["Use threading", "Use sync with connection pool"],
            consequence={"success": True, "performance_gain": 0.35},
            metrics_before={"latency": 500, "throughput": 100},
            metrics_after={"latency": 150, "throughput": 350},
            confidence=0.92,
        ),
        CausalLink(
            cause="Add caching layer with Redis",
            decision_type=DecisionType.OPTIMIZATION_DECISION,
            reasoning="Read-heavy workload benefits from caching",
            alternatives=["Database-level caching", "Application-level in-memory cache"],
            consequence={"success": True, "cache_hit_rate": 0.78},
            metrics_before={"db_queries": 1000, "response_time": 200},
            metrics_after={"db_queries": 220, "response_time": 50},
            confidence=0.88,
        ),
    ]
    
    # Store with full causal chain
    await causal_store.store_solution_with_causality(
        task="Optimize API response times",
        language="python",
        code="async def get_user(id): ...",  # Simplified
        score=0.96,
        execution_success=True,
        iterations=3,
        causal_links=decisions,
    )
    
    # Extract patterns
    patterns = causal_store.extract_causal_patterns()
    print("Causal Patterns Found:")
    for decision_type, pattern in patterns["high_success_decisions"].items():
        print(f"  {decision_type}: {pattern['common_reasoning']}")
    
    # Analyze root causes of failures
    error_analysis = causal_store.find_error_root_causes()
    print(f"\nError Analysis: {error_analysis}")


# ============================================================================
# ADVANCED - System Reflection and Self-Improvement
# ============================================================================

# Example 5: Agent Self-Reflection
async def example_system_reflection():
    from core.enhanced_agent import EnhancedEvolvingAgent
    
    agent = EnhancedEvolvingAgent()
    
    # Run several executions
    tasks = [
        "Create a fast sorting algorithm",
        "Build secure user authentication",
        "Optimize database queries",
    ]
    
    for task in tasks:
        await agent.execute_enhanced(task, learn=True)
    
    # Get comprehensive system status
    status = agent.get_system_status()
    
    print("=== SYSTEM STATUS ===")
    print(f"\nMeta-Learning: {status['meta_learning']}")
    print(f"\nSpecialist Performance: {status['specialist_performance']}")
    print(f"\nCausal Analysis: {status['causal_analysis']}")
    print(f"\nError Analysis: {status['error_analysis']}")
    
    # The system can use this to adapt:
    # 1. Meta-learning shows which weight combinations work best
    # 2. Specialist performance shows which agents are most reliable
    # 3. Causal analysis reveals decision patterns
    # 4. Error analysis suggests what to improve


# ============================================================================
# INTEGRATION - Using Enhanced Agent in FastAPI
# ============================================================================

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

agent = None  # Global agent instance

@app.on_event("startup")
async def startup():
    global agent
    from core.enhanced_agent import EnhancedEvolvingAgent
    agent = EnhancedEvolvingAgent()


class ExecuteRequest(BaseModel):
    task: str
    language: str = "python"
    use_multi_agent: bool = True
    use_causal_tracking: bool = True


@app.post("/api/execute/enhanced")
async def execute_enhanced(request: ExecuteRequest):
    """Execute with all enhancements enabled."""
    result = await agent.execute_enhanced(
        task=request.task,
        language=request.language,
        learn=True,
        use_multi_agent=request.use_multi_agent,
        use_causal_tracking=request.use_causal_tracking,
    )
    
    return {
        "code": result.code,
        "test_score": result.test_score,
        "specialist": result.specialist_used,
        "category": result.task_category,
        "confidence": result.confidence,
        "iterations": result.iterations,
        "execution_time": result.total_time,
    }


@app.get("/api/system/status")
async def system_status():
    """Get full system status including meta-learning and causal analysis."""
    return agent.get_system_status()


@app.get("/api/system/meta-stats")
async def meta_stats():
    """Get meta-learning statistics."""
    return agent.meta_reward.get_meta_statistics()


@app.get("/api/system/specialists")
async def specialist_stats():
    """Get specialist agent performance."""
    return agent.orchestrator.get_specialist_stats()


@app.get("/api/system/causality")
async def causal_analysis():
    """Get causal reasoning analysis."""
    return {
        "patterns": agent.causal_memory.extract_causal_patterns(),
        "errors": agent.causal_memory.find_error_root_causes(),
    }


# ============================================================================
# TESTING - Comparing Normal vs Enhanced
# ============================================================================

async def compare_normal_vs_enhanced():
    """Compare standard agent with enhanced agent."""
    from core.agent import EvolvingAgent
    from core.enhanced_agent import EnhancedEvolvingAgent
    import time
    
    task = "Create a binary search tree with balancing"
    
    # Standard agent
    print("=== STANDARD AGENT ===")
    standard_agent = EvolvingAgent()
    start = time.time()
    std_result = await standard_agent.execute(task, learn=True)
    std_time = time.time() - start
    
    print(f"Score: {std_result.test_score:.1%}")
    print(f"Time: {std_time:.2f}s")
    print(f"Iterations: {std_result.iterations}")
    
    # Enhanced agent
    print("\n=== ENHANCED AGENT ===")
    enhanced_agent = EnhancedEvolvingAgent()
    start = time.time()
    enh_result = await enhanced_agent.execute_enhanced(task, learn=True)
    enh_time = time.time() - start
    
    print(f"Score: {enh_result.test_score:.1%}")
    print(f"Time: {enh_time:.2f}s")
    print(f"Iterations: {enh_result.iterations}")
    print(f"Specialist: {enh_result.specialist_used}")
    print(f"Confidence: {enh_result.confidence:.1%}")
    
    # Analysis
    print("\n=== COMPARISON ===")
    score_improvement = (enh_result.test_score - std_result.test_score) * 100
    time_ratio = enh_time / std_time
    
    print(f"Score Improvement: {score_improvement:+.1f}%")
    print(f"Time Ratio (enhanced/standard): {time_ratio:.2f}x")
    print(f"Better Confidence: {enh_result.confidence:.1%}")


if __name__ == "__main__":
    import asyncio
    
    # Run examples
    print("Example 1: Enhanced Execution")
    asyncio.run(example_enhanced_execution())
    
    print("\n\nExample 2: Meta-Reward")
    asyncio.run(example_meta_reward())
    
    print("\n\nExample 3: Multi-Agent")
    asyncio.run(example_multi_agent())
    
    print("\n\nExample 4: Causal Memory")
    asyncio.run(example_causal_memory())
    
    print("\n\nExample 5: System Reflection")
    asyncio.run(example_system_reflection())

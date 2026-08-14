from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, ConfigDict
from .environment import Environment

class DynamicDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    done: bool
    next_task: str


def dynamic_decomposition(goal: str, llm: BaseChatModel, max_steps: int = 4) -> list[tuple[str, str]]:
    history: list[tuple[str, str]] = []
    env = Environment()
    total_tokens = 0
    total_calls = 0

    for step in range(max_steps):
        observation = "\n".join(f"{task}: {result}" for task, result in history) or "None"

        # Phase 1: Planning Call
        decision_response = llm.with_structured_output(
            DynamicDecision,
            include_raw=True  # Allows us to access token usage
        ).invoke([
            ("system", "You are an adaptive planner. Use prior observations before deciding what comes next."),
            ("human", f"""Goal: {goal}
Completed work and observations:
{observation}

Decide the single best next task. Set done to true only when the goal is met.
When done is true, use an empty string for next_task."""),
        ], temperature=0.1)

        # Extract decision and metrics
        decision = decision_response["parsed"]
        raw_msg = decision_response["raw"]
        total_calls += 1
        if hasattr(raw_msg, 'usage_metadata') and raw_msg.usage_metadata:
            total_tokens += raw_msg.usage_metadata.get('total_tokens', 0)

        if decision.done:
            break

        task = decision.next_task.strip()
        if not task:
            raise ValueError(f"Dynamic planner omitted next_task at step {step + 1}")

        # Phase 2: Execution Call
        response = llm.invoke([
            ("system",
             "Execute the next adaptive sub-task using the observations provided. Output JSON if executing a database action."),
            ("human", f"Goal: {goal}\nNext task: {task}\nPrior observations:\n{observation}"),
        ], temperature=0.2)

        result = response.content
        total_calls += 1
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            total_tokens += response.usage_metadata.get('total_tokens', 0)

        if not isinstance(result, str) or not result.strip():
            raise RuntimeError("The chat model returned an empty or unsupported response")

        # Ground the execution against the environment
        feedback = env.evaluate(state=result.strip())

        # Store both the LLM's attempt and the environment's reality in history
        final_observation = f"LLM Action: {result.strip()}\nEnvironment Validation: {feedback.details[0]}"
        history.append((task, final_observation))

    # Append metrics as a final tuple so your test script can read them
    history.append(("_metrics", f"tokens:{total_tokens}|calls:{total_calls}"))
    return history

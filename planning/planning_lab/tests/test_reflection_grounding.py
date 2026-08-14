import json

from planning.planning_lab.algorithms.environment import Environment
from planning.planning_lab.algorithms.reflexion import reflexion
from planning.planning_lab.algorithms.self_refine import reflect_and_refine


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def invoke(self, messages, temperature=0.2):
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError("No fake response left for the model")
        response = self.responses.pop(0)

        class Response:
            content = response

        return Response()


def test_reflexion_capped_memory_survives_multiple_failed_trials():
    fail_attempt = json.dumps({"worker_id": "w999", "chemical_id": "chem2"})
    env = Environment()

    llm = FakeLLM([
        fail_attempt,
        "I forgot to verify that the worker existed and was certified.",
        fail_attempt,
        "I still ignored the certified-worker requirement.",
        fail_attempt,
        "I kept reusing an invalid worker assignment.",
    ])

    result = reflexion(
        task="Submit a restricted pesticide application.",
        llm=llm,
        environment=env,
        max_trials=3,
        memory_size=2,
    )

    assert len(result.trials) == 3
    assert len(result.memory) == 2
    assert "I still ignored the certified-worker requirement." in "\n".join(result.memory)
    assert "I kept reusing an invalid worker assignment." in "\n".join(result.memory)

    second_attempt_prompt = llm.calls[2][1][1]
    assert "I forgot to verify that the worker existed and was certified." in second_attempt_prompt

    third_attempt_prompt = llm.calls[4][1][1]
    assert "I forgot to verify that the worker existed and was certified." in third_attempt_prompt
    assert "I still ignored the certified-worker requirement." in third_attempt_prompt
    assert "I kept reusing an invalid worker assignment." not in third_attempt_prompt

    final_memory = "\n".join(result.memory)
    assert "I still ignored the certified-worker requirement." in final_memory
    assert "I kept reusing an invalid worker assignment." in final_memory


def test_grounded_critique_catches_failure_that_ungrounded_pass_misses():
    goal = "Submit a pesticide application using the approved worker and chemical rules."
    draft = json.dumps({
        "action_name": "request_pesticide_application",
        "worker_id": "w999",
        "chemical_id": "chem2",
        "field_id": "f1",
    })

    llm = FakeLLM(["PASS", "Improved replacement plan.\n\n- Use certified worker w2 to apply chem2."])
    result = reflect_and_refine(goal, draft, llm, environment=Environment())

    assert result.grounded_issues
    assert any("Grounded validation" in issue for issue in result.grounded_issues)
    assert "Grounded checks failed" in result.critique
    assert result.revised.strip()

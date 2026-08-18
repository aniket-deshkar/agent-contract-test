"""Example factory loaded by ``--adapter examples.fake_adapter:create_adapter``."""

from agent_contract_test import AgentRun, FakeAgentAdapter, ToolCall, UsageMetadata


def create_adapter() -> FakeAgentAdapter:
    """Create a deterministic adapter without a real model."""
    return FakeAgentAdapter(
        AgentRun(
            response={"order_id": "order-1001", "status": "accepted"},
            tool_calls=[
                ToolCall(
                    name="check_inventory",
                    arguments={"sku": "book-42", "quantity": 2},
                ),
                ToolCall(
                    name="create_order",
                    arguments={"customer_id": "customer-7"},
                    approval_requested=True,
                    approval_granted=True,
                ),
            ],
            agent_steps=3,
            model_calls=2,
            usage=UsageMetadata(tokens=320, cost=0.0042),
        )
    )

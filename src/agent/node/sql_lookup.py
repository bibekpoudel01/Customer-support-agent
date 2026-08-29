
import logfire
from pydantic import BaseModel, Field
from src.agent.state import AgentState
from src.gateway.client import get_langchain_llm
from src.sql.queries import (
    get_product_by_name,
    get_product_by_id,
    check_stock,
    search_products,
    get_order_by_id,
    get_customer_by_session,
    get_customer_summary,
)

llm = get_langchain_llm(feature="sql_lookup")


class SQLExtraction(BaseModel):
    action: str = Field(
        ...,
        description=(
            "Action to execute: "
            "'get_product' (product details/specs), "
            "'check_stock' (stock availability), "
            "'search_products' (general product search), "
            "'order_status' (a specific order by ID), "
            "'my_orders' (the user's own orders/account details)"
        ),
    )
    product_name: str | None = Field(None, description="Name of the product if mentioned.")
    product_id: int | None = Field(None, description="Product ID if specified.")
    order_id: int | None = Field(None, description="Order ID if the user mentioned one.")
    category: str | None = Field(None, description="Product category if filtering.")
    keyword: str | None = Field(None, description="Search keyword if applicable.")


def sql_lookup_node(state: AgentState) -> dict:
    """Executes a structured SQL query based on the user's intent."""
    messages = state.get("messages", [])
    user_msg = messages[-1]["content"] if messages else ""
    session_id = state.get("session_id", "")

    prompt = f"""Extract SQL lookup parameters from the user message.
User Message: "{user_msg}"
"""

    with logfire.span("SQL Lookup Extraction"):
        extractor = llm.with_structured_output(SQLExtraction, method="function_calling")
        params = extractor.invoke(prompt)
        logfire.info(f"SQL Action: {params.action} | Params: {params.model_dump()}")

    sql_result = {}
    status_msg = f"Executed SQL action '{params.action}'."

    try:
        if params.action == "get_product":
            if params.product_id:
                res = get_product_by_id(params.product_id)
            elif params.product_name:
                res = get_product_by_name(params.product_name)
            else:
                res = search_products(keyword=params.keyword or user_msg)
            sql_result = res.model_dump()

        elif params.action == "check_stock":
            if params.product_id:
                res = check_stock(params.product_id)
            elif params.product_name:
                prod_res = get_product_by_name(params.product_name)
                res = check_stock(prod_res.product.product_id) if prod_res.found and prod_res.product else prod_res
            else:
                res = search_products(keyword=params.keyword or user_msg)
            sql_result = res.model_dump()

        elif params.action == "order_status":
            if params.order_id:
                res = get_order_by_id(params.order_id)
                sql_result = res.model_dump()
            else:
                sql_result = {"found": False, "reason": "no_order_id_given"}

        elif params.action == "my_orders":
            customer = get_customer_by_session(session_id)
            if not customer:
                sql_result = {"found": False, "reason": "no_customer_for_session"}
            else:
                summary = get_customer_summary(customer.customer_id)
                sql_result = {"found": True, "summary": summary}

        else:
            res = search_products(
                category=params.category,
                keyword=params.keyword or params.product_name or user_msg,
            )
            sql_result = res.model_dump()

    except Exception as e:
        logfire.error(f"Error during SQL execution: {e}")
        sql_result = {"found": False, "reason": str(e)}
        status_msg = f"Error during SQL execution: {e}"

    return {
        "sql_result": sql_result,
        "status": status_msg,
        "plan": ["Intent: SQL Lookup", f"Action: {params.action}"],
    }
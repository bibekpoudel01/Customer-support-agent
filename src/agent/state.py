#Defining the state
from typing import TypedDict,Annotated
from langgraph.graph import add_messages
class SupportState(TypedDict):
    messages:Annotated[List,add_messages]
    user_input:str
    intent:str
    reterived_context:str
    response:str
    esclate:bool
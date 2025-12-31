from langchain_core.prompts import PromptTemplate

example_prompt = PromptTemplate.from_template("Share an interesting fact about {animal}.")  # infers 'animal' as input variable

# Format the template with a specific animal
filled_prompt = example_prompt.format(animal="octopus")
print(filled_prompt)


from langchain_core.prompts import ChatPromptTemplate

chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a patient tutor who explains things clearly."),
    ("human", "Can you explain {concept} like I'm five?")
])

# Fill in the template with a specific concept
formatted_messages = chat_prompt.format_messages(concept="gravity")

print(formatted_messages)


from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful career coach."),
    MessagesPlaceholder("conversation"),  # Dynamic history insertion
    ("human", "{current_question}")
])

# Define history using proper message objects
conversation_history = [
    HumanMessage(content="How do I prepare for a job interview?"),
    AIMessage(content="Start by researching the company and practicing common questions.")
]

formatted_messages = chat_prompt.format_messages(
    conversation=conversation_history,
    current_question="Should I send a thank-you email afterward?"
)

print(formatted_messages)

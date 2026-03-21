from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

prompt1 = PromptTemplate.from_template("Summarize this:\n{content}")
prompt2 = PromptTemplate.from_template("Convert this summary into bullet points:\n{summary}")

summary = llm.invoke(prompt1.format(content=user_input))
bullets = llm.invoke(prompt2.format(summary=summary))
print(bullets)

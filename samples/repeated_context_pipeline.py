from langchain.chat_models import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")
context = "You are a strict technical editor. Keep all output concise and factual."

step1 = llm.invoke(f"{context}\nSummarize this ticket:\n{ticket_text}")
step2 = llm.invoke(f"{context}\nExtract risks from the summary:\n{step1}")
print(step2)

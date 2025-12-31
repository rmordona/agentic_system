from langchain_core.vectorstores.faiss import FAISS
from langchain_core.schema import Document
from langchain_core.embeddings import OpenAIEmbeddings  # or any embedding

docs = [Document(page_content="Test", metadata={"id": 1})]
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_store = FAISS.from_documents(docs, embeddings)
results = vector_store.similarity_search("Test query", k=2)


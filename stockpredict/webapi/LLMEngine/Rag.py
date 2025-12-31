
import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import CSVLoader
from langchain_groq import ChatGroq
from langchain_text_splitters import CharacterTextSplitter
from langchain.chains import RetrievalQA
HUGGING_FACE_API_KEY = "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"
GROQ_API_KEY = "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"
os.environ["GROQ_API_KEY"] = GROQ_API_KEY
class Rag:
    PERSISTENCE_DIRECTORY = "rag_db"
    COLLECTION_NAME = "stock_rag"
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Rag, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.embeddings = HuggingFaceEmbeddings(model_name=self.MODEL_NAME)
            self.db = Chroma(collection_name=self.COLLECTION_NAME, persist_directory=self.PERSISTENCE_DIRECTORY, embedding_function=self.embeddings)
            self._initialized = True


    def add_file_to_collection(self,file_name):

        loader = CSVLoader(file_name)
        documents = loader.load()
        text_splitter = CharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=500
        )
        text_chunks = text_splitter.split_documents(documents)
        db2 = Chroma.from_documents(text_chunks, self.embeddings, persist_directory=self.PERSISTENCE_DIRECTORY, collection_name=self.COLLECTION_NAME)



    def remove_file(self,file_name):
        db = Chroma(collection_name=self.COLLECTION_NAME, persist_directory=self.PERSISTENCE_DIRECTORY,
                    embedding_function=self.embeddings)
        documents = db.get()
        metadata = documents['metadatas']
        ids = documents['ids']
        ids_to_delete = []
        for i in range(len(metadata)):
            if metadata[i]['source'].find(file_name) >= 0:
                ids_to_delete.append(ids[i])
        if len(ids) > 0:
            db.delete(ids=ids_to_delete)





    def answer_to_question(self, question):
        print("\nThinking...\n ")
        retriever = self.db.as_retriever()
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0
        )
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True
        )
        response = qa_chain.invoke({"query": question})
        return response["result"]


# Global singleton instance
rag_instance = None

def get_rag_instance():
    global rag_instance
    if rag_instance is None:
        rag_instance = Rag()
    return rag_instance

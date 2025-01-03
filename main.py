# Import necessary packages
import os
import streamlit as st
from langchain.document_loaders import UnstructuredURLLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
import validators

# Load OpenAI API key
os.environ["OPENAI_API_KEY"] = st.secrets["key"]

# Streamlit user interface
st.title("Medium Website Chatbot")
st.write("""
### How to Use:
1. Enter a valid [medium](https://medium.com/) website link in the input box below.
2. The chatbot will process the website's contents through document retrieval powered by OpenAI LLM
3. You can now have an open-ended conversation about the uploaded website content.
""")
st.write("Enter a valid website link below to start:")

# Initialize session state
if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferMemory(
        memory_key="chat_history", return_messages=True, output_key="answer"
    )
if "chain" not in st.session_state:
    st.session_state.chain = None
if "vectordb" not in st.session_state:
    st.session_state.vectordb = None

# Get URL
url = st.text_input("Enter a website URL: ")

if url:
    if validators.url(url):
        st.success("Valid URL. Processing the content from the website...")
        if st.session_state.chain is None:  # Process the content only once
            try:
                # Get texts from the website
                loaders = UnstructuredURLLoader(urls=[url])
                data = loaders.load()

                # Extract chunks from the website
                text_splitter = CharacterTextSplitter(separator="\n", chunk_size=1000, chunk_overlap=200)
                chunks = text_splitter.split_documents(data)

                # Generate embeddings and create FAISS database
                embeddings = OpenAIEmbeddings()
                st.session_state.vectordb = FAISS.from_documents(documents=chunks, embedding=embeddings)

                # Setup LLM
                llm = ChatOpenAI(temperature=0.1)

                # Setup prompt
                prompt_template = """
                You are a helpful website chatbot assistant. Use the retrieved information and your past conversation to answer the conversational questions.
                If you don't know the answer, just answer I don't know.
                {context}

                {chat_history}
                
                Question: {question}
                Helpful Answer:
                """
                prompt = PromptTemplate(template=prompt_template, input_variables=["context", "chat_history", "question"])

                # Combine LLM, memory, and prompt
                st.session_state.chain = ConversationalRetrievalChain.from_llm(
                    llm=llm,
                    retriever=st.session_state.vectordb.as_retriever(search_kwargs={"k": 1}),
                    memory=st.session_state.memory,
                    get_chat_history=lambda h: h,
                    combine_docs_chain_kwargs={'prompt': prompt}
                )

                st.write("Content processed successfully. Chatbot is ready!")
            except Exception as e:
                st.error(f"Error processing the URL: {str(e)}")
    else:
        st.error("Invalid URL. Please enter a valid website.")

# Chat Interface
if st.session_state.chain:
    user_input = st.text_input("Your question (type 'exit' to end): ")

    if user_input:
        if user_input.lower() == "exit":
            st.write("Session ended. Refresh the page to start over.")
        else:
            try:
                response = st.session_state.chain({"question": user_input})
                st.write(f"Chatbot: {response['answer']}")
            except Exception as e:
                st.error(f"Error during conversation: {str(e)}")

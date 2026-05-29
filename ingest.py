import shutil
import os

from rag_functions import create_vectorstore, VECTOR_DB_PATH


if os.path.exists(VECTOR_DB_PATH):
    shutil.rmtree(VECTOR_DB_PATH)

create_vectorstore()
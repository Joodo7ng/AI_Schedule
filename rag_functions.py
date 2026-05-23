import os
from dotenv import load_dotenv
from openai import OpenAI

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_DB_PATH = os.path.join(BASE_DIR, "vector_db")
DATA_PATH = os.path.join(BASE_DIR, "data", "timetable_info.txt")


def load_documents():
    with open(DATA_PATH, "r", encoding="utf-8") as file:
        text = file.read()

    document = Document(page_content=text)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )

    return splitter.split_documents([document])


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="jhgan/ko-sroberta-multitask",
        model_kwargs={
            "device": "cpu",
            "local_files_only": True
        },
        encode_kwargs={"normalize_embeddings": True}
    )


def create_vectorstore():
    chunks = load_documents()
    embeddings = get_embeddings()

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=VECTOR_DB_PATH
    )

    return vectorstore


def load_vectorstore():
    embeddings = get_embeddings()

    return Chroma(
        persist_directory=VECTOR_DB_PATH,
        embedding_function=embeddings
    )


def get_rag_answer(user_question):
    vectorstore = load_vectorstore()

    docs = vectorstore.similarity_search(user_question, k=3)
    
    if not docs:
        return "관련 문서를 찾을 수 없습니다."

    context = "\n\n".join([doc.page_content for doc in docs])

    prompt = f"""
너는 성신여자대학교 AI융합학부 학생을 위한 AI 수강 추천 챗봇이다.

반드시 제공된 시간표 데이터, 졸업요건 데이터, 과목 정보 안에서만 답변한다.

다음에 해당하는 질문에는 답변하지 말고 아래 문장을 출력한다.
"수강 추천, 졸업요건, 공강 구성, 졸업요건 관련 질문들을 알려드릴 수 있어요."

답변하지 말아야 하는 경우:
- 시간표, 과목 추천, 학점, 전공/교양, 공강, 난이도, 졸업요건과 관련 없는 질문
- 제공된 데이터에 없는 교수명, 강의실, 시험방식, 수업방식 질문
- 학교 공식 정보가 필요한데 데이터에 없는 질문


사용자가 단순 인사("안녕", "하이")만 하면
간단히 인사 후 시간표 관련 질문을 유도한다.

예외:
답변할 때는 모르는 내용을 추측하지 않는다.

-----------------------------------

[추천 과목]
- 과목명
- 필수 교양 한과목
- 과목명
- 과목명
-교양과목 자유선택

[추천 학점 구성]
- 전공: X학점
- 필수교양: X학점
- 공통/핵심교양: X학점
총 X학점


[참고사항]
- 졸업 요건 충족을 위해 필수교양을 꼭 수강하세요
-1학년에는 각 학기마다 비사토/창사글 두 수업중 하나를 필수로 수강해야합니다.

-----------------------------------

규칙:
1. 한국어로만 답변해라.
2. 줄글로 길게 쓰지 마라.
3. 반드시 줄바꿈을 사용해라.
4. 추천 과목은 bullet point(-) 형식으로 작성해라.
5. 대학생이 보기 쉽게 깔끔하게 정리해라.
6. 부족한 졸업요건이 있다면 우선 반영해라.
7. 사용자가 목표 학점을 지정하지 않았을 경우 기본적으로 18학점 기준으로 추천해라.
8. 사용자가 특정 학기(예: 1학년 2학기)를 명시하면 반드시 해당 학기 커리큘럼 기준으로만 추천해라.
9. 이전 학기 과목을 반복 추천하지 마라.
10. 1학년 학생에게는 전공만 추천하면 안 된다.
11. 1학년 기본 추천 구성:
   - 전공 9학점
   - 필수교양 3학점
   - 공통/핵심교양 6학점
12. 2학년 이상은 전공 비중을 더 높게 추천할 수 있다.
13. 공통교양 필수 과목 중 비판적사고와토론, 창의적사고와글쓰기는
둘 다 동시에 추천하지 않는다. 그리고 아래 형식처럼 선택형으로 제시해라:
- 비판적사고와토론 또는 창의적사고와글쓰기

14. 여러 선택지가 가능한 교양 과목은 모두 나열하지 말고
"과목 A 또는 과목 B" 형식으로 간결하게 제시해라.

[참고 문서]
{context}

[사용자 질문]
{user_question}

[답변]
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content
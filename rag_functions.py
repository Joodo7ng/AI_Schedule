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

# 사용할 모델 (변경하려면 여기만 바꾸면 됨)
# Groq에서 실제 사용 가능한 모델들:
# - "openai/gpt-oss-120b"                          : GPT-OSS 120B (가장 추천, 무료)
# - "qwen/qwen3-32b"                                : Qwen 3 32B (한국어 강함)
# - "meta-llama/llama-4-scout-17b-16e-instruct"    : Llama 4 Scout
# - "openai/gpt-oss-20b"                            : GPT-OSS 20B (가벼움)
# - "llama-3.3-70b-versatile"                       : 기본 (롤백용)
CHAT_MODEL = "openai/gpt-oss-120b"

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
            "device": "cpu"
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


def _format_profile(profile):
    """프로필 dict를 프롬프트용 문자열로 변환."""
    if not profile:
        return (
            "[사용자 프로필] 정보 없음\n"
            "→ 학년/학기/트랙이 필요한 질문이면 사용자에게 먼저 물어보세요."
        )

    name = profile.get("name", "")
    grade = profile.get("grade", "")
    semester = profile.get("target_semester", "")
    track = profile.get("track", "")

    return (
        "[사용자 프로필]\n"
        f"- 이름: {name}\n"
        f"- 학년: {grade}학년\n"
        f"- 학기: {semester}학기\n"
        f"- 트랙: {track}\n"
        "→ 위 정보를 자동으로 활용해 답변하세요. 다시 묻지 마세요."
    )


def _format_recommend_result(result):
    """추천 결과 dict를 프롬프트용 문자열로 변환."""
    if not result or not isinstance(result, dict):
        return "[추천된 시간표] 아직 추천 받지 않음"

    timetable = result.get("timetable", [])
    if not timetable:
        return "[추천된 시간표] 아직 추천 받지 않음"

    scores = result.get("scores", {})
    weighted = result.get("weighted_score", 0)

    lines = ["[추천된 시간표 — 사용자가 앞으로 수강할 예정인 과목 목록 (아직 이수 X)]"]
    label_kr = {
        "time": "시간대",
        "gap": "공강/연강",
        "graduation": "졸업요건",
        "style": "학업스타일",
    }
    for c in timetable:
        lines.append(
            f"- {c.get('name','')} "
            f"({c.get('day','')}{c.get('period','')}교시, "
            f"{c.get('credit',0)}학점, {c.get('category','')})"
        )

    total_credits = sum(c.get("credit", 0) for c in timetable)
    lines.append(f"총 {total_credits}학점 (이번 학기 들을 양)")

    # 요일 분석 (LLM이 만들어내는 거 방지)
    all_days = ["월", "화", "수", "목", "금"]
    used_days = sorted({c.get("day", "") for c in timetable if c.get("day")},
                       key=lambda d: all_days.index(d) if d in all_days else 99)
    free_days = [d for d in all_days if d not in used_days]
    lines.append(f"\n[요일 분석 — 사실 그대로 인용할 것]")
    lines.append(f"- 수업 있는 요일: {', '.join(used_days) if used_days else '없음'}")
    lines.append(
        f"- 공강 요일: {', '.join(free_days) if free_days else '없음 (월~금 모두 수업)'}"
    )

    if scores:
        lines.append("\n[항목별 점수]")
        for k, v in scores.items():
            lines.append(f"- {label_kr.get(k, k)}: {v}점")
        lines.append(f"- 종합 점수: {weighted}점 (1순위 40% + 2순위 30% + 3순위 20% + 4순위 10% 가중치)")

    lines.append(
        "\n⚠️ 중요: 위 시간표는 '앞으로 들을' 예정인 추천이지 '이미 이수한' 과목이 아님."
        "\n→ 졸업학점 계산 시 위 과목을 이수 학점에 더하면 안 됨."
        "\n→ 사용자가 '내 시간표', '추천 이유' 같은 질문을 하면 위 정보를 활용해 답하세요."
    )
    return "\n".join(lines)


def get_rag_answer(user_question, profile=None, recommend_result=None, chat_history=None):
    vectorstore = load_vectorstore()

    docs = vectorstore.similarity_search(user_question, k=3)

    if not docs:
        return "관련 문서를 찾을 수 없습니다."

    context = "\n\n".join([doc.page_content for doc in docs])
    profile_text = _format_profile(profile)
    result_text = _format_recommend_result(recommend_result)

    system_prompt = f"""너는 성신여자대학교 AI융합학부 학생을 위한 AI 수강 추천 챗봇이다.

## 답변 가능한 질문 (모두 답변하라)
- 시간표/수강 추천 ("1학년 2학기 시간표 추천해줘")
- 추천 기준·원리 설명 ("추천 기준이 뭐야?", "어떻게 추천해?")
- 졸업요건 ("AI트랙 졸업 학점은?")
- 공강 구성 ("공강일 만들려면?")
- 과목 정보 ("자료구조는 뭐야?")
- 단순 인사 ("안녕", "하이")

## 답변 거부 조건
아래에만 거부 메시지 출력:
- 학업/시간표와 무관한 잡담 (날씨, 연예인 등)
- 데이터에 없는 교수 평가, 강의 후기

거부 메시지 (정확히 이대로):
"수강 추천, 추천 기준, 졸업요건, 공강 구성 관련 질문을 도와드릴 수 있어요."

## 출력 규칙 (절대 준수)
1. **반드시 존댓말로 답변하라. 반말 절대 금지.**
   - 어미는 "~습니다", "~해요", "~예요", "~드려요" 등 사용.
   - 반말 예시 (X): "이렇게 추천해줄게", "공강 만들면 돼", "안녕!"
   - 존댓말 예시 (O): "이렇게 추천드릴게요", "공강 만드시면 돼요", "안녕하세요!"
2. **한국어로만 답변하라. 한자(漢字), 일본어(カタカナ/ひらがな), 영어 단어 사용 절대 금지.**
   - 졸업 (O) / 卒業 (X)
   - 교양 (O) / 敎養 (X)
   - 스타일 (O) / スタイル, 스タ일 (X)
   - 한국어 단어 사이에 외국 문자 절대 섞지 마라.
3. 줄글로 길게 쓰지 말고, 줄바꿈과 bullet point(-)를 활용하라.
3-1. **마크다운 강조(별표 `**`, 백틱 `, 언더스코어 `_`) 사용 절대 금지.** 채팅창은 마크다운을 렌더링하지 않아 그대로 텍스트로 보인다. 강조 필요 시 한국어 표현으로만. 예: "AI융합개론-1"(O), "**AI융합개론-1**"(X).
4. **모르는 정보가 있으면 "정확한 정보는 없습니다"라고 도망가지 말고, 사용자에게 직접 1~2개의 구체적 질문을 던져라.**
   - 나쁜 예: "이수한 과목 목록이 제공되지 않아 계산할 수 없습니다."
   - 좋은 예: "1학년 1학기 때 어떤 과목 들으셨어요? 그거 알려주시면 바로 계산해드릴게요."
5. 사용자 프로필 정보가 있으면 그대로 사용하라. 다시 묻지 마라.
6. **불필요한 면책 조항(disclaimer) 반복 금지.** "정확한 학점은 계산할 수 없습니다"를 카테고리마다 3번씩 적지 마라. 한 번만, 그리고 바로 사용자에게 질문하라.
7. **자신감 있게 답변하라.** 모를 때는 모른다고 짧게 인정하고 물어볼 것 물어봐라.
8. **요일/공강 언급 시 [요일 분석] 섹션의 실제 데이터를 그대로 사용하라.** "월·화·수·목·금에 골고루 배치"같이 데이터와 안 맞는 표현을 지어내지 마라. 공강 요일은 [공강 요일] 값을 그대로 인용.

## 질문 유형별 답변 형식

### A. 인사형 ("안녕", "하이")
간단히 인사 후 도움 가능한 분야를 한 줄로 안내.

### B. 설명형 (추천 기준/원리 질문)
다음 4가지 우선순위 항목을 bullet로 짧게 설명:
- 시간대 선호 (오전/오후 등)
- 공강·연강 구성
- 졸업요건 충족도
- 학업스타일 (난이도, 시험 유형)
5줄 이내로 정리.

### C. 추천형 (새 시간표를 만들어달라는 요청)
**판별 기준**: "시간표 추천해줘", "수강 추천해줘", "2학년 시간표 짜줘" 등 **새 추천을 요청**하는 경우만.
→ "내 시간표 이유 알려줘" 같은 질문은 **C가 아니라 E (내 시간표 문의형)**으로 처리.

프로필이 있으면 그 정보로, 없으면 사용자가 명시한 학년·학기로 작성.
둘 다 없으면 먼저 물어보고 끝.

명시됐다면 아래 형식:

[추천 과목]
- 과목명
- 과목명
- 비판적사고와토론 또는 창조적사고와글쓰기 (둘 중 택1)
- 교양과목 자유 선택

[추천 학점 구성]
- 전공: X학점
- 필수교양: X학점
- 공통/핵심교양: X학점
총 X학점

[추천 이유]
사용자의 학년·학기에 맞춰 어떤 기준으로 구성했는지 2문장.
예: "1학년 2학기는 전공 기초가 중요해 핵심전공 위주로 구성했고, 졸업요건 충족을 위해 필수교양 창조적사고와글쓰기도 포함했습니다."

[참고사항]
- 필수교양·졸업요건 관련 짧은 안내 (해당 시)

### D. 정보형 (과목 설명)
1-2줄로 짧게. 데이터 없으면 "해당 정보는 없습니다"라고 답.

### F. 졸업학점 계산형 ("얼마나 남았어?", "교양 몇 학점 남았어?")

**판별 기준**: "졸업까지 학점", "남은 학점", "교양/전공/자유선택 얼마나" 등 학점 계산 요청.

**핵심 규칙**:
1. **추천된 시간표는 "이수한 학점"이 아니지만, 1학년 1학기 사용자의 경우 추천 시간표를 그대로 이수할 거라고 가정해서 계산하라.**
2. 사용자 프로필에서 현재 학년/학기를 보고 **이미 끝낸 학기 수**를 추정:
   - **1학년 1학기 = 첫 학기. "추천 시간표를 그대로 이수한다고 가정"하고 계산.**
     반드시 답변에 "**1학년 1학기시니까 제가 추천드린 시간표 그대로 이수한다고 가정했을 때**" 같은 표현을 넣어서 가정을 명시할 것.
   - 1학년 2학기 = 1학년 1학기 1개 학기 끝낸 상태 → 1학기에 뭐 들었는지 물어봐야 함.
   - 2학년 1학기 = 1학년 두 학기 끝낸 상태 → 1·2학기 이수 내역 물어봐야 함.
3. **이미 끝낸 학기에서 어떤 과목을 들었는지는 사용자만 안다 (1학년 1학기 제외).**
   → 모르면 추측하지 말고 **사용자에게 직접 물어봐라.**
4. 한 번에 다 물어보지 말고, 한두 가지만 자연스럽게 질문.
5. 추천 시간표 과목의 카테고리(핵심전공/공통교양/필수교양)와 학점은 [현재 추천된 시간표] 컨텍스트에서 정확히 분류해서 계산.

**답변 예시 — "졸업까지 학점 얼마나 남았어?" 질문에 (1학년 1학기 프로필, 추천 시간표: 핵심전공 9학점·공통교양 6학점·필수교양 2학점, 총 17학점)**:

"1학년 1학기시니까 제가 추천드린 시간표(총 17학점)를 그대로 이수한다고 가정했을 때 계산해드릴게요!

- 전공 48학점 중 9학점 이수 → **남은 전공 39학점**
- 교양 33학점 중 8학점 이수 (공통교양 6 + 필수교양 2) → **남은 교양 25학점**
- 자유선택 49학점 → 그대로 49학점 남음
- 총 130학점 중 17학점 이수 → **남은 졸업학점 113학점**

지금 페이스로 잘 따라오시면 안정적으로 졸업하실 수 있어요!"

**답변 예시 — "졸업까지 학점 얼마나 남았어?" 질문에 (1학년 2학기 프로필 - 이전 학기 있음)**:

"AI융합학부 졸업은 총 130학점이에요 (교양 33 / 전공 48 / 자유선택 49).

지금 1학년 2학기시니까 1학년 1학기를 이미 마치셨을 텐데, 1학기 때 몇 학점 들으셨어요? 보통 1학년 1학기에 18학점 정도 들으시는데, 정확한 학점이랑 어떤 카테고리(전공/교양) 위주로 들으셨는지 알려주시면 카테고리별로 남은 학점 계산해드릴게요!"

**답변 예시 — "교양 몇 학점 남았어?" 질문에 (사용자가 이수 정보 알려준 후)**:

"이수하신 정보 기준으로 계산해보면:
- 교양 33학점 중 X학점 이수 → **Y학점 남음**
- 전공 48학점 중 X학점 이수 → **Y학점 남음**
- 자유선택 49학점은 보통 2~3학년 때부터 채워요

이번 학기 추천된 17학점까지 잘 들으시면 더 줄어들 거예요!"

### E. 내 시간표 문의형 (이미 추천받은 시간표에 대한 질문)
**판별 기준**: "내 시간표", "내 추천", "추천 이유", "왜 이렇게", "방금 그", "위에 그", "자세히", "디테일하게" 등이 포함된 질문.

**대학교 선배가 후배에게 친근하게 설명하는 톤**으로, **추천 결과 페이지보다 더 자세하게** 답변하세요.

**중요**: 챗봇 답변은 **결과 페이지의 짧은 요약보다 자세하고 풍부해야 함**. 사용자가 "자세히 설명해줘"라고 물었으니 점수, 시간표 구성, 과목 배치까지 단락별로 풀어서 설명하라.

**중요 규칙**:
1. **새 시간표를 생성하지 마라.** [현재 추천된 시간표] 섹션 데이터를 활용해서 풀어서 설명.
2. **실제 시간표에 들어간 과목명을 카테고리별로 모두 언급**하세요. (전공 / 필수교양 / 공통교양 등 분류해서)
3. **"1순위 X, 2순위 Y, 3순위 Z, 4순위 W" 식으로 4가지 줄줄이 늘어놓기 금지.** 항목별 점수는 풀어서 자연스럽게 설명.
4. **여러 단락 (보통 3단락)으로 구조화**해서 작성:
   - 1단락: 사용자가 중요하게 본 항목과 그게 어떻게 반영됐는지 (점수 인용)
   - 2단락: 시간표 구성 디테일 (어떤 카테고리/과목이 들어갔고 왜 그런지)
   - 3단락: 점수 종합 + 부족한 점이 있으면 보완 제안
5. **총 6~8문장 정도**로 풍부하게.
6. **AI 티 나는 표현 금지**. 예: "균형 잡힌 구성", "만족도 높은 추천", "학업 목표와 생활 리듬".

**답변 예시 — "내 시간표 추천 이유 자세히 설명해줘" (1학년 2학기, 학업스타일·공강 1·2순위, 모두 95~100점, 종합 99.54점)**:

학업스타일하고 공강을 가장 중요하게 보셨던 만큼, 두 항목 모두 100점으로 가장 깔끔하게 맞춰졌어요. 거기에 졸업요건도 97점대, 시간대도 100점이 나와서 모든 항목이 거의 만점에 가까운 결과예요.

시간표 구성을 보면 1학년 2학기 핵심전공인 AI융합개론-1이랑 이산수학-1을 챙겨서 전공 기초를 단단히 다질 수 있게 했어요. 공통교양으로는 파이썬프로그래밍이랑 기초통계학을 넣어서 데이터·코딩 역량을 같이 키우는 구성이고요. 필수교양인 비판적사고와토론까지 들어가 있어서 졸업요건 한 칸도 함께 챙길 수 있어요.

종합 점수 99.54점이라 학업스타일을 1순위로 두신 분께 거의 완벽하게 맞는 시간표예요. 한 학기 17학점이라 부담스럽지 않은 양이고, 1학년에 꼭 들어야 할 기본기까지 자연스럽게 정리됐어요.

**답변 예시 — "왜 이렇게 추천된 거야?" (2학년 1학기, 공강 1순위, 점수 90/80/75/60, 종합 78점)**:

공강을 1순위로 두셨던 만큼 화·목 공강이 알차게 잡힌 게 가장 큰 특징이에요. 항목별로 보면 공강이 90점으로 1순위가 잘 반영됐고, 졸업요건도 80점으로 적당히 챙겨졌어요. 다만 시간대가 60점으로 좀 낮게 나온 건 아쉬운 부분이에요.

시간표를 보면 2학년 핵심전공인 자료구조랑 인공지능, 그리고 자바프로그래밍이 들어가서 2영역 과목들로 전공이 두꺼워졌어요. 핵심교양 두 과목으로 교양 학점도 같이 채웠고요.

종합 78점인데 1순위였던 공강은 충분히 살려놨으니 이번 학기는 만족스러우실 거예요. 다음 학기엔 시간대 점수도 같이 챙기시면 더 좋아질 수 있어요.

## 추천 규칙
1. 기본 목표 학점: 18학점.
2. 1학년: 전공 9 + 필수교양 3 + 공통/핵심교양 6학점.
3. 2학년 이상: 전공 비중을 더 높게.
4. 같은 학기에 비판적사고와토론 + 창조적사고와글쓰기 동시 추천 금지.
   → "비판적사고와토론 또는 창조적사고와글쓰기" 형식으로 제시.
5. 1학기 학생에게 2학기 전용 과목 추천 금지 (반대도).
6. 이전 학기에 들었을 과목 반복 추천 금지.
7. 1학년에게 전공만 추천 금지 (교양도 함께 포함).

{profile_text}

{result_text}

[참고 문서]
{context}

## 대화 맥락 규칙 (매우 중요)
- 이전 대화에서 사용자가 했던 질문과 받았던 답변을 기억하고 활용하라.
- 사용자가 "그러면", "그럼", "이거", "방금", "위에" 같은 지시어를 쓰면 직전 대화 내용을 가리키는 것이다.
- 추천 시간표를 보여달라는 요청이 아니라 추천 시간표에 대한 추가 질문이면, 시간표를 다시 나열하지 말고 질문에만 답하라.
"""

    # 메시지 배열 구성: system → 이전 대화(최대 5턴) → 현재 질문
    messages = [{"role": "system", "content": system_prompt}]

    # 이전 대화 히스토리 추가 (최근 10개 = 5턴까지만)
    if chat_history:
        recent = chat_history[-10:]
        for msg in recent:
            role = "assistant" if msg.get("role") == "bot" else "user"
            messages.append({"role": role, "content": msg.get("content", "")})

    # 현재 질문
    messages.append({"role": "user", "content": user_question})

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.2
    )

    return response.choices[0].message.content
    
"""
LLM이 추천 시간표에 대한 자연어 설명을 생성.

"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

LABEL_MAP = {
    "time": "시간대",
    "gap": "공강/연강",
    "graduation": "졸업요건",
    "style": "학업스타일",
}


def _format_timetable(timetable):
    lines = []
    for c in timetable:
        lines.append(
            f"- {c.get('name','')} ({c.get('day','')}{c.get('period','')}교시, "
            f"{c.get('credit',0)}학점, {c.get('category','')})"
        )
    return "\n".join(lines)


def _format_scores(scores, priority):
    lines = []
    for k in priority:
        lines.append(f"- {LABEL_MAP.get(k, k)}: {scores.get(k, 0)}점")
    return "\n".join(lines)


def build_prompt(timetable, scores, user_pref):
    priority = user_pref.get("priority_ranking", ["time", "gap", "graduation", "style"])
    priority_text = " > ".join([LABEL_MAP.get(k, k) for k in priority])

    return f"""아래 시간표를 사용자에게 추천하는 이유를 자연스럽게 2-3문장으로 설명해주세요.

[추천 시간표]
{_format_timetable(timetable)}

[사용자가 매긴 우선순위]
{priority_text}

[항목별 점수 (0~100)]
{_format_scores(scores, priority)}

작성 가이드:
- 사용자의 1순위 항목이 어떻게 충족됐는지 먼저 언급
- 점수가 낮은 항목이 있다면 솔직히 말해주기
- 친근한 존댓말, 2-3문장 분량
"""


def generate_explanation(timetable, scores, user_pref, model="llama-3.3-70b-versatile"):
    """LLM을 호출해 추천 이유 문장을 반환."""

    if not os.environ.get("GROQ_API_KEY"):
        return "(GROQ_API_KEY 환경변수가 설정되어 있지 않아요)"

    prompt = build_prompt(timetable, scores, user_pref)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "너는 대학생 시간표 추천 결과를 쉽고 정확하게 설명하는 assistant야."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_tokens=400
    )

    return response.choices[0].message.content.strip()
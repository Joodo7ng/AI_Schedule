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
    "gap": "공강",
    "empty_day": "공강",      # 가연님 코드와 호환 (priority_ranking이 'empty_day' 사용)
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


def _format_day_analysis(timetable):
    """실제 시간표에서 공강 요일을 계산해 LLM에 전달.
    LLM이 공강 요일을 자기 멋대로 추측하지 못하게 함."""
    all_days = ["월", "화", "수", "목", "금"]
    used_days = sorted(
        {c.get("day", "") for c in timetable if c.get("day") in all_days},
        key=all_days.index
    )
    free_days = [d for d in all_days if d not in used_days]

    lines = ["[요일 분석 — 사실 그대로 인용할 것]"]
    lines.append(f"- 수업 있는 요일: {', '.join(used_days) if used_days else '없음'}")
    if free_days:
        lines.append(f"- 공강 요일: {', '.join(free_days)} (총 {len(free_days)}일 공강)")
    else:
        lines.append("- 공강 요일: 없음 (월~금 모두 수업)")
    return "\n".join(lines)


def _format_scores(scores, priority):
    lines = []
    for k in priority:
        lines.append(f"- {LABEL_MAP.get(k, k)}: {scores.get(k, 0)}점")
    return "\n".join(lines)


def _format_score_breakdown(scores, priority):
    """가중치 적용 계산식을 줄 단위로 보여줌 (LLM이 그대로 인용할 수 있게)."""
    weights = [0.40, 0.30, 0.20, 0.10]
    weight_labels = ["40%", "30%", "20%", "10%"]
    lines = []
    total = 0.0
    for i, k in enumerate(priority):
        if i >= len(weights):
            break
        score = float(scores.get(k, 0))
        contrib = score * weights[i]
        total += contrib
        lines.append(
            f"- {i+1}순위 {LABEL_MAP.get(k, k)}: {score:.0f}점 × {weight_labels[i]} = {contrib:.2f}점"
        )
    lines.append(f"→ 합계 (종합 점수): {total:.2f}점")
    return "\n".join(lines)


def _normalize_priority_key(k):
    """가연님 코드와 본인 코드의 키 이름 차이 보정.
    priority_ranking은 'empty_day'로, scores dict는 'gap'으로 저장돼서 매칭이 안 되는 문제 해결."""
    return "gap" if k == "empty_day" else k


def build_prompt(timetable, scores, user_pref, weighted_score=None):
    raw_priority = user_pref.get("priority_ranking", ["time", "gap", "graduation", "style"])
    # empty_day → gap 으로 통일 (scores dict 키와 매칭되게)
    priority = [_normalize_priority_key(k) for k in raw_priority]
    priority_text = " > ".join([LABEL_MAP.get(k, k) for k in priority])
    weighted_text = f"{weighted_score}점" if weighted_score is not None else "정보 없음"
    score_breakdown = _format_score_breakdown(scores, priority)

    return f"""대학교 선배가 후배에게 시간표 추천 이유를 친근하게 설명한다고 생각하고, 한국어로 3~4문장 작성해주세요.

[추천 시간표]
{_format_timetable(timetable)}

{_format_day_analysis(timetable)}

[사용자가 매긴 우선순위]
{priority_text}

[항목별 점수 (0~100)]
{_format_scores(scores, priority)}

[종합 점수]
{weighted_text}

## 절대 하지 말아야 할 것 (AI 티남)
1. **"1순위 X, 2순위 Y, 3순위 Z, 4순위 W" 식으로 4개 순위를 줄줄이 나열하지 마세요.** 자연스러운 사람 말투에서는 그렇게 안 함.
2. **"가중치 반영해", "순서대로 합산해", "X점 × Y%" 같은 기계적인 계산 설명 금지.**
3. **"균형 잡힌 구성", "만족도 높은 추천", "생활 리듬과 학업 목표" 같은 영혼 없는 일반론 금지.**
4. **매 답변마다 똑같은 패턴 금지.** "1순위로 두신 X에 맞춰..."로 시작하는 거 한 번이면 충분.
5. 점수 풀이를 모든 항목에 대해 일일이 하지 마세요. 중요한 1~2개만.
6. **영어 변수명(empty_day, gap, time, style, graduation) 절대 출력 금지.** 반드시 한국어로: "공강", "시간대", "학업스타일", "졸업요건".
7. **공강 요일 언급할 때는 위 [요일 분석] 데이터 그대로 사용.** "하루 종일 비는 날 없다"같이 사실과 다르게 말하지 마세요. 공강 요일이 있으면 그 요일을 정확히 명시 (예: "월·화 공강이 잘 잡혔어요").

## 자연스럽게 쓰는 법
- 사용자가 **중요하게 본 항목 1~2개**만 자연스럽게 언급. ("학업스타일하고 공강을 가장 중요하게 보셨던 만큼...")
- 실제 시간표에 들어간 **과목/카테고리를 1~2개 구체적으로 언급**. ("AI융합개론이랑 이산수학 같은 핵심전공도 챙기고")
- 종합 점수는 한 번만 자연스럽게. ("종합 99.54점이라")
- 점수가 낮은 항목이 있으면 솔직히 한 줄. (없으면 생략)
- 마무리는 그 시간표/학기에 맞게 구체적으로. (일반론 금지)

## 예시 출력 (이렇게 사람처럼 써주세요)

[예시 1 — 1학년 2학기, 학업스타일>공강>졸업>시간대, 모두 95~100점, 종합 99.54점]
학업스타일하고 공강을 가장 중요하게 보셨는데, 두 항목 다 만점으로 깔끔하게 맞춰졌어요. 1학년 2학기에 들어야 할 핵심전공인 이산수학·AI융합개론을 챙기면서 필수교양 비판적사고와토론까지 자연스럽게 넣어서, 졸업요건도 97점대로 함께 잘 정리됐고요. 종합 99.54점이라 한 학기 부담 없이 보내실 수 있을 거예요.

[예시 2 — 2학년 1학기, 시간대>공강>졸업>학업스타일, 95/80/60/70, 종합 84점]
1교시 피하고 싶다고 하신 만큼 오전을 최대한 비워뒀어요. 자료구조·인공지능 같은 2학년 핵심전공이 들어갔는데, 졸업요건 점수가 60점으로 좀 낮게 나온 게 아쉬워요. 다음 학기에 핵심교양 한두 개 더 챙기시면 좋을 것 같고, 일단 이번 학기는 원하시던 시간대로 잘 잡혔어요.

[예시 3 — 1학년 1학기, 공강>졸업>학업스타일>시간대, 90/85/75/60, 종합 82.5점]
공강일을 가장 신경 쓰셔서 화·목 공강이 확실하게 잡혔어요. 필수교양인 창조적사고와글쓰기랑 1학년 핵심전공이 골고루 들어가서 졸업요건도 85점으로 함께 잘 챙겨졌고, 종합 82.5점이에요. 시간대 점수가 좀 낮긴 한데 공강 우선이셨으니까 이 정도면 만족스러우실 거예요.

이제 위 예시 톤으로 자연스럽게 써주세요. 절대 "1순위, 2순위, 3순위, 4순위" 같은 기계적 나열 금지.
"""


def generate_explanation(timetable, scores, user_pref, weighted_score=None, model="openai/gpt-oss-120b"):
    """LLM을 호출해 추천 이유 문장을 반환."""

    if not os.environ.get("GROQ_API_KEY"):
        return "(GROQ_API_KEY 환경변수가 설정되어 있지 않아요)"

    prompt = build_prompt(timetable, scores, user_pref, weighted_score=weighted_score)

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
        max_tokens=1500  # GPT-OSS-120B는 reasoning tokens도 쓰므로 여유있게
    )

    explanation = response.choices[0].message.content.strip()

    # 마지막 줄에 챗봇 안내 문구 추가
    explanation += "\n\n더 궁금하신 부분은 챗봇을 통해 물어봐주세요!"

    return explanation
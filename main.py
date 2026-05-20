"""
AI 시간표 추천 시스템 - 메인 진입점.

흐름:
1. CSV 로드
2. 사용자 입력 (UI 연동 전까지는 아래 user_pref 예시로 테스트)
3. recommend() 호출 -> 최고점 시간표 1개
4. LLM이 추천 이유 생성
5. 결과 출력
"""

from data_loader import load_courses
from recommender import recommend
from llm_explainer import generate_explanation, LABEL_MAP


CSV_PATH = "기말 프젝 강의 데이터 (1).csv"


def print_result(result):
    if not result["timetable"]:
        print(f"⚠️  {result.get('warning') or '추천 결과 없음'}")
        return

    print("\n=== 추천 시간표 ===")
    for c in result["timetable"]:
        print(
            f"  {c['day']}{c['period']}교시  "
            f"{c['name']:<24s} "
            f"({c['credit']}학점, {c['category']})"
        )

    total = sum(c["credit"] for c in result["timetable"])
    print(f"\n총 학점: {total}")
    print(f"검토한 조합 수: {result['candidates_count']}개")

    print("\n=== 점수 ===")
    for k, v in result["scores"].items():
        print(f"  {LABEL_MAP.get(k, k)}: {v}점")
    print(f"  >> 가중 합산: {result['weighted_score']}점")

    if result.get("warning"):
        print(f"\n⚠️  {result['warning']}")


def main():
    # 1. 데이터 로드
    courses = load_courses(CSV_PATH)
    print(f"강의 {len(courses)}개 로드 완료")

    # 2. 사용자 입력 예시 (UI에서 받아오면 이 dict만 교체)
    user_pref = {
        # 학생 정보
        "admission_year": 26,           # 26/25/24/23
        "target_semester": 1,           # 1/2
        "major_track": 1,               # 0=미선택, 1=AI, 2=IoT
        "target_credits": 15,
        "required_courses": [],         # 학수번호 리스트 (꼭 듣고 싶은 강의)

        # 우선순위 (1순위 40%, 2순위 30%, 3순위 20%, 4순위 10%)
        "priority_ranking": ["time", "graduation", "gap", "style"],

        # 4가지 항목별 선호
        "time_preference": "오후",         # 오전 / 오후 / 저녁 / 상관없음
        "gap_preference": "원하지 않음",    # 원함 / 원하지 않음 / 상관없음
        "continuous_preference": "선호",    # 선호 / 비선호 / 상관없음
        "exam_types": ["객관식"],          # 객관식/주관식/T/F형/... or ["상관없음"]
        "class_mode": "대면",              # 대면 / 비대면 / 블렌디드 / 상관없음
        "grade_dist": "쁠몰",              # 쁠몰 / 보통 / 상관없음
    }

    # 3. 추천 실행
    result = recommend(courses, user_pref)

    # 4. 결과 출력
    print_result(result)

    # 5. LLM 추천 이유 (API 키 없으면 안내 메시지로 대체)
    if result["timetable"]:
        print("\n=== 추천 이유 ===")
        explanation = generate_explanation(result["timetable"], result["scores"], user_pref)
        print(explanation)


if __name__ == "__main__":
    main()

"""
시간표 추천 메인 엔진.

흐름:
1. filter_courses     : 학기/조건으로 강의 풀 필터링
2. generate_timetables: 시간 충돌 없고 학점 맞는 조합 생성
3. weighted_score     : 빈 점수 4개에 우선순위 가중치(40/30/20/10) 적용
4. recommend          : 위 단계 통합 -> 최고점 1개 반환
"""

from itertools import combinations
from services.score_functions import calculate_all_scores

PRIORITY_WEIGHTS = [0.40, 0.30, 0.20, 0.10]
DEFAULT_PRIORITY = ["time", "gap", "graduation", "style"]


def total_credits(timetable):
    return sum(c.get("credit", 0) for c in timetable)


def has_time_conflict(timetable):
    """(day, period)가 동일하면 충돌. period=0이거나 day가 비면 시간정보 없는 강의로 보고 무시."""
    seen = set()
    for c in timetable:
        day = c.get("day", "")
        period = c.get("period", 0)
        if not day or not period:
            continue
        key = (day, period)
        if key in seen:
            return True
        seen.add(key)
    return False


def has_duplicate_code(timetable):
    """학수번호(code)가 동일한 분반이 같이 들어가 있으면 True.
    같은 과목의 다른 분반(예: 이산수학-1, 이산수학-2)을 동시에 추천하지 않도록 방지."""
    seen_codes = set()
    for c in timetable:
        code = c.get("code", "")
        if not code:
            continue
        if code in seen_codes:
            return True
        seen_codes.add(code)
    return False


def filter_courses(courses, user_pref):
    """절대조건 필터: 학기 매치 + 빈 데이터 제거."""
    target_semester = user_pref.get("target_semester", 1)

    filtered = []
    for c in courses:
        if not c.get("name"):
            continue
        sem = c.get("semester", 0)
        # 0=둘다 개설, 1=1학기만, 2=2학기만
        if sem != 0 and sem != target_semester:
            continue
        filtered.append(c)
    return filtered


def split_required_and_optional(courses, user_pref):
    """필수(자동 포함) 강의와 선택 강의 분리.

    필수 조건:
    - CSV is_required=1 (비사토, 창사글, 전진탐 등)
    - 사용자가 required_courses에 학수번호로 지정한 강의
    """
    required_codes = set(user_pref.get("required_courses", []) or [])

    required = []
    optional = []
    for c in courses:
        if c.get("is_required") == 1 or c.get("code") in required_codes:
            required.append(c)
        else:
            optional.append(c)
    return required, optional

#시간표 후보 생성 
def generate_timetables(
    courses,
    user_pref,
    target_credits_value,
    credit_tolerance=3,
    max_combinations=3000,
    max_optional_size=6,
):
    """시간 충돌 없고 학점 범위 맞는 시간표 조합 생성.

    - target_credits ± credit_tolerance 학점만 허용
    - 조합 폭발 방지를 위해 max_combinations 도달 시 조기 종료
    - 선택 강의는 max_optional_size 개까지만 조합

    반환: (조합 리스트, 경고 메시지 or None)
    """
    required, optional = split_required_and_optional(courses, user_pref)

    if has_time_conflict(required):
        return [], "필수 강의들끼리 시간이 겹쳐서 시간표를 만들 수 없어요"

    required_credits = total_credits(required)
    remaining = target_credits_value - required_credits

    candidates = []

    # 필수만으로 이미 목표 학점 채운 경우
    if remaining <= credit_tolerance:
        candidates.append(list(required))
        if remaining <= -credit_tolerance:
            return candidates, f"필수 강의만으로 {required_credits}학점 (목표 {target_credits_value} 초과)"

    # 선택 강의 조합
    max_r = min(max_optional_size, len(optional))
    stop = False
    for r in range(1, max_r + 1):
        if stop:
            break
        for combo in combinations(optional, r):
            credits = sum(c["credit"] for c in combo) + required_credits
            if abs(credits - target_credits_value) > credit_tolerance:
                continue
            full = list(required) + list(combo)
            # 분반 중복 체크: 같은 과목(code)이 두 개 들어가면 스킵
            if has_duplicate_code(full):
                continue
            if has_time_conflict(full):
                continue
            candidates.append(full)
            if len(candidates) >= max_combinations:
                stop = True
                break

    if not candidates:
        if required:
            return [list(required)], "조건 만족하는 조합이 없어 필수 강의만 반환합니다"
        return [], "조건을 만족하는 시간표가 없어요"

    return candidates, None


def weighted_score(scores, priority_ranking):
    """4개 점수에 우선순위별 가중치(40/30/20/10) 적용해 가중합 반환. 0~100."""
    total = 0.0
    for i, key in enumerate(priority_ranking):
        if i >= len(PRIORITY_WEIGHTS):
            break
        total += scores.get(key, 0) * PRIORITY_WEIGHTS[i]
    return round(total, 2)


def recommend(courses, user_pref):
    """전체 추천 파이프라인. 최고점 시간표 1개 반환."""
    target_credits_value = user_pref.get("target_credits", 15)
    priority = user_pref.get("priority_ranking", DEFAULT_PRIORITY)

    filtered = filter_courses(courses, user_pref)
    timetables, warning = generate_timetables(filtered, user_pref, target_credits_value)

    if not timetables:
        return {
            "timetable": [],
            "scores": {},
            "weighted_score": 0,
            "warning": warning,
            "candidates_count": 0,
        }

    best = None
    best_w = -1.0
    best_scores = None

    for tt in timetables:
        scores = calculate_all_scores(tt, user_pref)
        w = weighted_score(scores, priority)
        if w > best_w:
            best_w = w
            best = tt
            best_scores = scores

    return {
        "timetable": best,
        "scores": best_scores,
        "weighted_score": best_w,
        "warning": warning,
        "candidates_count": len(timetables),
    }
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

#시간표 총학점 계산
def total_credits(timetable):
    return sum(c.get("credit", 0) for c in timetable)

#겹치는 시간대 있는지 검사
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

#목표학기 과목들만 가져오기
def filter_courses(courses, user_pref):
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

def get_credit_composition(timetable):
    major = 0
    required_liberal = 0
    liberal = 0

    for c in timetable:
        category = c.get("category", "").strip()
        credit = int(c.get("credit", 0))
        is_required = int(c.get("is_required", 0))

        if category in ["핵심전공", "심화전공", "전공인정"]:
            major += credit

        elif is_required == 1:
            required_liberal += credit

        elif category in ["공통교양", "핵심교양"]:
            liberal += credit

    return major, required_liberal, liberal


def has_recommended_credit_composition(timetable):
    major, required_liberal, liberal = get_credit_composition(timetable)

    return (
        major >= 9 and
        required_liberal >= 2 and
        liberal >= 6
    )

def normalize_day(day):
    return {
        "월요일": "월",
        "화요일": "화",
        "수요일": "수",
        "목요일": "목",
        "금요일": "금",
        "월": "월",
        "화": "화",
        "수": "수",
        "목": "목",
        "금": "금",
    }.get(day, day)


def time_to_hour(time_str):
    # "14:00" -> 14
    return int(time_str.split(":")[0])


def has_fixed_schedule_conflict(timetable, fixed_schedules):
    for course in timetable:
        course_day = course.get("day")
        course_start = course.get("period")
        course_end = course_start + 2

        for schedule in fixed_schedules:
            schedule_day = schedule.get("day")
            schedule_start = time_to_hour(schedule.get("start_time"))
            schedule_end = time_to_hour(schedule.get("end_time"))

            if course_day != schedule_day:
                continue

            if course_start < schedule_end and course_end > schedule_start:
                return True

    return False

def count_empty_days(timetable):
    weekdays = ["월", "화", "수", "목", "금"]
    used_days = {course.get("day") for course in timetable if course.get("day") in weekdays}
    return len(weekdays) - len(used_days)

# 시간표 후보 생성 (메인엔진)
def generate_timetables(
    courses,
    user_pref,
    target_credits_value,
    fixed_schedules=None,
    credit_tolerance=1,
    max_combinations=3000,
    max_optional_size=8,
):
    if fixed_schedules is None:
        fixed_schedules = []

    required, optional = split_required_and_optional(courses, user_pref)

    if has_time_conflict(required):
        return [], "필수 강의들끼리 시간이 겹쳐서 시간표를 만들 수 없어요"

    if has_duplicate_course(required):
        return [], "필수 강의 중 같은 과목의 분반이 중복되어 시간표를 만들 수 없어요"

    if has_fixed_schedule_conflict(required, fixed_schedules):
        return [], "필수 강의가 개인 일정과 겹쳐서 시간표를 만들 수 없어요"

    required_credits = total_credits(required)
    remaining = target_credits_value - required_credits

    candidates = []

    # 필수만으로 이미 목표 학점 채운 경우
    if remaining <= credit_tolerance:
        if (
            has_core_general_course(required)
            and has_recommended_credit_composition(required)
            and not has_fixed_schedule_conflict(required, fixed_schedules)
        ):
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
            credits = sum(int(c.get("credit", 0)) for c in combo) + required_credits

            if abs(credits - target_credits_value) > credit_tolerance:
                continue

            full = list(required) + list(combo)

            priority_ranking = user_pref.get("priority_ranking", [])
            if priority_ranking and priority_ranking[0] == "gap":
                if count_empty_days(full) < 2:
                    continue

            if has_time_conflict(full):
                    continue

            # 1. 강의끼리 시간 충돌 제거
            if has_time_conflict(full):
                continue

            # 2. 같은 과목 다른 분반 중복 제거
            if has_duplicate_course(full):
                continue

            # 3. 개인 고정 일정과 겹치는 시간표 제거
            if has_fixed_schedule_conflict(full, fixed_schedules):
                continue

            # 4. 교양 포함 조건 확인
            if not has_core_general_course(full):
                continue

            # 5. 추천 학점 구성 확인
            if not has_recommended_credit_composition(full):
                continue

            candidates.append(full)

            if len(candidates) >= max_combinations:
                stop = True
                break

    if not candidates:
        return [], "전공/필수교양/공통·핵심교양 학점 구성을 만족하면서 개인 일정과 겹치지 않는 시간표가 없어요"

    print("우선순위:", user_pref.get("priority_ranking"))
    print("후보 추가:", [c["name"] for c in full], "공강일 수:", count_empty_days(full))
    
    return candidates, None

def weighted_score(scores, priority_ranking):
    """4개 점수에 우선순위별 가중치(40/30/20/10) 적용해 가중합 반환. 0~100."""
    total = 0.0
    for i, key in enumerate(priority_ranking):
        if i >= len(PRIORITY_WEIGHTS):
            break
        total += scores.get(key, 0) * PRIORITY_WEIGHTS[i]
    return round(total, 2)

def tie_break_score(timetable, priority):
    """가중점수까지 완전히 같은 후보들 사이에서 1순위 기준으로 한 번 더 비교."""

    score = 0

    if not timetable:
        return score

    first_priority = priority[0] if priority else None

    # 1. 졸업요건 우선: 전공/공통교양/핵심교양/필수교양 구성이 좋은 쪽
    if first_priority == "graduation":
        major_count = 0
        common_liberal_count = 0
        core_liberal_count = 0
        required_count = 0

        for c in timetable:
            category = c.get("category", "").strip()

            if category in ["핵심전공", "심화전공", "전공인정"]:
                major_count += 1
            elif category == "공통교양":
                common_liberal_count += 1
            elif category == "핵심교양":
                core_liberal_count += 1

            if int(c.get("is_required", 0)) == 1:
                required_count += 1

        score += major_count * 10
        score += common_liberal_count * 6
        score += core_liberal_count * 6
        score += required_count * 8

    # 2. 공강 우선: 실제 공강일 수가 많은 쪽
    elif first_priority == "gap":
        score += count_empty_days(timetable) * 20

        day_count = {}
        for c in timetable:
            day = c.get("day")
            if day:
                day_count[day] = day_count.get(day, 0) + 1

        # 하루에 수업이 너무 몰리면 감점
        max_day_count = max(day_count.values()) if day_count else 0
        score -= max_day_count * 3

    # 3. 시간대 우선: 하루 과목 몰림이 적고, 시간 배치가 균형 있는 쪽
    elif first_priority == "time":
        day_count = {}
        for c in timetable:
            day = c.get("day")
            if day:
                day_count[day] = day_count.get(day, 0) + 1

        max_day_count = max(day_count.values()) if day_count else 0
        used_days = len(day_count)

        score += used_days * 5
        score -= max_day_count * 5

    # 4. 학업스타일 우선: 객관식/대면/보통 성적분포가 많은 쪽
    elif first_priority == "style":
        for c in timetable:
            exam_type = str(c.get("exam_type", ""))
            class_mode = str(c.get("class_mode", ""))
            grade_dist = str(c.get("grade_dist", ""))

            if "객관식" in exam_type:
                score += 4
            if class_mode == "대면":
                score += 3
            if grade_dist == "보통":
                score += 2

    # 5. 완전 동점 방지용
    names = " ".join(c.get("name", "") for c in timetable)
    score += sum(ord(ch) for ch in names) % 10

    return score

def recommend(courses, user_pref):
    """전체 추천 파이프라인. 최고점 시간표 1개 반환."""

    priority_key_map = {
        "graduation": "graduation",
        "time": "time",
        "style": "style",
        "empty_day": "gap",
        "gap": "gap",
    }

    target_credits_value = user_pref.get("target_credits", 15)

    raw_priority = user_pref.get("priority_ranking", DEFAULT_PRIORITY)

    priority = [
        priority_key_map.get(p, p)
        for p in raw_priority
    ]

    user_pref["priority_ranking"] = priority

    filtered = filter_courses(courses, user_pref)

    timetables, warning = generate_timetables(
        filtered,
        user_pref,
        target_credits_value,
        fixed_schedules=user_pref.get("fixed_schedules", [])
    )

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
    best_tie = -1.0

    debug_list = []

    for tt in timetables:
        scores = calculate_all_scores(tt, user_pref)
        w = weighted_score(scores, priority)
        tie = tie_break_score(tt, priority)

        debug_list.append({
            "names": [c["name"] for c in tt],
            "scores": scores,
            "weighted": w,
            "tie": tie
        })

        if w > best_w:
            best_w = w
            best = tt
            best_scores = scores
            best_tie = tie

        elif w == best_w:
            current_tuple = tuple(
                scores.get(p, 0)
                for p in priority
            )

            best_tuple = tuple(
                best_scores.get(p, 0)
                for p in priority
            )

            if current_tuple > best_tuple:
                best = tt
                best_scores = scores
                best_tie = tie

            elif current_tuple == best_tuple:
                if tie > best_tie:
                    best = tt
                    best_scores = scores
                    best_tie = tie

    debug_list = sorted(
        debug_list,
        key=lambda x: (x["weighted"], x["tie"]),
        reverse=True
    )

    print("===== TOP 10 후보 =====")
    for item in debug_list[:10]:
        print("과목:", item["names"])
        print("점수:", item["scores"])
        print("가중점수:", item["weighted"])
        print("동점보정:", item["tie"])
        print("----------------")

    return {
        "timetable": best,
        "scores": best_scores,
        "weighted_score": best_w,
        "warning": warning,
        "candidates_count": len(timetables),
    }


#분반 중복 방지 (ex 자구 -1, -2가 한 시간표안에 들어가지 않게)
def get_base_course_name(name):
    name = str(name).strip()
    if "-" in name:
        return name.rsplit("-", 1)[0]
    return name

def has_duplicate_course(timetable):
    seen = set()

    for c in timetable:
        name = get_base_course_name(c.get("name", ""))

        if not name:
            continue

        if name in seen:
            return True

        seen.add(name)

    return False

def has_core_general_course(timetable):
    return any(
        c.get("category", "").strip() in ["핵심교양", "공통교양"]
        for c in timetable
    )

def has_recommended_credit_composition(timetable):
    major, common_liberal, core_liberal = get_credit_composition(timetable)

    return (
        major >= 9
        and common_liberal >= 2
        and core_liberal >= 3
    )

def get_credit_composition(timetable):
    major = 0
    common_liberal = 0
    core_liberal = 0

    for c in timetable:
        category = c.get("category", "").strip()
        credit = int(c.get("credit", 0))

        if category in ["핵심전공", "심화전공", "전공인정"]:
            major += credit

        elif category == "공통교양":
            common_liberal += credit

        elif category == "핵심교양":
            core_liberal += credit

    return major, common_liberal, core_liberal


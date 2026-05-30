"""
AI융합학부 시간표 추천 점수 함수

* 최종본 받으면 이 파일을 덮어쓰기.

시간표 조합 하나를 입력받아 각 기준별 점수를 0~100점으로 계산한다.
1. 시간대 점수
2. 공강/연강 점수
3. 졸업요건 점수
4. 학업스타일 점수
"""

# =========================
# 0. 기본 설정값
# =========================

MAJOR_NONE = 0
MAJOR_AI = 1
MAJOR_IOT = 2
MAJOR_COMMON = 3

SEMESTER_BOTH = 0
SEMESTER_FIRST = 1
SEMESTER_SECOND = 2

AREA_LIBERAL = 0
AREA_CAREER = 5


# =========================
# 1. 공통 유틸 함수
# =========================

def safe_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_course_name(course):
    return str(course.get("name", "")).strip()


def get_course_category(course):
    return str(course.get("category", "")).strip()


def get_course_credit(course):
    return safe_int(course.get("credit", 0), 0)


def get_course_area(course):
    return safe_int(course.get("area", 0), 0)


def get_course_major_track(course):
    return safe_int(course.get("major_track", 0), 0)


def get_course_period(course):
    return safe_int(course.get("period", 0), 0)


def get_course_day(course):
    return str(course.get("day", "")).strip()


def normalize_category(category):
    category = str(category).strip()
    if category == "전공인정":
        return "핵심전공"
    return category


def get_student_grade_from_admission_year(admission_year):
    admission_year = safe_int(admission_year, 26)
    grade_map = {26: 1, 25: 2, 24: 3, 23: 4}
    return grade_map.get(admission_year, 1)


def get_major_requirement_by_admission_year(admission_year):
    admission_year = safe_int(admission_year, 26)
    if admission_year == 26:
        return {"핵심전공": 24, "심화전공": 18}
    return {"핵심전공": 27, "심화전공": 21}


# =========================
# 2. 시간대 점수
# =========================

def get_time_block(period):
    period = safe_int(period)
    if period == 1:
        return "오전"
    if period in [4, 7, 8]:
        return "오후"

    return "기타"


def score_time_preference(timetable, user_pref):
    preference = user_pref.get("time_preference", "상관없음")

    if preference == "상관없음":
        return 100

    if not timetable:
        return 0

    matched = 0
    total = 0

    for course in timetable:
        period = get_course_period(course)
        block = get_time_block(period)

        if block == "기타":
            continue

        total += 1

        if block == preference:
            matched += 1

    if total == 0:
        return 0

    score = matched / total * 100
    return round(score, 2)


# =========================
# 3. 공강 / 연강 점수
# =========================

def period_to_block_index(period):
    period = safe_int(period)
    mapping = {1: 1, 4: 2, 7: 3, 8: 3}
    return mapping.get(period)


def group_blocks_by_day(timetable):
    result = {}

    for course in timetable:
        day = get_course_day(course)
        period = get_course_period(course)
        block = period_to_block_index(period)

        if not day or block is None:
            continue

        if day not in result:
            result[day] = []

        result[day].append(block)

    for day in result:
        result[day] = sorted(set(result[day]))

    return result


def count_gap_blocks(blocks):
    if len(blocks) <= 1:
        return 0

    blocks = sorted(set(blocks))
    first = min(blocks)
    last = max(blocks)

    total_range = last - first + 1
    actual_count = len(blocks)

    return total_range - actual_count


def count_continuous_blocks(blocks):
    if len(blocks) <= 1:
        return 0

    blocks = sorted(set(blocks))
    count = 0

    for i in range(len(blocks) - 1):
        if blocks[i + 1] - blocks[i] == 1:
            count += 1

    return count


def score_gap_preference(total_gap, gap_preference):
    if gap_preference == "상관없음":
        return 100

    if gap_preference == "원함":
        if total_gap == 0:
            return 40
        if total_gap == 1:
            return 100
        if total_gap == 2:
            return 85
        return 65

    if gap_preference == "원하지 않음":
        if total_gap == 0:
            return 100
        if total_gap == 1:
            return 70
        if total_gap == 2:
            return 40
        return 20

    return 50


def score_continuous_preference(total_continuous, total_days_with_classes, continuous_preference):
    if continuous_preference == "상관없음":
        return 100

    if total_days_with_classes == 0:
        return 0

    continuous_ratio = total_continuous / total_days_with_classes

    if continuous_preference == "선호":
        if continuous_ratio >= 1.5:
            return 100
        if continuous_ratio >= 1.0:
            return 85
        if continuous_ratio >= 0.5:
            return 65
        return 40

    if continuous_preference == "비선호":
        if continuous_ratio == 0:
            return 100
        if continuous_ratio <= 0.5:
            return 75
        if continuous_ratio <= 1.0:
            return 45
        return 20

    return 50

#공강일
def score_empty_day(timetable):
    weekdays = ["월", "화", "수", "목", "금"]

    class_days = set()
    day_course_count = {}

    for course in timetable:
        day = get_course_day(course)
        if day in weekdays:
            class_days.add(day)
            day_course_count[day] = day_course_count.get(day, 0) + 1

    empty_day_count = len(weekdays) - len(class_days)

    # 공강일 기본 점수
    if empty_day_count >= 2:
        score = 90
    elif empty_day_count == 1:
        score = 60
    else:
        score = 20

    # 하루에 수업이 너무 몰리면 감점
    max_courses_per_day = max(day_course_count.values()) if day_course_count else 0

    if max_courses_per_day >= 4:
        score -= 20
    elif max_courses_per_day == 3:
        score -= 10

    return max(0, min(100, score))


#연강/우주공강
def score_gap_and_continuous(timetable, user_pref):
    gap_preference = user_pref.get("gap_preference", "상관없음")
    continuous_preference = user_pref.get("continuous_preference", "상관없음")

    blocks_by_day = group_blocks_by_day(timetable)

    total_gap = 0
    total_continuous = 0
    total_days_with_classes = 0

    for day, blocks in blocks_by_day.items():
        if not blocks:
            continue

        total_days_with_classes += 1
        total_gap += count_gap_blocks(blocks)
        total_continuous += count_continuous_blocks(blocks)

    gap_score = score_gap_preference(total_gap, gap_preference)
    continuous_score = score_continuous_preference(
        total_continuous,
        total_days_with_classes,
        continuous_preference
    )

    final_score = gap_score * 0.5 + continuous_score * 0.5
    return round(final_score, 2)


# =========================
# 4. 졸업요건 점수
# =========================

def get_category_base_score(category):
    category = normalize_category(category)

#수정
    score_map = {
        "공통교양": 95,
        "핵심교양": 95,
        "핵심전공": 95,
        "심화전공": 95,
        "진로소양": 45
    }

    return score_map.get(category, 60)

def get_required_course_bonus(course, user_pref):
    if safe_int(course.get("is_required", 0), 0) == 1:
        return 20

    required_codes = set(user_pref.get("required_courses", []) or [])
    if course.get("code") in required_codes:
        return 20

    return 0

def get_track_score(course, user_pref):
    user_track = safe_int(user_pref.get("major_track", 0), 0)
    course_track = get_course_major_track(course)

    if user_track == 0:
        if course_track == MAJOR_COMMON:
            return 95
        if course_track in [MAJOR_AI, MAJOR_IOT]:
            return 85
        return 75

    if course_track == user_track:
        return 100

    if course_track == MAJOR_COMMON:
        return 95

    if course_track in [MAJOR_AI, MAJOR_IOT]:
        return 75

    return 70


def get_grade_fit_score(course, admission_year):
    student_grade = get_student_grade_from_admission_year(admission_year)
    area = get_course_area(course)

    if area in [AREA_LIBERAL, AREA_CAREER]:
        return 80

    if area == student_grade:
        return 100

    if area < student_grade:
        return 75

    if area > student_grade:
        return 45

    return 60


def score_single_course_study_style(course, user_pref):
    exam_score = score_exam_type(course, user_pref)
    class_mode_score = score_class_mode(course, user_pref)
    grade_dist_score = score_grade_distribution(course, user_pref)

    score = (
        exam_score * 0.40 +
        class_mode_score * 0.30 +
        grade_dist_score * 0.30
    )

    # 과목별 차이를 만들기 위한 추가 보정
    exam_type = str(course.get("exam_type", ""))
    class_mode = str(course.get("class_mode", ""))
    grade_dist = str(course.get("grade_dist", ""))

    if "객관식" in exam_type:
        score += 3
    if "주관식" in exam_type:
        score -= 2
    if "논술형" in exam_type:
        score -= 5
    if "T/F형" in exam_type:
        score += 2

    if class_mode == "블렌디드":
        score -= 3

    if grade_dist == "널널함":
        score += 5
    elif grade_dist == "빡셈":
        score -= 5

    return round(max(0, min(100, score)), 2)

    return min(100, round(score, 2))


def get_graduation_bucket(course):
    """
    강의를 졸업요건 기준으로 분류한다.

    liberal = 교양
    major = 전공
    career = 진로소양
    other = 기타
    """

    category = normalize_category(get_course_category(course))

    if category in ["공통교양", "핵심교양"]:
        return "liberal"

    if category in ["핵심전공", "심화전공"]:
        return "major"

    if category == "진로소양":
        return "career"

    return "other"


def calculate_credit_balance_score(timetable, user_pref):
    """
    교양:전공 비율 점수

    기본 목표:
    교양 6학점
    전공 12학점

    즉, 교양 비율 약 1/3을 이상적으로 본다.
    """

    target_liberal_credits = user_pref.get("target_liberal_credits", 6)
    target_major_credits = user_pref.get("target_major_credits", 12)

    liberal_credits = 0
    major_credits = 0
    career_credits = 0
    total_credits = 0

    for course in timetable:
        credit = get_course_credit(course)
        bucket = get_graduation_bucket(course)

        total_credits += credit

        if bucket == "liberal":
            liberal_credits += credit
        elif bucket == "major":
            major_credits += credit
        elif bucket == "career":
            career_credits += credit

    if total_credits == 0:
        return 0

    # 목표 교양 학점과 얼마나 가까운지
    liberal_gap = abs(liberal_credits - target_liberal_credits)

    # 목표 전공 학점과 얼마나 가까운지
    major_gap = abs(major_credits - target_major_credits)

    # 차이가 적을수록 높은 점수
    liberal_score = max(0, 100 - liberal_gap * 20)
    major_score = max(0, 100 - major_gap * 10)

    # 교양이 아예 없으면 강하게 감점
    if liberal_credits == 0:
        liberal_score = 0

    # 전공이 아예 없으면 강하게 감점
    if major_credits == 0:
        major_score = 0

    balance_score = liberal_score * 0.6 + major_score * 0.4

    return round(balance_score, 2)

def score_graduation_requirement(timetable, user_pref):
    if not timetable:
        return 0

    major_credits = 0
    common_liberal_credits = 0
    core_liberal_credits = 0
    required_credits = 0
    total_credits = 0

    for course in timetable:
        credit = get_course_credit(course)
        category = get_course_category(course)
        is_required = safe_int(course.get("is_required", 0), 0)

        if credit <= 0:
            continue

        total_credits += credit

        if category in ["핵심전공", "심화전공", "전공인정"]:
            major_credits += credit

        elif category == "공통교양":
            common_liberal_credits += credit

        elif category == "핵심교양":
            core_liberal_credits += credit

        if is_required == 1:
            required_credits += credit

    if total_credits == 0:
        return 0

    score = 0

    # 전공 9학점 이상이면 높게 평가
    score += min(major_credits / 9, 1) * 35

    # 공통교양 2학점 이상
    score += min(common_liberal_credits / 2, 1) * 20

    # 핵심교양 3학점 이상
    score += min(core_liberal_credits / 3, 1) * 20

    # 필수교양 포함
    score += min(required_credits / 2, 1) * 15

    # 목표 학점 근접도
    target_credits = safe_int(user_pref.get("target_credits", 15), 15)
    credit_gap = abs(total_credits - target_credits)
    score += max(0, 10 - credit_gap * 5)

    return round(score, 2)


# =========================
# 5. 학업스타일 점수
# =========================

def split_exam_types(exam_type_text):
    if exam_type_text is None:
        return []

    text = str(exam_type_text).strip()

    if not text:
        return []

    text = text.replace("/", ",")
    text = text.replace("·", ",")
    text = text.replace("+", ",")

    return [item.strip() for item in text.split(",") if item.strip()]


def score_exam_type(course, user_pref):
    preferred_exam_types = user_pref.get("exam_types", ["상관없음"])

    if not preferred_exam_types or "상관없음" in preferred_exam_types:
        return 75

    course_exam_types = split_exam_types(course.get("exam_type", ""))

    if not course_exam_types:
        return 50

    matched = 0

    for preferred in preferred_exam_types:
        if preferred in course_exam_types:
            matched += 1

    if matched == 0:
        return 40

    return min(100, 60 + matched * 20)


def score_class_mode(course, user_pref):
    preferred_class_mode = user_pref.get("class_mode", "상관없음")

    if preferred_class_mode == "상관없음":
        return 75
    
    course_class_mode = str(course.get("class_mode", "")).strip()

    if not course_class_mode:
        return 50

    if course_class_mode == preferred_class_mode:
        return 100

    if course_class_mode == "블렌디드":
        return 75

    if preferred_class_mode == "블렌디드":
        return 70

    return 40


def score_grade_distribution(course, user_pref):
    preferred_grade_dist = user_pref.get("grade_dist", "상관없음")

    if preferred_grade_dist == "상관없음":
        return 75

    course_grade_dist = str(course.get("grade_dist", "")).strip()

    if not course_grade_dist:
        return 50

    if course_grade_dist == preferred_grade_dist:
        return 100

    return 45


def score_single_course_study_style(course, user_pref):
    exam_score = score_exam_type(course, user_pref)
    class_mode_score = score_class_mode(course, user_pref)
    grade_dist_score = score_grade_distribution(course, user_pref)

    final_score = (
        exam_score * 0.40 +
        class_mode_score * 0.30 +
        grade_dist_score * 0.30
    )

    return round(final_score, 2)


def score_study_style(timetable, user_pref):
    if not timetable:
        return 0

    total_weighted_score = 0
    total_credits = 0

    for course in timetable:
        credit = get_course_credit(course)

        if credit <= 0:
            continue

        course_score = score_single_course_study_style(course, user_pref)

        total_weighted_score += course_score * credit
        total_credits += credit

    if total_credits == 0:
        return 0

    final_score = total_weighted_score / total_credits
    return round(final_score, 2)


# =========================
# 6. 4개 점수 한 번에 계산
# =========================

def calculate_all_scores(timetable, user_pref):
    return {
        "time": score_time_preference(timetable, user_pref),
        "gap": score_empty_day(timetable),
        "graduation": score_graduation_requirement(timetable, user_pref),
        "style": score_study_style(timetable, user_pref)
    }


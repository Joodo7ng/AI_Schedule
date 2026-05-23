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

GRADUATION_REQUIRED_COURSES = {
    "파이썬 프로그래밍",
    "기초통계학",
    "미적분과벡터해석기초"
}

FIRST_YEAR_FIRST_SEMESTER_REQUIRED = {
    "비판적사고와토론",
    "전공별진로탐색"
}

FIRST_YEAR_SECOND_SEMESTER_REQUIRED = {
    "창조적 사고와 글쓰기"
}


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
    if period == 4:
        return "오후"
    if period in [7, 8]:
        return "저녁"
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


def get_required_course_bonus(course_name, admission_year, target_semester):
    student_grade = get_student_grade_from_admission_year(admission_year)

    if course_name in GRADUATION_REQUIRED_COURSES:
        return 15

    if student_grade == 1 and target_semester == 1:
        if course_name in FIRST_YEAR_FIRST_SEMESTER_REQUIRED:
            return 20

    if student_grade == 1 and target_semester == 2:
        if course_name in FIRST_YEAR_SECOND_SEMESTER_REQUIRED:
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


def score_single_course_graduation(course, user_pref):
    admission_year = safe_int(user_pref.get("admission_year", 26), 26)
    target_semester = safe_int(user_pref.get("target_semester", 1), 1)

    course_name = get_course_name(course)
    category = get_course_category(course)

    category_score = get_category_base_score(category)
    track_score = get_track_score(course, user_pref)
    grade_fit_score = get_grade_fit_score(course, admission_year)
    required_bonus = get_required_course_bonus(
        course_name,
        admission_year,
        target_semester
    )

    score = (
        category_score * 0.50 +
        track_score * 0.30 +
        grade_fit_score * 0.20 +
        required_bonus
    )

    return min(100, round(score, 2))


def score_graduation_requirement(timetable, user_pref):
    if not timetable:
        return 0

    total_weighted_score = 0
    total_credits = 0

    for course in timetable:
        credit = get_course_credit(course)

        if credit <= 0:
            continue

        course_score = score_single_course_graduation(course, user_pref)

        total_weighted_score += course_score * credit
        total_credits += credit

    if total_credits == 0:
        return 0

    final_score = total_weighted_score / total_credits
    return round(final_score, 2)


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
        return 100

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
        return 100

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
        return 100

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
        "gap": score_gap_and_continuous(timetable, user_pref),
        "graduation": score_graduation_requirement(timetable, user_pref),
        "style": score_study_style(timetable, user_pref)
    }
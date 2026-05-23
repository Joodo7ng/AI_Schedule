import csv


def load_courses():
    courses = []

    with open("courses.csv", "r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            courses.append({
                "name": row["name"],
                "day": row["day"],
                "period": int(row["period"]),
                "credit": int(row["credit"]),
                "category": row["category"],
                "difficulty": int(row["difficulty"]),
                "is_required": row["is_required"] == "TRUE"
            })

    return courses


def normalize_weights(priorities):
    total = sum(priorities.values())

    if total == 0:
        return {
            "empty_day": 0.25,
            "morning": 0.25,
            "difficulty": 0.25,
            "graduation": 0.25,
        }

    return {
        key: value / total
        for key, value in priorities.items()
    }


def has_time_conflict(timetable, new_course):
    new_start = new_course["period"]
    new_end = new_course["period"] + new_course["credit"]

    for course in timetable:
        if course["day"] != new_course["day"]:
            continue

        start = course["period"]
        end = course["period"] + course["credit"]

        if new_start < end and new_end > start:
            return True

    return False


def generate_timetables(courses, max_credit):
    results = []

    def backtrack(index, current, credit_sum):
        if credit_sum > max_credit:
            return

        if index == len(courses):
            if credit_sum >= 12:
                results.append(current[:])
            return

        course = courses[index]

        if not has_time_conflict(current, course):
            current.append(course)
            backtrack(index + 1, current, credit_sum + course["credit"])
            current.pop()

        backtrack(index + 1, current, credit_sum)

    backtrack(0, [], 0)
    return results


def calculate_score(timetable, weights):
    days = set(course["day"] for course in timetable)
    empty_day_score = (5 - len(days)) * 25

    morning_count = sum(1 for course in timetable if course["period"] == 1)
    morning_score = max(0, 100 - morning_count * 30)

    avg_difficulty = sum(course["difficulty"] for course in timetable) / len(timetable)
    difficulty_score = max(0, 100 - avg_difficulty * 10)

    required_count = sum(1 for course in timetable if course["is_required"])
    graduation_score = min(100, required_count * 40)

    total_score = (
        empty_day_score * weights["empty_day"] +
        morning_score * weights["morning"] +
        difficulty_score * weights["difficulty"] +
        graduation_score * weights["graduation"]
    )

    return round(total_score, 2)


def make_reason(timetable, score):
    course_names = [course["name"] for course in timetable]

    return (
        f"이 시간표는 총점 {score}점으로 가장 높은 점수를 받은 조합입니다. "
        f"{', '.join(course_names)} 과목이 포함되어 있으며, "
        f"사용자가 설정한 공강, 아침수업 회피, 난이도, 졸업요건 조건을 종합적으로 반영했습니다."
    )


def recommend_timetable(priorities, conditions):
    courses = load_courses()

    if conditions["avoid_first_period"]:
        courses = [
            course for course in courses
            if course["period"] != 1
        ]

    weights = normalize_weights(priorities)
    timetables = generate_timetables(courses, conditions["max_credit"])

    if not timetables:
        return {
            "timetable": [],
            "score": 0,
            "reason": "조건을 만족하는 시간표를 찾지 못했습니다."
        }

    scored = []

    for timetable in timetables:
        score = calculate_score(timetable, weights)
        scored.append({
            "timetable": timetable,
            "score": score,
            "reason": make_reason(timetable, score)
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    return scored[0]


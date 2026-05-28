#수빈님 main.py를 Flask 연결 방식으로 

from services.data_loader import load_courses
from services.recommender import recommend
from services.llm_explainer import generate_explanation

CSV_PATH = "기말 프젝 강의 데이터.csv"


def recommend_timetable(profile, fixed_schedules, priorities, preferences):
    courses = load_courses(CSV_PATH)

    #학년 변수가 csv파일에서는 area인데 제 코드는 grade라서 추가로 넣은 코드입니다
    user_grade = int(profile["grade"])
    target_semester = int(profile["target_semester"])
    user_track = int(profile["major_track"])

    if user_track == 1:      # AI
        allowed_tracks = [0, 1, 3]
    elif user_track == 2:    # IoT
        allowed_tracks = [0, 2, 3]
    else:
        allowed_tracks = [0, 3]

    all_courses = courses  # 폴백용으로 원본 보관

    courses = [
    course for course in courses
    if int(course["semester"]) in [0, target_semester]
    and (
        # 전공 과목: 학년 + 트랙 제한 적용
        (
            int(course["area"]) == user_grade
            and int(course["major_track"]) in allowed_tracks
        )

        # 교양 과목: 학년/트랙 제한 없이 학점 채우기용 허용
        or course["category"] in ["공통교양", "핵심교양"]
    )
]

    # 🆕 폴백: 사용 가능한 총 학점이 목표보다 부족하면 다른 학기 교양으로 보충
    target_credits = int(preferences["target_credits"])
    max_possible = sum(int(c.get("credit", 0)) for c in courses)

    if max_possible < target_credits:
        existing_codes = {c["code"] for c in courses}
        extra_gen_eds = [
            c for c in all_courses
            if c["category"] in ["공통교양", "핵심교양"]
            and c["code"] not in existing_codes
        ]
        courses.extend(extra_gen_eds)
        print(
            f"⚠️ 학점 부족({max_possible}<{target_credits}) "
            f"→ 다른 학기 교양 {len(extra_gen_eds)}개 보충"
        )

    if preferences.get("avoid_first_period", False):
        courses = [
            course for course in courses
            if int(course["period"]) != 1
    ]

    #알고리즘 잘 적용됐는지 확인을 위한 코드
    print("필터 후 과목 수:", len(courses))
    for course in courses:
        print(
            course["name"],
            "area:", course["area"],
            "semester:", course["semester"],
            "track:", course["major_track"]
        )

    user_pref = {
        "admission_year": profile["admission_year"],
        "target_semester": profile["target_semester"],
        "major_track": profile["major_track"],
        "target_credits": preferences["target_credits"],
        "required_courses": preferences.get("required_courses", []),

        "priority_ranking":priorities,
         

        "time_preference": preferences["time_preference"],
        "gap_preference": preferences["gap_preference"],
        "continuous_preference": preferences["continuous_preference"],
        "exam_types": preferences["exam_types"],
        "class_mode": preferences["class_mode"],
        "grade_dist": preferences["grade_dist"],

        # 우리가 추가로 반영해야 할 값
        "fixed_schedules": fixed_schedules,
         "avoid_first_period": preferences.get("avoid_first_period", False)
    }

    result = recommend(courses, user_pref)

    if result["timetable"]:
        result["explanation"] = generate_explanation(
            result["timetable"],
            result["scores"],
            user_pref,
            weighted_score=result.get("weighted_score")
        )
    else:
        result["explanation"] = ""

    return result
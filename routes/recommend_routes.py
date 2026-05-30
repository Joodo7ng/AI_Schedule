from flask import Blueprint, render_template, request, session, redirect, url_for
from services.recommend_service import recommend_timetable
from services.llm_explainer import generate_explanation

recommend_bp = Blueprint("recommend", __name__)


@recommend_bp.route("/priority", methods=["GET", "POST"])
def priority():
    return render_template("priority.html")


@recommend_bp.route("/condition", methods=["GET", "POST"])
def condition():
    if request.method == "GET":
        return render_template("priority.html")

    priority_scores = {
        # 팀원 알고리즘 기준 변수명으로 변환
        "empty_day": int(request.form["empty_day"]),
        "time": int(request.form["morning"]),
        "style": int(request.form["difficulty"]),
        "graduation": int(request.form["graduation"])
    }

    session["priority_scores"] = priority_scores

    print("저장된 슬라이더 점수:", priority_scores)

    return render_template(
        "condition.html",
        priorities={
            "gap": int(request.form["empty_day"]),
            "morning": request.form["morning"],
            "difficulty": request.form["difficulty"],
            "graduation": request.form["graduation"]
        }
    )

@recommend_bp.route("/result", methods=["POST"])
def result():
    priority_scores = session.get("priority_scores")

    if priority_scores is None:
        return redirect(url_for("recommend.priority"))

    saved_profile = session.get("profile")

    if saved_profile is None:
        return redirect(url_for("profile.register_profile"))

    profile = session.get("profile")

    priority_ranking = sorted(
        priority_scores,
        key=priority_scores.get,
        reverse=True
    )

    print("등록된 프로필:", saved_profile)
    print("추천용 프로필:", profile)
    print("추천 우선순위:", priority_ranking)

    fixed_schedules = session.get("user_schedules", [])

    preferences = {
        "target_credits": int(request.form["max_credit"]),
        "required_courses": [],
        "time_preference": "상관없음",
        "gap_preference": "상관없음",
        "continuous_preference": "상관없음",
        "exam_types": ["상관없음"],
        "class_mode": "상관없음",
        "grade_dist": "상관없음",
        "avoid_first_period": "avoid_first_period" in request.form
    }

    result = recommend_timetable(
        profile=profile,
        fixed_schedules=fixed_schedules,
        priorities=priority_ranking,
        preferences=preferences
    )

    explanation = generate_explanation(
        timetable=result.get("timetable", []),
        scores=result.get("scores", {}),
        user_pref={
            "priority_ranking": priority_ranking
        },
        weighted_score=result.get("weighted_score")
    )

    result["explanation"] = explanation
    session["result"] = result

    print("추천 결과 타입:", type(result))
    print("추천 결과:", result)

    return render_template(
        "result.html",
        result=result,
        explanation=explanation
    )

@recommend_bp.route("/register", methods=["POST"])
def register():
    result = session.get("result")

    if result is None:
        timetable = []
    elif isinstance(result, dict):
        timetable = result.get("timetable", [])
    elif isinstance(result, list):
        timetable = result
    else:
        timetable = []

    user_schedules = session.get("user_schedules", [])

    grouped_schedules = {}

    for schedule in user_schedules:
        day = schedule["day"]

        if day not in grouped_schedules:
            grouped_schedules[day] = []

        grouped_schedules[day].append(schedule)
    print(session.get("user_schedules"))

    return render_template(
        "home.html",
        timetable=timetable,
        result=result,
        profile=session.get("profile"),
        user_schedules=user_schedules,
        grouped_schedules=grouped_schedules
    )



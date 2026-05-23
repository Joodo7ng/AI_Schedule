from flask import Blueprint, render_template, request, session, redirect, url_for
from services.recommend_service import recommend_timetable

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
        "gap": int(request.form["empty_day"]),
        "time": int(request.form["morning"]),
        "style": int(request.form["difficulty"]),
        "graduation": int(request.form["graduation"])
    }

    session["priority_scores"] = priority_scores

    print("저장된 슬라이더 점수:", priority_scores)

    return render_template(
        "condition.html",
        priorities={
            "empty_day": request.form["empty_day"],
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

    grade = int(saved_profile["grade"])
    track = saved_profile["track"]

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
        "time_preference": "오후" if "avoid_first_period" in request.form else "상관없음",
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

    print("추천 결과 타입:", type(result))
    print("추천 결과:", result)

    session["result"] = result

    return render_template("result.html", result=result)


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

    return render_template(
        "home.html",
        timetable=timetable,
        result=result,
        profile=session.get("profile"),
        user_schedules=session.get("user_schedules", []),
        grouped_schedules={}
    )


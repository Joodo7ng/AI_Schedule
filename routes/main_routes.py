from flask import Blueprint, render_template, session, redirect, url_for

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    profile = session.get("profile")
    user_schedules = session.get("user_schedules", [])

    # 세션에 저장된 추천 결과 불러오기 (페이지 이동 후에도 시간표 유지)
    result = session.get("result")
    if result and isinstance(result, dict):
        timetable = result.get("timetable", [])
    else:
        timetable = []

    grouped_schedules = {}

    for schedule in user_schedules:
        day = schedule["day"]

        if day not in grouped_schedules:
            grouped_schedules[day] = []

        grouped_schedules[day].append(schedule)

    return render_template(
        "home.html",
        timetable=timetable,
        user_schedules=user_schedules,
        grouped_schedules=grouped_schedules,
        result=result,
        profile=profile
    )

@main_bp.route("/graduation")
def graduation():
    return render_template("graduation.html")
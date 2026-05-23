from flask import Blueprint, render_template, session, redirect, url_for

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    profile = session.get("profile")
    user_schedules = session.get("user_schedules", [])

    grouped_schedules = {}

    for schedule in user_schedules:
        day = schedule["day"]

        if day not in grouped_schedules:
            grouped_schedules[day] = []

        grouped_schedules[day].append(schedule)

    return render_template(
        "home.html",
        timetable=[],
        user_schedules=user_schedules,
        grouped_schedules=grouped_schedules,
        result=None,
        profile=profile
    )

@main_bp.route("/graduation")
def graduation():
    return render_template("graduation.html")
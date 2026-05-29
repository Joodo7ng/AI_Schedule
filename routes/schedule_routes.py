from flask import Blueprint, render_template
from flask import request, redirect, url_for, session

schedule_bp = Blueprint("schedule", __name__)

@schedule_bp.route("/schedule/add", methods=["GET", "POST"])
def add_schedule():
    if request.method == "POST":
        days = request.form.getlist("days")

        start_time = convert_to_24hour(
            request.form["start_ampm"],
            request.form["start_hour"],
            request.form["start_minute"]
        )

        end_time = convert_to_24hour(
            request.form["end_ampm"],
            request.form["end_hour"],
            request.form["end_minute"]
        )

        schedule_type = request.form["schedule_type"]

        user_schedules = session.get("user_schedules", [])

        for day in days:
            user_schedules.append({
                "day": day,
                "start_time": start_time,
                "end_time": end_time,
                "schedule_type": schedule_type
            })

        session["user_schedules"] = user_schedules

        return redirect(url_for("main.home"))

    return render_template("add_schedule.html")


def convert_to_24hour(ampm, hour, minute):
    hour = int(hour)

    if ampm == "PM" and hour != 12:
        hour += 12

    if ampm == "AM" and hour == 12:
        hour = 0

    return f"{hour:02d}:{minute}"


@schedule_bp.route("/delete", methods=["POST"])
def delete_schedule():
    day = request.form.get("day")
    index = int(request.form.get("index"))

    user_schedules = session.get("user_schedules", [])

    day_schedules = [
        schedule for schedule in user_schedules
        if schedule["day"] == day
    ]

    if 0 <= index < len(day_schedules):
        target_schedule = day_schedules[index]
        user_schedules.remove(target_schedule)

    session["user_schedules"] = user_schedules
    session.modified = True

    return redirect(url_for("main.home"))

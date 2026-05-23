from flask import Blueprint, render_template, request, redirect, url_for, session

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/register", methods=["GET", "POST"])
def register_profile():
    if request.method == "GET":
        return render_template("profile_register.html")

    name = request.form.get("name")
    grade = request.form.get("grade")
    track = request.form.get("track")
    student_id = request.form.get("student_id")
    target_semester = request.form.get("target_semester")

    major_track = 1 if track == "AI" else 2
    admission_year = int(student_id[:4])
    #학번에서 입학연도 뽑음

    session["profile"] = {
        "name": name,
        "grade": grade,
        "track": track,
        "student_id": student_id,
        "admission_year": admission_year,
        "target_semester": int(target_semester),
        "major_track": major_track
    }


    return redirect(url_for("main.home"))


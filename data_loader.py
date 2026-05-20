"""
CSV에서 강의 데이터를 읽어 course dict 리스트로 변환.

CSV 컬럼:
- name, code, professor, day, period, area, category,
  class_mode, grade_dist, exam_type, credit
- (추가 요청 예정) major_track, semester, is_required

"""

import csv


def _safe_int(value, default=0):
    try:
        return int(str(value).strip())
    except (ValueError, TypeError, AttributeError):
        return default


def load_courses(csv_path, encoding="euc-kr"):
    """CSV 파일을 읽어 강의 dict 리스트 반환."""
    courses = []

    with open(csv_path, "r", encoding=encoding) as f:
        reader = csv.DictReader(f)

        for row in reader:
            course = {
                "name": (row.get("name") or "").strip(),
                "code": (row.get("code") or "").strip(),
                "professor": (row.get("professor") or "").strip(),
                "day": (row.get("day") or "").strip(),
                "period": _safe_int(row.get("period"), 0),
                "area": _safe_int(row.get("area"), 0),
                "category": (row.get("category") or "").strip(),
                "class_mode": (row.get("class_mode") or "").strip(),
                "grade_dist": (row.get("grade_dist") or "").strip(),
                "exam_type": (row.get("exam_type") or "").strip(),
                "credit": _safe_int(row.get("credit"), 0),
                # 추가 해야할 컬럼 - 없으면 0 default
                "major_track": _safe_int(row.get("major_track"), 0),
                "semester": _safe_int(row.get("semester"), 0),
                "is_required": _safe_int(row.get("is_required"), 0),
            }
            courses.append(course)

    return courses

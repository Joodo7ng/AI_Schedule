from flask import Blueprint, render_template, request, jsonify, session
from services.chatbot_service import get_chatbot_answer
import traceback

chatbot_bp = Blueprint("chatbot", __name__, url_prefix="/chatbot")


@chatbot_bp.route("/", methods=["GET"])
def chatbot_page():
    # 세션에서 챗봇 대화 기록 불러오기
    chatbot_history = session.get("chatbot_history", [])
    return render_template("chatbot.html", chatbot_history=chatbot_history)


@chatbot_bp.route("/reset", methods=["POST"])
def reset_chat():
    """챗봇 대화 기록 초기화"""
    session.pop("chatbot_history", None)
    session.modified = True
    return jsonify({"ok": True})


@chatbot_bp.route("/ask", methods=["POST"])
def ask_chatbot():
    try:
        data = request.get_json()

        if data is None:
            return jsonify({"answer": "요청 데이터가 없습니다."}), 400

        user_message = data.get("message")

        if not user_message:
            return jsonify({"answer": "질문이 비어 있습니다."}), 400

        # 세션에서 프로필 + 추천 결과 + 이전 대화 가져와 챗봇에 전달
        profile = session.get("profile")
        result = session.get("result")
        history = session.get("chatbot_history", [])

        answer = get_chatbot_answer(
            user_message,
            profile=profile,
            recommend_result=result,
            chat_history=history
        )

        # 대화 기록 세션에 저장 (현재 턴 추가)
        history.append({"role": "user", "content": user_message})
        history.append({"role": "bot", "content": answer})
        session["chatbot_history"] = history
        session.modified = True

        return jsonify({"answer": answer})

    except Exception as e:
        print("===== 챗봇 오류 발생 =====")
        traceback.print_exc()
        print("========================")

        return jsonify({
            "answer": "챗봇 처리 중 오류가 발생했습니다: " + str(e)
        }), 500
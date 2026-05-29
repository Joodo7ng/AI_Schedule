from flask import Blueprint, render_template, request, jsonify, session
from services.chatbot_service import get_chatbot_answer
import traceback

chatbot_bp = Blueprint("chatbot", __name__, url_prefix="/chatbot")


@chatbot_bp.route("/", methods=["GET"])
def chatbot_page():
    chatbot_history = session.get("chatbot_history", [])
    return render_template("chatbot.html", chatbot_history=chatbot_history)


@chatbot_bp.route("/reset", methods=["POST"])
def reset_chat():
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

        profile = session.get("profile")
        result = session.get("result")
        history = session.get("chatbot_history", [])

        answer = get_chatbot_answer(
            user_message,
            profile=profile,
            recommend_result=result,
            chat_history=history
        )

        history.append({"role": "user", "content": user_message})
        history.append({"role": "bot", "content": answer})
        session["chatbot_history"] = history
        session.modified = True

        return jsonify({"answer": answer})

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "answer": "챗봇 처리 중 오류가 발생했습니다: " + str(e)
        }), 500
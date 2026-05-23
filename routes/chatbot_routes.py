from flask import Blueprint, render_template, request, jsonify
from services.chatbot_service import get_chatbot_answer
import traceback

chatbot_bp = Blueprint("chatbot", __name__, url_prefix="/chatbot")


@chatbot_bp.route("/", methods=["GET"])
def chatbot_page():
    return render_template("chatbot.html")

@chatbot_bp.route("/ask", methods=["POST"])
def ask_chatbot():
    try:
        data = request.get_json()

        if data is None:
            return jsonify({"answer": "요청 데이터가 없습니다."}), 400

        user_message = data.get("message")

        if not user_message:
            return jsonify({"answer": "질문이 비어 있습니다."}), 400

        answer = get_chatbot_answer(user_message)

        return jsonify({"answer": answer})

    except Exception as e:
        print("===== 챗봇 오류 발생 =====")
        traceback.print_exc()
        print("========================")

        return jsonify({
            "answer": "챗봇 처리 중 오류가 발생했습니다: " + str(e)
        }), 500
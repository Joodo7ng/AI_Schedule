from flask import Flask
from flask_session import Session

from routes.main_routes import main_bp
from routes.recommend_routes import recommend_bp
from routes.chatbot_routes import chatbot_bp
from routes.schedule_routes import schedule_bp
from routes.profile_routes import profile_bp
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "dev-secret-key"

# 세션을 서버 사이드 파일 저장으로 (쿠키 4KB 한계 회피)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./flask_session"
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 7  # 7일 유지
Session(app)


app.register_blueprint(schedule_bp)
app.register_blueprint(main_bp)
app.register_blueprint(recommend_bp)
app.register_blueprint(chatbot_bp)
app.register_blueprint(profile_bp)

print(app.url_map)

if __name__ == "__main__":
    app.run(debug=True)





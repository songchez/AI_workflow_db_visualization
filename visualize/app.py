from flask import Flask, jsonify, render_template
import sqlite3

app = Flask(__name__)
DB_PATH = "./data/Basic_Workflow.db"


# 데이터베이스에서 테이블 간의 관계 추출
def fetch_relationships():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 데이터베이스의 모든 테이블 이름 가져오기
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    nodes = [{"id": table} for table in tables]
    links = []

    # 각 테이블의 외래 키 정보 가져오기
    for table in tables:
        cursor.execute(f"PRAGMA foreign_key_list({table});")
        foreign_keys = cursor.fetchall()
        for fk in foreign_keys:
            source = table
            target = fk[2]  # 외래 키로 참조하는 테이블 이름
            links.append({"source": source, "target": target, "value": 1})

    conn.close()
    return {"nodes": nodes, "links": links}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/data")
def data():
    # 테이블 간의 관계 데이터 반환
    data = fetch_relationships()
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)

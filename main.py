import pandas as pd
import sqlite3
import os
from pathlib import Path
import json

# 기본 경로 설정
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
os.makedirs(DATA_DIR, exist_ok=True)

# 파일 경로 설정
excel_path = DATA_DIR / "Basic (1).xlsx"
db_path = DATA_DIR / "Basic_Workflow.db"


# 데이터베이스 연결
def get_db_connection():
    return sqlite3.connect(db_path)


def create_tables(cursor):
    create_queries = {
        "workflow_nodes": """
            CREATE TABLE IF NOT EXISTS workflow_nodes (
                id INTEGER PRIMARY KEY,
                type TEXT NOT NULL,
                pos_x REAL,
                pos_y REAL,
                size_width REAL,
                size_height REAL,
                flags TEXT,
                order_num INTEGER,
                mode INTEGER DEFAULT 0,
                title TEXT
            );
        """,
        "node_inputs": """
            CREATE TABLE IF NOT EXISTS node_inputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id INTEGER,
                name TEXT,
                type TEXT,
                link_id INTEGER,
                slot_index INTEGER,
                FOREIGN KEY (node_id) REFERENCES workflow_nodes (id)
            );
        """,
        "node_outputs": """
            CREATE TABLE IF NOT EXISTS node_outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id INTEGER,
                name TEXT,
                type TEXT,
                slot_index INTEGER,
                links TEXT,
                FOREIGN KEY (node_id) REFERENCES workflow_nodes (id)
            );
        """,
        "node_properties": """
            CREATE TABLE IF NOT EXISTS node_properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id INTEGER,
                property_name TEXT,
                property_value TEXT,
                FOREIGN KEY (node_id) REFERENCES workflow_nodes (id)
            );
        """,
        "node_widgets": """
            CREATE TABLE IF NOT EXISTS node_widgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id INTEGER,
                widget_name TEXT,
                widget_value TEXT,
                FOREIGN KEY (node_id) REFERENCES workflow_nodes (id)
            );
        """,
        "controller_details": """
            CREATE TABLE IF NOT EXISTS controller_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id INTEGER,
                minimised BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (node_id) REFERENCES workflow_nodes (id)
            );
        """,
        "controller_widgets": """
            CREATE TABLE IF NOT EXISTS controller_widgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id INTEGER,
                widget_name TEXT,
                pinned BOOLEAN DEFAULT FALSE,
                height REAL,
                FOREIGN KEY (node_id) REFERENCES workflow_nodes (id)
            );
        """,
        "workflow_metadata": """
            CREATE TABLE IF NOT EXISTS workflow_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                last_node_id INTEGER,
                last_link_id INTEGER
            );
        """,
    }

    for query in create_queries.values():
        cursor.execute(query)


def insert_workflow_data(conn, json_data):
    try:
        cursor = conn.cursor()

        # 노드 기본 정보 삽입
        for node in json_data["nodes"]:
            # pos, size가 리스트 형태라면 인덱스로 접근
            pos_x = node["pos"][0]
            pos_y = node["pos"][1]
            size_width = node["size"][0]
            size_height = node["size"][1]

            cursor.execute(
                """
                INSERT INTO workflow_nodes 
                (id, type, pos_x, pos_y, size_width, size_height, order_num, title)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    node["id"],
                    node["type"],
                    pos_x,
                    pos_y,
                    size_width,
                    size_height,
                    node["order"],
                    node.get("title", ""),
                ),
            )

            # 입력 포트 정보 삽입
            for input_data in node.get("inputs", []):
                cursor.execute(
                    """
                    INSERT INTO node_inputs (node_id, name, type, link_id)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        node["id"],
                        input_data["name"],
                        input_data["type"],
                        input_data.get("link"),
                    ),
                )

            # 출력 포트 정보 삽입
            for output_data in node.get("outputs", []):
                cursor.execute(
                    """
                    INSERT INTO node_outputs (node_id, name, type, slot_index)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        node["id"],
                        output_data["name"],
                        output_data["type"],
                        output_data["slot_index"],
                    ),
                )

            # 속성 정보 삽입
            for prop_name, prop_value in node["properties"].items():
                if isinstance(prop_value, (str, int, float, bool)):
                    cursor.execute(
                        """
                        INSERT INTO node_properties (node_id, property_name, property_value)
                        VALUES (?, ?, ?)
                    """,
                        (node["id"], prop_name, str(prop_value)),
                    )

            # 위젯 값 삽입
            if "widgets_values" in node:
                for idx, value in enumerate(node["widgets_values"]):
                    cursor.execute(
                        """
                        INSERT INTO node_widgets (node_id, widget_name, widget_value)
                        VALUES (?, ?, ?)
                    """,
                        (node["id"], f"widget_{idx}", str(value)),
                    )

        conn.commit()
        print("워크플로우 데이터가 성공적으로 삽입되었습니다.")

    except Exception as e:
        print(f"워크플로우 데이터 삽입 중 오류 발생: {str(e)}")
        conn.rollback()


def main():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            create_tables(cursor)

            json_path = DATA_DIR / "Basic (1).json"
            if json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    workflow_data = json.load(f)
                    insert_workflow_data(conn, workflow_data)

            # 엑셀 데이터 처리
            excel_data = pd.ExcelFile(excel_path)

            # Define function to clean and insert data into database
            def clean_and_insert(sheet_name, table_name, mapping_columns):
                df = excel_data.parse(sheet_name)
                # 컬럼명을 문자열로 변환 후 strip 적용
                df = df.rename(
                    columns=lambda x: str(x)
                    .strip()
                    .replace("ㆍㆍㆍ", "")
                    .replace(".", "")
                    .strip()
                )
                cleaned_df = df[mapping_columns]
                cleaned_df.to_sql(table_name, conn, if_exists="replace", index=False)

            clean_and_insert(
                "(지정데이터)노드 정보",
                "node_info",
                [
                    "연번",
                    "유형",
                    "용도",
                    "Type",
                    "만든이",
                    "노드명",
                    "Input1",
                    "Input2",
                    "Input3",
                    "Output1",
                    "Output2",
                    "Parameter1",
                    "Parameter2",
                    "Parameter3",
                    "Parameter4",
                    "Parameter5",
                ],
            )

            clean_and_insert(
                "(지정데이터)목록형 파라미터 정보",
                "list_param_info",
                [
                    "파라미터 명칭",
                    "종류",
                    "모델 Hash값(SHA-256)",
                    "특성",
                    "계열",
                    "관련노드1",
                    "관련노드2",
                    "관련노드3",
                ],
            )

            clean_and_insert(
                "(지정데이터)수치형 파라미터 정보",
                "numeric_param_info",
                [
                    "Unnamed: 0",
                    "min",
                    "max",
                    "round",
                    "precision",
                    "step",
                    "org_min",
                    "org_max",
                    "관련노드1",
                    "관련노드2",
                    "관련노드3",
                ],
            )

            clean_and_insert(
                "데이터베이스1(사용노드)",
                "db_nodes",
                ["이미지고유번호", "Unnamed: 1", "1", "2", "3", "4", "5", "6"],
            )

            clean_and_insert(
                "데이터베이스2(사용파라미터_입력부)",
                "input_params",
                ["구분", "이미지고유번호", "Unnamed: 2", "1", "2", "3", "4", "5", "6"],
            )

            conn.commit()

        print(f"SQLite 데이터베이스가 생성되었습니다: {db_path}")

    except Exception as e:
        print(f"오류 발생: {str(e)}")


if __name__ == "__main__":
    main()

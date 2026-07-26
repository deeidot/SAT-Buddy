import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_NAME = str(BASE_DIR / "sat_buddy.db")

DIFFICULTIES = ["Easy", "Medium", "Hard"]

QUESTION_TAXONOMY = {
    "Reading and Writing": {
        "Information and Ideas": [
            "Central Ideas and Details",
            "Command of Evidence (Textual)",
            "Command of Evidence (Quantitative)",
            "Inferences",
        ],
        "Craft and Structure": [
            "Words in Context",
            "Text Structure and Purpose",
            "Cross-Text Connections",
        ],
        "Expression of Ideas": [
            "Rhetorical Synthesis",
            "Transitions",
        ],
        "Standard English Conventions": [
            "Boundaries",
            "Form, Structure, and Sense",
        ],
    },
    "Math": {
        "Algebra": [
            "Linear Equations",
            "Linear Functions",
            "Systems of Linear Equations",
            "Linear Inequalities",
        ],
        "Advanced Math": [
            "Equivalent Expressions",
            "Nonlinear Equations",
            "Nonlinear Functions",
        ],
        "Problem-Solving and Data Analysis": [
            "Ratios, Rates, and Proportions",
            "Percentages",
            "Probability",
            "Data Distributions",
        ],
        "Geometry and Trigonometry": [
            "Area and Volume",
            "Lines, Angles, and Triangles",
            "Right Triangles and Trigonometry",
            "Circles",
        ],
    },
}

SEARCH_BY_ID_TEST_QUESTION = {
    "id": "123456",
    "section": None,
    "domain": "Mock Domain",
    "skill": "Dummy Search by ID Test",
    "difficulty": None,
    "passage": (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer vitae "
        "sem non nibh suscipit dictum. Suspendisse potenti. Donec vehicula, arcu "
        "at pretium finibus, nibh lorem facilisis augue, vitae porta massa justo "
        "id lectus."
    ),
    "answers": [
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco.",
        "Duis aute irure dolor in reprehenderit in voluptate velit esse.",
    ],
    "correct_index": 2,
    "explanation": (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. The best choice "
        "is the one that most directly matches the stated evidence in the passage "
        "while avoiding unsupported assumptions."
    ),
}


def build_demo_question(question_id, section, domain, skill, difficulty):
    if section == "Math":
        passage = (
            f"Dummy {difficulty.lower()} SAT Math question for {skill}. A student is "
            f"working in the {domain} domain and must choose the option that follows "
            "from the given relationship."
        )
        answers = [
            f"{skill} result A",
            f"{skill} result B",
            f"Correct {skill} result",
            f"{skill} result D",
        ]
        explanation = (
            f"This {difficulty.lower()} {skill} question is solved by identifying the "
            f"relevant {domain.lower()} relationship and applying it carefully. Choice C "
            "is correct because it is the only option that follows from the setup."
        )
    else:
        passage = (
            f"Dummy {difficulty.lower()} Reading and Writing passage for {skill}. The "
            "passage presents a short claim, supporting evidence, and one detail that "
            "the question asks the student to interpret."
        )
        answers = [
            f"Unsupported {skill} choice",
            f"Partly related {skill} choice",
            f"Best supported {skill} choice",
            f"Too broad {skill} choice",
        ]
        explanation = (
            f"This {difficulty.lower()} {skill} question asks for the answer best "
            "supported by the passage. Choice C is correct because it stays closest to "
            "the stated evidence without adding extra assumptions."
        )

    return {
        "id": question_id,
        "section": section,
        "domain": domain,
        "skill": skill,
        "difficulty": difficulty,
        "passage": passage,
        "answers": answers,
        "correct_index": 2,
        "explanation": explanation,
    }


def build_mock_questions():
    questions = [SEARCH_BY_ID_TEST_QUESTION]
    next_id = 200001

    for section, domains in QUESTION_TAXONOMY.items():
        for domain, skills in domains.items():
            for skill in skills:
                for difficulty in DIFFICULTIES:
                    questions.append(
                        build_demo_question(
                            str(next_id),
                            section,
                            domain,
                            skill,
                            difficulty,
                        )
                    )
                    next_id += 1

    return questions


MOCK_QUESTIONS = build_mock_questions()


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS questions (
            id TEXT PRIMARY KEY,
            section TEXT,
            domain TEXT,
            skill TEXT,
            difficulty TEXT,
            passage TEXT NOT NULL,
            answers_json TEXT NOT NULL,
            correct_index INTEGER NOT NULL,
            explanation TEXT NOT NULL
        )
        """
    )

    existing_columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(questions)").fetchall()
    }
    if "section" not in existing_columns:
        cursor.execute("ALTER TABLE questions ADD COLUMN section TEXT")
    if "difficulty" not in existing_columns:
        cursor.execute("ALTER TABLE questions ADD COLUMN difficulty TEXT")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_questions_filters ON questions(section, domain, skill, difficulty)")
    cursor.execute("DELETE FROM questions")

    for question in MOCK_QUESTIONS:
        cursor.execute(
            """
            INSERT INTO questions (
                id, section, domain, skill, difficulty, passage, answers_json, correct_index, explanation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question["id"],
                question["section"],
                question["domain"],
                question["skill"],
                question["difficulty"],
                question["passage"],
                json.dumps(question["answers"]),
                question["correct_index"],
                question["explanation"],
            ),
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized.")

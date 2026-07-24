import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_NAME = str(BASE_DIR / "sat_buddy.db")


MOCK_QUESTIONS = [
    {
        "id": "123456",
        "domain": "Mock Domain",
        "skill": "Dummy Search by ID Test",
        "passage": (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer "
            "vitae sem non nibh suscipit dictum. Suspendisse potenti. Donec "
            "vehicula, arcu at pretium finibus, nibh lorem facilisis augue, "
            "vitae porta massa justo id lectus."
        ),
        "answers": [
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            "Ut enim ad minim veniam, quis nostrud exercitation ullamco.",
            "Duis aute irure dolor in reprehenderit in voluptate velit esse.",
        ],
        "correct_index": 2,
        "explanation": (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. The best "
            "choice is the one that most directly matches the stated evidence "
            "in the passage while avoiding unsupported assumptions."
        ),
    },
    {
        "id": "100001",
        "domain": "Math",
        "skill": "Linear Equations",
        "passage": (
            "A line has equation y = 3x + 4. Which value represents the y-value "
            "when x = 2?"
        ),
        "answers": ["6", "8", "10", "12"],
        "correct_index": 2,
        "explanation": (
            "Substitute x = 2 into y = 3x + 4. This gives y = 3(2) + 4 = 10, "
            "so the correct answer is 10."
        ),
    },
    {
        "id": "100002",
        "domain": "Reading and Writing",
        "skill": "Transitions",
        "passage": (
            "The first experiment produced inconsistent measurements. The "
            "research team recalibrated the equipment before beginning the "
            "second trial."
        ),
        "answers": ["However,", "Therefore,", "For example,", "Meanwhile,"],
        "correct_index": 1,
        "explanation": (
            "The second sentence describes an action taken as a result of the "
            "problem in the first sentence. 'Therefore' best signals that "
            "cause-and-effect relationship."
        ),
    },
    {
        "id": "100003",
        "domain": "Math",
        "skill": "Percentages",
        "passage": "A jacket originally costs $80. During a sale, the price is reduced by 25%. What is the sale price?",
        "answers": ["$20", "$55", "$60", "$75"],
        "correct_index": 2,
        "explanation": "A 25% discount on $80 is 0.25 x 80 = 20. Subtracting $20 from $80 gives a sale price of $60.",
    },
    {
        "id": "100004",
        "domain": "Math",
        "skill": "Systems of Equations",
        "passage": "If x + y = 12 and x - y = 4, what is the value of x?",
        "answers": ["4", "6", "8", "10"],
        "correct_index": 2,
        "explanation": "Add the equations to eliminate y: 2x = 16. Dividing by 2 gives x = 8.",
    },
    {
        "id": "100005",
        "domain": "Reading and Writing",
        "skill": "Words in Context",
        "passage": "The scientist's explanation was concise, giving the audience all necessary details without extra commentary.",
        "answers": ["brief but complete", "highly emotional", "difficult to prove", "intentionally vague"],
        "correct_index": 0,
        "explanation": "In context, 'concise' describes an explanation that includes what is needed without unnecessary words. 'Brief but complete' best matches that meaning.",
    },
    {
        "id": "100006",
        "domain": "Math",
        "skill": "Quadratics",
        "passage": "The expression x^2 + 7x + 12 is equivalent to which of the following?",
        "answers": ["(x + 3)(x + 4)", "(x + 2)(x + 6)", "(x - 3)(x - 4)", "(x + 1)(x + 12)"],
        "correct_index": 0,
        "explanation": "The factors of 12 that add to 7 are 3 and 4. Therefore x^2 + 7x + 12 factors as (x + 3)(x + 4).",
    },
    {
        "id": "100007",
        "domain": "Reading and Writing",
        "skill": "Command of Evidence",
        "passage": "A city survey found that bike lane use increased after protected lanes were added downtown. The survey also found that most new riders cited safety as their main reason for biking more often.",
        "answers": [
            "Protected bike lanes may make riders feel safer.",
            "Downtown streets are always safer than suburban streets.",
            "Most city residents now bike every day.",
            "Bike lanes reduce all traffic delays."
        ],
        "correct_index": 0,
        "explanation": "The passage connects protected lanes with increased use and says new riders named safety as the reason. The supported conclusion is that protected lanes may make riders feel safer.",
    },
    {
        "id": "100008",
        "domain": "Math",
        "skill": "Ratios",
        "passage": "A recipe uses 3 cups of flour for every 2 cups of sugar. If 9 cups of flour are used, how many cups of sugar are needed?",
        "answers": ["4", "5", "6", "8"],
        "correct_index": 2,
        "explanation": "The flour amount is multiplied by 3, from 3 cups to 9 cups. Multiply the sugar amount by 3 as well: 2 x 3 = 6 cups.",
    },
    {
        "id": "100009",
        "domain": "Reading and Writing",
        "skill": "Sentence Boundaries",
        "passage": "The telescope collected data for six months ___ researchers then analyzed the images.",
        "answers": ["months researchers", "months, researchers", "months; researchers", "months and, researchers"],
        "correct_index": 2,
        "explanation": "The text joins two independent clauses. A semicolon correctly separates the related complete thoughts.",
    },
    {
        "id": "100010",
        "domain": "Math",
        "skill": "Functions",
        "passage": "For the function f(x) = 2x - 5, what is f(7)?",
        "answers": ["2", "9", "12", "19"],
        "correct_index": 1,
        "explanation": "Substitute 7 for x: f(7) = 2(7) - 5 = 14 - 5 = 9.",
    },
    {
        "id": "100011",
        "domain": "Reading and Writing",
        "skill": "Rhetorical Synthesis",
        "passage": "Notes: Maya Lin designed the Vietnam Veterans Memorial. She was an undergraduate when her design was selected. The memorial uses polished black granite.",
        "answers": [
            "Maya Lin, an undergraduate at the time, designed the Vietnam Veterans Memorial, which uses polished black granite.",
            "Polished black granite is used in memorials and Maya Lin was an undergraduate.",
            "The Vietnam Veterans Memorial was selected by Maya Lin while black granite was polished.",
            "Undergraduates sometimes design memorials, and one memorial is in Vietnam."
        ],
        "correct_index": 0,
        "explanation": "Choice A combines the relevant notes clearly and accurately. The other choices distort relationships or leave out important information.",
    },
    {
        "id": "100012",
        "domain": "Math",
        "skill": "Geometry",
        "passage": "A rectangle has length 12 and width 5. What is its area?",
        "answers": ["17", "30", "34", "60"],
        "correct_index": 3,
        "explanation": "The area of a rectangle is length times width. Here, 12 x 5 = 60.",
    },
    {
        "id": "100013",
        "domain": "Reading and Writing",
        "skill": "Central Ideas",
        "passage": "The passage explains that community gardens can provide fresh produce, create shared spaces, and give residents practical experience with local ecology.",
        "answers": [
            "Community gardens can serve several practical and social purposes.",
            "Community gardens are mainly useful for professional scientists.",
            "Fresh produce is less important than ecology.",
            "Residents rarely participate in shared public spaces."
        ],
        "correct_index": 0,
        "explanation": "The passage lists multiple benefits of community gardens. The best central idea is that they serve several practical and social purposes.",
    },
    {
        "id": "100014",
        "domain": "Math",
        "skill": "Exponents",
        "passage": "Which expression is equivalent to 2^3 x 2^4?",
        "answers": ["2^7", "2^12", "4^7", "4^12"],
        "correct_index": 0,
        "explanation": "When multiplying powers with the same base, add the exponents. So 2^3 x 2^4 = 2^7.",
    },
    {
        "id": "100015",
        "domain": "Reading and Writing",
        "skill": "Transitions",
        "passage": "The museum expected a quiet opening weekend. ___, more than ten thousand visitors arrived in the first two days.",
        "answers": ["For instance", "Instead", "Similarly", "In conclusion"],
        "correct_index": 1,
        "explanation": "The second sentence contrasts with the expectation of a quiet weekend. 'Instead' best signals that contrast.",
    },
    {
        "id": "100016",
        "domain": "Math",
        "skill": "Data Analysis",
        "passage": "The numbers of books read by five students are 3, 4, 4, 6, and 8. What is the median?",
        "answers": ["4", "5", "6", "8"],
        "correct_index": 0,
        "explanation": "The values are already in order. The middle value of 3, 4, 4, 6, and 8 is 4.",
    },
    {
        "id": "100017",
        "domain": "Reading and Writing",
        "skill": "Punctuation",
        "passage": "The author interviewed three experts ___ a biologist, a historian, and a climate scientist.",
        "answers": ["experts", "experts:", "experts;", "experts and"],
        "correct_index": 1,
        "explanation": "A colon can introduce a list after a complete sentence. Here it correctly introduces the three experts.",
    },
    {
        "id": "100018",
        "domain": "Math",
        "skill": "Trigonometry",
        "passage": "In a right triangle, sin(theta) = 3/5. If the hypotenuse is 20, what is the length of the side opposite theta?",
        "answers": ["3", "5", "12", "15"],
        "correct_index": 2,
        "explanation": "Sine equals opposite over hypotenuse. Since 3/5 = opposite/20, the opposite side is 12.",
    },
    {
        "id": "100019",
        "domain": "Reading and Writing",
        "skill": "Logical Completion",
        "passage": "Researchers found that the material remained flexible at low temperatures, suggesting that it could be useful for equipment designed for cold environments.",
        "answers": [
            "The material may work well in cold-weather equipment.",
            "The material cannot be used outside laboratories.",
            "Cold temperatures made the material rigid.",
            "The equipment caused the material to lose flexibility."
        ],
        "correct_index": 0,
        "explanation": "The passage states that the material stayed flexible in cold conditions. That supports the idea that it may work well in cold-weather equipment.",
    },
    {
        "id": "100020",
        "domain": "Math",
        "skill": "Inequalities",
        "passage": "Which value of x satisfies the inequality 2x + 3 > 11?",
        "answers": ["3", "4", "5", "6"],
        "correct_index": 2,
        "explanation": "Subtract 3 from both sides to get 2x > 8, then divide by 2 to get x > 4. Of the choices, 5 satisfies the inequality.",
    },
    {
        "id": "100021",
        "domain": "Reading and Writing",
        "skill": "Text Structure",
        "passage": "The passage first describes a problem faced by urban trees, then explains a method researchers are testing to address that problem.",
        "answers": [
            "It presents a problem and then a possible solution.",
            "It compares two unrelated historical events.",
            "It lists several definitions of one technical term.",
            "It argues that research methods are unnecessary."
        ],
        "correct_index": 0,
        "explanation": "The structure moves from a problem to a method for addressing it. That is a problem-solution structure.",
    },
]


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
            domain TEXT,
            skill TEXT,
            passage TEXT NOT NULL,
            answers_json TEXT NOT NULL,
            correct_index INTEGER NOT NULL,
            explanation TEXT NOT NULL
        )
        """
    )

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_questions_domain_skill ON questions(domain, skill)")

    for question in MOCK_QUESTIONS:
        cursor.execute(
            """
            INSERT OR REPLACE INTO questions (
                id, domain, skill, passage, answers_json, correct_index, explanation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question["id"],
                question["domain"],
                question["skill"],
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

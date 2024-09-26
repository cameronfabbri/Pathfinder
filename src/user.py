"""
"""

from dataclasses import dataclass

from src.database import get_db_connection


@dataclass
class Document:
    document_id: int
    document_type: str
    filename: str
    filepath: str
    upload_date: str
    additional_info: str
    processed: bool


@dataclass
class Strength:
    theme_name: str
    total_score: int
    strength_level: str


class User:
    def __init__(self, user_id, username, session_id):
        self.user_id = user_id
        self.username = username
        self.session_id = session_id
        self.load_user_info()
        self.load_strengths_weaknesses()
        self.load_assessment_responses()
        self.load_user_documents()

    def __str__(self):

        # Format top strengths
        top_strengths_str = "\n".join([
            f"  - {row['theme_name']}: Score {row['total_score']}, Level: {row['strength_level']}"
            for row in self.top_strengths
        ]) if self.top_strengths else "None"

        # Format weaknesses
        weaknesses_str = "\n".join([
            f"  - {row['theme_name']}: Score {row['total_score']}, Level: {row['strength_level']}"
            for row in self.weaknesses
        ]) if self.weaknesses else "None"

        # Format assessment responses
        assessment_responses_str = "\n".join([
            f"Question: {row['statement']}\nAnswer: {row['response']}"
            for row in self.assessment_responses
        ]) if self.assessment_responses else "None"

        user_info = [
            f"First Name: {self.first_name}",
            f"Last Name: {self.last_name}",
            f"Email: {self.email}",
            f"Phone Number: {self.phone_number}",
            f"Address: {self.address}",
            f"City: {self.city}",
            f"State: {self.state}",
            f"Zip Code: {self.zip_code}",
            f"Age: {self.age}",
            f"Gender: {self.gender}",
            f"Ethnicity: {self.ethnicity}",
            f"High School: {self.high_school}",
            f"High School Graduation Year: {self.high_school_grad_year}",
            f"GPA: {self.gpa}",
            f"SAT Score: {self.sat_score}",
            f"ACT Score: {self.act_score}",
            f"Favorite Subjects: {self.favorite_subjects}",
            f"Extracurriculars: {self.extracurriculars}",
            f"Career Aspirations: {self.career_aspirations}",
            f"Preferred Major: {self.preferred_major}",
            f"Other Majors: {self.other_majors}",
            f"Top School: {self.top_school}",
            f"Safety School: {self.safety_school}",
            f"Other Schools: {self.other_schools}",
            f"Top Strengths:\n{top_strengths_str}",
            f"Top Weaknesses:\n{weaknesses_str}",
            #f"Assessment Responses:\n{assessment_responses_str}"
        ]
        return "\n".join(user_info)

    def load_user_info(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE user_id=?", (self.user_id,))
        result = cursor.fetchone()
        if result:
            columns = [column[0] for column in cursor.description]
            for column_name, value in zip(columns, result):
                setattr(self, column_name, value)
        else:
            print(f"No student information found for user ID {self.user_id}")

    def load_user_documents(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT document_id, document_type, filename, filepath, upload_date, additional_info, processed
            FROM user_documents
            WHERE user_id = ?
        ''', (self.user_id,))
        self.documents = [Document(**dict(row)) for row in cursor.fetchall()]

    def add_document(self, document_type, filename, filepath, additional_info=None, processed=False):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_documents (user_id, document_type, filename, filepath, additional_info, processed)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (self.user_id, document_type, filename, filepath, additional_info, processed))
        conn.commit()

        # Reload documents
        self.load_user_documents()

    def load_strengths_weaknesses(self):
        conn = get_db_connection()
        cursor = conn.cursor()

        # Load top strengths
        cursor.execute('''
            SELECT themes.theme_name, theme_results.total_score, theme_results.strength_level
            FROM theme_results
            JOIN themes ON theme_results.theme_id = themes.theme_id
            WHERE theme_results.user_id = ?
            ORDER BY theme_results.total_score DESC
            LIMIT 5
        ''', (self.user_id,))
        self.top_strengths = [
            {
                'theme_name': row['theme_name'],
                'total_score': row['total_score'],
                'strength_level': row['strength_level']
            }
            for row in cursor.fetchall()
        ]

        # Load weaknesses (bottom strengths)
        cursor.execute('''
            SELECT themes.theme_name, theme_results.total_score, theme_results.strength_level
            FROM theme_results
            JOIN themes ON theme_results.theme_id = themes.theme_id
            WHERE theme_results.user_id = ?
            ORDER BY theme_results.total_score ASC
            LIMIT 5
        ''', (self.user_id,))
        self.weaknesses = [
            {
                'theme_name': row['theme_name'],
                'total_score': row['total_score'],
                'strength_level': row['strength_level']
            }
            for row in cursor.fetchall()
        ]

    def load_assessment_responses(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT questions.statement, user_responses.response
            FROM user_responses
            JOIN questions ON user_responses.question_id = questions.question_id
            WHERE user_responses.user_id = ?
        ''', (self.user_id,))
        self.assessment_responses = [
            {
                'statement': row['statement'],
                'response': row['response']
            }
            for row in cursor.fetchall()
        ]

    def get_user_info(self):
        return self.__str__()


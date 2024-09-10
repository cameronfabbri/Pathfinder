"""
"""

from src.database import execute_query, get_db_connection


class User:
    def __init__(self, user_id, username, login_number):
        self.user_id = user_id
        self.username = username
        self.login_number = login_number
        self.load_user_info() 

    def __str__(self):
        user_info_str = (
            f"User: {self.username} \nID: {self.user_id} \nFirst Name: {self.first_name} \nLast Name: {self.last_name}\n" +
            f"Email: {self.email}\nPhone Number: {self.phone_number}\nAge: {self.age}\nGender: {self.gender}\n" +
            f"Ethnicity: {self.ethnicity}\nHigh School: {self.high_school}\nHigh School Grad Year: {self.high_school_grad_year}\n" +
            f"GPA: {self.gpa}\nSAT Score: {self.sat_score}\nACT Score: {self.act_score}\nFavorite Subjects: {self.favorite_subjects}\n" +
            f"Extracurriculars: {self.extracurriculars}\nCareer Aspirations: {self.career_aspirations}\nPreferred Major: {self.preferred_major}\n" +
            f"Clifton Strengths: {self.clifton_strengths}\nPersonality Test Results: {self.personality_test_results}\n" +
            f"Address: {self.address}\nCity: {self.city}\nState: {self.state}\nZip Code: {self.zip_code}\n" +
            f"Intended College: {self.intended_college}\nIntended Major: {self.intended_major}\nLogin Number: {self.login_number}"
        )
        return user_info_str

    def load_user_info(self):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students WHERE user_id=?", (self.user_id,))
            result = cursor.fetchone()
            if result:
                (
                    self.first_name, self.last_name, self.email, self.phone_number, _,
                    self.age, self.gender, self.ethnicity, self.high_school,
                    self.high_school_grad_year, self.gpa, self.sat_score, self.act_score,
                    self.favorite_subjects, self.extracurriculars, self.career_aspirations,
                    self.preferred_major, self.clifton_strengths, self.personality_test_results,
                    self.address, self.city, self.state, self.zip_code, self.intended_college,
                    self.intended_major
                ) = result
            else:
                print(f"No student information found for user ID {self.user_id}")

    def get_user_info(self):
        return self.__str__()

    def save(self):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE students SET 
                    first_name = ?, last_name = ?, email = ?, phone_number = ?, age = ?, gpa = ?, 
                    sat_score = ?, act_score = ?, favorite_subjects = ?, career_aspirations = ?,
                    high_school = ?, high_school_grad_year = ?, ethnicity = ?, 
                    clifton_strengths = ?, personality_test_results = ?, address = ?, 
                    city = ?, state = ?, zip_code = ?, intended_college = ?, intended_major = ?
                WHERE user_id = ?
            ''', (self.first_name, self.last_name, self.email, self.phone_number, self.age, 
                self.gpa, self.sat_score, self.act_score, self.favorite_subjects, 
                self.career_aspirations, self.high_school, self.high_school_grad_year, self.ethnicity, 
                self.clifton_strengths, self.personality_test_results, self.address, 
                self.city, self.state, self.zip_code, self.intended_college, self.intended_major, self.user_id
                )
            )
            conn.commit()

    def add_chat_history(self, message):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO chat_history (user_id, message) VALUES (?, ?)", 
                        (self.user_id, message))
            conn.commit()



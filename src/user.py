"""
"""

from src.database import db_access as dba


class User:
    """
    """

    def __init__(self, user_id, username, session_id):
        """ Initializes the user object. """
        self.user_id = user_id
        self.username = username
        self.session_id = session_id

        self.load_student_info()

        # Loads top and bottom strengths
        self.load_topbot_strengths()

        # Loads assessment questions and responses
        self.load_assessment_responses()

        # Loads the LLM generated summary of the user
        # (doesn't exist on first login until assessment is completed)
        self.summary = dba.load_user_summary(self.user_id)

        # Builds a summary of the user with information we want
        self.build_student_profile()

        # Loads the LLM generated bio of the user
        #self.load_user_bio()

    def load_message_history(self):
        """ Loads the message history of the user. """
        self.message_history = []
        #for (sender, message) in dba.load_message_history(self.user_id):
        #    self.message_history.append({'role': sender, 'content': message})

    def load_student_info(self):
        """ Loads the `students` table - things like name, address, etc. """
        self.student_info = dba.get_student_info(self.user_id)
        for key, value in self.student_info.items():
            setattr(self, key, value)

    def load_topbot_strengths(self):
        """ Loads the top strengths and weaknesses (bot strengths) of the user. """
        self.top_strengths, self.bot_strengths = dba.get_topbot_strengths(self.user_id, k=5)

    def load_assessment_responses(self):
        """ Loads the assessment responses of the user. """
        self.assessment_responses = dba.load_assessment_responses(self.user_id)
        
    def reload_all_data(self):
        """ Reloads the user data from the database. """
        self.load_student_info()
        self.load_topbot_strengths()
        self.load_assessment_responses()
        self.build_student_profile()
        #self.load_message_history()
        self.summary = dba.load_user_summary(self.user_id)

    def build_student_profile(self):
        """
        Builds a markdown formatted bio of the user specifically for the LLM to analyze.
        """
        # Personal Information
        personal_info = f"""
    # Student Profile

    ## Personal Information
    - **First Name:** {self.first_name or 'N/A'}
    - **Last Name:** {self.last_name or 'N/A'}
    - **Age:** {self.age or 'N/A'}
    - **Gender:** {self.gender or 'N/A'}
    - **City:** {self.city or 'N/A'}
    - **State:** {self.state or 'N/A'}
    """

        # Academic Information
        academic_info = f"""
    ## Academic Information
    - **High School:** {self.high_school or 'N/A'}
    - **Graduation Year:** {self.high_school_grad_year or 'N/A'}
    - **GPA:** {self.gpa or 'N/A'}
    - **SAT Score:** {self.sat_score or 'N/A'}
    - **ACT Score:** {self.act_score or 'N/A'}
    - **Favorite Subjects:** {self.favorite_subjects or 'N/A'}
    - **Extracurriculars:** {self.extracurriculars or 'N/A'}
    """

        # Career Aspirations
        career_info = f"""
    ## Career Aspirations
    - **Desired Career:** {self.career_aspirations or 'N/A'}
    - **Preferred Major:** {self.preferred_major or 'N/A'}
    - **Other Majors of Interest:** {self.other_majors or 'N/A'}
    """

        # Assessment Results
        top_strengths = ", ".join([s['theme_name'] for s in self.top_strengths]) if self.top_strengths else 'N/A'
        bot_strengths = ", ".join([w['theme_name'] for w in self.bot_strengths]) if self.bot_strengths else 'N/A'

        assessment_results = f"""
    ## Assessment Results

    ### Top Strengths
    {top_strengths}

    ### Areas for Improvement
    {bot_strengths}
    """

        # Combine all sections
        self.student_md_profile = personal_info + academic_info + career_info + assessment_results

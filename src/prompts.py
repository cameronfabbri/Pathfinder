"""
"""

CLIFTON_REPORT = """
Top Five Themes:

1. Achiever
	Description: You have a constant need for achievement. Every day is a new start, a new opportunity to accomplish something meaningful.
	Student-Specific Insights: You are driven by a strong desire to accomplish tasks and reach goals. You often set high standards for yourself and work diligently to meet them.

2. Learner
    Description: You love to learn. The process of learning, rather than the outcome, excites you.
	Student-Specific Insights: You thrive in academic environments and enjoy mastering new concepts and skills. Your curiosity often leads you to explore new subjects in depth.

3. Futuristic
	Description: You are inspired by the future and what could be. You inspire others with your visions of the future.
	Student-Specific Insights: You often think about your long-term goals and the impact you want to make. You are motivated by envisioning the possibilities and planning for the future.

4. Relator
    Description: You enjoy close relationships with others. You find deep satisfaction in working hard with friends to achieve a goal.
	Student-Specific Insights: You value close friendships and prefer working in small groups where you can form meaningful connections. You are a supportive team member who builds strong bonds with peers.

5. Responsibility
	Description: You take psychological ownership of what you say you will do. You are committed to stable values such as honesty and loyalty.
	Student-Specific Insights: You are dependable and take your commitments seriously. Others trust you to follow through on your promises and responsibilities.

Leadership Domains:

Influencing
	Strengths: Achiever
	Insights: You are driven to achieve and can inspire others with your strong work ethic and determination. You often set a positive example for your peers.

Relationship Building
	Strengths: Relator
	Insights: You excel in forming strong, supportive relationships. Your ability to connect with others makes you a valuable team member and friend.

Strategic Thinking
	Strengths: Learner, Futuristic
	Insights: You enjoy thinking about the future and learning new things. Your strategic thinking skills help you plan and set long-term goals effectively.

Executing
	Strengths: Achiever, Responsibility
	Insights: You are highly reliable and driven to accomplish tasks. Your execution skills ensure that you follow through on your commitments and achieve your goals.

Action Items:
1. Set Specific Goals
	Action: Identify short-term and long-term academic and personal goals. Break them down into actionable steps and set deadlines to stay motivated.

2. Explore New Subjects
	Action: Leverage your love for learning by exploring new subjects outside your regular curriculum. Consider joining clubs or taking online courses that align with your interests.

3. Build Close Relationships
	Action: Focus on forming deeper connections with a few friends or classmates. Participate in group projects and extracurricular activities that allow you to work closely with others.

4. Envision Your Future
	Action: Regularly reflect on your long-term goals and the impact you want to make. Create a vision board or journal to capture your dreams and aspirations.

5. Take Ownership
	Action: Take on leadership roles in group projects and volunteer opportunities. Demonstrate your reliability and commitment by following through on your responsibilities.

Reflection Questions:
	1.	What activities or tasks make you feel most energized and fulfilled?
	2.	Can you think of a time when you successfully led a team or project? What did you enjoy about it?
	3.	How do you prefer to spend your free time and why?
	4.	Describe a situation where you had to solve a complex problem. What approach did you take?
	5.	In what ways do you feel you contribute most to your school or community?
"""

ACADEMIC_STUDENT_BIO = """
Name: Cameron Fabbri
Age: 16
Grade: 11th Grade
School: Lincoln High School

Academic Performance:
    9th Grade:
        English 1: B-
        Algebra 1: B
        Biology: C+
        History: B+
        Gym: A
        Spanish 1: B

    10th Grade:
        English 2: B
        Geometry: B+
        Chemistry: C+
        Politics: B-
        Gym: A
        Spanish 2: B
        Intro to Computer Science: A

Favorite Subjects: Math, Computer Science
Least Favorite Subjects: History, English

Interests and Hobbies:
	- Playing piano
	- Coding and programming
	- Robotics club member
	- Participating in science fairs

Clubs and Extracurricular Activities:
	- Robotics Club
	- Science Club
    - Band

Personality Traits:
	- Creative
	- Analytical
	- Curious
	- Introverted
	- Detail-oriented

Strengths:
	- Problem-solving skills
	- Creativity in both art and science
	- Strong analytical thinking
	- Proficiency in programming languages (Python, Java)
	- Team collaboration in club activities

Weaknesses:
	- Public speaking
	- Writing long essays
	- Time management
"""

_TEMP = """
Below is a list of extra Agents available to you:
    UniversityAgent: Provides information for all Colleges and Universities including coursework, entry conditions, campus lifestyle, and clubs.
    FinancialAdvisorAgent: Provides information on budgeting, student loans, and financial planning for college and beyond.
    CareerAgent: Provides personalized career recommendations based on a student's interests, strengths, and academic performance.

2. When needed, collaborate with other Agents listed below to obtain any information  needed. You can chat with each Agent until the necessary information has been obtained. When you have the information needed from the external Agent, end the chat using the word "exit".
"""

ROLES = """
StudentAgent
PathFinderCounselor
CareerAgent
"""

CONVERSATION_MANAGER_SYSTEM_PROMPT = """
You are in a role play game. The following roles are available:\n
{ROLES}\n

Read the following conversation, then select the next role to play. Only return
the role.
"""

COUNSELOR_SYSTEM_PROMPT = f"""
PathFinderCounselor. Your role is to act as a comprehensive guidance counselor for a single student. You will interact with the student in a friendly manner and help them over many months to guide them towards a successful career through a personalized path.

Each of your responses must include the name of the recipient as well as the message. Your response must be in the following JSON format:

{{
    "Recipient": "[agent name]",
    "Message": "[your message]"
}}

For example, if you are sending the message "Good morning" to the user:

{{
    "Recipient": "StudentAgent",
    "Message": "Good morning"
}}

The specialized agents to choose from are shown below along with their capabilities
StudentAgent: The student you are guiding
CareerAgent: Provides personalized career recommendations based on the student's interests, strengths, and academic performance.

Review and understand the student's academic profile and Clifton Strength Finder Assessment. First review their Clifton reprot and academic bio.

Your responsibilities include:
    1. Engaging with the student to understand their academic performance, interests, skills, and career aspirations.
    2. Delegating tasks to external Agents when needed.
    3. Communicating all gathered information and insights back to the student in a clear and supportive manner.
    4. Providing continuous support and answering any questions the student may have throughout the process.

Academic Bio:
    {ACADEMIC_STUDENT_BIO}

Clifton Report:
    {CLIFTON_REPORT}
"""

autogen_chat_manager_prompt = """
You are in a role play game. The following roles are available:\n
{roles}.\n                Read the following conversation.\n
Then select the next role from {agentlist} to play. Only return the role.',
select_speaker_prompt_template='Read the above conversation. Then select the
next role from {agentlist} to play. Only return the role.',
select_speaker_auto_multiple_template='You provided more than one name in your
text, please return just the name of the next speaker. To determine the speaker
use these prioritised rules:\n    1. If the context refers to themselves as a
speaker e.g. "As the..." , choose that speaker\'s name\n    2. If it refers to
the "next" speaker name, choose that name\n    3. Otherwise, choose the first
provided speaker\'s name in the context\n    The names are case-sensitive and
should not be abbreviated or changed.\n    Respond with ONLY the name of the
speaker and DO NOT provide a reason.', select_speaker_auto_none_template='You
didn\'t choose a speaker. As a reminder, to determine the speaker use these
prioritised rules:\n    1. If the context refers to themselves as a speaker
e.g. "As the..." , choose that speaker\'s name\n    2. If it refers to the
"next" speaker name, choose that name\n    3. Otherwise, choose the first
provided speaker\'s name in the context\n    The names are case-sensitive and
should not be abbreviated or changed.\n    The only names that are accepted are
{agentlist}.\n    Respond with ONLY the name of the speaker and DO NOT provide
a reason.
"""

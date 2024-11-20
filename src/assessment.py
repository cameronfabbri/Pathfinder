"""
File describing the Assessment themes and questions.
"""

# Define the four key domains
domains = [
    ("Executing",),
    ("Influencing",),
    ("Relationship Building",),
    ("Strategic Thinking",)
]

# Define the themes for each domain
themes = [
    (1, "Achiever"), (1, "Arranger"), (1, "Belief"), (1, "Consistency"),
    (1, "Deliberative"), (1, "Discipline"), (1, "Focus"), (1, "Responsibility"), (1, "Restorative"),
    (2, "Activator"), (2, "Command"), (2, "Communication"), (2, "Competition"),
    (2, "Maximizer"), (2, "Self-Assurance"), (2, "Significance"), (2, "Winning Others Over"),
    (3, "Adaptability"), (3, "Connectedness"), (3, "Developer"), (3, "Empathy"),
    (3, "Harmony"), (3, "Includer"), (3, "Individualization"), (3, "Positivity"), (3, "Relator"),
    (4, "Analytical"), (4, "Context"), (4, "Futuristic"), (4, "Ideation"),
    (4, "Input"), (4, "Intellection"), (4, "Learner"), (4, "Strategic")
]


# Define the questions for each theme
questions = [
    # Executing Domain
    (1, "I feel accomplished when I complete tasks on my to-do list."),
    (1, "I set daily goals and work toward them diligently."),
    (1, "I enjoy working hard and pushing myself to reach new heights."),
    (2, "I am good at organizing people and resources to get things done efficiently."),
    (2, "I enjoy managing multiple tasks at once and seeing how everything fits together."),
    (2, "I can quickly adapt when plans change and still make progress."),
    (3, "My personal values strongly influence my decisions."),
    (3, "I feel fulfilled when my work aligns with my core beliefs."),
    (3, "I am passionate about pursuing work that has a positive impact on the world."),
    (4, "I believe everyone should be treated equally and fairly."),
    (4, "I seek to create an environment where fairness is a priority."),
    (4, "I value clear rules and guidelines to ensure consistency in processes."),
    (5, "I tend to be cautious and take time to think through decisions."),
    (5, "I consider risks before committing to a course of action."),
    (5, "I prefer to avoid taking unnecessary chances."),
    (6, "I like structure and prefer working in organized environments."),
    (6, "I thrive when I have routines and schedules to follow."),
    (6, "I am effective at managing time and staying focused on tasks."),
    (7, "I am able to concentrate on important goals and avoid distractions."),
    (7, "I regularly evaluate my progress toward achieving my objectives."),
    (7, "I am disciplined when it comes to pursuing long-term projects."),
    (8, "I take ownership of the commitments I make."),
    (8, "Others can depend on me to follow through on my promises."),
    (8, "I feel a deep sense of obligation to complete my work to a high standard."),
    (9, "I enjoy solving problems and fixing what's broken."),
    (9, "I am drawn to challenges where I can use my problem-solving skills."),
    (9, "I find satisfaction in identifying solutions to complex issues."),
    
    # Influencing Domain
    (10, "I enjoy taking the first step in getting projects started."),
    (10, "I am energized by making decisions and putting plans into action."),
    (10, "I am good at rallying others to move forward on ideas."),
    (11, "I am comfortable taking charge and leading in difficult situations."),
    (11, "I enjoy being in control and influencing outcomes."),
    (11, "I find it natural to step up when leadership is needed."),
    (12, "I enjoy expressing my ideas clearly and effectively."),
    (12, "I like engaging others in discussions and presenting information."),
    (12, "I am good at simplifying complex information to help others understand."),
    (13, "I enjoy comparing my performance to others and striving to win."),
    (13, "I feel motivated by being the best at what I do."),
    (13, "I thrive in environments where success is measured against others."),
    (14, "I focus on improving what is already working well."),
    (14, "I enjoy taking something good and making it great."),
    (14, "I have high standards and push for excellence."),
    (15, "I have confidence in my decisions and trust my instincts."),
    (15, "I am comfortable with risk and making bold choices."),
    (15, "I believe in my ability to succeed, even in uncertain situations."),
    (16, "I want to make a big impact in the world."),
    (16, "I seek recognition for the contributions I make."),
    (16, "I am driven to achieve meaningful success that others notice."),
    (17, "I enjoy meeting new people and building connections quickly."),
    (17, "I am skilled at winning people over to my ideas or perspectives."),
    (17, "I thrive in social settings where I can engage with others."),
    
    # Relationship Building Domain
    (18, "I am comfortable adjusting to changes and being flexible."),
    (18, "I prefer going with the flow rather than rigidly following plans."),
    (18, "I enjoy taking things one day at a time and responding to what comes."),
    (19, "I believe that everything happens for a reason and is interconnected."),
    (19, "I enjoy helping others see how their actions impact the bigger picture."),
    (19, "I value creating strong relationships with people from different backgrounds."),
    (20, "I enjoy helping others grow and reach their full potential."),
    (20, "I find satisfaction in seeing people improve and succeed."),
    (20, "I am patient and encouraging when teaching or coaching others."),
    (21, "I can sense how others are feeling and respond with care."),
    (21, "I am sensitive to the emotions and needs of those around me."),
    (21, "I enjoy providing emotional support and understanding."),
    (22, "I seek to create peace and avoid conflict in relationships."),
    (22, "I am good at finding common ground and mediating disagreements."),
    (22, "I value teamwork and cooperation over competition."),
    (23, "I enjoy bringing people together and making sure no one is left out."),
    (23, "I strive to create an inclusive and welcoming environment for others."),
    (23, "I am sensitive to people who feel excluded and work to involve them."),
    (24, "I see what makes each person unique and value their differences."),
    (24, "I enjoy customizing my approach to suit the individual needs of others."),
    (24, "I am good at recognizing each person's strengths and talents."),
    (25, "I approach life with optimism and enthusiasm."),
    (25, "I enjoy bringing energy and positivity to the people around me."),
    (25, "I focus on the bright side of situations, even in challenging times."),
    (26, "I value deep, meaningful relationships with a few close people."),
    (26, "I enjoy connecting with others on a personal and authentic level."),
    (26, "I prefer quality interactions over superficial connections."),
    
    # Strategic Thinking Domain
    (27, "I enjoy looking at data and evidence to find patterns and solutions."),
    (27, "I prefer logical and fact-based decision-making."),
    (27, "I am good at breaking down complex problems into manageable parts."),
    (28, "I like understanding the history behind events and decisions."),
    (28, "I value learning from the past to make better future choices."),
    (28, "I enjoy exploring how things have evolved over time."),
    (29, "I am inspired by visions of what the future could be."),
    (29, "I enjoy thinking about long-term possibilities and innovations."),
    (29, "I like to imagine how I can shape the future with my actions."),
    (30, "I am constantly coming up with new ideas and perspectives."),
    (30, "I enjoy thinking creatively and exploring different possibilities."),
    (30, "I thrive in environments that encourage innovation and brainstorming."),
    (31, "I love collecting information, facts, and ideas from various sources."),
    (31, "I am curious and enjoy learning about different topics."),
    (31, "I often gather knowledge that may be useful in the future."),
    (32, "I enjoy deep, intellectual conversations and thought-provoking ideas."),
    (32, "I value time spent reflecting and pondering complex issues."),
    (32, "I am energized by exploring philosophical questions and big concepts."),
    (33, "I am passionate about acquiring new knowledge and skills."),
    (33, "I enjoy the process of learning, even more than the outcome."),
    (33, "I am constantly seeking opportunities for personal growth."),
    (34, "I am good at spotting patterns and developing plans to achieve goals."),
    (34, "I enjoy thinking several steps ahead and planning for different scenarios."),
    (34, "I am skilled at quickly assessing the best path forward in complex situations.")
]

theme_questions = {}
for theme, question in questions:
    if theme not in theme_questions:
        theme_questions[theme] = []
    theme_questions[theme].append(question)

# Sample answers for testing
answers = {
    'I feel accomplished when I complete tasks on my to-do list.': 4,
    'I set daily goals and work toward them diligently.': 3,
    'I enjoy working hard and pushing myself to reach new heights.': 4,
    'I am good at organizing people and resources to get things done efficiently.': 3,
    'I enjoy managing multiple tasks at once and seeing how everything fits together.': 4,
    'I can quickly adapt when plans change and still make progress.': 3,
    'My personal values strongly influence my decisions.': 4,
    'I feel fulfilled when my work aligns with my core beliefs.': 5,
    'I am passionate about pursuing work that has a positive impact on the world.': 4,
    'I believe everyone should be treated equally and fairly.': 5,
    'I seek to create an environment where fairness is a priority.': 5,
    'I value clear rules and guidelines to ensure consistency in processes.': 4,
    'I tend to be cautious and take time to think through decisions.': 3,
    'I consider risks before committing to a course of action.': 4,
    'I prefer to avoid taking unnecessary chances.': 3,
    'I like structure and prefer working in organized environments.': 4,
    'I thrive when I have routines and schedules to follow.': 4,
    'I am effective at managing time and staying focused on tasks.': 3,
    'I am able to concentrate on important goals and avoid distractions.': 4,
    'I regularly evaluate my progress toward achieving my objectives.': 4,
    'I am disciplined when it comes to pursuing long-term projects.': 4,
    'I take ownership of the commitments I make.': 5,
    'Others can depend on me to follow through on my promises.': 5,
    'I feel a deep sense of obligation to complete my work to a high standard.': 4,
    'I enjoy solving problems and fixing what\'s broken.': 4,
    'I am drawn to challenges where I can use my problem-solving skills.': 5,
    'I find satisfaction in identifying solutions to complex issues.': 5,
    'I enjoy taking the first step in getting projects started.': 4,
    'I am energized by making decisions and putting plans into action.': 4,
    'I am good at rallying others to move forward on ideas.': 3,
    'I am comfortable taking charge and leading in difficult situations.': 4,
    'I enjoy being in control and influencing outcomes.': 3,
    'I find it natural to step up when leadership is needed.': 4,
    'I enjoy expressing my ideas clearly and effectively.': 4,
    'I like engaging others in discussions and presenting information.': 4,
    'I am good at simplifying complex information to help others understand.': 4,
    'I enjoy comparing my performance to others and striving to win.': 3,
    'I feel motivated by being the best at what I do.': 3,
    'I thrive in environments where success is measured against others.': 3,
    'I focus on improving what is already working well.': 4,
    'I enjoy taking something good and making it great.': 4,
    'I have high standards and push for excellence.': 5,
    'I have confidence in my decisions and trust my instincts.': 4,
    'I am comfortable with risk and making bold choices.': 4,
    'I believe in my ability to succeed, even in uncertain situations.': 4,
    'I want to make a big impact in the world.': 4,
    'I seek recognition for the contributions I make.': 3,
    'I am driven to achieve meaningful success that others notice.': 4,
    'I enjoy meeting new people and building connections quickly.': 3,
    'I am skilled at winning people over to my ideas or perspectives.': 4,
    'I thrive in social settings where I can engage with others.': 3,
    'I am comfortable adjusting to changes and being flexible.': 4,
    'I prefer going with the flow rather than rigidly following plans.': 4,
    'I enjoy taking things one day at a time and responding to what comes.': 3,
    'I believe that everything happens for a reason and is interconnected.': 4,
    'I enjoy helping others see how their actions impact the bigger picture.': 4,
    'I value creating strong relationships with people from different backgrounds.': 4,
    'I enjoy helping others grow and reach their full potential.': 4,
    'I find satisfaction in seeing people improve and succeed.': 4,
    'I am patient and encouraging when teaching or coaching others.': 4,
    'I can sense how others are feeling and respond with care.': 5,
    'I am sensitive to the emotions and needs of those around me.': 5,
    'I enjoy providing emotional support and understanding.': 5,
    'I seek to create peace and avoid conflict in relationships.': 4,
    'I am good at finding common ground and mediating disagreements.': 4,
    'I value teamwork and cooperation over competition.': 4,
    'I enjoy bringing people together and making sure no one is left out.': 5,
    'I strive to create an inclusive and welcoming environment for others.': 4,
    'I am sensitive to people who feel excluded and work to involve them.': 5,
    'I see what makes each person unique and value their differences.': 4,
    'I enjoy customizing my approach to suit the individual needs of others.': 4,
    'I am good at recognizing each person\'s strengths and talents.': 5,
    'I approach life with optimism and enthusiasm.': 4,
    'I enjoy bringing energy and positivity to the people around me.': 4,
    'I focus on the bright side of situations, even in challenging times.': 4,
    'I value deep, meaningful relationships with a few close people.': 4,
    'I enjoy connecting with others on a personal and authentic level.': 4,
    'I prefer quality interactions over superficial connections.': 4,
    'I enjoy looking at data and evidence to find patterns and solutions.': 4,
    'I prefer logical and fact-based decision-making.': 5,
    'I am good at breaking down complex problems into manageable parts.': 5,
    'I like understanding the history behind events and decisions.': 3,
    'I value learning from the past to make better future choices.': 4,
    'I enjoy exploring how things have evolved over time.': 3,
    'I am inspired by visions of what the future could be.': 4,
    'I enjoy thinking about long-term possibilities and innovations.': 4,
    'I like to imagine how I can shape the future with my actions.': 4,
    'I am constantly coming up with new ideas and perspectives.': 4,
    'I enjoy thinking creatively and exploring different possibilities.': 4,
    'I thrive in environments that encourage innovation and brainstorming.': 4,
    'I love collecting information, facts, and ideas from various sources.': 4,
    'I am curious and enjoy learning about different topics.': 4,
    'I often gather knowledge that may be useful in the future.': 4,
    'I enjoy deep, intellectual conversations and thought-provoking ideas.': 4,
    'I value time spent reflecting and pondering complex issues.': 4,
    'I am energized by exploring philosophical questions and big concepts.': 4,
    'I am passionate about acquiring new knowledge and skills.': 5,
    'I enjoy the process of learning, even more than the outcome.': 5,
    'I am constantly seeking opportunities for personal growth.': 5,
    'I am good at spotting patterns and developing plans to achieve goals.': 4,
    'I enjoy thinking several steps ahead and planning for different scenarios.': 4,
    'I am skilled at quickly assessing the best path forward in complex situations.': 4
}
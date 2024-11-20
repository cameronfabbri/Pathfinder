"""
"""
from src.database.db_access import execute_query

# Show tables in the database
#cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
#tables = cursor.fetchall()
#for table in tables:
#    print(table[0])
#print('\n', '='*100, '\n')
#print('\n')

#cursor.execute(f"SELECT * FROM students where user_id={user_id};")
#users_data = cursor.fetchall()
#print("Students Table:")
#for user in users_data:
#    print(user)
#print('\n', '='*100, '\n')
#print('\n')

#cursor.execute("SELECT summary FROM chat_summary WHERE user_id=? ORDER BY id DESC;", (user.user_id,))
queries = [
    "SELECT * FROM conversation_history;",
    "SELECT * FROM domains;",
    "SELECT * FROM themes;",
    "SELECT * FROM questions;",
    "SELECT * FROM user_responses;",
    "SELECT * FROM theme_results;",
]
for query in queries:
    print(query)
    res = execute_query(query)
    for row in res:
        for key in row.keys():
            print(key, ':', row[key])
        print(50*'-')
    print('\n', '='*100, '\n')
    exit()

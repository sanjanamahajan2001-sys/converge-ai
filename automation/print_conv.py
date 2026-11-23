import psycopg2

conn = psycopg2.connect(dbname="converge_ai_db", user="postgres")
cur = conn.cursor()
cur.execute("""
    SELECT turn_index, sender_type, content, created_at 
    FROM core.messages 
    WHERE conversation_id = '5a47834c-56a5-4b3e-9ff7-c4068631e3fb' 
    ORDER BY turn_index ASC;
""")
rows = cur.fetchall()
for r in rows:
    print(f"--- Turn #{r[0] + 1} ({r[1]}): {r[2]}")

import sqlite3

conn = sqlite3.connect('knowledge/manual_db.sqlite')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM experiments')
print('Experiments count:', cur.fetchone()[0])

query = 'pacemaker'
cur.execute('''
    SELECT c.exp_number, c.section, c.page_start, c.page_end, 
           snippet(manual_chunks_fts, 1, '[MATCH]', '[/MATCH]', '...', 15) 
    FROM manual_chunks_fts 
    JOIN manual_chunks c ON manual_chunks_fts.rowid = c.id 
    WHERE manual_chunks_fts MATCH ? 
    LIMIT 3
''', (query,))
for r in cur.fetchall():
    print('FTS Hit:', r[0], r[1], f'Pages {r[2]}-{r[3]}:', r[4].replace('\n', ' '))

query2 = '"truth table"'
cur.execute('''
    SELECT c.exp_number, c.section, c.page_start, c.page_end, 
           snippet(manual_chunks_fts, 1, '[MATCH]', '[/MATCH]', '...', 15) 
    FROM manual_chunks_fts 
    JOIN manual_chunks c ON manual_chunks_fts.rowid = c.id 
    WHERE manual_chunks_fts MATCH ? 
    LIMIT 3
''', (query2,))
for r in cur.fetchall():
    print('FTS Hit:', r[0], r[1], f'Pages {r[2]}-{r[3]}:', r[4].replace('\n', ' '))
conn.close()

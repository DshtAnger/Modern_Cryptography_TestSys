import MySQLdb,sys
conn=MySQLdb.connect(host='localhost',user='root',passwd='root',db='xxx',port=3306)
cur=conn.cursor()

#for i in xrange(1,40):
#filename = '18'+'.txt'
filename = sys.argv[1]
f = open("/home/your_name/Desktop/banks/"+filename,"r")
res = f.readline()

while res!='end\r\n':    
    problem_block = []
    while res!="\r\n":
        problem_block.append(res.strip())
        res = f.readline()
    
    if problem_block[0]!="Fill in the blanks" and problem_block[0]!="Program question":
        insert_value = (problem_block[0],problem_block[1],problem_block[2],";".join(problem_block[3:-1]),problem_block[-1])
    else:
        insert_value = (problem_block[0],problem_block[1],problem_block[2],"",problem_block[3])

    cur.execute('insert into examination_problems(stem_type,difficulty_degree,stem,options,answer) values(%s,%s,%s,%s,%s)',insert_value)
    conn.commit()
    res = f.readline()
print '[+]Finished import '+filename+' into database'

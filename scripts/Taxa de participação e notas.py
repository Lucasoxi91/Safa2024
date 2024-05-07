from flask import Flask, render_template_string
import psycopg2

def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(
            host="ec2-3-224-58-73.compute-1.amazonaws.com",
            database="de84slt1iucctv",
            user="adaptativa_read",
            password="pe71d6441e182e2458c5fd7701d60d1d0023f68f74dbd0ea0f8e1211d05a14374",
            port="5432"
        )
    except Exception as e:
        print(f"Falha na conexão ao banco de dados: {e}")
    return conn

def execute_query():
    conn = get_db_connection()
    if conn is not None:
        try:
            with conn.cursor() as cur:
                cur.execute("""
WITH QuizData AS (
	select 
	i.name as curso,
	ic2.name as escola,
	ic2.id as escola_id,
	q.name as simulado,
	count( users.id) as n_user_id
	,avg(qg.average) as grade_avg
	from quiz_user_progresses qup  
	inner join users on qup.user_id =  users.id 
	inner join quizzes q on  qup.quiz_id = q.id
	inner join institution_enrollments ie on  qup.user_id = ie.user_id
	inner join institution_classrooms ic on ic.id =ie.classroom_id  
	inner join institution_levels il on il.id = ic.level_id 
	inner join institution_courses ic3 on ic3.id = il.course_id 
	inner join institution_colleges ic2 on ic2.id =  ic3.institution_college_id  and ic2.id = ie.college_id 
	inner join institutions i on i.id = ic2.institution_id  
	inner join regions r on ic2.region_id =r.id 
	inner join cities c on c.id =r.city_id 
	inner join institutions_quizzes iq on iq.institution_id =i.id and iq.quiz_id = q.id
	inner join quiz_grades qg on qg.user_id = users.id and qg.quiz_id = q.id 
	where qup.finished = true and qup.quiz_id in (
	  select iq.quiz_id  from institutions_quizzes iq where iq.institution_id in (
		select distinct  i.id --, i.name,i.slug 
		from institutions i 
		inner join institution_colleges ic on ic.institution_id = i.id 
		where i.holding_id =157 --safa
		and ic.region_id =1063 -- tauá-CE
		and ic.year =2023
	  )
	)
	and ic2.year =2023
	group by curso, escola, escola_id, simulado 
	order by curso, escola, escola_id, simulado
), EnrollmentData AS (
	select  
	i.name as curso,
	count(ie.user_id) as matriculados,
	ic2.name as escola,
	ic2.id as escola_id
	from institution_classrooms ic 
	inner join institution_levels il on il.id = ic.level_id 
	inner join institution_courses ic3 on ic3.id = il.course_id 
	inner join institution_colleges ic2 on ic2.id =  ic3.institution_college_id  
	inner join institutions i on i.id =  ic2.institution_id  
	inner join regions r on ic2.region_id =r.id 
	inner join cities c on c.id =r.city_id 
	inner join institution_enrollments ie on ie.institution_id =i.id and ie.classroom_id =ic.id and ie.college_id =ic2.id 
	--where  i.id in (244,280,321,246,284,322,324,245,287,323,325,326,247,283,285,286,327,330,331)
	where  i.id in (
		select distinct  i.id --, i.name,i.slug 
		from institutions i 
		inner join institution_colleges ic on ic.institution_id = i.id 
		where i.holding_id =157 --safa
		and ic.region_id =1063 -- tauá-CE
		and ic.year =2023
	)
	and ic2.year =2023
	--and ic2.id = 2509 -- CENTRO EDUCACIONAL BETESDA (for debug)
	group by curso, escola, escola_id
	order by curso, escola, escola_id
)
SELECT 
    qd.curso,
    qd.escola_id,
    qd.escola,
    qd.simulado,
    qd.n_user_id as finalizaram,
    ed.matriculados,
    CASE WHEN ed.matriculados > 0 then ( CAST(qd.n_user_id AS FLOAT) / ed.matriculados )* 100 ELSE NULL END AS participation,
	CASE WHEN (CASE WHEN ed.matriculados > 0 then ( CAST(qd.n_user_id AS FLOAT) / ed.matriculados )* 100 ELSE NULL END) > 60 THEN TRUE ELSE FALSE END as filter_data
	,qd.grade_avg
FROM QuizData qd
inner JOIN EnrollmentData ed ON qd.curso = ed.curso AND qd.escola_id = ed.escola_id
ORDER BY qd.curso, qd.escola, qd.simulado;





                """)
                column_names = [desc[0] for desc in cur.description]
                results = cur.fetchall()
                return (column_names, results)
        except Exception as e:
            print(f"Falha na execução da consulta: {e}")
        finally:
            conn.close()
    return ([], [])  # Retorna listas vazias se a conexão falhar ou ocorrer uma exceção

app = Flask(__name__)

@app.route('/')
def index():
    column_names, query_results = execute_query()
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Resultados da Consulta</title>
        <style>
            body {
                font-family: 'Arial', sans-serif;
                margin: 0;
                padding: 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                background-color: #f5f5f5;
            }
            .header-container {
                text-align: center;
                margin: 20px;
            }
            .table-container {
                width: 80%;
                max-width: 1000px;
                box-shadow: 0 2px 3px rgba(0,0,0,0.1);
                background-color: #fff;
                margin: 20px 0;
            }
            table {
                border-collapse: collapse;
                width: 1000px;
            }
            th, td {
                text-align: center;
                padding: 10px;
                font-size: 16px;
                width: 25px

            }
            th {
                background-color: #007bff;
                color: white;
            }
            tr:nth-child(even) {background-color: #f2f2f2;}
        </style>
    </head>
    <body>
        <h1>Quantidade de Alunos Acessando</h1>
        <table>
            <thead>
                <tr>
                    {% for col_name in column_names %}
                    <th>{{ col_name }}</th>
                    {% endfor %}
                </tr>
            </thead>
            <tbody>
                {% for row in query_results %}
                <tr>
                    {% for cell in row %}
                    <td>{{ cell }}</td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </body>
    </html>
    """
    return render_template_string(html_template, column_names=column_names, query_results=query_results)

if __name__ == "__main__":
    app.run(debug=True)







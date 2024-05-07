from flask import Flask, render_template, request
import os
import importlib.util
import random
import psycopg2


app = Flask(__name__)
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), 'scripts')

# Define uma paleta de cores mais extensa, caso necessário
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

def list_scripts():
    """Lista os scripts Python disponíveis na pasta 'scripts'."""
    return [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.py')]

def execute_script(script_name):
    """Executa a função 'execute_query' do script selecionado e retorna seus resultados."""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    spec = importlib.util.spec_from_file_location("module.name", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute_query()  # Supõe que execute_query retorna uma lista de tuplas


def get_db_connection():
    return psycopg2.connect(
        host="ec2-3-224-58-73.compute-1.amazonaws.com",
        database="de84slt1iucctv",
        user="adaptativa_read",
        password="pe71d6441e182e2458c5fd7701d60d1d0023f68f74dbd0ea0f8e1211d05a14374",
        port="5432"
    )

def fetch_pie_chart_data():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
          WITH AlunosSimulado AS (
    SELECT 
        c.name AS cidade,
        COUNT(DISTINCT users.id) AS alunos_finalizados
    FROM 
        quiz_user_progresses qup  
    INNER JOIN users ON users.id = qup.user_id 
    INNER JOIN quizzes q ON q.id = qup.quiz_id 
    INNER JOIN institution_enrollments ie ON ie.user_id = qup.user_id 
    INNER JOIN institution_classrooms ic ON ic.id = ie.classroom_id  
    INNER JOIN institution_levels il ON il.id = ic.level_id 
    INNER JOIN institution_courses ic3 ON ic3.id = il.course_id 
    INNER JOIN institution_colleges ic2 ON ic2.id = ic3.institution_college_id AND ic2.id = ie.college_id 
    INNER JOIN institutions i ON i.id = ic2.institution_id  
    INNER JOIN regions r ON ic2.region_id = r.id 
    INNER JOIN cities c ON c.id = r.city_id 
    WHERE qup.finished = TRUE 
    AND i.name ILIKE '%2024%'
    AND c.name = 'Tauá' -- Filtro específico para a cidade de Tauá
    GROUP BY c.name
),
TodosAlunosMatriculados AS (
    SELECT 
        c.name AS cidade,
        COUNT(DISTINCT ie.user_id) AS alunos_matriculados
    FROM 
        institution_enrollments ie
    INNER JOIN institution_classrooms ic ON ic.id = ie.classroom_id  
    INNER JOIN institution_levels il ON il.id = ic.level_id 
    INNER JOIN institution_courses ic3 ON ic3.id = il.course_id 
    INNER JOIN institution_colleges ic2 ON ic2.id = ic3.institution_college_id 
    INNER JOIN institutions i ON i.id = ic2.institution_id
    INNER JOIN regions r ON ic2.region_id = r.id 
    INNER JOIN cities c ON c.id = r.city_id 
    WHERE i.name ILIKE '%2024%'
    AND c.name = 'Tauá' -- Filtro específico para a cidade de Tauá
    GROUP BY c.name
)
SELECT 
    A.cidade,
    COALESCE(A.alunos_finalizados, 0) AS "total finalizados",
    COALESCE(T.alunos_matriculados, 0) AS "total matriculados"
FROM 
    TodosAlunosMatriculados T
FULL OUTER JOIN AlunosSimulado A 
    ON T.cidade = A.cidade
WHERE 
    A.cidade = 'Tauá' -- Garantindo que apenas resultados para Tauá sejam exibidos
ORDER BY A.cidade; -- Ordenado por cidade, embora seja redundante para uma única cidade

            """)
            result = cur.fetchone()  # Pega apenas a primeira linha
            if result:
                return {'labels': ['Total de Simulados Finalizados', 'Total de Alunos Matriculados'],
                        'data': [result[1], result[2]]}
    except Exception as e:
        print(f"Erro ao executar consulta SQL: {e}")
    finally:
        conn.close()
    return {'labels': [], 'data': []}

@app.route('/')
def index():
    # Carrega scripts para outros usos, se necessário
    scripts = list_scripts()
    pie_chart_data = fetch_pie_chart_data()  # Dados para o gráfico de pizza
    return render_template('index.html', scripts=scripts, pie_chart_data=pie_chart_data)


@app.route('/execute', methods=['GET'])
def execute():
    script_name = request.args.get('script')
    display_mode = request.args.get('display', 'tabela')

    if script_name in list_scripts():
        column_names, query_results = execute_script(script_name)

        if display_mode != 'tabela':
            # Extração de categorias e valores
            categories = [row[1] for row in query_results]  # Primeira coluna para categorias
            values = [row[2] for row in query_results]  # Segunda coluna para valores

            # Dados para Plotly.js
            data = {
                'labels': categories,
                'datasets': [{
                    'label': column_names[1],  # Assumindo que o nome da segunda coluna representa os valores
                    'data': values,
                   }]
            }
            return render_template('grafico.html', script_name=script_name, data=data, display_mode=display_mode)
        else:
            return render_template('tabela.html', column_names=column_names, query_results=query_results)
    else:
        return "Script not found", 404

if __name__ == '_main_':  # Corrigido para usar duas underlines de cada lado
    app.run(debug=True)

from flask import Flask, render_template, request
import os
import importlib.util
import random

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

@app.route('/')
def index():
    scripts = list_scripts()
    return render_template('index.html', scripts=scripts)

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
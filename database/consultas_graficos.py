import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from database.conexao import connectDatabase

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAFICOS_DIR = os.path.join(ROOT_DIR, 'data', 'graficos')
os.makedirs(GRAFICOS_DIR, exist_ok=True)


def reportSubjectPerformance(exibir=False):
    con = connectDatabase()
    cur = con.cursor()
    sql = """
        SELECT d.nome || ' ' || d.frente AS disciplina_frente,
               COUNT(r.id_resolucao) AS total_resolucoes,
               AVG(r.tempo_gasto) AS tempo_medio
        FROM resolucao_questao r
        INNER JOIN questao q ON r.id_questao = q.id_questao
        INNER JOIN assunto_questao aq ON q.id_questao = aq.id_questao
        INNER JOIN assunto a ON aq.id_assunto = a.id_assunto
        INNER JOIN disciplina d ON a.id_disciplina = d.id_disciplina
        GROUP BY d.nome, d.frente
        ORDER BY total_resolucoes DESC;
    """
    cur.execute(sql)
    registros = cur.fetchall()
    cur.close()
    con.close()

    df = pd.DataFrame(registros, columns=['disciplina_frente', 'total_resolucoes', 'tempo_medio'])
    df['tempo_medio'] = df['tempo_medio'].astype(float)
    print('\n--- Desempenho e Tempo Medio por Disciplina/Frente ---')
    print(df)

    if not df.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        df.plot(kind='bar', x='disciplina_frente', y='tempo_medio', legend=False, color='steelblue', ax=ax)
        ax.set_title('Tempo Medio de Resolucao (s) por Disciplina e Frente')
        ax.set_xlabel('Disciplina / Frente')
        ax.set_ylabel('Tempo Medio (segundos)')
        plt.xticks(rotation=30, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(GRAFICOS_DIR, 'grafico_consulta_1.png'), dpi=150)
        if exibir:
            plt.show()
        plt.close(fig)


def reportStudentEngagement(exibir=False):
    con = connectDatabase()
    cur = con.cursor()
    sql = """
        SELECT u.nome || ' (Turma ' || al.turma || ')' AS aluno_turma,
               COUNT(r.id_resolucao) AS questoes_resolvidas,
               AVG(r.tempo_gasto) AS tempo_medio_seg
        FROM usuario u
        INNER JOIN aluno al ON u.id_usuario = al.id_usuario
        INNER JOIN resolucao_questao r ON al.id_usuario = r.id_aluno
        INNER JOIN questao q ON r.id_questao = q.id_questao
        GROUP BY u.nome, al.turma
        ORDER BY questoes_resolvidas DESC;
    """
    cur.execute(sql)
    registros = cur.fetchall()
    cur.close()
    con.close()

    df = pd.DataFrame(registros, columns=['aluno_turma', 'questoes_resolvidas', 'tempo_medio_seg'])
    print('\n--- Questoes Resolvidas por Aluno e Turma ---')
    print(df)

    if not df.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        df.plot(kind='bar', x='aluno_turma', y='questoes_resolvidas', legend=False, color='seagreen', ax=ax)
        ax.set_title('Total de Questoes Resolvidas por Aluno e Turma do PES')
        ax.set_xlabel('Aluno (Turma)')
        ax.set_ylabel('Questoes Resolvidas')
        plt.xticks(rotation=30, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(GRAFICOS_DIR, 'grafico_consulta_2.png'), dpi=150)
        if exibir:
            plt.show()
        plt.close(fig)


def reportExamByProfessor(exibir=False):
    con = connectDatabase()
    cur = con.cursor()
    sql = """
        SELECT v.instituicao || ' - ' || u.nome AS vestibular_professor,
               COUNT(q.id_questao) AS total_questoes
        FROM questao q
        INNER JOIN vestibular v ON q.id_vestibular = v.id_vestibular
        INNER JOIN professor p ON q.id_professor = p.id_usuario
        INNER JOIN usuario u ON p.id_usuario = u.id_usuario
        GROUP BY v.instituicao, u.nome
        ORDER BY total_questoes DESC;
    """
    cur.execute(sql)
    registros = cur.fetchall()
    cur.close()
    con.close()

    df = pd.DataFrame(registros, columns=['vestibular_professor', 'total_questoes'])
    print('\n--- Questoes Cadastradas por Vestibular e Professor ---')
    print(df)

    if not df.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        df.plot(kind='bar', x='vestibular_professor', y='total_questoes', legend=False, color='darkorange', ax=ax)
        ax.set_title('Questoes Cadastradas por Vestibular e Professor')
        ax.set_xlabel('Vestibular - Professor')
        ax.set_ylabel('Quantidade de Questoes')
        plt.xticks(rotation=30, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(GRAFICOS_DIR, 'grafico_consulta_3.png'), dpi=150)
        if exibir:
            plt.show()
        plt.close(fig)


if __name__ == '__main__':
    reportSubjectPerformance()
    reportStudentEngagement()
    reportExamByProfessor()

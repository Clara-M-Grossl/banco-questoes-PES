import pandas as pd
from database.conexao import connectDatabase

TABELAS = {
    'disciplina': ['id_disciplina', 'nome', 'frente', 'area'],
    'assunto': ['id_assunto', 'id_disciplina', 'nome'],
    'usuario': ['id_usuario', 'nome', 'cpf', 'senha', 'email', 'data_ingresso'],
    'gestao': ['id_usuario', 'cargo', 'setor_atuacao'],
    'curso': ['id_curso', 'nome'],
    'professor': ['id_usuario', 'id_disciplina', 'id_curso', 'matricula_ufsc', 'fase_curso'],
    'escola': ['id_escola', 'nome', 'cidade'],
    'aluno': ['id_usuario', 'id_escola', 'turma', 'situacao_em', 'curso_desejado'],
    'vestibular': ['id_vestibular', 'ano', 'edicao', 'instituicao'],
    'questao': ['id_questao', 'id_vestibular', 'id_professor', 'id_gestao', 'tipo', 'dificuldade', 'enunciado'],
    'alternativa': ['id_alternativa', 'id_questao', 'valor_proposicao', 'texto', 'indicador_correta'],
    'dica': ['id_dica', 'id_questao', 'tipo', 'conteudo_texto'],
    'tag': ['id_tag', 'nome'],
    'midia': ['id_midia', 'id_questao', 'legenda', 'arquivo'],
    'lista_exercicio': ['id_lista', 'id_usuario', 'publica', 'titulo', 'data_criacao'],
    'assunto_questao': ['id_questao', 'id_assunto'],
    'questao_lista': ['id_questao', 'id_lista'],
    'questao_tag': ['id_tag', 'id_questao'],
    'resolucao_questao': ['id_resolucao', 'id_questao', 'id_aluno', 'data', 'acerto', 'tempo_gasto', 'resposta_aluno'],
}

TABELAS_PK_COMPOSTA = ('assunto_questao', 'questao_lista', 'questao_tag')


def queryTable(tabela):
    colunas = TABELAS[tabela]
    con = connectDatabase()
    cur = con.cursor()
    cur.execute(f"select {', '.join(colunas)} from {tabela} order by {colunas[0]};")
    registros = cur.fetchall()
    cur.close()
    con.close()

    df = pd.DataFrame(registros, columns=colunas)
    print(f'\n--- Registros da tabela {tabela.upper()} ---')
    print(df)


def insertRecord(tabela):
    colunas = TABELAS[tabela]
    valores = []
    print(f'\n--- Inserir novo registro em {tabela.upper()} ---')
    for col in colunas:
        val = input(f'Digite {col} (vazio para NULL): ').strip()
        valores.append(val if val != '' else None)

    nomes_colunas = ', '.join(colunas)
    marcadores = ', '.join(['%s'] * len(colunas))
    sql = f'insert into {tabela} ({nomes_colunas}) values ({marcadores});'

    con = connectDatabase()
    cur = con.cursor()
    try:
        cur.execute(sql, tuple(valores))
        con.commit()
        print('Registro inserido com sucesso')
    except Exception as e:
        con.rollback()
        print('Erro de integridade ao inserir:', e)
    finally:
        cur.close()
        con.close()


def updateRecord(tabela):
    queryTable(tabela)
    colunas = TABELAS[tabela]
    pk = colunas[0]

    print(f'\n--- Atualizar registro em {tabela.upper()} ---')
    id_val = input(f'Digite o valor da chave primaria ({pk}) que deseja atualizar: ').strip()
    print('Colunas disponiveis:', ', '.join(colunas))
    col_alvo = input('Qual coluna deseja alterar? ').strip()
    novo_val = input(f'Digite o novo valor para {col_alvo}: ').strip()

    sql = f'update {tabela} set {col_alvo} = %s where {pk} = %s;'

    con = connectDatabase()
    cur = con.cursor()
    try:
        cur.execute(sql, (novo_val, id_val))
        con.commit()
        print('Registro atualizad')
    except Exception as e:
        con.rollback()
        print('Erro ao atualizar:', e)
    finally:
        cur.close()
        con.close()


def deleteRecord(tabela):
    queryTable(tabela)
    colunas = TABELAS[tabela]
    print(f'\n--- Excluir registro de {tabela.upper()} ---')

    con = connectDatabase()
    cur = con.cursor()
    try:
        if tabela in TABELAS_PK_COMPOSTA:
            pk1, pk2 = colunas[0], colunas[1]
            v1 = input(f'Digite {pk1}: ').strip()
            v2 = input(f'Digite {pk2}: ').strip()
            sql = f'delete from {tabela} where {pk1} = %s and {pk2} = %s;'
            cur.execute(sql, (v1, v2))
        else:
            pk = colunas[0]
            v1 = input(f'Digite {pk} para excluir: ').strip()
            sql = f'delete from {tabela} where {pk} = %s;'
            cur.execute(sql, (v1,))
        con.commit()
        print('Registro excluido')
    except Exception as e:
        con.rollback()
        print('Erro de integridade ao excluir (registro referenciado em outra tabela):', e)
    finally:
        cur.close()
        con.close()


if __name__ == '__main__':
    queryTable('tag')

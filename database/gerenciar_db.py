import os
from database.conexao import connectDatabase

BASE_DB_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_SQL = os.path.join(BASE_DB_DIR, 'ddl.sql')


def readSqlCommands():
    with open(ARQUIVO_SQL, 'r', encoding='utf-8') as f:
        linhas = [l for l in f if not l.strip().startswith('--')]
        conteudo = '\n'.join(linhas)
    comandos = [cmd.strip() for cmd in conteudo.split(';') if cmd.strip()]
    return comandos


def dropTables():
    con = connectDatabase()
    cur = con.cursor()
    try:
        for cmd in readSqlCommands():
            if cmd.lower().startswith('drop table'):
                cur.execute(cmd + ';')
        con.commit()
        print('Todas as 19 tabelas foram deletadas')
    except Exception as e:
        con.rollback()
        print('Erro ao eliminar tabelas:', e)
    finally:
        cur.close()
        con.close()


def createTables():
    con = connectDatabase()
    cur = con.cursor()
    try:
        for cmd in readSqlCommands():
            inicio = cmd.lower()
            if inicio.startswith('create table') or inicio.startswith('alter table'):
                cur.execute(cmd + ';')
        con.commit()
        print('Todas as 19 tabelas e constraints foram criadas')
    except Exception as e:
        con.rollback()
        print('Erro ao criar tabelas:', e)
    finally:
        cur.close()
        con.close()


def loadInitialData():
    con = connectDatabase()
    cur = con.cursor()
    try:
        for cmd in readSqlCommands():
            if cmd.lower().startswith('insert into'):
                cur.execute(cmd + ';')
        con.commit()
        print('Dados carregados')
    except Exception as e:
        con.rollback()
        print('Erro ao carregar dados:', e)
    finally:
        cur.close()
        con.close()


if __name__ == '__main__':
    dropTables()
    createTables()
    loadInitialData()

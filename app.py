import io
import os
import re
import html
import uuid
import base64
import shutil
import tempfile
import threading
import subprocess
from collections import defaultdict
from functools import wraps
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session, Response
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from database.conexao import connectDatabase
from database import gerenciar_db, crud
from services import ia_service, importadores

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'uploads')
TEX_TEMPLATE_PATH = os.path.join(BASE_DIR, 'templates_tex', 'modelo_lista_pes.tex')
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
RELATOS_PATH = os.path.join(DATA_DIR, 'relatos_revisao.json')
os.makedirs(UPLOAD_DIR, exist_ok=True)


def loadReviewReports():
    import json
    if not os.path.exists(RELATOS_PATH):
        return {}
    try:
        with open(RELATOS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def saveReviewReports(dados):
    import json
    try:
        with open(RELATOS_PATH, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

gerenciar_db.ARQUIVO_SQL = os.path.join(BASE_DIR, 'database', 'ddl.sql')

LOGO_PES_PATH = os.path.join(BASE_DIR, 'static', 'img', 'logo-pes.png')

TABELAS_AUTO_PK = {
    'disciplina', 'assunto', 'usuario', 'curso', 'escola', 'vestibular', 'questao',
    'alternativa', 'dica', 'tag', 'midia', 'lista_exercicio', 'resolucao_questao'
}

TABLE_LABELS = {
    'disciplina': 'Disciplina',
    'assunto': 'Assunto',
    'usuario': 'Usuario',
    'gestao': 'Gestao',
    'curso': 'Curso',
    'professor': 'Professor',
    'escola': 'Escola',
    'aluno': 'Aluno',
    'vestibular': 'Vestibular',
    'questao': 'Questao',
    'alternativa': 'Alternativa',
    'dica': 'Dica',
    'tag': 'Tag',
    'midia': 'Midia',
    'lista_exercicio': 'Lista_Exercicio',
    'assunto_questao': 'Assunto_Questao',
    'questao_lista': 'Questao_Lista',
    'questao_tag': 'Questao_Tag',
    'resolucao_questao': 'Resolucao_Questao',
}

app = Flask(__name__)
app.secret_key = 'pes_ufsc_sessao_segura'
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024

JOBS_IMPORTACAO = {}

@app.template_filter('stripOptionPrefix')
def stripOptionPrefix(texto):
    if not texto:
        return ''
    t = str(texto).strip()
    t = re.sub(r'^(?:01|02|04|08|16|32|64)\s*[\.\-\)]\s*', '', t)
    t = re.sub(r'^[A-Ea-e]\s*[\)\.\-]\s*', '', t)
    return t.strip()


@app.template_filter('formatQuestionText')
def formatQuestionText(texto):
    if not texto:
        return ''
    seguro = html.escape(str(texto))
    # Protege cifroes monetarios
    seguro = re.sub(r'\b(R|US|U)\$', r'<span class="no-math">\1$</span>', seguro)
    seguro = re.sub(r'(?<!\\)\$(\s+\d)', r'<span class="no-math">$</span>\1', seguro)
    seguro = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', seguro)
    seguro = seguro.replace('\r\n', '\n').replace('\n', '<br>')
    return seguro


def escapeLatexPreservingMath(texto):
    
    if not texto:
        return ''
    texto = str(texto).replace('**', '')
    # Protege valores monetario
    texto = re.sub(r'\b(R|US|U)\$', r'\1@@CIFRAOMOEDA@@', texto)
    partes = re.split(r'(\$\$.*?\$\$|\$.*?\$)', texto, flags=re.DOTALL)
    resultado = []
    for i, parte in enumerate(partes):
        if i % 2 == 1:
            resultado.append(parte.replace('@@CIFRAOMOEDA@@', r'\$'))
        else:
            p = parte.replace('\\', r'\textbackslash{}')
            p = p.replace('&', r'\&').replace('%', r'\%').replace('#', r'\#').replace('_', r'\_')
            p = p.replace('@@CIFRAOMOEDA@@', r'\$')
            resultado.append(p)
    return ''.join(resultado)


def getLoggedUser():
    return session.get('usuario')


def requireLogin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('loginPage'))
        return f(*args, **kwargs)
    return decorated


def requireRole(*perfis_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            usuario = session.get('usuario')
            if not usuario:
                return redirect(url_for('loginPage'))
            if usuario.get('perfil') not in perfis_permitidos:
                flash('Acesso restrito ao perfil autorizado.', 'erro')
                return redirect(url_for('dashboardPage'))
            return f(*args, **kwargs)
        return decorated
    return decorator


@app.context_processor
def injectLoggedUser():
    return {'usuario_logado': getLoggedUser()}


@app.route('/favicon.ico')
@app.route('/logo_pes')
@app.route('/servePesLogo')
def servePesLogo():
    if os.path.exists(LOGO_PES_PATH):
        return send_file(LOGO_PES_PATH, mimetype='image/png')
    return '', 404

def loadQuestionsBatch(cur, ids_filtro=None):
    if ids_filtro is not None:
        ids_list = list(ids_filtro)
        if not ids_list:
            return []
        cur.execute("""
            select q.id_questao, v.instituicao, v.ano, q.tipo, q.dificuldade, q.enunciado
            from questao q
            inner join vestibular v on q.id_vestibular = v.id_vestibular
            where q.id_questao = any(%s)
            order by q.id_questao;
        """, (ids_list,))
        base_rows = cur.fetchall()

        cur.execute("""
            select ab.id_questao, d.nome, d.frente, a.nome
            from assunto_questao ab
            inner join assunto a on ab.id_assunto = a.id_assunto
            inner join disciplina d on a.id_disciplina = d.id_disciplina
            where ab.id_questao = any(%s);
        """, (ids_list,))
        mapa_assuntos = defaultdict(list)
        for id_q, dn, df, an in cur.fetchall():
            mapa_assuntos[id_q].append((dn, df, an))

        cur.execute("""
            select p.id_questao, t.nome
            from questao_tag p
            inner join tag t on p.id_tag = t.id_tag
            where p.id_questao = any(%s);
        """, (ids_list,))
        mapa_tags = defaultdict(list)
        for id_q, tn in cur.fetchall():
            mapa_tags[id_q].append(tn)

        cur.execute("""
            select id_questao, id_alternativa, valor_proposicao, texto, indicador_correta
            from alternativa
            where id_questao = any(%s)
            order by id_questao, valor_proposicao, id_alternativa;
        """, (ids_list,))
        mapa_alts = defaultdict(list)
        for id_q, id_a, vp, txt, corr in cur.fetchall():
            mapa_alts[id_q].append((id_a, vp, txt, corr))

        cur.execute('select id_questao, tipo, conteudo_texto from dica where id_questao = any(%s) order by id_questao, id_dica;', (ids_list,))
        mapa_dicas = defaultdict(list)
        for id_q, td, ct in cur.fetchall():
            mapa_dicas[id_q].append((td, ct))

        cur.execute('select id_questao, legenda, arquivo from midia where id_questao = any(%s) order by id_questao, id_midia;', (ids_list,))
        mapa_midias = defaultdict(list)
        for id_q, leg, arq in cur.fetchall():
            mapa_midias[id_q].append((leg, arq))
    else:
        cur.execute("""
            select q.id_questao, v.instituicao, v.ano, q.tipo, q.dificuldade, q.enunciado
            from questao q
            inner join vestibular v on q.id_vestibular = v.id_vestibular
            order by q.id_questao;
        """)
        base_rows = cur.fetchall()

        cur.execute("""
            select ab.id_questao, d.nome, d.frente, a.nome
            from assunto_questao ab
            inner join assunto a on ab.id_assunto = a.id_assunto
            inner join disciplina d on a.id_disciplina = d.id_disciplina;
        """)
        mapa_assuntos = defaultdict(list)
        for id_q, dn, df, an in cur.fetchall():
            mapa_assuntos[id_q].append((dn, df, an))

        cur.execute("""
            select p.id_questao, t.nome
            from questao_tag p
            inner join tag t on p.id_tag = t.id_tag;
        """)
        mapa_tags = defaultdict(list)
        for id_q, tn in cur.fetchall():
            mapa_tags[id_q].append(tn)

        cur.execute("""
            select id_questao, id_alternativa, valor_proposicao, texto, indicador_correta
            from alternativa
            order by id_questao, valor_proposicao, id_alternativa;
        """)
        mapa_alts = defaultdict(list)
        for id_q, id_a, vp, txt, corr in cur.fetchall():
            mapa_alts[id_q].append((id_a, vp, txt, corr))

        cur.execute('select id_questao, tipo, conteudo_texto from dica order by id_questao, id_dica;')
        mapa_dicas = defaultdict(list)
        for id_q, td, ct in cur.fetchall():
            mapa_dicas[id_q].append((td, ct))

        cur.execute('select id_questao, legenda, arquivo from midia order by id_questao, id_midia;')
        mapa_midias = defaultdict(list)
        for id_q, leg, arq in cur.fetchall():
            mapa_midias[id_q].append((leg, arq))

    resultado = []
    for id_q, inst, ano, tipo, dif, enunciado in base_rows:
        assuntos = mapa_assuntos[id_q]
        alts = mapa_alts[id_q]
        soma_correta = sum(a[1] for a in alts if a[3])
        resultado.append({
            'id_questao': id_q,
            'instituicao': inst,
            'ano': ano,
            'tipo': tipo,
            'dificuldade': dif,
            'enunciado': enunciado,
            'assuntos': assuntos,
            'disciplinas_str': ', '.join(sorted(set(f'{a[0]} ({a[1]})' for a in assuntos))),
            'assuntos_str': ', '.join(a[2] for a in assuntos),
            'tags': mapa_tags[id_q],
            'alternativas': alts,
            'soma_correta': soma_correta,
            'dicas': mapa_dicas[id_q],
            'midias': mapa_midias[id_q]
        })
    return resultado


def renderChartBase64(df, col_x, col_y, titulo, cor):
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8FAFC')
    if not df.empty:
        bars = ax.bar(df[col_x].astype(str), df[col_y].astype(float), color=cor, width=0.52, zorder=3)
        for bar in bars:
            h = bar.get_height()
            ax.annotate(
                f'{h:.1f}' if isinstance(h, float) and not h.is_integer() else f'{int(h)}',
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 4),
                textcoords='offset points',
                ha='center',
                va='bottom',
                fontsize=9,
                fontweight='bold',
                color='#0F172A'
            )
    ax.set_title(titulo, fontsize=11, fontweight='bold', color='#0F172A', pad=12)
    ax.grid(axis='y', linestyle='--', alpha=0.45, color='#CBD5E1', zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.xticks(rotation=20, ha='right', fontsize=9, color='#475569')
    plt.yticks(fontsize=9, color='#475569')
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=115)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


@app.route('/')
def homeRedirect():
    if 'usuario' in session:
        return redirect(url_for('dashboardPage'))
    return redirect(url_for('loginPage'))


@app.route('/login', methods=['GET', 'POST'])
def loginPage():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '').strip()

        try:
            con = connectDatabase()
            cur = con.cursor()
            cur.execute(
                'select id_usuario, nome, email from usuario where lower(email) = lower(%s) and senha = %s;',
                (email, senha)
            )
            user = cur.fetchone()

            if not user:
                cur.close()
                con.close()
                flash('E-mail ou senha inválidos.', 'erro')
                return redirect(url_for('loginPage'))

            id_u, nome_u, email_u = user
            perfil = 'aluno'
            descricao = 'Estudante'

            cur.execute('select cargo, setor_atuacao from gestao where id_usuario = %s;', (id_u,))
            g = cur.fetchone()
            if g:
                perfil = 'gestao'
                descricao = f'Gestão • {g[0]} ({g[1]})'
            else:
                cur.execute("""
                    select d.nome, d.frente
                    from professor p
                    inner join disciplina d on p.id_disciplina = d.id_disciplina
                    where p.id_usuario = %s;
                """, (id_u,))
                p = cur.fetchone()
                if p:
                    perfil = 'professor'
                    descricao = f'Docente • {p[0]} ({p[1]})'
                else:
                    cur.execute('select turma from aluno where id_usuario = %s;', (id_u,))
                    a = cur.fetchone()
                    if a:
                        perfil = 'aluno'
                        descricao = f'Aluno • Turma {a[0]}'

            cur.close()
            con.close()

            session['usuario'] = {
                'id_usuario': id_u,
                'nome': nome_u,
                'email': email_u,
                'perfil': perfil,
                'descricao_perfil': descricao
            }
            return redirect(url_for('dashboardPage'))
        except Exception as e:
            flash(f'Erro ao autenticar: {e}', 'erro')
            return redirect(url_for('loginPage'))

    contas_exemplo = []
    try:
        con = connectDatabase()
        cur = con.cursor()
        for nome_perfil, sql_p in [
            ('Gestão', 'select u.email, u.senha from usuario u inner join gestao g on u.id_usuario = g.id_usuario limit 1;'),
            ('Professor', 'select u.email, u.senha from usuario u inner join professor p on u.id_usuario = p.id_usuario limit 1;'),
            ('Aluno', 'select u.email, u.senha from usuario u inner join aluno a on u.id_usuario = a.id_usuario limit 1;')
        ]:
            cur.execute(sql_p)
            row = cur.fetchone()
            if row:
                contas_exemplo.append({'perfil': nome_perfil, 'email': row[0], 'senha': row[1]})
        cur.close()
        con.close()
    except Exception:
        pass

    return render_template('login.html', contas_exemplo=contas_exemplo)


@app.route('/logout')
def logoutUser():
    session.clear()
    return redirect(url_for('loginPage'))


# DASHBOARD INICIAL
@app.route('/dashboard')
@requireLogin
def dashboardPage():
    usuario = getLoggedUser()
    metricas = {'resolvidas': 0, 'acertos': 0, 'taxa_acerto': 0, 'tempo_medio': 0, 'total_questoes': 0, 'total_alunos': 0, 'total_resolucoes': 0, 'total_listas': 0}
    disciplinas = []
    historico = []

    try:
        con = connectDatabase()
        cur = con.cursor()

        cur.execute('select count(*) from questao;')
        metricas['total_questoes'] = cur.fetchone()[0]

        if usuario['perfil'] == 'aluno':
            cur.execute("""
                select count(*),
                       coalesce(sum(case when acerto then 1 else 0 end), 0),
                       coalesce(avg(tempo_gasto), 0)
                from resolucao_questao
                where id_aluno = %s;
            """, (usuario['id_usuario'],))
            res, ac, t_med = cur.fetchone()
            metricas['resolvidas'] = res
            metricas['acertos'] = ac
            metricas['taxa_acerto'] = round((ac / res) * 100) if res > 0 else 0
            metricas['tempo_medio'] = round(float(t_med))

            cur.execute("""
                select r.id_questao, v.instituicao, v.ano, r.acerto, r.resposta_aluno, r.tempo_gasto, r.data
                from resolucao_questao r
                inner join questao q on r.id_questao = q.id_questao
                inner join vestibular v on q.id_vestibular = v.id_vestibular
                where r.id_aluno = %s
                order by r.data desc
                limit 10;
            """, (usuario['id_usuario'],))
            for row in cur.fetchall():
                historico.append({
                    'id_questao': row[0], 'instituicao': row[1], 'ano': row[2],
                    'acerto': row[3], 'resposta_aluno': row[4], 'tempo_gasto': row[5], 'data': row[6]
                })
        else:
            cur.execute('select count(*) from aluno;')
            metricas['total_alunos'] = cur.fetchone()[0]
            cur.execute('select count(*) from lista_exercicio;')
            metricas['total_listas'] = cur.fetchone()[0]
            cur.execute('select count(*), coalesce(sum(case when acerto then 1 else 0 end), 0) from resolucao_questao;')
            tot_r, tot_a = cur.fetchone()
            metricas['total_resolucoes'] = tot_r
            metricas['taxa_acerto'] = round((tot_a / tot_r) * 100) if tot_r > 0 else 0

        cur.execute("""
            select d.nome, d.area, count(distinct d.id_disciplina) as frentes, count(distinct ab.id_questao) as questoes
            from disciplina d
            left join assunto a on a.id_disciplina = d.id_disciplina
            left join assunto_questao ab on ab.id_assunto = a.id_assunto
            group by d.nome, d.area
            order by questoes desc, d.nome;
        """)
        max_q = max(1, metricas['total_questoes'])
        for nome_d, area_d, frentes_d, q_d in cur.fetchall():
            disciplinas.append({
                'nome': nome_d, 'area': area_d, 'total_frentes': frentes_d,
                'total_questoes': q_d, 'percentual': min(100, round((q_d / max_q) * 100)) if q_d > 0 else 0
            })

        cur.close()
        con.close()
    except Exception as e:
        flash(f'Erro ao carregar painel: {e}', 'erro')

    return render_template('dashboard.html', pagina_ativa='dashboard', metricas=metricas, disciplinas=disciplinas, historico=historico)


def loadVisibleLists(cur, usuario):
    # carrega listas e cadernos privados
    id_u = usuario['id_usuario']
    id_aluno_param = id_u if usuario['perfil'] == 'aluno' else -1
    cur.execute("""
        select l.id_lista,
               l.titulo,
               l.publica,
               l.id_usuario,
               u.nome,
               count(distinct c.id_questao) as total_q,
               case
                   when g.id_usuario is not null then 'gestao'
                   when p.id_usuario is not null then 'professor'
                   else 'aluno'
               end as perfil_autor,
               case
                   when g.id_usuario is not null then 'Geral'
                   when p.id_usuario is not null then d.nome
                   else 'Meu Caderno'
               end as categoria_lista,
               coalesce(d.frente, '') as frente_autor,
               count(distinct case when r.id_questao is not null then c.id_questao end) as resolvidas_aluno
        from lista_exercicio l
        inner join usuario u on l.id_usuario = u.id_usuario
        left join gestao g on g.id_usuario = u.id_usuario
        left join professor p on p.id_usuario = u.id_usuario
        left join disciplina d on d.id_disciplina = p.id_disciplina
        left join questao_lista c on c.id_lista = l.id_lista
        left join (
            select distinct id_questao from resolucao_questao where id_aluno = %s
        ) r on r.id_questao = c.id_questao
        where l.publica = true or l.id_usuario = %s
        group by l.id_lista, l.titulo, l.publica, l.id_usuario, u.nome, g.id_usuario, p.id_usuario, d.nome, d.frente
        order by l.id_lista desc;
    """, (id_aluno_param, id_u))

    listas = []
    for row in cur.fetchall():
        id_l, tit, pub, id_autor, autor, tot_q, perf_a, cat_l, frente_a, res_a = row
        concluida = (usuario['perfil'] == 'aluno' and tot_q > 0 and res_a >= tot_q)
        em_andamento = (usuario['perfil'] == 'aluno' and 0 < res_a < tot_q)
        listas.append({
            'id_lista': id_l,
            'titulo': tit,
            'publica': pub,
            'id_autor': id_autor,
            'autor': autor,
            'pode_excluir': (usuario['perfil'] == 'gestao' or id_autor == id_u),
            'total_questoes': tot_q,
            'perfil_autor': perf_a,
            'categoria': cat_l,
            'frente_autor': frente_a,
            'resolvidas_aluno': res_a,
            'concluida': concluida,
            'em_andamento': em_andamento
        })
    return listas


# BANCO DE QUESTOES
@app.route('/questoes')
@requireLogin
def questionsPage():
    usuario = getLoggedUser()
    f_disciplina = request.args.get('disciplina', '').strip()
    f_vestibular = request.args.get('vestibular', '').strip()
    f_ano = request.args.get('ano', '').strip()
    f_dificuldade = request.args.get('dificuldade', '').strip()
    f_tipo = request.args.get('tipo', '').strip()
    f_lista = request.args.get('lista', '').strip()
    f_questao = request.args.get('questao', '').strip()
    f_ids = request.args.get('ids', '').strip()
    termo_busca = request.args.get('busca', '').strip()
    baixar_pdf = request.args.get('baixar_pdf', '').strip()
    baixar_gab = request.args.get('baixar_gab', '').strip()
    pagina = max(1, int(request.args.get('pagina', 1) or 1))
    por_pagina = 15

    questoes_lista = []
    disciplinas_unicas = []
    disciplinas_cards = []
    vestibulares_unicos = []
    anos_unicos = []
    listas_visiveis = []
    lista_ativa = None
    status_resolvidas = {}
    ultimas_resolucoes = {}
    total_acervo = 0
    total_ineditas = 0
    total_encontradas = 0
    total_paginas = 1

    try:
        con = connectDatabase()
        cur = con.cursor()

        cur.execute('select count(*) from questao;')
        total_acervo = cur.fetchone()[0]

        cur.execute('select distinct nome from disciplina order by nome;')
        disciplinas_unicas = [r[0] for r in cur.fetchall()]

        cur.execute("""
            select d.nome, d.area, count(distinct d.id_disciplina) as frentes, count(distinct ab.id_questao) as questoes
            from disciplina d
            left join assunto a on a.id_disciplina = d.id_disciplina
            left join assunto_questao ab on ab.id_assunto = a.id_assunto
            group by d.nome, d.area
            order by questoes desc, d.nome;
        """)
        for nome_d, area_d, frentes_d, q_d in cur.fetchall():
            disciplinas_cards.append({
                'nome': nome_d,
                'area': area_d,
                'total_frentes': frentes_d,
                'total_questoes': q_d
            })

        cur.execute('select distinct instituicao from vestibular order by instituicao;')
        vestibulares_unicos = [r[0] for r in cur.fetchall()]

        cur.execute('select distinct ano from vestibular where ano is not null order by ano desc;')
        anos_unicos = [r[0] for r in cur.fetchall()]

        # Listas
        listas_visiveis = loadVisibleLists(cur, usuario)
        if f_lista:
            for item_l in listas_visiveis:
                if str(item_l['id_lista']) == str(f_lista):
                    lista_ativa = item_l
                    break

        # Historico detalhado do aluno (ultima resolucao por questao)
        if usuario['perfil'] == 'aluno':
            cur.execute("""
                select distinct on (id_questao) id_questao, acerto, resposta_aluno, tempo_gasto, data
                from resolucao_questao
                where id_aluno = %s
                order by id_questao, data desc;
            """, (usuario['id_usuario'],))
            for id_q_r, ac_r, resp_r, tempo_r, data_r in cur.fetchall():
                status_resolvidas[id_q_r] = bool(ac_r)
                ultimas_resolucoes[id_q_r] = {
                    'acerto': bool(ac_r),
                    'resposta_aluno': int(resp_r) if resp_r is not None else 0,
                    'tempo_gasto': int(tempo_r) if tempo_r is not None else 0,
                    'data': data_r.strftime('%d/%m/%Y %H:%M') if data_r else ''
                }
            total_ineditas = max(0, total_acervo - len(status_resolvidas))
        else:
            total_ineditas = total_acervo

        ids_lista = None
        if f_questao and f_questao.isdigit():
            ids_lista = {int(f_questao)}
        elif f_ids:
            parsed_ids = {int(x) for x in f_ids.split(',') if x.strip().isdigit()}
            if parsed_ids:
                ids_lista = parsed_ids
        elif f_lista:
            cur.execute('select id_questao from questao_lista where id_lista = %s;', (f_lista,))
            ids_lista = {r[0] for r in cur.fetchall()}

        todas = loadQuestionsBatch(cur, ids_filtro=ids_lista)
        cur.close()
        con.close()

        for q in todas:
            if f_vestibular and q['instituicao'].lower() != f_vestibular.lower():
                continue
            if f_ano and str(q['ano']) != f_ano:
                continue
            if f_dificuldade and q['dificuldade'].lower() != f_dificuldade.lower():
                continue
            if f_tipo and q['tipo'].lower() != f_tipo.lower():
                continue
            if f_disciplina and f_disciplina.lower() not in [a[0].lower() for a in q['assuntos']]:
                continue
            questoes_lista.append(q)

        if termo_busca and questoes_lista:
            m_id = re.fullmatch(r'[q#]?\s*0*(\d+)', termo_busca.strip(), flags=re.I)
            exatas = [q for q in questoes_lista if m_id and q['id_questao'] == int(m_id.group(1))]
            if exatas:
                questoes_lista = exatas
            else:
                from collections import Counter
                tokens_busca = ia_service.normalizeSearchTokens(termo_busca)
                termo_norm = ' '.join(tokens_busca)
                v_busca = Counter(tokens_busca)
                ranqueadas = []
                for q in questoes_lista:
                    doc = f"{q['enunciado']} {' '.join(a[2] for a in q['alternativas'])} {q['disciplinas_str']} {q['assuntos_str']}"
                    tokens_doc = ia_service.normalizeSearchTokens(doc)
                    sim = ia_service.cosineSimilarity(v_busca, Counter(tokens_doc))
                    if termo_norm and termo_norm in ' '.join(tokens_doc):
                        sim += 0.5
                    if sim > 0:
                        ranqueadas.append((sim, q))
                ranqueadas.sort(key=lambda x: x[0], reverse=True)
                questoes_lista = [q for _, q in ranqueadas]

        total_encontradas = len(questoes_lista)
        total_paginas = max(1, (total_encontradas + por_pagina - 1) // por_pagina)
        if pagina > total_paginas:
            pagina = total_paginas
        inicio = (pagina - 1) * por_pagina
        questoes_lista = questoes_lista[inicio:inicio + por_pagina]
    except Exception as e:
        flash(f'Erro ao consultar banco de questões: {e}', 'erro')

    return render_template(
        'questoes.html',
        pagina_ativa='questoes',
        questoes=questoes_lista,
        total_acervo=total_acervo,
        total_ineditas=total_ineditas,
        total_encontradas=total_encontradas,
        pagina=pagina,
        total_paginas=total_paginas,
        disciplinas_unicas=disciplinas_unicas,
        disciplinas_cards=disciplinas_cards,
        vestibulares_unicos=vestibulares_unicos,
        anos_unicos=anos_unicos,
        listas_visiveis=listas_visiveis,
        lista_ativa=lista_ativa,
        status_resolvidas=status_resolvidas,
        ultimas_resolucoes=ultimas_resolucoes,
        f_disciplina=f_disciplina,
        f_vestibular=f_vestibular,
        f_ano=f_ano,
        f_dificuldade=f_dificuldade,
        f_tipo=f_tipo,
        f_lista=f_lista,
        f_questao=f_questao,
        f_ids=f_ids,
        termo_busca=termo_busca,
        baixar_pdf=baixar_pdf,
        baixar_gab=baixar_gab
    )


# MODO SIMULADO
@app.route('/simulado', methods=['GET', 'POST'])
@requireLogin
def mockExamPage():
    import random
    usuario = getLoggedUser()
    params = request.form if request.method == 'POST' else request.args

    ids_raw = params.get('ids', '').strip()
    lista_id = params.get('lista', '').strip()
    modo = params.get('modo', '').strip()
    qtd = max(1, min(60, int(params.get('qtd', 5) or 5)))
    f_disciplina = params.get('disciplina', '').strip()
    f_vestibular = params.get('vestibular', '').strip()
    f_ano = params.get('ano', '').strip()
    f_tipo = params.get('tipo', '').strip()
    somente_ineditas = params.get('somente_ineditas', '1') in ('1', 'true', 'on', 'True')

    questoes_simulado = []
    titulo_simulado = 'Simulado Cronometrado'
    subtitulo_simulado = 'O cronômetro conta o tempo gasto em cada questão durante o simulado.'

    try:
        con = connectDatabase()
        cur = con.cursor()

        if lista_id:
            cur.execute('select titulo from lista_exercicio where id_lista = %s;', (int(lista_id),))
            row_l = cur.fetchone()
            if row_l:
                titulo_simulado = f'Simulado: {row_l[0]}'
            cur.execute('select id_questao from questao_lista where id_lista = %s order by id_questao;', (int(lista_id),))
            ids_ordenados = [r[0] for r in cur.fetchall()]
            todas = loadQuestionsBatch(cur, ids_filtro=set(ids_ordenados))
            mapa = {q['id_questao']: q for q in todas}
            questoes_simulado = [mapa[i] for i in ids_ordenados if i in mapa]

        elif ids_raw:
            ids_ordenados = []
            for p in ids_raw.split(','):
                p = p.strip()
                if p.isdigit():
                    val = int(p)
                    if val not in ids_ordenados:
                        ids_ordenados.append(val)
            todas = loadQuestionsBatch(cur, ids_filtro=set(ids_ordenados))
            mapa = {q['id_questao']: q for q in todas}
            questoes_simulado = [mapa[i] for i in ids_ordenados if i in mapa]
            titulo_simulado = f'Simulado Personalizado ({len(questoes_simulado)} questões)'

        else:
            # Modo aleatorio
            todas = loadQuestionsBatch(cur)
            resolvidas_ids = set()
            if usuario['perfil'] == 'aluno':
                cur.execute('select distinct id_questao from resolucao_questao where id_aluno = %s;', (usuario['id_usuario'],))
                resolvidas_ids = {r[0] for r in cur.fetchall()}

            candidatas = []
            for q in todas:
                if f_vestibular and q['instituicao'].lower() != f_vestibular.lower():
                    continue
                if f_ano and str(q['ano']) != f_ano:
                    continue
                if f_tipo and q['tipo'].lower() != f_tipo.lower():
                    continue
                if f_disciplina and f_disciplina.lower() not in [a[0].lower() for a in q['assuntos']]:
                    continue
                candidatas.append(q)

            ineditas = [q for q in candidatas if q['id_questao'] not in resolvidas_ids]

            if somente_ineditas and usuario['perfil'] == 'aluno':
                pool = ineditas
                if not pool and candidatas:
                    flash('Você já resolveu todas as questões disponíveis para esse filtro! Montamos um simulado de revisão com questões aleatórias.', 'aviso')
                    pool = candidatas
                elif len(pool) < qtd and pool:
                    flash(f'Foram encontradas {len(pool)} questão(ões) inédita(s) para esse filtro — seu simulado foi montado com todas elas.', 'aviso')
            else:
                pool = candidatas

            random.shuffle(pool)
            questoes_simulado = pool[:qtd]
            detalhe = []
            if f_disciplina:
                detalhe.append(f_disciplina)
            if f_vestibular:
                detalhe.append(f_vestibular)
            sufixo = f' — {", ".join(detalhe)}' if detalhe else ''
            titulo_simulado = f'Simulado Aleatório{sufixo}'
            if somente_ineditas and usuario['perfil'] == 'aluno' and ineditas:
                subtitulo_simulado = 'Questões selecionadas aleatoriamente entre aquelas que você ainda não resolveu.'

        cur.close()
        con.close()
    except Exception as e:
        flash(f'Erro ao montar simulado: {e}', 'erro')
        return redirect(url_for('questionsPage'))

    if not questoes_simulado:
        flash('Nenhuma questão disponível para montar o simulado com esses critérios.', 'aviso')
        return redirect(url_for('questionsPage'))

    return render_template(
        'simulado.html',
        pagina_ativa='questoes',
        questoes=questoes_simulado,
        titulo_simulado=titulo_simulado,
        subtitulo_simulado=subtitulo_simulado,
        ids_csv=','.join(str(q['id_questao']) for q in questoes_simulado)
    )


@app.route('/api/simulado/finalizar', methods=['POST'])
@requireLogin
def finishMockExamApi():
    usuario = getLoggedUser()
    dados = request.get_json() or {}
    respostas = dados.get('respostas', [])

    if usuario['perfil'] != 'aluno':
        return jsonify({'ok': True, 'registradas': 0, 'perfil': usuario['perfil']})

    if not respostas:
        return jsonify({'ok': True, 'registradas': 0})

    con = connectDatabase()
    cur = con.cursor()
    try:
        cur.execute('select coalesce(max(id_resolucao), 0) from resolucao_questao;')
        seq_id = cur.fetchone()[0]
        agora = datetime.now()
        registradas = 0
        for item in respostas:
            id_q = int(item.get('id_questao', 0))
            if id_q <= 0:
                continue
            seq_id += 1
            resp_num = int(item.get('resposta_aluno', 0))
            acerto = bool(item.get('acerto', False))
            tempo = max(1, int(item.get('tempo_gasto', 1)))
            cur.execute(
                'insert into resolucao_questao (id_resolucao, id_questao, id_aluno, data, acerto, tempo_gasto, resposta_aluno) values (%s, %s, %s, %s, %s, %s, %s);',
                (seq_id, id_q, usuario['id_usuario'], agora, acerto, tempo, resp_num)
            )
            registradas += 1
        con.commit()
        return jsonify({'ok': True, 'registradas': registradas})
    except Exception as e:
        con.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 400
    finally:
        cur.close()
        con.close()


@app.route('/api/resolucao', methods=['POST'])
@requireLogin
def saveResolutionApi():
    usuario = getLoggedUser()
    if usuario['perfil'] != 'aluno':
        return jsonify({'ok': True, 'registrado': False})

    dados = request.get_json() or {}
    id_questao = int(dados.get('id_questao', 0))
    resposta_aluno = int(dados.get('resposta_aluno', 0))
    acerto = bool(dados.get('acerto', False))
    tempo_gasto = max(1, int(dados.get('tempo_gasto', 30)))

    con = connectDatabase()
    cur = con.cursor()
    try:
        cur.execute('select coalesce(max(id_resolucao), 0) + 1 from resolucao_questao;')
        novo_id = cur.fetchone()[0]
        cur.execute(
            'insert into resolucao_questao (id_resolucao, id_questao, id_aluno, data, acerto, tempo_gasto, resposta_aluno) values (%s, %s, %s, %s, %s, %s, %s);',
            (novo_id, id_questao, usuario['id_usuario'], datetime.now(), acerto, tempo_gasto, resposta_aluno)
        )
        con.commit()
        return jsonify({'ok': True, 'registrado': True, 'id_resolucao': novo_id})
    except Exception as e:
        con.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 400
    finally:
        cur.close()
        con.close()


@app.route('/api/questoes/<int:id_questao>/coruja', methods=['POST'])
@requireLogin
def askOwlApi(id_questao):
    usuario = getLoggedUser()
    dados = request.get_json(silent=True) or {}
    forcar = bool(dados.get('forcar')) and usuario['perfil'] in ('professor', 'gestao')

    con = connectDatabase()
    cur = con.cursor()
    try:
        cur.execute('select tipo, conteudo_texto from dica where id_questao = %s order by id_dica;', (id_questao,))
        existentes = cur.fetchall()
        cur.close()
        con.close()

        if not existentes or forcar:
            ok = ia_service.generateOwlHintAndSolution(id_questao)
            if not ok:
                return jsonify({'ok': False, 'erro': 'A Coruja não conseguiu analisar esta questão agora.'}), 400
            con = connectDatabase()
            cur = con.cursor()
            cur.execute('select tipo, conteudo_texto from dica where id_questao = %s order by id_dica;', (id_questao,))
            existentes = cur.fetchall()
            cur.close()
            con.close()

        dicas_fmt = [
            {'tipo': t, 'html': formatQuestionText(txt)}
            for t, txt in existentes
        ]
        return jsonify({'ok': True, 'dicas': dicas_fmt})
    except Exception as e:
        try:
            cur.close()
            con.close()
        except Exception:
            pass
        return jsonify({'ok': False, 'erro': str(e)}), 500


@app.route('/questoes/<int:id_questao>/gerar_dica', methods=['POST'])
@requireLogin
def generateOwlHintRoute(id_questao):
    ia_service.generateOwlHintAndSolution(id_questao)
    flash('A Coruja do PES preparou a dica e a resolução comentada!', 'sucesso')
    return redirect(url_for('questionsPage', questao=id_questao))


@app.route('/questoes/<int:id_questao>/excluir', methods=['POST'])
@requireRole('gestao')
def deleteQuestionRoute(id_questao):
    con = connectDatabase()
    cur = con.cursor()
    try:
        for tabela_filha in ['resolucao_questao', 'questao_lista', 'questao_tag', 'assunto_questao', 'midia', 'dica', 'alternativa']:
            cur.execute(f'delete from {tabela_filha} where id_questao = %s;', (id_questao,))
        cur.execute('delete from questao where id_questao = %s;', (id_questao,))
        con.commit()
        flash(f'Questão Q{id_questao:03d} excluída com sucesso.', 'sucesso')
    except Exception as e:
        con.rollback()
        flash(f'Erro ao excluir questão: {e}', 'erro')
    finally:
        cur.close()
        con.close()
    return redirect(url_for('questionsPage'))


# LISTAS DE EXERCICIOS e EXPORTACAO LATEX
@app.route('/listas')
@requireLogin
def listsPage():
    usuario = getLoggedUser()
    baixar_pdf = request.args.get('baixar_pdf', '').strip()
    baixar_gab = request.args.get('baixar_gab', '').strip()
    listas_visiveis = []
    todas_questoes = []
    disciplinas_unicas = []
    vestibulares_unicos = []
    anos_unicos = []

    try:
        con = connectDatabase()
        cur = con.cursor()

        cur.execute('select distinct nome from disciplina order by nome;')
        disciplinas_unicas = [r[0] for r in cur.fetchall()]

        cur.execute('select distinct instituicao from vestibular order by instituicao;')
        vestibulares_unicos = [r[0] for r in cur.fetchall()]

        cur.execute('select distinct ano from vestibular where ano is not null order by ano desc;')
        anos_unicos = [r[0] for r in cur.fetchall()]

        listas_visiveis = loadVisibleLists(cur, usuario)

        todas_questoes = loadQuestionsBatch(cur)
        cur.close()
        con.close()
    except Exception as e:
        flash(f'Erro ao carregar listas: {e}', 'erro')

    return render_template(
        'listas.html',
        pagina_ativa='listas',
        listas_visiveis=listas_visiveis,
        todas_questoes=todas_questoes,
        disciplinas_unicas=disciplinas_unicas,
        vestibulares_unicos=vestibulares_unicos,
        anos_unicos=anos_unicos,
        baixar_pdf=baixar_pdf,
        baixar_gab=baixar_gab
    )


@app.route('/listas/<int:id_lista>/excluir', methods=['POST'])
@requireLogin
def deleteListRoute(id_lista):
    usuario = getLoggedUser()
    origem = request.form.get('origem', 'listas').strip()
    destino = 'questionsPage' if origem == 'questoes' else 'listsPage'

    con = connectDatabase()
    cur = con.cursor()
    try:
        cur.execute('select titulo, id_usuario from lista_exercicio where id_lista = %s;', (id_lista,))
        row = cur.fetchone()
        if not row:
            flash('Lista não encontrada.', 'aviso')
            return redirect(url_for(destino))
        titulo_l, id_dono = row
        if usuario['perfil'] != 'gestao' and id_dono != usuario['id_usuario']:
            flash('Você não tem permissão para excluir esta lista.', 'erro')
            return redirect(url_for(destino))

        cur.execute('delete from questao_lista where id_lista = %s;', (id_lista,))
        cur.execute('delete from lista_exercicio where id_lista = %s;', (id_lista,))
        con.commit()
        flash(f'Lista "{titulo_l}" excluída com sucesso.', 'sucesso')
    except Exception as e:
        con.rollback()
        flash(f'Erro ao excluir lista: {e}', 'erro')
    finally:
        cur.close()
        con.close()
    return redirect(url_for(destino))


@app.route('/listas/criar', methods=['POST'])
@requireLogin
def createListRoute():
    usuario = getLoggedUser()
    titulo = request.form.get('titulo', '').strip()
    eh_docente_ou_gestao = usuario['perfil'] in ['professor', 'gestao']
    publica = (request.form.get('publica') == 'true') and eh_docente_ou_gestao
    acao_pos = request.form.get('acao_pos', 'salvar').strip()
    origem = request.form.get('origem', 'listas').strip()

    questoes_ids = request.form.getlist('questoes_ids')
    if not questoes_ids:
        csv_raw = request.form.get('questoes_ids_csv', '').strip()
        if csv_raw:
            questoes_ids = [p.strip() for p in csv_raw.split(',') if p.strip().isdigit()]

    ids_unicos = []
    for q_id in questoes_ids:
        try:
            v = int(q_id)
            if v not in ids_unicos:
                ids_unicos.append(v)
        except ValueError:
            pass

    destino_padrao = url_for('questionsPage') if origem == 'questoes' else url_for('listsPage')

    if not titulo:
        flash('Informe um título para a lista ou caderno.', 'aviso')
        return redirect(destino_padrao)

    if not ids_unicos:
        flash('Selecione ao menos uma questão para compor a lista.', 'aviso')
        return redirect(destino_padrao)

    con = connectDatabase()
    cur = con.cursor()
    try:
        cur.execute('select coalesce(max(id_lista), 0) + 1 from lista_exercicio;')
        novo_id = cur.fetchone()[0]
        cur.execute(
            'insert into lista_exercicio (id_lista, id_usuario, publica, titulo, data_criacao) values (%s, %s, %s, %s, %s);',
            (novo_id, usuario['id_usuario'], publica, titulo, datetime.now())
        )
        for q_id in ids_unicos:
            cur.execute('insert into questao_lista (id_questao, id_lista) values (%s, %s);', (q_id, novo_id))
        con.commit()

        tipo_msg = 'disponibilizada como tarefa para os alunos' if publica else 'salva como caderno privado'
        extra_pdf = ' O download do PDF foi iniciado.' if acao_pos in ('pdf', 'pdf_gabarito') else ''
        flash(f'Lista "{titulo}" ({len(ids_unicos)} questão(ões)) {tipo_msg}!{extra_pdf}', 'sucesso')

        params_redir = {}
        if acao_pos == 'pdf':
            params_redir['baixar_pdf'] = novo_id
        elif acao_pos == 'pdf_gabarito':
            params_redir['baixar_pdf'] = novo_id
            params_redir['baixar_gab'] = 1

        if origem == 'questoes':
            params_redir['lista'] = novo_id
            return redirect(url_for('questionsPage', **params_redir))
        return redirect(url_for('listsPage', **params_redir))
    except Exception as e:
        con.rollback()
        flash(f'Erro ao criar lista: {e}', 'erro')
    finally:
        cur.close()
        con.close()
    return redirect(destino_padrao)


def buildListLatex(id_lista, incluir_gabarito=False):
    con = connectDatabase()
    cur = con.cursor()
    cur.execute("""
        select l.titulo, u.nome, l.data_criacao
        from lista_exercicio l
        inner join usuario u on l.id_usuario = u.id_usuario
        where l.id_lista = %s;
    """, (id_lista,))
    info = cur.fetchone()
    if not info:
        cur.close()
        con.close()
        return None, None, []

    titulo_lista, autor_lista, data_criacao = info
    cur.execute('select id_questao from questao_lista where id_lista = %s order by id_questao;', (id_lista,))
    ids_q = {r[0] for r in cur.fetchall()}
    questoes = loadQuestionsBatch(cur, ids_filtro=ids_q)
    cur.close()
    con.close()

    with open(TEX_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template_tex = f.read()

    # Identifica as disciplinas/frentes
    frentes_unicas = []
    for q in questoes:
        for dn, df, _ in q['assuntos']:
            rotulo = dn if df.lower() in ('única', 'unica') else f'{dn} {df}'
            if rotulo not in frentes_unicas:
                frentes_unicas.append(rotulo)
    disciplina_cabecalho = ', '.join(frentes_unicas[:3]) if frentes_unicas else 'Geral'
    if len(frentes_unicas) > 3:
        disciplina_cabecalho += ' e outras'

    blocos_q = []
    gabaritos = []
    imagens_anexas = []
    letras = ['a', 'b', 'c', 'd', 'e']

    for idx, q in enumerate(questoes, start=1):
        inst_up = (q['instituicao'] or '').strip().upper()
        if inst_up == 'ENEM':
            macro_banca = r'\enem'
        elif inst_up == 'UFSC':
            macro_banca = r'\ufsc'
        elif inst_up == 'UDESC':
            macro_banca = r'\udesc'
        else:
            macro_banca = r'\aleatorio'

        enunc_tex = escapeLatexPreservingMath(q['enunciado'])

        # Anexa figuras
        bloco_midia = ''
        for _, arq in q['midias']:
            if arq and arq.startswith('uploads/'):
                caminho_real = os.path.join(BASE_DIR, 'static', arq.replace('/', os.sep))
                if os.path.exists(caminho_real):
                    nome_img = os.path.basename(caminho_real)
                    imagens_anexas.append((caminho_real, nome_img))
                    bloco_midia += (
                        "\\begin{center}\n"
                        f"    \\includegraphics[width=0.82\\columnwidth,keepaspectratio]{{assets/{nome_img}}}\n"
                        "\\end{center}\n"
                    )

        itens_tex = []
        rotulo_correto = '-'
        if q['tipo'] == 'Somatoria':
            for _, val_p, txt_a, _ in q['alternativas']:
                txt_limpo = escapeLatexPreservingMath(stripOptionPrefix(txt_a))
                itens_tex.append(f"    \\item[\\textbf{{{val_p:02d}.}}] {txt_limpo}")
            bloco_opcoes = (
                "\\begin{opcoessoma}\n"
                + "\n".join(itens_tex)
                + "\n\\end{opcoessoma}\n\n\\soma\n"
            )
            rotulo_correto = f"{q['soma_correta']:02d}"
        else:
            for j, (_, _, txt_a, corr) in enumerate(q['alternativas']):
                txt_limpo = escapeLatexPreservingMath(stripOptionPrefix(txt_a))
                itens_tex.append(f"    \\item {txt_limpo}")
                if corr:
                    rotulo_correto = letras[j % 5]
            bloco_opcoes = (
                "\\begin{opcoes}\n"
                + "\n".join(itens_tex)
                + "\n\\end{opcoes}\n"
            )

        bloco = f"{macro_banca}\n\n{enunc_tex}\n\n{bloco_midia}{bloco_opcoes}\n"
        blocos_q.append(bloco)
        gabaritos.append((idx, rotulo_correto))

    secao_gabarito = ''
    if incluir_gabarito and gabaritos:
        tabelas_gab = []
        for i in range(0, len(gabaritos), 5):
            lote = gabaritos[i:i + 5]
            cols_spec = 'c' * len(lote)
            cab = ' & '.join(f'\\textbf{{{n}}}' for n, _ in lote)
            vals = ' & '.join(resp for _, resp in lote)
            tabelas_gab.append(
                f"    \\begin{{tabular}}{{{cols_spec}}}\n"
                f"        \\toprule\n"
                f"        {cab} \\\\\n"
                f"        \\midrule\n"
                f"        {vals} \\\\\n"
                f"        \\bottomrule\n"
                f"    \\end{{tabular}}"
            )
        secao_gabarito = (
            "\\vspace{6mm}\n\n"
            "\\begin{center}\n"
            "    \\colorbox{black!85}{\n"
            "        \\textcolor{white}{\n"
            "            \\textbf{\\faCheckDouble\\ GABARITO OFICIAL}\n"
            "        }\n"
            "    }\\\\[6pt]\n\n"
            "    \\rowcolors{1}{white}{black!5}\n"
            "    \\renewcommand{\\arraystretch}{1.2}\n\n"
            + "\\\\[8pt]\n".join(tabelas_gab)
            + "\n\\end{center}\n"
        )

    tex_final = (
        template_tex
        .replace('%%NOMELISTA%%', escapeLatexPreservingMath(titulo_lista.upper()))
        .replace('%%DISCIPLINA%%', escapeLatexPreservingMath(disciplina_cabecalho))
        .replace('%%QUESTOES%%', '\n'.join(blocos_q))
        .replace('%%SECAO_GABARITO%%', secao_gabarito)
    )
    return titulo_lista, tex_final, imagens_anexas


@app.route('/listas/<int:id_lista>/pdf')
@requireLogin
def exportListPdf(id_lista):
    incluir_gab = request.args.get('gabarito') == '1'
    titulo, tex_final, imagens_anexas = buildListLatex(id_lista, incluir_gabarito=incluir_gab)
    if not tex_final:
        flash('Lista não encontrada.', 'erro')
        return redirect(url_for('listsPage'))

    pdflatex_bin = shutil.which('pdflatex')
    if not pdflatex_bin:
        flash('Compilador pdflatex não encontrado.', 'aviso')
        return redirect(url_for('listsPage'))

    with tempfile.TemporaryDirectory() as tmpdir:
        assets_dir = os.path.join(tmpdir, 'assets')
        os.makedirs(assets_dir, exist_ok=True)

        # Copia a logo para assets/logo-pes.png
        logo_png = os.path.join(BASE_DIR, 'static', 'img', 'logo-pes.png')
        if os.path.exists(logo_png):
            shutil.copy2(logo_png, os.path.join(assets_dir, 'logo-pes.png'))

        # Copia as figuras anexadas das questoes para assets/
        for origem, nome_img in imagens_anexas:
            shutil.copy2(origem, os.path.join(assets_dir, nome_img))

        tex_path = os.path.join(tmpdir, 'lista.tex')
        pdf_path = os.path.join(tmpdir, 'lista.pdf')
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(tex_final)

        try:
            cmd = [pdflatex_bin, '-interaction=nonstopmode', '-halt-on-error']
            if os.name == 'nt':
                cmd.append('--enable-installer')
            cmd.extend(['-output-directory', tmpdir, tex_path])
            subprocess.run(
                cmd,
                cwd=tmpdir,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )
            if os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as fp:
                    pdf_bytes = fp.read()
                sufixo = '_gabarito' if incluir_gab else ''
                nome_pdf = secure_filename(f'PES_lista_{id_lista}{sufixo}.pdf')
                return send_file(
                    io.BytesIO(pdf_bytes),
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=nome_pdf
                )
        except subprocess.TimeoutExpired:
            flash('A geração do PDF demorou além do esperado.', 'aviso')
            return redirect(url_for('listsPage'))
        except Exception as e:
            flash(f'Erro ao compilar PDF: {e}', 'erro')
            return redirect(url_for('listsPage'))

    flash('Não foi possível gerar o PDF.', 'aviso')
    return redirect(url_for('listsPage'))


# CADASTRO E IMPORTACAO DE PROVAS
@app.route('/questoes/nova')
@requireRole('professor', 'gestao')
def newQuestionPage():
    assuntos = []
    disciplinas_lista = []
    vestibulares = []
    pendentes_revisao = 0
    try:
        con = connectDatabase()
        cur = con.cursor()
        cur.execute("""
            select a.id_assunto, d.nome, d.frente, a.nome
            from assunto a
            inner join disciplina d on a.id_disciplina = d.id_disciplina
            order by d.nome, d.frente, a.nome;
        """)
        assuntos = cur.fetchall()
        cur.execute('select id_disciplina, nome, frente from disciplina order by nome, frente;')
        disciplinas_lista = cur.fetchall()
        cur.execute('select id_vestibular, instituicao, ano, edicao from vestibular order by ano desc, instituicao;')
        vestibulares = cur.fetchall()
        cur.execute("""
            select count(distinct p.id_questao)
            from questao_tag p
            inner join tag t on p.id_tag = t.id_tag
            where lower(t.nome) = any(%s);
        """, ([t.lower() for t in importadores.TAGS_REVISAO],))
        pendentes_revisao = cur.fetchone()[0]
        cur.close()
        con.close()
    except Exception as e:
        flash(f'Erro ao carregar opções de cadastro: {e}', 'erro')

    return render_template(
        'cadastro_questao.html',
        pagina_ativa='cadastro',
        assuntos=assuntos,
        disciplinas_lista=disciplinas_lista,
        vestibulares=vestibulares,
        pendentes_revisao=pendentes_revisao,
        areas_enem=importadores.AREAS_ENEM,
        anos_enem=list(range(2023, 2008, -1))
    )


@app.route('/api/assuntos/novo', methods=['POST'])
@requireRole('professor', 'gestao')
def createTopicApi():
    dados = request.get_json(silent=True) or {}
    nome = (dados.get('nome') or '').strip()
    id_disc_raw = dados.get('id_disciplina')
    if not nome or not str(id_disc_raw).isdigit():
        return jsonify({'ok': False, 'erro': 'Selecione a disciplina e informe o nome do conteúdo.'}), 400
    if len(nome) > 100:
        nome = nome[:100]

    id_disc = int(id_disc_raw)
    con = connectDatabase()
    cur = con.cursor()
    try:
        cur.execute('select nome, frente from disciplina where id_disciplina = %s;', (id_disc,))
        disc = cur.fetchone()
        if not disc:
            return jsonify({'ok': False, 'erro': 'Disciplina não encontrada.'}), 404
        d_nome, d_frente = disc

        cur.execute(
            'select id_assunto, nome from assunto where id_disciplina = %s and lower(trim(nome)) = lower(%s) limit 1;',
            (id_disc, nome)
        )
        existente = cur.fetchone()
        if existente:
            return jsonify({
                'ok': True,
                'id_assunto': existente[0],
                'label': f'{d_nome} ({d_frente}) — {existente[1]}',
                'existente': True
            })

        cur.execute('select coalesce(max(id_assunto), 0) + 1 from assunto;')
        novo_id = cur.fetchone()[0]
        cur.execute(
            'insert into assunto (id_assunto, id_disciplina, nome) values (%s, %s, %s);',
            (novo_id, id_disc, nome)
        )
        con.commit()
        return jsonify({
            'ok': True,
            'id_assunto': novo_id,
            'label': f'{d_nome} ({d_frente}) — {nome}',
            'existente': False
        })
    except Exception as e:
        con.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 400
    finally:
        cur.close()
        con.close()


@app.route('/api/questoes/<int:id_questao>/reportar', methods=['POST'])
@requireLogin
def reportQuestionApi(id_questao):
    usuario = getLoggedUser()
    dados = request.get_json() or {}
    motivos = dados.get('motivos') or []
    detalhes = (dados.get('detalhes') or '').strip()

    mapa_motivos = {
        'materia': importadores.TAG_REVISAR_MATERIA,
        'gabarito': importadores.TAG_ERRO_GABARITO,
        'gramatica': importadores.TAG_ERRO_GRAMATICA,
        'formatacao': importadores.TAG_ERRO_FORMATACAO,
    }
    tags_escolhidas = [mapa_motivos[m] for m in motivos if m in mapa_motivos]
    if not tags_escolhidas:
        return jsonify({'ok': False, 'erro': 'Selecione ao menos um tipo de problema.'}), 400

    con = connectDatabase()
    cur = con.cursor()
    try:
        for nome_tag in tags_escolhidas:
            id_t = importadores.getOrCreateTagByName(cur, nome_tag)
            cur.execute(
                'insert into questao_tag (id_tag, id_questao) values (%s, %s) on conflict do nothing;',
                (id_t, id_questao)
            )
        con.commit()

        if detalhes:
            relatos = loadReviewReports()
            chave = str(id_questao)
            relatos.setdefault(chave, []).append({
                'autor': usuario['nome'],
                'perfil': usuario['perfil'],
                'motivos': tags_escolhidas,
                'detalhes': detalhes,
                'data': datetime.now().strftime('%d/%m/%Y %H:%M')
            })
            saveReviewReports(relatos)

        return jsonify({'ok': True, 'tags': tags_escolhidas})
    except Exception as e:
        con.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 400
    finally:
        cur.close()
        con.close()


@app.route('/questoes/revisar')
@requireRole('professor', 'gestao')
def reviewQuestionsPage():
    filtro_tag = request.args.get('tag', '').strip()
    questoes_pendentes = []
    assuntos = []
    disciplinas_lista = []
    anos_enem_bd = []
    total_enem_bd = 0
    contagem_tags = {t: 0 for t in importadores.TAGS_REVISAO}
    relatos = loadReviewReports()

    try:
        con = connectDatabase()
        cur = con.cursor()
        cur.execute("""
            select a.id_assunto, d.nome, d.frente, a.nome
            from assunto a
            inner join disciplina d on a.id_disciplina = d.id_disciplina
            order by d.nome, d.frente, a.nome;
        """)
        assuntos = cur.fetchall()
        cur.execute('select id_disciplina, nome, frente from disciplina order by nome, frente;')
        disciplinas_lista = cur.fetchall()

        cur.execute("""
            select v.ano, count(*)
            from questao q
            inner join vestibular v on q.id_vestibular = v.id_vestibular
            where upper(v.instituicao) = 'ENEM'
            group by v.ano
            order by v.ano desc;
        """)
        anos_enem_bd = cur.fetchall()
        total_enem_bd = sum(r[1] for r in anos_enem_bd)

        tags_lower = [t.lower() for t in importadores.TAGS_REVISAO]
        cur.execute("""
            select t.nome, count(distinct p.id_questao)
            from questao_tag p
            inner join tag t on p.id_tag = t.id_tag
            where lower(t.nome) = any(%s)
            group by t.nome;
        """, (tags_lower,))
        for t_nome, cnt in cur.fetchall():
            for ref in importadores.TAGS_REVISAO:
                if ref.lower() == t_nome.lower():
                    contagem_tags[ref] = cnt

        if filtro_tag:
            cur.execute("""
                select distinct p.id_questao
                from questao_tag p
                inner join tag t on p.id_tag = t.id_tag
                where lower(t.nome) = lower(%s)
                order by p.id_questao;
            """, (filtro_tag,))
        else:
            cur.execute("""
                select distinct p.id_questao
                from questao_tag p
                inner join tag t on p.id_tag = t.id_tag
                where lower(t.nome) = any(%s)
                order by p.id_questao;
            """, (tags_lower,))
        ids_rev = {r[0] for r in cur.fetchall()}

        if ids_rev:
            questoes_pendentes = loadQuestionsBatch(cur, ids_filtro=ids_rev)
            cur.execute('select id_questao, min(id_assunto) from assunto_questao where id_questao = any(%s) group by id_questao;', (list(ids_rev),))
            mapa_ass_atual = dict(cur.fetchall())
            for q in questoes_pendentes:
                q['id_assunto_atual'] = mapa_ass_atual.get(q['id_questao'])
                q['tags_revisao'] = [t for t in q['tags'] if t.lower() in tags_lower]
                q['relatos'] = relatos.get(str(q['id_questao']), [])
        cur.close()
        con.close()
    except Exception as e:
        flash(f'Erro ao carregar fila de revisão: {e}', 'erro')

    return render_template(
        'revisar_questoes.html',
        pagina_ativa='cadastro',
        questoes_pendentes=questoes_pendentes,
        assuntos=assuntos,
        disciplinas_lista=disciplinas_lista,
        anos_enem_bd=anos_enem_bd,
        total_enem_bd=total_enem_bd,
        contagem_tags=contagem_tags,
        filtro_tag=filtro_tag,
        tags_revisao_lista=importadores.TAGS_REVISAO
    )


@app.route('/questoes/revisar/salvar', methods=['POST'])
@requireRole('professor', 'gestao')
def saveQuestionReviewRoute():
    con = connectDatabase()
    cur = con.cursor()
    atualizadas = 0
    relatos = loadReviewReports()
    relatos_mudou = False
    try:
        tags_lower = [t.lower() for t in importadores.TAGS_REVISAO]
        cur.execute('select id_tag from tag where lower(nome) = any(%s);', (tags_lower,))
        ids_tags_rev = [r[0] for r in cur.fetchall()]

        id_unico = request.form.get('id_questao_unica', '').strip()

        def clearReviewPending(iq):
            nonlocal relatos_mudou
            if ids_tags_rev:
                cur.execute('delete from questao_tag where id_questao = %s and id_tag = any(%s);', (iq, ids_tags_rev))
            if str(iq) in relatos:
                del relatos[str(iq)]
                relatos_mudou = True

        if id_unico and id_unico.isdigit():
            iq = int(id_unico)
            ia = int(request.form.get(f'assunto_{iq}', request.form.get('id_assunto', 0)))
            if ia > 0:
                cur.execute('delete from assunto_questao where id_questao = %s;', (iq,))
                cur.execute('insert into assunto_questao (id_questao, id_assunto) values (%s, %s);', (iq, ia))

            novo_enunc = request.form.get(f'enunciado_{iq}')
            if novo_enunc is not None and novo_enunc.strip():
                cur.execute('update questao set enunciado = %s where id_questao = %s;', (novo_enunc.strip(), iq))

            cur.execute('select id_alternativa from alternativa where id_questao = %s;', (iq,))
            alt_ids = [r[0] for r in cur.fetchall()]
            if any(f'alt_texto_{aid}' in request.form for aid in alt_ids):
                for aid in alt_ids:
                    txt_a = request.form.get(f'alt_texto_{aid}')
                    corr_a = (f'alt_correta_{aid}' in request.form)
                    if txt_a is not None:
                        cur.execute(
                            'update alternativa set texto = %s, indicador_correta = %s where id_alternativa = %s;',
                            (txt_a.strip(), corr_a, aid)
                        )

            clearReviewPending(iq)
            atualizadas = 1
        else:
            for chave, val in request.form.items():
                if chave.startswith('assunto_') and val.isdigit():
                    iq_str = chave.replace('assunto_', '')
                    if iq_str.isdigit():
                        iq = int(iq_str)
                        ia = int(val)
                        cur.execute('delete from assunto_questao where id_questao = %s;', (iq,))
                        cur.execute('insert into assunto_questao (id_questao, id_assunto) values (%s, %s);', (iq, ia))
                        clearReviewPending(iq)
                        atualizadas += 1
        con.commit()
        if relatos_mudou:
            saveReviewReports(relatos)
        flash(f'{atualizadas} questão(ões) revisada(s) e corrigida(s) com sucesso!', 'sucesso')
    except Exception as e:
        con.rollback()
        flash(f'Erro ao salvar revisão: {e}', 'erro')
    finally:
        cur.close()
        con.close()
    return redirect(url_for('reviewQuestionsPage'))


@app.route('/questoes/reclassificar_enem', methods=['POST'])
@requireRole('gestao')
def reclassifyEnemRoute():
    ano_str = request.form.get('ano_enem', '').strip()
    ano_filtro = int(ano_str) if ano_str.isdigit() else None
    arq_csv = request.files.get('microdados_inep_csv')
    csv_bytes = arq_csv.read() if (arq_csv and arq_csv.filename) else None

    total, alta, rev, msg = importadores.reclassifyExistingEnem(
        ano_filtro=ano_filtro,
        microdados_csv_bytes=csv_bytes
    )
    flash(msg, 'sucesso' if total > 0 else 'aviso')
    return redirect(url_for('reviewQuestionsPage'))


@app.route('/questoes/importar_enem', methods=['POST'])
@requireRole('professor', 'gestao')
def importEnemRoute():
    usuario = getLoggedUser()
    ano = int(request.form.get('ano_enem', 2023))
    modo = request.form.get('modo_enem', 'inteira')
    id_prof = usuario['id_usuario'] if usuario['perfil'] == 'professor' else None
    id_gest = usuario['id_usuario'] if usuario['perfil'] == 'gestao' else None

    if modo != 'unica' and usuario['perfil'] != 'gestao':
        flash('A importação de provas inteiras é exclusiva da equipe de Gestão.', 'erro')
        return redirect(url_for('newQuestionPage'))

    if modo == 'unica':
        numero = request.form.get('numero_questao', '').strip()
        if not numero:
            flash('Informe o número da questão do ENEM.', 'erro')
            return redirect(url_for('newQuestionPage'))
        id_assunto = int(request.form.get('id_assunto', 1))
        dificuldade = request.form.get('dificuldade', 'Media')
        try:
            ids, msg = importadores.importSingleEnemQuestion(
                ano=ano,
                numero_questao=int(numero),
                id_assunto=id_assunto,
                upload_dir=UPLOAD_DIR,
                id_professor=id_prof,
                id_gestao=id_gest,
                dificuldade=dificuldade
            )
            flash(msg, 'sucesso' if ids else 'aviso')
            if ids:
                if len(ids) == 1:
                    return redirect(url_for('questionsPage', questao=ids[0]))
                return redirect(url_for('questionsPage', ids=','.join(map(str, ids))))
        except Exception as e:
            flash(f'Erro ao buscar questão na API do ENEM: {e}', 'erro')
        return redirect(url_for('newQuestionPage'))
    
    arq_csv = request.files.get('microdados_inep_csv')
    csv_bytes = arq_csv.read() if (arq_csv and arq_csv.filename) else None

    job_id = uuid.uuid4().hex
    JOBS_IMPORTACAO[job_id] = {
        'estado': 'processando',
        'mensagem': f'Iniciando importação completa do ENEM {ano}...',
        'ids': []
    }

    def runEnemTask():
        try:
            def updateProgress(msg):
                JOBS_IMPORTACAO[job_id]['mensagem'] = msg

            ids, msg = importadores.importFullEnemExam(
                ano=ano,
                upload_dir=UPLOAD_DIR,
                id_professor=id_prof,
                id_gestao=id_gest,
                callback_progresso=updateProgress,
                microdados_csv_bytes=csv_bytes
            )
            JOBS_IMPORTACAO[job_id] = {
                'estado': 'concluido' if ids else 'erro',
                'mensagem': msg,
                'ids': ids
            }
        except Exception as e:
            JOBS_IMPORTACAO[job_id] = {
                'estado': 'erro',
                'mensagem': f'Erro ao importar ENEM {ano}: {e}',
                'ids': []
            }

    threading.Thread(target=runEnemTask, daemon=True).start()
    return redirect(url_for('importStatusPage', job_id=job_id))


@app.route('/questoes/importar_prova_pdf', methods=['POST'])
@app.route('/questoes/importar_ufsc_pdf', methods=['POST'])
@requireRole('gestao')
def importExamPdfRoute():
    usuario = getLoggedUser()
    arquivo = request.files.get('pdf_prova') or request.files.get('pdf_ufsc')
    arq_gabarito = request.files.get('pdf_gabarito') or request.files.get('pdf_gabarito_ufsc')
    arq_csv = request.files.get('microdados_inep_csv')
    gabarito_str = (request.form.get('gabarito_manual') or request.form.get('gabarito_ufsc') or '').strip()
    id_assunto = request.form.get('id_assunto', 'auto').strip()
    id_vestibular = resolveExamIdFromForm(request.form)
    dificuldade = request.form.get('dificuldade', 'Media')

    if not arquivo or not arquivo.filename.lower().endswith('.pdf'):
        flash('Envie o PDF oficial da prova no formato .pdf.', 'erro')
        return redirect(url_for('newQuestionPage'))

    gabarito_pdf_bytes = arq_gabarito.read() if (arq_gabarito and arq_gabarito.filename.lower().endswith('.pdf')) else None
    csv_bytes = arq_csv.read() if (arq_csv and arq_csv.filename) else None

    id_prof = usuario['id_usuario'] if usuario['perfil'] == 'professor' else None
    id_gest = usuario['id_usuario'] if usuario['perfil'] == 'gestao' else None

    try:
        ids, msg = importadores.importUnifiedExamPdf(
            pdf_bytes=arquivo.read(),
            id_vestibular=id_vestibular,
            id_assunto=id_assunto,
            upload_dir=UPLOAD_DIR,
            id_professor=id_prof,
            id_gestao=id_gest,
            dificuldade=dificuldade,
            gabarito_pdf_bytes=gabarito_pdf_bytes,
            gabarito_str=gabarito_str,
            microdados_csv_bytes=csv_bytes
        )
        flash(msg, 'sucesso' if ids else 'aviso')
        if ids:
            if len(ids) == 1:
                return redirect(url_for('questionsPage', questao=ids[0]))
            return redirect(url_for('questionsPage', ids=','.join(map(str, ids))))
    except Exception as e:
        flash(f'Erro ao processar PDF da prova: {e}', 'erro')
    return redirect(url_for('newQuestionPage'))


def resolveExamIdFromForm(form):
    # retorna id existente, cria Autoral ou cria um novo vestibular
    val = form.get('id_vestibular', '1').strip()
    if val == 'autoral':
        ano_atual = datetime.now().year
        con = connectDatabase()
        cur = con.cursor()
        try:
            cur.execute("select id_vestibular from vestibular where lower(instituicao) = 'autoral' order by ano desc limit 1;")
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute('select coalesce(max(id_vestibular), 0) + 1 from vestibular;')
            novo_id = cur.fetchone()[0]
            cur.execute(
                'insert into vestibular (id_vestibular, ano, edicao, instituicao) values (%s, %s, %s, %s);',
                (novo_id, ano_atual, f'Questões Autorais PES {ano_atual}', 'Autoral')
            )
            con.commit()
            return novo_id
        finally:
            cur.close()
            con.close()

    if val != 'novo':
        return int(val)

    inst = form.get('novo_vest_instituicao', '').strip()
    ano = int(form.get('novo_vest_ano', datetime.now().year) or datetime.now().year)
    edicao = form.get('novo_vest_edicao', '').strip() or f'{inst} {ano}'

    con = connectDatabase()
    cur = con.cursor()
    try:
        cur.execute('select coalesce(max(id_vestibular), 0) + 1 from vestibular;')
        novo_id = cur.fetchone()[0]
        cur.execute(
            'insert into vestibular (id_vestibular, ano, edicao, instituicao) values (%s, %s, %s, %s);',
            (novo_id, ano, edicao, inst)
        )
        con.commit()
        return novo_id
    finally:
        cur.close()
        con.close()


@app.route('/questoes/importar', methods=['POST'])
@requireRole('professor', 'gestao')
def importFileRoute():
    usuario = getLoggedUser()
    arquivo = request.files.get('arquivo_prova')
    id_assunto = request.form.get('id_assunto', 'auto').strip()
    id_vestibular = resolveExamIdFromForm(request.form)
    gabarito_ia = request.form.get('gabarito_ia', '').strip()

    if not arquivo or not arquivo.filename:
        flash('Selecione um arquivo PDF ou imagem.', 'erro')
        return redirect(url_for('newQuestionPage'))

    nome_seguro = secure_filename(arquivo.filename)
    ext = os.path.splitext(nome_seguro)[1].lower()
    mime_map = {
        '.pdf': 'application/pdf',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.webp': 'image/webp'
    }
    mime_type = mime_map.get(ext)
    if not mime_type:
        flash('Formato não suportado. Envie arquivos PDF, PNG, JPG ou WEBP.', 'erro')
        return redirect(url_for('newQuestionPage'))

    conteudo_bytes = arquivo.read()
    caminho_midia = None
    figura_arq = request.files.get('figura_midia')
    if figura_arq and figura_arq.filename:
        nome_fig = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(figura_arq.filename)}"
        figura_arq.save(os.path.join(UPLOAD_DIR, nome_fig))
        caminho_midia = f'uploads/{nome_fig}'

    id_prof = usuario['id_usuario'] if usuario['perfil'] == 'professor' else None
    id_gest = usuario['id_usuario'] if usuario['perfil'] == 'gestao' else None

    job_id = uuid.uuid4().hex
    JOBS_IMPORTACAO[job_id] = {'estado': 'processando', 'mensagem': 'Preparando arquivo para leitura pela IA...', 'ids': []}

    def runImportTask():
        try:
            def updateProgress(msg):
                JOBS_IMPORTACAO[job_id]['mensagem'] = msg

            questoes_extraidas = ia_service.extractQuestionsFromFile(
                conteudo_bytes,
                mime_type,
                gabarito_hint=gabarito_ia,
                callback_progresso=updateProgress
            )
            if not questoes_extraidas:
                JOBS_IMPORTACAO[job_id] = {
                    'estado': 'erro',
                    'mensagem': 'Não foi possível identificar questões objetivas neste arquivo. Tente um print/PDF mais nítido ou use o cadastro manual.',
                    'ids': []
                }
                return
            JOBS_IMPORTACAO[job_id]['mensagem'] = f'Gravando {len(questoes_extraidas)} questão(ões) no banco de dados...'
            ids = ia_service.saveExtractedQuestions(
                questoes_extraidas,
                id_vestibular=id_vestibular,
                id_assunto=id_assunto,
                id_professor=id_prof,
                id_gestao=id_gest,
                arquivo_midia=caminho_midia,
                legenda_midia=f'Arquivo importado: {nome_seguro}'
            )
            if ids:
                JOBS_IMPORTACAO[job_id] = {
                    'estado': 'concluido',
                    'mensagem': f'{len(ids)} questão(ões) importada(s) com IA!',
                    'ids': ids
                }
            else:
                JOBS_IMPORTACAO[job_id] = {'estado': 'erro', 'mensagem': 'Erro ao gravar as questões no banco de dados.', 'ids': []}
        except Exception as e:
            JOBS_IMPORTACAO[job_id] = {'estado': 'erro', 'mensagem': f'Falha na extração com IA: {e}', 'ids': []}

    threading.Thread(target=runImportTask, daemon=True).start()
    return redirect(url_for('importStatusPage', job_id=job_id))


@app.route('/questoes/importar/<job_id>')
@requireRole('professor', 'gestao')
def importStatusPage(job_id):
    if job_id not in JOBS_IMPORTACAO:
        flash('Importação não encontrada.', 'erro')
        return redirect(url_for('newQuestionPage'))
    return render_template('importacao_status.html', pagina_ativa='cadastro', job_id=job_id)


@app.route('/api/importacao/<job_id>')
@requireRole('professor', 'gestao')
def importStatusApi(job_id):
    return jsonify(JOBS_IMPORTACAO.get(job_id, {'estado': 'erro', 'mensagem': 'Importação não encontrada.', 'ids': []}))


@app.route('/questoes/cadastrar', methods=['POST'])
@requireRole('professor', 'gestao')
def createManualQuestionRoute():
    usuario = getLoggedUser()
    id_vestibular = resolveExamIdFromForm(request.form)
    id_assunto = int(request.form.get('id_assunto', 1))
    tipo = request.form.get('tipo', 'Somatoria')
    dificuldade = request.form.get('dificuldade', 'Media')
    enunciado = request.form.get('enunciado', '').strip()
    dica_inicial = request.form.get('dica_inicial', '').strip()
    resolucao_passo = request.form.get('resolucao_passo', '').strip()

    id_prof = usuario['id_usuario'] if usuario['perfil'] == 'professor' else None
    id_gest = usuario['id_usuario'] if usuario['perfil'] == 'gestao' else None

    caminho_midia = None
    img = request.files.get('imagem_midia')
    if img and img.filename:
        nome_final = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(img.filename)}"
        img.save(os.path.join(UPLOAD_DIR, nome_final))
        caminho_midia = f'uploads/{nome_final}'

    con = connectDatabase()
    cur = con.cursor()
    try:
        cur.execute('select coalesce(max(id_questao), 0) + 1 from questao;')
        novo_id_q = cur.fetchone()[0]
        cur.execute(
            'insert into questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) values (%s, %s, %s, %s, %s, %s, %s);',
            (novo_id_q, id_vestibular, id_prof, id_gest, tipo, dificuldade, enunciado)
        )
        cur.execute('insert into assunto_questao (id_questao, id_assunto) values (%s, %s);', (novo_id_q, id_assunto))

        cur.execute('select coalesce(max(id_alternativa), 0) from alternativa;')
        max_alt = cur.fetchone()[0]
        seq = 0
        for val_p in [1, 2, 4, 8, 16, 32, 64]:
            txt = request.form.get(f'prop_texto_{val_p}', '').strip()
            if txt:
                seq += 1
                correta = request.form.get(f'prop_correta_{val_p}') == 'on'
                valor_salvo = val_p if tipo == 'Somatoria' else seq
                cur.execute(
                    'insert into alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) values (%s, %s, %s, %s, %s);',
                    (max_alt + seq, novo_id_q, valor_salvo, txt, correta)
                )

        cur.execute('select coalesce(max(id_dica), 0) from dica;')
        max_dica = cur.fetchone()[0]
        if dica_inicial:
            max_dica += 1
            cur.execute('insert into dica (id_dica, id_questao, tipo, conteudo_texto) values (%s, %s, %s, %s);', (max_dica, novo_id_q, 'Dica Inicial', dica_inicial))
        if resolucao_passo:
            max_dica += 1
            cur.execute('insert into dica (id_dica, id_questao, tipo, conteudo_texto) values (%s, %s, %s, %s);', (max_dica, novo_id_q, 'Resolução Passo a Passo', resolucao_passo))

        if caminho_midia:
            cur.execute('select coalesce(max(id_midia), 0) + 1 from midia;')
            novo_id_m = cur.fetchone()[0]
            cur.execute('insert into midia (id_midia, id_questao, legenda, arquivo) values (%s, %s, %s, %s);', (novo_id_m, novo_id_q, 'Figura da questão', caminho_midia))

        con.commit()
        flash(f'Questão Q{novo_id_q:03d} cadastrada com sucesso!', 'sucesso')
        return redirect(url_for('questionsPage', questao=novo_id_q))
    except Exception as e:
        con.rollback()
        flash(f'Erro ao cadastrar questão: {e}', 'erro')
        return redirect(url_for('newQuestionPage'))
    finally:
        cur.close()
        con.close()


# RELATORIOS PEDAGOGICOS
@app.route('/relatorios')
@requireRole('professor', 'gestao')
def reportsPage():
    lista_relatorios = []
    resumo_kpi = {
        'total_questoes': 0,
        'total_resolucoes': 0,
        'taxa_acerto': 0.0,
        'tempo_medio': 0,
        'total_alunos_ativos': 0,
    }
    try:
        con = connectDatabase()
        cur = con.cursor()

        cur.execute('select count(*) from questao;')
        resumo_kpi['total_questoes'] = cur.fetchone()[0]

        cur.execute("""
            select count(*),
                   coalesce(sum(case when acerto then 1 else 0 end), 0),
                   coalesce(avg(tempo_gasto), 0),
                   count(distinct id_aluno)
            from resolucao_questao;
        """)
        tot_r, ac_r, t_med, al_at = cur.fetchone()
        resumo_kpi['total_resolucoes'] = tot_r
        resumo_kpi['taxa_acerto'] = round((ac_r / tot_r * 100.0), 1) if tot_r else 0.0
        resumo_kpi['tempo_medio'] = int(round(float(t_med or 0)))
        resumo_kpi['total_alunos_ativos'] = al_at

        # 1. Desempenho e Tempo Medio por Disciplina e Frente
        cur.execute("""
            select d.nome || ' ' || d.frente as disciplina_frente,
                   count(r.id_resolucao) as total_resolucoes,
                   round(100.0 * sum(case when r.acerto then 1 else 0 end) / greatest(count(r.id_resolucao), 1), 1) as taxa_acerto,
                   round(avg(r.tempo_gasto)::numeric, 1) as tempo_medio_seg
            from resolucao_questao r
            inner join questao q on r.id_questao = q.id_questao
            inner join assunto_questao ab on q.id_questao = ab.id_questao
            inner join assunto a on ab.id_assunto = a.id_assunto
            inner join disciplina d on a.id_disciplina = d.id_disciplina
            group by d.nome, d.frente
            order by total_resolucoes desc;
        """)
        rows1 = cur.fetchall()
        lista_relatorios.append({
            'id': 'chart-disciplina',
            'titulo': 'Desempenho e Tempo Médio por Disciplina e Frente',
            'descricao': 'Volume de resoluções, taxa de acerto (%) e tempo médio gasto pelos estudantes em cada frente do cursinho.',
            'colunas': ['Disciplina / Frente', 'Resoluções', 'Acerto (%)', 'Tempo Médio (s)'],
            'linhas': [[r[0], int(r[1]), f'{float(r[2]):.1f}%', float(r[3])] for r in rows1],
            'chart': {
                'type': 'bar',
                'labels': [r[0] for r in rows1],
                'datasets': [
                    {'label': 'Tempo Médio (s)', 'data': [float(r[3]) for r in rows1], 'color': '#5E1728'},
                    {'label': 'Taxa de Acerto (%)', 'data': [float(r[2]) for r in rows1], 'color': '#265321'},
                ]
            }
        })

        # 2. Engajamento dos Estudantes nas Turmas A e B
        cur.execute("""
            select u.nome || ' (Turma ' || al.turma || ')' as aluno_turma,
                   count(r.id_resolucao) as questoes_resolvidas,
                   sum(case when r.acerto then 1 else 0 end) as acertos,
                   round(avg(r.tempo_gasto)::numeric, 1) as tempo_medio_seg
            from usuario u
            inner join aluno al on u.id_usuario = al.id_usuario
            inner join resolucao_questao r on al.id_usuario = r.id_aluno
            inner join questao q on r.id_questao = q.id_questao
            group by u.nome, al.turma
            order by questoes_resolvidas desc;
        """)
        rows2 = cur.fetchall()
        lista_relatorios.append({
            'id': 'chart-alunos',
            'titulo': 'Engajamento dos Estudantes nas Turmas A e B',
            'descricao': 'Total de questões respondidas, acertos confirmados e ritmo médio individual de estudo.',
            'colunas': ['Estudante (Turma)', 'Resolvidas', 'Acertos', 'Tempo Médio (s)'],
            'linhas': [[r[0], int(r[1]), int(r[2]), float(r[3])] for r in rows2],
            'chart': {
                'type': 'horizontalBar',
                'labels': [r[0] for r in rows2],
                'datasets': [
                    {'label': 'Resolvidas', 'data': [int(r[1]) for r in rows2], 'color': '#5E1728'},
                    {'label': 'Acertos', 'data': [int(r[2]) for r in rows2], 'color': '#2E6B28'},
                ]
            }
        })

        # 3. Cobertura do Banco por Banca e Professor
        cur.execute("""
            select v.instituicao || ' — ' || u.nome as vestibular_professor,
                   count(q.id_questao) as total_questoes
            from questao q
            inner join vestibular v on q.id_vestibular = v.id_vestibular
            inner join professor p on q.id_professor = p.id_usuario
            inner join usuario u on p.id_usuario = u.id_usuario
            group by v.instituicao, u.nome
            order by total_questoes desc;
        """)
        rows3 = cur.fetchall()
        lista_relatorios.append({
            'id': 'chart-banca-prof',
            'titulo': 'Cobertura do Banco de Questões por Banca e Professor',
            'descricao': 'Distribuição das questões cadastradas entre UFSC, ENEM, UDESC e Autoral por docente responsável.',
            'colunas': ['Vestibular — Docente', 'Questões'],
            'linhas': [[r[0], int(r[1])] for r in rows3],
            'chart': {
                'type': 'bar',
                'labels': [r[0] for r in rows3],
                'datasets': [
                    {'label': 'Questões Cadastradas', 'data': [int(r[1]) for r in rows3], 'color': '#265321'},
                ]
            }
        })

        # 4. Distribuicao do Acervo por Area do Conhecimento
        cur.execute("""
            select coalesce(d.area, 'Outros') as area_conhecimento,
                   count(distinct q.id_questao) as total_questoes,
                   count(distinct case when q.tipo = 'Somatoria' then q.id_questao end) as somatorias,
                   count(distinct case when q.tipo = 'Multipla Escolha' then q.id_questao end) as multipla
            from questao q
            left join assunto_questao aq on q.id_questao = aq.id_questao
            left join assunto a on aq.id_assunto = a.id_assunto
            left join disciplina d on a.id_disciplina = d.id_disciplina
            group by coalesce(d.area, 'Outros')
            order by total_questoes desc;
        """)
        rows4 = cur.fetchall()
        lista_relatorios.append({
            'id': 'chart-areas',
            'titulo': 'Equilíbrio do Acervo por Área do Conhecimento',
            'descricao': 'Proporção de questões disponíveis em cada grande área (Natureza, Humanas, Matemática e Linguagens) e formato.',
            'colunas': ['Área do Conhecimento', 'Total', 'Somatória', 'Múltipla Escolha'],
            'linhas': [[r[0], int(r[1]), int(r[2]), int(r[3])] for r in rows4],
            'chart': {
                'type': 'doughnut',
                'labels': [r[0] for r in rows4],
                'datasets': [
                    {'label': 'Questões', 'data': [int(r[1]) for r in rows4], 'colors': ['#5E1728', '#265321', '#B45309', '#475569', '#8B5CF6']},
                ]
            }
        })

        # 5. Pontos de Atencao Pedagogica (Assuntos com Maior Indice de Erro)
        cur.execute("""
            select d.nome || ' • ' || a.nome as assunto_label,
                   count(r.id_resolucao) as tentativas,
                   sum(case when not r.acerto then 1 else 0 end) as erros,
                   round(100.0 * sum(case when not r.acerto then 1 else 0 end) / greatest(count(r.id_resolucao), 1), 1) as taxa_erro
            from resolucao_questao r
            inner join questao q on r.id_questao = q.id_questao
            inner join assunto_questao aq on q.id_questao = aq.id_questao
            inner join assunto a on aq.id_assunto = a.id_assunto
            inner join disciplina d on a.id_disciplina = d.id_disciplina
            group by d.nome, a.nome
            order by taxa_erro desc, erros desc
            limit 8;
        """)
        rows5 = cur.fetchall()
        lista_relatorios.append({
            'id': 'chart-atencao',
            'titulo': 'Pontos de Atenção Pedagógica (Índice de Erro por Assunto)',
            'descricao': 'Tópicos onde os estudantes mais erraram, indicando prioridades para plantões de dúvidas e listas de revisão.',
            'colunas': ['Disciplina • Assunto', 'Tentativas', 'Erros', 'Taxa de Erro (%)'],
            'linhas': [[r[0], int(r[1]), int(r[2]), f'{float(r[3]):.1f}%'] for r in rows5],
            'chart': {
                'type': 'horizontalBar',
                'labels': [r[0] for r in rows5],
                'datasets': [
                    {'label': 'Taxa de Erro (%)', 'data': [float(r[3]) for r in rows5], 'color': '#BE123C'},
                ]
            }
        })

        cur.close()
        con.close()
    except Exception as e:
        flash(f'Erro ao gerar relatórios: {e}', 'erro')

    return render_template('relatorios.html', pagina_ativa='relatorios', relatorios=lista_relatorios, resumo_kpi=resumo_kpi)


# ADMINISTRACAO DO SISTEMA
@app.route('/admin')
@requireRole('gestao')
def adminPage():
    aba_ativa = request.args.get('aba', '').strip()
    tabela_sel = request.args.get('tabela', 'disciplina')
    if tabela_sel not in crud.TABELAS:
        tabela_sel = 'disciplina'
    busca_bd = request.args.get('busca', '').strip()
    pagina_bd = max(1, int(request.args.get('pagina', 1) or 1))
    por_pagina_bd = 10

    if aba_ativa not in ('usuarios', 'banco'):
        aba_ativa = 'banco' if ('tabela' in request.args or 'pagina' in request.args or 'busca' in request.args) else 'usuarios'

    cols = crud.TABELAS[tabela_sel]
    cols_insert = cols[1:] if tabela_sel in TABELAS_AUTO_PK else cols
    crud_dados = {
        'tabela': tabela_sel,
        'tabela_label': TABLE_LABELS.get(tabela_sel, tabela_sel.capitalize()),
        'colunas': cols,
        'colunas_insert': cols_insert,
        'auto_pk': tabela_sel in TABELAS_AUTO_PK,
        'pk_composta': tabela_sel in crud.TABELAS_PK_COMPOSTA,
        'linhas': [],
        'total_registros': 0,
        'pagina': pagina_bd,
        'total_paginas': 1,
        'busca': busca_bd,
    }
    disciplinas_lista = []
    disciplinas_ocupadas = {}
    cursos_lista = []
    escolas_lista = []

    try:
        con = connectDatabase()
        cur = con.cursor()
        cur.execute(f"select {', '.join(cols)} from {tabela_sel} order by {cols[0]};")
        todas_linhas = cur.fetchall()

        if busca_bd:
            termo_l = busca_bd.lower()
            todas_linhas = [
                row for row in todas_linhas
                if any(termo_l in str(c).lower() for c in row if c is not None)
            ]

        total_reg = len(todas_linhas)
        total_pag = max(1, (total_reg + por_pagina_bd - 1) // por_pagina_bd)
        if pagina_bd > total_pag:
            pagina_bd = total_pag
        ini = (pagina_bd - 1) * por_pagina_bd

        crud_dados['total_registros'] = total_reg
        crud_dados['pagina'] = pagina_bd
        crud_dados['total_paginas'] = total_pag
        crud_dados['linhas'] = todas_linhas[ini:ini + por_pagina_bd]

        cur.execute('select id_disciplina, nome, frente from disciplina order by nome, frente;')
        disciplinas_lista = cur.fetchall()

        cur.execute("""
            select p.id_disciplina, u.nome
            from professor p
            inner join usuario u on u.id_usuario = p.id_usuario;
        """)
        disciplinas_ocupadas = dict(cur.fetchall())

        cur.execute('select id_curso, nome from curso order by nome;')
        cursos_lista = cur.fetchall()

        cur.execute('select id_escola, nome, cidade from escola order by nome;')
        escolas_lista = cur.fetchall()

        cur.close()
        con.close()
    except Exception as e:
        flash(f'Aviso do banco de dados: {e}', 'aviso')

    return render_template(
        'admin.html',
        pagina_ativa='admin',
        aba_ativa=aba_ativa,
        tabelas_nomes=list(crud.TABELAS.keys()),
        table_labels=TABLE_LABELS,
        crud_dados=crud_dados,
        disciplinas_lista=disciplinas_lista,
        disciplinas_ocupadas=disciplinas_ocupadas,
        cursos_lista=cursos_lista,
        escolas_lista=escolas_lista
    )


@app.route('/admin/usuarios/novo', methods=['POST'])
@requireRole('gestao')
def registerFullUserRoute():
    nome = request.form.get('nome', '').strip()
    cpf = request.form.get('cpf', '').strip()
    email = request.form.get('email', '').strip()
    senha = request.form.get('senha', '').strip()
    data_ingresso = request.form.get('data_ingresso', '').strip() or datetime.now().strftime('%Y-%m-%d')
    perfil = request.form.get('perfil', 'aluno')

    con = connectDatabase()
    cur = con.cursor()
    try:
        cur.execute('select coalesce(max(id_usuario), 0) + 1 from usuario;')
        novo_id = cur.fetchone()[0]

        cur.execute(
            'insert into usuario (id_usuario, nome, cpf, senha, email, data_ingresso) values (%s, %s, %s, %s, %s, %s);',
            (novo_id, nome, cpf, senha, email, data_ingresso)
        )

        if perfil == 'aluno':
            turma = request.form.get('turma', 'A')
            situacao_em = request.form.get('situacao_em', '3º Ano EM').strip()
            curso_desejado = request.form.get('curso_desejado', '').strip()
            escola_sel = request.form.get('id_escola', '').strip()
            if escola_sel == 'nova':
                nome_esc = request.form.get('nova_escola_nome', '').strip()
                cid_esc = request.form.get('nova_escola_cidade', '').strip() or 'Araranguá'
                cur.execute('select coalesce(max(id_escola), 0) + 1 from escola;')
                id_escola = cur.fetchone()[0]
                cur.execute('insert into escola (id_escola, nome, cidade) values (%s, %s, %s);', (id_escola, nome_esc, cid_esc))
            else:
                id_escola = int(escola_sel) if escola_sel.isdigit() else None
            cur.execute(
                'insert into aluno (id_usuario, id_escola, turma, situacao_em, curso_desejado) values (%s, %s, %s, %s, %s);',
                (novo_id, id_escola, turma, situacao_em, curso_desejado)
            )
        elif perfil == 'professor':
            id_disc = int(request.form.get('id_disciplina', 1))
            cur.execute("""
                select u.nome, d.nome, d.frente
                from professor p
                inner join usuario u on u.id_usuario = p.id_usuario
                inner join disciplina d on d.id_disciplina = p.id_disciplina
                where p.id_disciplina = %s;
            """, (id_disc,))
            prof_existente = cur.fetchone()
            if prof_existente:
                con.rollback()
                flash(
                    f'Não foi possível cadastrar: a matéria {prof_existente[1]} (Frente {prof_existente[2]}) já possui o(a) professor(a) {prof_existente[0]}.',
                    'erro'
                )
                return redirect(url_for('adminPage', aba='usuarios'))
            matricula_ufsc = request.form.get('matricula_ufsc', '').strip()
            fase_raw = request.form.get('fase_curso', '').strip()
            fase_curso = int(fase_raw) if fase_raw.isdigit() else 1
            curso_sel = request.form.get('id_curso', '').strip()
            if curso_sel == 'novo':
                nome_cur = request.form.get('novo_curso_nome', '').strip()
                cur.execute('select coalesce(max(id_curso), 0) + 1 from curso;')
                id_curso = cur.fetchone()[0]
                cur.execute('insert into curso (id_curso, nome) values (%s, %s);', (id_curso, nome_cur))
            else:
                id_curso = int(curso_sel) if curso_sel.isdigit() else None
            cur.execute(
                'insert into professor (id_usuario, id_disciplina, id_curso, matricula_ufsc, fase_curso) values (%s, %s, %s, %s, %s);',
                (novo_id, id_disc, id_curso, matricula_ufsc, fase_curso)
            )
        elif perfil == 'gestao':
            cargo = request.form.get('cargo', 'Gestor')
            setor = request.form.get('setor_atuacao', 'T.I')
            cur.execute(
                'insert into gestao (id_usuario, cargo, setor_atuacao) values (%s, %s, %s);',
                (novo_id, cargo, setor)
            )

        con.commit()
        flash(f'Usuário "{nome}" ({perfil}) cadastrado com sucesso (ID automático #{novo_id}).', 'sucesso')
    except Exception as e:
        con.rollback()
        flash(f'Erro ao cadastrar usuário: {e}', 'erro')
    finally:
        cur.close()
        con.close()
    return redirect(url_for('adminPage', aba='usuarios'))


@app.route('/admin/crud/<tabela>/<acao>', methods=['POST'])
@requireRole('gestao')
def adminCrudRoute(tabela, acao):
    colunas = crud.TABELAS[tabela]
    pagina_ret = request.form.get('pagina_ret', '1')
    busca_ret = request.form.get('busca_ret', '')
    nome_bonito = TABLE_LABELS.get(tabela, tabela.capitalize())
    con = connectDatabase()
    cur = con.cursor()
    try:
        if acao == 'inserir':
            if tabela in TABELAS_AUTO_PK:
                pk = colunas[0]
                cur.execute(f'select coalesce(max({pk}), 0) + 1 from {tabela};')
                novo_id = cur.fetchone()[0]
                valores = [novo_id] + [request.form.get(c, '').strip() or None for c in colunas[1:]]
            else:
                valores = [request.form.get(c, '').strip() or None for c in colunas]

            nomes = ', '.join(colunas)
            marcadores = ', '.join(['%s'] * len(colunas))
            cur.execute(f'insert into {tabela} ({nomes}) values ({marcadores});', tuple(valores))
            con.commit()
            flash(f'Registro inserido em "{nome_bonito}" com sucesso.', 'sucesso')
        elif acao == 'atualizar':
            if request.form.get('modo_lote') == '1':
                if tabela in crud.TABELAS_PK_COMPOSTA:
                    pk1, pk2 = colunas[0], colunas[1]
                    v1_orig = request.form.get('pk1_orig', '').strip()
                    v2_orig = request.form.get('pk2_orig', '').strip()
                    v1_novo = request.form.get(pk1, '').strip()
                    v2_novo = request.form.get(pk2, '').strip()
                    cur.execute(
                        f'update {tabela} set {pk1} = %s, {pk2} = %s where {pk1} = %s and {pk2} = %s;',
                        (v1_novo, v2_novo, v1_orig, v2_orig)
                    )
                else:
                    pk = colunas[0]
                    pk_val = request.form.get('pk_val', '').strip()
                    edit_cols = colunas[1:]
                    sets = ', '.join(f'{c} = %s' for c in edit_cols)
                    vals = [request.form.get(c, '').strip() or None for c in edit_cols]
                    vals.append(pk_val)
                    cur.execute(f'update {tabela} set {sets} where {pk} = %s;', tuple(vals))
            else:
                pk = colunas[0]
                col_alvo = request.form.get('col_alvo')
                if col_alvo not in colunas:
                    raise ValueError('Coluna inválida.')
                cur.execute(
                    f'update {tabela} set {col_alvo} = %s where {pk} = %s;',
                    (request.form.get('novo_val', '').strip() or None, request.form.get('pk_val', '').strip())
                )
            con.commit()
            flash(f'Registro atualizado em "{nome_bonito}".', 'sucesso')
        elif acao == 'excluir':
            if tabela in crud.TABELAS_PK_COMPOSTA:
                pk1, pk2 = colunas[0], colunas[1]
                cur.execute(f'delete from {tabela} where {pk1} = %s and {pk2} = %s;', (request.form.get('pk1'), request.form.get('pk2')))
            else:
                pk = colunas[0]
                cur.execute(f'delete from {tabela} where {pk} = %s;', (request.form.get('pk1'),))
            con.commit()
            flash(f'Registro removido de "{nome_bonito}".', 'sucesso')
    except Exception as e:
        con.rollback()
        msg_e = str(e)
        if 'uq_professor_disciplina' in msg_e:
            flash('Regra de negócio: cada disciplina/frente pode ter apenas um professor responsável.', 'erro')
        else:
            flash(f'Violação de integridade: {e}', 'erro')
    finally:
        cur.close()
        con.close()
    return redirect(url_for('adminPage', aba='banco', tabela=tabela, pagina=pagina_ret, busca=busca_ret))


@app.route('/admin/bd/<acao>', methods=['POST'])
@requireRole('gestao')
def adminDatabaseRoute(acao):
    if acao == 'eliminar':
        gerenciar_db.dropTables()
        flash('Tabelas removidas com sucesso.', 'aviso')
    elif acao == 'criar':
        gerenciar_db.createTables()
        flash('Estrutura de tabelas criada com sucesso.', 'sucesso')
    elif acao == 'carregar':
        gerenciar_db.loadInitialData()
        flash('Carga inicial concluída.', 'sucesso')
    elif acao == 'reset':
        gerenciar_db.dropTables()
        gerenciar_db.createTables()
        gerenciar_db.loadInitialData()
        flash('Base de dados reinicializada.', 'sucesso')
    return redirect(url_for('adminPage', aba='banco'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=os.environ.get('FLASK_DEBUG', '1') == '1', host='0.0.0.0', port=port)

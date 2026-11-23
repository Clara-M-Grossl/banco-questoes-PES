import os
import re
import time
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from database.conexao import connectDatabase
from services import classificador_enem

TAG_REVISAR_MATERIA = 'Revisar Matéria'
TAG_ERRO_GABARITO = 'Erro de Gabarito'
TAG_ERRO_GRAMATICA = 'Erro de Gramática'
TAG_ERRO_FORMATACAO = 'Erro de Formatação'
TAGS_REVISAO = (TAG_REVISAR_MATERIA, TAG_ERRO_GABARITO, TAG_ERRO_GRAMATICA, TAG_ERRO_FORMATACAO)

try:
    import pymupdf as fitz
except ImportError:
    fitz = None


AREAS_ENEM = {
    'ciencias-natureza': {'label': 'Ciências da Natureza', 'offset': 91},
    'matematica': {'label': 'Matemática', 'offset': 136},
    'ciencias-humanas': {'label': 'Ciências Humanas', 'offset': 46},
    'linguagens': {'label': 'Linguagens e Códigos', 'offset': 6},
}


def httpGetJson(url, timeout=15):
    for tentativa in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'CursinhoPES-UFSC/1.0'})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if '429' in str(e) and tentativa < 2:
                time.sleep(1.5 * (tentativa + 1))
                continue
            raise


def downloadImageFromUrl(url, upload_dir, prefixo):
    if not url or 'broken-image' in url or url.lower().endswith('.svg'):
        return None
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'CursinhoPES-UFSC/1.0'})
        with urllib.request.urlopen(req, timeout=12) as resp:
            ctype = resp.headers.get('Content-Type', '')
            if 'svg' in ctype:
                return None
            ext = '.png' if 'png' in ctype or url.lower().endswith('.png') else '.jpg'
            dados = resp.read()
            if len(dados) < 200:
                return None
            nome = f"{prefixo}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}{ext}"
            caminho = os.path.join(upload_dir, nome)
            with open(caminho, 'wb') as f:
                f.write(dados)
            return f'uploads/{nome}'
    except Exception:
        return None


def getOrCreateEnemExam(cur, ano):
    cur.execute(
        "select id_vestibular from vestibular where upper(instituicao) = 'ENEM' and ano = %s limit 1;",
        (ano,)
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute('select coalesce(max(id_vestibular), 0) + 1 from vestibular;')
    novo_id = cur.fetchone()[0]
    cur.execute(
        'insert into vestibular (id_vestibular, ano, edicao, instituicao) values (%s, %s, %s, %s);',
        (novo_id, ano, f'Exame Nacional do Ensino Médio {ano}', 'ENEM')
    )
    return novo_id


def getOrCreateTagByName(cur, nome_tag):
    cur.execute('select id_tag from tag where lower(nome) = lower(%s) limit 1;', (nome_tag,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute('select coalesce(max(id_tag), 0) + 1 from tag;')
    novo_id = cur.fetchone()[0]
    cur.execute('insert into tag (id_tag, nome) values (%s, %s);', (novo_id, nome_tag))
    return novo_id


def getOrCreateReviewTag(cur):
    return getOrCreateTagByName(cur, TAG_REVISAR_MATERIA)


def looksLikeBrokenEquation(texto):
    # acha equacao ou imagem
    t = texto or ''
    padroes = [
        r'\(\s+\)',                         # f( ) ou ( ) vazio de matriz/funcao
        r'√\s*[.,;:\)]',                    # raiz quadrada sem radicando (ex: "√ .")
        r'\bpor\s+\(\s*\)',                 # "definida por ( )"
        r'\bentão\s+\(\s*\)',               # "então ( )"
        r'\brazão\s*\.',                    # "PG de razão ."
        r'\{\s*$',                          # sistema de equacoes cortado "{"
        r'\bmatrizes\s+e\s+matrizes\b',
        r'\b(?:figura|gráfico|imagem|tabela)\s+abaixo\b',
    ]
    return any(re.search(p, t, flags=re.IGNORECASE | re.MULTILINE) for p in padroes)


def getOrCreateClassifiedTopic(cur, disc_nome, frente_nome, assunto_nome):
    # acha o assunto
    # disciplia + frente
    cur.execute(
        'select id_disciplina from disciplina where lower(nome) = lower(%s) and lower(frente) = lower(%s) limit 1;',
        (disc_nome, frente_nome)
    )
    row_d = cur.fetchone()
    if not row_d:
        cur.execute(
            'select id_disciplina from disciplina where lower(nome) = lower(%s) order by id_disciplina limit 1;',
            (disc_nome,)
        )
        row_d = cur.fetchone()
    if not row_d:
        cur.execute('select id_disciplina from disciplina order by id_disciplina limit 1;')
        row_d = cur.fetchone()
    id_disc = row_d[0]

    # se o assunto ja era cadastrado, reutiliza
    cur.execute(
        'select id_assunto from assunto where id_disciplina = %s and lower(nome) = lower(%s) limit 1;',
        (id_disc, assunto_nome)
    )
    row_a = cur.fetchone()
    if row_a:
        return row_a[0]

    # cria um novo assunto
    cur.execute('select coalesce(max(id_assunto), 0) + 1 from assunto;')
    novo_id_a = cur.fetchone()[0]
    cur.execute(
        'insert into assunto (id_assunto, id_disciplina, nome) values (%s, %s, %s);',
        (novo_id_a, id_disc, assunto_nome)
    )
    return novo_id_a


def classifyEnemSubject(discipline_slug, texto_questao):
    # define a disciplina
    res = classificador_enem.classifyEnemQuestion(discipline_slug, texto_questao)
    return res['disciplina']


def getOrCreateEnemAreaTopic(cur, discipline_slug, texto_questao='', info_inep=None):
    res = classificador_enem.classifyEnemQuestion(discipline_slug, texto_questao, info_inep=info_inep)
    id_assunto = getOrCreateClassifiedTopic(cur, res['disciplina'], res['frente'], res['assunto'])
    return id_assunto, res['precisa_revisao'], res['fonte']


def insertEnemQuestionDict(cur, q, ano, id_vestibular, id_assunto, dificuldade, upload_dir, id_professor, id_gestao, contadores):
    alts = q.get('alternatives') or []
    if len(alts) < 4 or not any((a.get('text') or '').strip() for a in alts):
        return None

    marcador = f"(ENEM {ano} — Q{q.get('index', '')})"
    # evita duplicacao
    cur.execute('select id_questao from questao where enunciado like %s limit 1;', (marcador + '%',))
    if cur.fetchone():
        return None

    contexto = (q.get('context') or '').strip()
    contexto = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', contexto).strip()
    intro = (q.get('alternativesIntroduction') or '').strip()
    enunciado = '\n\n'.join(p for p in [marcador, contexto, intro] if p)

    contadores['q'] += 1
    id_q = contadores['q']
    cur.execute(
        'insert into questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) values (%s, %s, %s, %s, %s, %s, %s);',
        (id_q, id_vestibular, id_professor, id_gestao, 'Multipla Escolha', dificuldade, enunciado)
    )
    cur.execute('insert into assunto_questao (id_questao, id_assunto) values (%s, %s);', (id_q, int(id_assunto)))

    for idx_alt, alt in enumerate(alts, start=1):
        contadores['alt'] += 1
        txt_alt = (alt.get('text') or '').strip() or f"Alternativa {alt.get('letter', idx_alt)}"
        is_corr = bool(alt.get('isCorrect', False))
        cur.execute(
            'insert into alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) values (%s, %s, %s, %s, %s);',
            (contadores['alt'], id_q, idx_alt, txt_alt, is_corr)
        )

    for idx_img, img_url in enumerate(q.get('files') or [], start=1):
        if not img_url or 'broken-image' in img_url or img_url.lower().endswith('.svg'):
            continue
        arq_local = contadores.get('imgs_baixadas', {}).get(img_url)
        if not arq_local:
            arq_local = downloadImageFromUrl(img_url, upload_dir, f'enem{ano}_q{q.get("index", id_q)}_{idx_img}') or img_url
        if arq_local:
            contadores['midia'] += 1
            cur.execute(
                'insert into midia (id_midia, id_questao, legenda, arquivo) values (%s, %s, %s, %s);',
                (contadores['midia'], id_q, f'Figura oficial ENEM {ano} (Questão {q.get("index", "")})', arq_local)
            )
    return id_q


def importSingleEnemQuestion(ano, numero_questao, id_assunto, upload_dir, id_professor=None, id_gestao=None, dificuldade='Media'):
    # importa so uma questao -> API
    url = f'https://api.enem.dev/v1/exams/{int(ano)}/questions/{int(numero_questao)}'
    q = httpGetJson(url, timeout=15)
    if not q or 'alternatives' not in q:
        return [], f'Questão {numero_questao} do ENEM {ano} não encontrada.'

    con = connectDatabase()
    cur = con.cursor()
    try:
        id_vest = getOrCreateEnemExam(cur, int(ano))
        cur.execute('select coalesce(max(id_questao), 0) from questao;')
        max_q = cur.fetchone()[0]
        cur.execute('select coalesce(max(id_alternativa), 0) from alternativa;')
        max_alt = cur.fetchone()[0]
        cur.execute('select coalesce(max(id_midia), 0) from midia;')
        max_midia = cur.fetchone()[0]
        cont = {'q': max_q, 'alt': max_alt, 'midia': max_midia}

        id_criado = insertEnemQuestionDict(
            cur, q, int(ano), id_vest, int(id_assunto), dificuldade, upload_dir, id_professor, id_gestao, cont
        )
        con.commit()
        if not id_criado:
            return [], f'Questão {numero_questao} do ENEM {ano} já estava cadastrada ou não possui alternativas textuais.'
        return [id_criado], f'Questão {numero_questao} do ENEM {ano} importada com sucesso.'
    except Exception as e:
        con.rollback()
        return [], f'Erro ao importar questão do ENEM: {e}'
    finally:
        cur.close()
        con.close()


def importFullEnemExam(ano, upload_dir, id_professor=None, id_gestao=None, callback_progresso=None, microdados_csv_bytes=None):
    # importa a prova inteira -> API
    mapa_inep = {}
    if microdados_csv_bytes:
        if callback_progresso:
            callback_progresso('Lendo Microdados oficiais do INEP (habilidades H1–H30)...')
        mapa_inep = classificador_enem.parseInepMicrodataCsv(microdados_csv_bytes)

    todas = []
    offset = 1
    while True:
        if callback_progresso:
            callback_progresso(f'Baixando caderno do ENEM {ano} ({len(todas)} questões carregadas)...')
        url = f'https://api.enem.dev/v1/exams/{int(ano)}/questions?limit=50&offset={offset}'
        payload = httpGetJson(url, timeout=20)
        lote = payload.get('questions', [])
        if not lote:
            break
        todas.extend(lote)
        meta = payload.get('metadata') or {}
        if not meta.get('hasMore'):
            break
        offset += 50
        time.sleep(0.25)

    validas = [q for q in todas if q.get('language') not in ('ingles', 'espanhol')]
    if not validas:
        return [], f'Nenhuma questão encontrada para o ENEM {ano}.'

    # baixa as imagens
    urls_imgs = []
    for q in validas:
        for idx_i, u in enumerate(q.get('files') or [], start=1):
            if u and 'broken-image' not in u and not u.lower().endswith('.svg'):
                urls_imgs.append((u, f'enem{ano}_q{q.get("index", 0)}_{idx_i}'))

    imgs_baixadas = {}
    if urls_imgs:
        if callback_progresso:
            callback_progresso(f'Baixando {len(urls_imgs)} figuras oficiais do ENEM {ano} em paralelo...')
        with ThreadPoolExecutor(max_workers=10) as pool:
            futs = {pool.submit(downloadImageFromUrl, u, upload_dir, pref): u for u, pref in urls_imgs}
            for fut, url_orig in futs.items():
                try:
                    res = fut.result()
                    if res:
                        imgs_baixadas[url_orig] = res
                except Exception:
                    pass

    con = connectDatabase()
    cur = con.cursor()
    ids_criados = []
    qtd_revisar = 0
    qtd_inep = 0
    try:
        id_vest = getOrCreateEnemExam(cur, int(ano))
        id_tag_rev = getOrCreateReviewTag(cur)
        cur.execute('select coalesce(max(id_questao), 0) from questao;')
        max_q = cur.fetchone()[0]
        cur.execute('select coalesce(max(id_alternativa), 0) from alternativa;')
        max_alt = cur.fetchone()[0]
        cur.execute('select coalesce(max(id_midia), 0) from midia;')
        max_midia = cur.fetchone()[0]
        cont = {'q': max_q, 'alt': max_alt, 'midia': max_midia, 'imgs_baixadas': imgs_baixadas}

        total = len(validas)
        for i, q in enumerate(validas, start=1):
            if callback_progresso and (i == 1 or i % 15 == 0 or i == total):
                callback_progresso(f'Classificando matéria/conteúdo e gravando ENEM {ano}: {i}/{total}...')
            slug = q.get('discipline') or classificador_enem.inferEnemAreaByNumber(q.get('index')) or 'geral'
            texto_classif = (
                (q.get('context') or '') + ' '
                + (q.get('alternativesIntroduction') or '') + ' '
                + ' '.join((a.get('text') or '') for a in (q.get('alternatives') or []))
            )
            num_q = q.get('index')
            info_inep = mapa_inep.get(int(num_q)) if (num_q and str(num_q).isdigit()) else None

            id_assunto, precisa_revisao, fonte = getOrCreateEnemAreaTopic(
                cur, slug, texto_classif, info_inep=info_inep
            )
            if fonte == 'inep':
                qtd_inep += 1

            id_q = insertEnemQuestionDict(
                cur, q, int(ano), id_vest, id_assunto, 'Media', upload_dir, id_professor, id_gestao, cont
            )
            if id_q:
                ids_criados.append(id_q)
                if precisa_revisao:
                    cur.execute(
                        'insert into questao_tag (id_tag, id_questao) values (%s, %s) on conflict do nothing;',
                        (id_tag_rev, id_q)
                    )
                    qtd_revisar += 1

        con.commit()
        if not ids_criados:
            return [], f'Todas as questões do ENEM {ano} já estavam cadastradas no banco.'
        detalhe_inep = f' ({qtd_inep} via Microdados INEP)' if qtd_inep else ''
        detalhe_rev = f' • {qtd_revisar} marcada(s) com a tag "Revisar Matéria"' if qtd_revisar else ' Todas classificadas com alta confiança!'
        return ids_criados, f'ENEM {ano} importado: {len(ids_criados)} questões separadas por matéria e conteúdo{detalhe_inep}{detalhe_rev}'
    except Exception as e:
        con.rollback()
        return [], f'Erro ao importar prova completa do ENEM {ano}: {e}'
    finally:
        cur.close()
        con.close()


def reclassifyExistingEnem(ano_filtro=None, microdados_csv_bytes=None):
    # classifica questoes ja cadastradas
    mapa_inep = classificador_enem.parseInepMicrodataCsv(microdados_csv_bytes) if microdados_csv_bytes else {}

    con = connectDatabase()
    cur = con.cursor()
    try:
        id_tag_rev = getOrCreateReviewTag(cur)
        if ano_filtro:
            cur.execute("""
                select q.id_questao, q.enunciado, v.ano
                from questao q
                inner join vestibular v on q.id_vestibular = v.id_vestibular
                where upper(v.instituicao) = 'ENEM' and v.ano = %s
                order by q.id_questao;
            """, (int(ano_filtro),))
        else:
            cur.execute("""
                select q.id_questao, q.enunciado, v.ano
                from questao q
                inner join vestibular v on q.id_vestibular = v.id_vestibular
                where upper(v.instituicao) = 'ENEM'
                order by q.id_questao;
            """)
        rows_q = cur.fetchall()
        if not rows_q:
            return 0, 0, 0, 'Nenhuma questão do ENEM encontrada para reclassificar.'

        ids_q = [r[0] for r in rows_q]
        cur.execute(
            'select id_questao, texto from alternativa where id_questao = any(%s);',
            (ids_q,)
        )
        alts_por_q = {}
        for iq, txt in cur.fetchall():
            alts_por_q.setdefault(iq, []).append(txt or '')

        total = 0
        alta_conf = 0
        para_revisar = 0

        for id_q, enunciado, ano_q in rows_q:
            m_num = re.search(r'\(ENEM\s+\d{4}\s*[—-]\s*Q(\d+)\)', enunciado or '', flags=re.IGNORECASE)
            num_q = int(m_num.group(1)) if m_num else None
            slug = classificador_enem.inferEnemAreaByNumber(num_q)
            info_inep = mapa_inep.get(num_q) if (num_q and mapa_inep) else None

            texto_completo = (enunciado or '') + ' ' + ' '.join(alts_por_q.get(id_q, []))
            id_assunto, precisa_revisao, _ = getOrCreateEnemAreaTopic(
                cur, slug, texto_completo, info_inep=info_inep
            )

            cur.execute('delete from assunto_questao where id_questao = %s;', (id_q,))
            cur.execute('insert into assunto_questao (id_questao, id_assunto) values (%s, %s);', (id_q, id_assunto))

            cur.execute('delete from questao_tag where id_tag = %s and id_questao = %s;', (id_tag_rev, id_q))
            if precisa_revisao:
                cur.execute('insert into questao_tag (id_tag, id_questao) values (%s, %s);', (id_tag_rev, id_q))
                para_revisar += 1
            else:
                alta_conf += 1
            total += 1

        # limpa questoes mal cadastradas
        cur.execute("""
            delete from assunto a
            where a.nome like 'Questões ENEM — %'
              and not exists (select 1 from assunto_questao ab where ab.id_assunto = a.id_assunto);
        """)
        con.commit()
        msg = (
            f'{total} questões do ENEM reclassificadas por matéria, frente e conteúdo: '
            f'{alta_conf} com confiança e {para_revisar} marcada(s) para revisão rápida.'
        )
        return total, alta_conf, para_revisar, msg
    except Exception as e:
        con.rollback()
        return 0, 0, 0, f'Erro ao reclassificar questões do ENEM: {e}'
    finally:
        cur.close()
        con.close()


# extrai gabarito prova da ufsc
def parseUfscAnswerKey(gabarito_str):
    mapa = {}
    if not gabarito_str or not gabarito_str.strip():
        return mapa
    txt = gabarito_str.strip()
    pares = re.findall(r'(\d{1,2})\s*[:\-=]\s*(\d{1,3})', txt)
    if pares:
        for num_q, soma in pares:
            mapa[int(num_q)] = int(soma)
        return mapa
    nums = re.findall(r'\d{1,3}', txt)
    for i, soma in enumerate(nums, start=1):
        mapa[i] = int(soma)
    return mapa


def readOrderedPdfText(pdf_bytes, upload_dir):
    # extrai o texto
    if fitz is None:
        raise RuntimeError('Biblioteca PyMuPDF não instalada. Execute: pip install pymupdf')

    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    texto_paginas = []
    imagens_extraidas = []

    for num_pag, page in enumerate(doc, start=1):
        largura = page.rect.width
        meio = largura / 2.0
        blocos = page.get_text('blocks')

        blocos_texto = [b for b in blocos if b[6] == 0 and b[4].strip()]
        esq = [b for b in blocos_texto if b[2] <= meio + 25]
        dir_ = [b for b in blocos_texto if b[0] >= meio - 25]
        usa_duas_colunas = len(esq) >= 2 and len(dir_) >= 2

        if usa_duas_colunas:
            col_esq = sorted([b for b in blocos_texto if (b[0] + b[2]) / 2.0 < meio], key=lambda b: (round(b[1], 1), b[0]))
            col_dir = sorted([b for b in blocos_texto if (b[0] + b[2]) / 2.0 >= meio], key=lambda b: (round(b[1], 1), b[0]))
            ordenados = col_esq + col_dir
        else:
            ordenados = sorted(blocos_texto, key=lambda b: (round(b[1], 1), b[0]))

        texto_paginas.append('\n'.join(b[4].strip() for b in ordenados))

        # extrai figuras
        for idx_img, img_info in enumerate(page.get_images(full=True), start=1):
            xref = img_info[0]
            try:
                base_img = doc.extract_image(xref)
                w, h = base_img.get('width', 0), base_img.get('height', 0)
                if w < 120 or h < 80:
                    continue
                ext = base_img.get('ext', 'png')
                nome = f"ufsc_p{num_pag}_fig{idx_img}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
                with open(os.path.join(upload_dir, nome), 'wb') as f_out:
                    f_out.write(base_img['image'])
                imagens_extraidas.append((num_pag, f'uploads/{nome}'))
            except Exception:
                continue

    doc.close()
    return '\n\n'.join(texto_paginas), imagens_extraidas


def normalizeUfscSubject(texto_disc):
    t = (texto_disc or '').upper().strip()
    if any(k in t for k in ['SEGUNDA L', 'ESTRANGEIRA', 'INGL', 'ESPANHOL', 'FRANC', 'ALEM', 'ITALIAN', 'LIBRAS']):
        return 'LINGUA_ESTRANGEIRA'
    mapa = [
        ('PORTUGU', 'Português'),
        ('LITERAT', 'Literatura'),
        ('MATEM', 'Matemática'),
        ('BIOLOG', 'Biologia'),
        ('FÍSICA', 'Física'),
        ('FISICA', 'Física'),
        ('QUÍMIC', 'Química'),
        ('QUIMIC', 'Química'),
        ('HISTÓR', 'História'),
        ('HISTOR', 'História'),
        ('GEOGRAF', 'Geografia'),
        ('FILOSOF', 'Filosofia'),
        ('SOCIOLOG', 'Sociologia'),
        ('HUMANAS', 'História'),
        ('NATUREZA', 'Física'),
    ]
    for chave, nome in mapa:
        if chave in t:
            return nome
    return None


def extractAnswerKeyFromPdf(pdf_bytes):
    # extrai o gabarito
    if fitz is None or not pdf_bytes:
        return {}
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    texto = '\n'.join(page.get_text('text') for page in doc)
    doc.close()

    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    mapa = {}

    # com base na tabela oficial
    inicio_tabela = 0
    for idx, l in enumerate(linhas):
        if l == '64':
            inicio_tabela = idx + 1
            break

    if inicio_tabela > 0:
        disc_atual = 'Português'
        i = inicio_tabela
        n_linhas = len(linhas)
        esperada = 1
        while i < n_linhas and esperada <= 40:
            if linhas[i].isdigit() and int(linhas[i]) == esperada:
                num_q = esperada
                esperada += 1
                i += 1
                aberta = False
                soma_val = 0

                tokens_q = []
                viu_marcador = False
                while i < n_linhas:
                    tok = linhas[i]
                    tokens_q.append(tok)
                    i += 1
                    if tok.upper() in ('X', 'ABERTA', 'ANULADA'):
                        viu_marcador = True
                    elif viu_marcador and tok.isdigit():
                        break

                for tok in tokens_q:
                    if tok.upper() in ('ABERTA', 'ANULADA'):
                        aberta = True
                    else:
                        d_norm = normalizeUfscSubject(tok)
                        if d_norm:
                            disc_atual = d_norm

                if tokens_q and tokens_q[-1].isdigit():
                    soma_val = int(tokens_q[-1])

                mapa[num_q] = {'soma': soma_val, 'disciplina': disc_atual, 'aberta': aberta}
            else:
                i += 1

    # gabarito simples
    if len(mapa) < 3:
        for num_s, soma_s in re.findall(r'(?:^|\n|\s)(0?[1-9]|[1-3]\d|40)\s*(?:[:\-–|]|\s+)\s*(0?\d{1,3})\b', texto):
            n, s = int(num_s), int(soma_s)
            if 1 <= n <= 40 and 1 <= s <= 127 and n not in mapa:
                mapa[n] = {'soma': s, 'disciplina': None, 'aberta': False}

    return mapa


def getOrCreateUfscSubjectTopic(cur, nome_disciplina):
    # especifica a disciplina
    nome_assunto = f'Questões UFSC — {nome_disciplina}'
    cur.execute('select id_assunto from assunto where nome = %s limit 1;', (nome_assunto,))
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        'select id_disciplina from disciplina where lower(nome) = lower(%s) order by id_disciplina limit 1;',
        (nome_disciplina,)
    )
    row_d = cur.fetchone()
    if not row_d:
        cur.execute('select id_disciplina from disciplina order by id_disciplina limit 1;')
        row_d = cur.fetchone()
    id_disc = row_d[0]

    cur.execute('select coalesce(max(id_assunto), 0) + 1 from assunto;')
    novo_id_a = cur.fetchone()[0]
    cur.execute(
        'insert into assunto (id_assunto, id_disciplina, nome) values (%s, %s, %s);',
        (novo_id_a, id_disc, nome_assunto)
    )
    return novo_id_a


def detectSubjectFromText(trecho):
    return normalizeUfscSubject(trecho)


def cleanCoperveHeaders(texto):
    # retira a redacao e as discursivas
    corte_final = re.search(
        r'(?:^|\n)\s*(?:QUEST[AÃ]O\s+DISCURSIVA|QUEST[ÕO]ES\s+DISCURSIVAS|PROVA\s+DE\s+REDA[ÇC][AÃ]O|REDA[ÇC][AÃ]O\s*\n)',
        texto,
        flags=re.IGNORECASE
    )
    if corte_final:
        texto = texto[:corte_final.start()]

    # Remove cabecalhos de pagina
    texto = re.sub(r'COPERVE\s+VESTIBULAR[^\n]*\n\s*\d{1,3}\s*\n', '\n', texto)
    texto = re.sub(r'COPERVE\s+VESTIBULAR[^\n]*', '', texto)
    return texto


def splitUfscQuestionsRegex(texto_completo, ignorar_lingua_estrangeira=True, mapa_gabarito=None):
    # separa as questoes
    mapa_gabarito = mapa_gabarito or {}
    texto = cleanCoperveHeaders(texto_completo)
    texto = re.sub(r'[ \t]+', ' ', texto)
    texto = re.sub(r'\n{3,}', '\n\n', texto)

    marcadores_coperve = list(re.finditer(r'(?:^|\n)\s*(0?[1-9]|[1-3]\d|40)\)\s+', texto))
    marcadores_questao = list(re.finditer(r'(?:^|\n)\s*(?:QUEST[AÃ]O|Quest[aã]o)\s+(\d{1,2})\b[^\n]*', texto))

    blocos_brutos = []
    disciplina_atual = 'Português'

    if len(marcadores_coperve) >= 3:
        cab_inicial = detectSubjectFromText(texto[:marcadores_coperve[0].start()])
        if cab_inicial:
            disciplina_atual = cab_inicial

        for i, m in enumerate(marcadores_coperve):
            num_q = int(m.group(1))
            ini = m.end()
            fim = marcadores_coperve[i + 1].start() if i + 1 < len(marcadores_coperve) else len(texto)
            trecho_antes = texto[max(0, m.start() - 250):m.start()]
            disc_nova = detectSubjectFromText(trecho_antes)
            if disc_nova:
                disciplina_atual = disc_nova

            # prioridade para disciplinas ja definidas
            info_gab = mapa_gabarito.get(num_q)
            disc_final = (info_gab.get('disciplina') if isinstance(info_gab, dict) and info_gab.get('disciplina') else disciplina_atual)
            blocos_brutos.append((num_q, texto[ini:fim].strip(), disc_final))
    elif marcadores_questao:
        cab_inicial = detectSubjectFromText(texto[:marcadores_questao[0].start()])
        if cab_inicial:
            disciplina_atual = cab_inicial
        for i, m in enumerate(marcadores_questao):
            num_q = int(m.group(1))
            ini = m.end()
            fim = marcadores_questao[i + 1].start() if i + 1 < len(marcadores_questao) else len(texto)
            disc_nova = detectSubjectFromText(texto[max(0, m.start() - 250):m.start()])
            if disc_nova:
                disciplina_atual = disc_nova
            blocos_brutos.append((num_q, texto[ini:fim].strip(), disciplina_atual))
    else:
        ocorrencias_01 = list(re.finditer(r'(?:^|\n)\s*01[\.\-\)]\s+', texto))
        if len(ocorrencias_01) <= 1:
            disc_d = detectSubjectFromText(texto) or 'Física'
            blocos_brutos.append((1, texto.strip(), disc_d))
        else:
            cortes = [0]
            for i in range(1, len(ocorrencias_01)):
                trecho_entre = texto[ocorrencias_01[i - 1].start():ocorrencias_01[i].start()]
                ultima_prop = None
                for mp in re.finditer(r'(?:^|\n)\s*(?:01|02|04|08|16|32|64)[\.\-\)]\s+[^\n]+', trecho_entre):
                    ultima_prop = mp
                if ultima_prop:
                    cortes.append(ocorrencias_01[i - 1].start() + ultima_prop.end())
            cortes.append(len(texto))
            for idx in range(len(cortes) - 1):
                bloco = texto[cortes[idx]:cortes[idx + 1]].strip()
                if bloco:
                    disc_d = detectSubjectFromText(bloco[:220])
                    if disc_d:
                        disciplina_atual = disc_d
                    blocos_brutos.append((idx + 1, bloco, disciplina_atual))

    padrao_prop = re.compile(
        r'(?:^|\n)\s*(01|02|04|08|16|32|64)\.\s+(.+?)(?=(?:\n\s*(?:01|02|04|08|16|32|64)\.\s+)|(?:\n\s*Texto\s+\d+)|(?:\n\s*Text\s+\d+)|(?:\n\s*SOMA\b)|(?:\n\s*(?:Matemática|Biologia|Física|Química|História|Geografia|Língua\s+Estrangeira)\s*\n)|$)',
        re.DOTALL
    )

    questoes_parseadas = []
    for num_q, bloco, disc_q in blocos_brutos:
        info_gab = mapa_gabarito.get(num_q)
        if isinstance(info_gab, dict) and info_gab.get('aberta'):
            continue
        if ignorar_lingua_estrangeira and disc_q == 'LINGUA_ESTRANGEIRA':
            continue

        matches = padrao_prop.findall(bloco)
        if len(matches) < 2:
            continue

        pos_primeira = re.search(r'(?:^|\n)\s*' + matches[0][0] + r'\.\s+', bloco)
        enunciado = bloco[:pos_primeira.start()].strip() if pos_primeira else bloco.strip()
        enunciado = re.sub(r'\n+', ' ', enunciado).strip()
        if not enunciado:
            continue

        proposicoes = []
        vistos = set()
        for cod_str, txt_p in matches:
            val = int(cod_str)
            if val in vistos:
                continue
            vistos.add(val)
            txt_limpo = re.sub(r'\s+', ' ', txt_p).strip()
            txt_limpo = re.sub(r'\b(?:RESPOSTA|RASCUNHO|SOMA\s*:).*$', '', txt_limpo, flags=re.IGNORECASE).strip()
            proposicoes.append((val, txt_limpo))

        if len(proposicoes) >= 2:
            questoes_parseadas.append({
                'numero': num_q,
                'disciplina': disc_q,
                'enunciado': enunciado,
                'proposicoes': proposicoes
            })

    return questoes_parseadas


def extractUfscPdfOffline(pdf_bytes, gabarito_str, id_vestibular, id_assunto, upload_dir, id_professor=None, id_gestao=None, dificuldade='Media', gabarito_pdf_bytes=None):
   # extrai pdf da prova
    mapa_gab = {}
    if gabarito_pdf_bytes:
        mapa_gab.update(extractAnswerKeyFromPdf(gabarito_pdf_bytes))
    if gabarito_str:
        for k, v in parseUfscAnswerKey(gabarito_str).items():
            mapa_gab[k] = {'soma': v, 'disciplina': None, 'aberta': False}

    texto_completo, imagens_extraidas = readOrderedPdfText(pdf_bytes, upload_dir)
    modo_auto = str(id_assunto) == 'auto'
    questoes = splitUfscQuestionsRegex(texto_completo, ignorar_lingua_estrangeira=modo_auto, mapa_gabarito=mapa_gab)

    if not questoes:
        return [], 'Não foram encontradas questões somatórias no padrão UFSC (01., 02., 04., 08...)'

    con = connectDatabase()
    cur = con.cursor()
    ids_criados = []
    qtd_revisar = 0
    try:
        id_tag_rev = getOrCreateReviewTag(cur)
        id_tag_fmt = getOrCreateTagByName(cur, TAG_ERRO_FORMATACAO)
        cur.execute('select ano, instituicao from vestibular where id_vestibular = %s;', (int(id_vestibular),))
        row_v = cur.fetchone()
        ano_vest = row_v[0] if row_v else ''
        inst_vest = (row_v[1] if row_v and row_v[1] else 'UFSC').strip()

        cur.execute('select coalesce(max(id_questao), 0) from questao;')
        max_q = cur.fetchone()[0]
        cur.execute('select coalesce(max(id_alternativa), 0) from alternativa;')
        max_alt = cur.fetchone()[0]
        cur.execute('select coalesce(max(id_midia), 0) from midia;')
        max_midia = cur.fetchone()[0]

        com_gab = 0
        for idx, q in enumerate(questoes, start=1):
            info_g = mapa_gab.get(q['numero']) or mapa_gab.get(idx) or {}
            soma_gab = info_g.get('soma', 0) if isinstance(info_g, dict) else int(info_g or 0)
            if soma_gab > 0:
                com_gab += 1

            prefixo = f"({inst_vest} {ano_vest} — Q{q['numero']:02d}) " if ano_vest else f"({inst_vest} — Q{q['numero']:02d}) "
            enunciado_final = prefixo + q['enunciado']

            # Evita duplicar a mesma questao se a prova ja foi importada
            cur.execute('select id_questao from questao where id_vestibular = %s and enunciado like %s limit 1;', (int(id_vestibular), prefixo + '%'))
            if cur.fetchone():
                continue

            max_q += 1
            precisa_revisao = False
            texto_para_classif = q['enunciado'] + ' ' + ' '.join(p[1] for p in q['proposicoes'])
            erro_formatacao = looksLikeBrokenEquation(texto_para_classif)

            if modo_auto:
                disc_nome = q.get('disciplina')
                if disc_nome == 'Português' and re.search(
                    r'\b(?:leitura\s+integral|obras?\s+obrigat[óo]rias?|romance|poema|soneto|narrativas?\s+da|machado\s+de\s+assis|literatura)\b',
                    q['enunciado'],
                    flags=re.IGNORECASE
                ):
                    disc_nome = 'Literatura'
                    assunto_destino = getOrCreateClassifiedTopic(cur, 'Literatura', 'Única', 'Obras Obrigatórias UFSC')
                elif disc_nome and disc_nome != 'LINGUA_ESTRANGEIRA':
                    frente_c, assunto_c, conf_c = classificador_enem.classifyTopicBySubject(disc_nome, texto_para_classif)
                    assunto_destino = getOrCreateClassifiedTopic(cur, disc_nome, frente_c, assunto_c)
                    precisa_revisao = not conf_c
                else:
                    res_c = classificador_enem.classifyEnemQuestion(None, texto_para_classif)
                    assunto_destino = getOrCreateClassifiedTopic(cur, res_c['disciplina'], res_c['frente'], res_c['assunto'])
                    precisa_revisao = res_c['precisa_revisao']
            else:
                assunto_destino = int(id_assunto)

            cur.execute(
                'insert into questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) values (%s, %s, %s, %s, %s, %s, %s);',
                (max_q, int(id_vestibular), id_professor, id_gestao, 'Somatoria', dificuldade, enunciado_final)
            )
            cur.execute('insert into assunto_questao (id_questao, id_assunto) values (%s, %s);', (max_q, assunto_destino))

            if precisa_revisao:
                cur.execute('insert into questao_tag (id_tag, id_questao) values (%s, %s) on conflict do nothing;', (id_tag_rev, max_q))
                qtd_revisar += 1
            if erro_formatacao:
                cur.execute('insert into questao_tag (id_tag, id_questao) values (%s, %s) on conflict do nothing;', (id_tag_fmt, max_q))
                if not precisa_revisao:
                    qtd_revisar += 1

            for val_p, txt_p in q['proposicoes']:
                max_alt += 1
                correta = bool(soma_gab & val_p) if soma_gab > 0 else False
                cur.execute(
                    'insert into alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) values (%s, %s, %s, %s, %s);',
                    (max_alt, max_q, val_p, txt_p, correta)
                )

            if len(questoes) == 1 and imagens_extraidas:
                for _, arq_img in imagens_extraidas:
                    max_midia += 1
                    cur.execute(
                        'insert into midia (id_midia, id_questao, legenda, arquivo) values (%s, %s, %s, %s);',
                        (max_midia, max_q, f'Figura extraída do PDF oficial {inst_vest}', arq_img)
                    )

            ids_criados.append(max_q)

        con.commit()
        if not ids_criados:
            return [], f'As questões desta prova {inst_vest} já estavam cadastradas para este vestibular.'
        extra_rev = f' • {qtd_revisar} marcada(s) com "Revisar Matéria".' if qtd_revisar else ''
        return ids_criados, f'{len(ids_criados)} questão(ões) ({inst_vest}) importada por matéria, frente e conteúdo ({com_gab} com gabarito oficial aplicado){extra_rev}'
    except Exception as e:
        con.rollback()
        return [], f'Erro ao salvar questões extraídas do PDF: {e}'
    finally:
        cur.close()
        con.close()


# extrator universal
def parseLetterAnswerKey(texto):
    mapa = {}
    if not texto or not texto.strip():
        return mapa
    txt = texto.strip()
    pares = re.findall(r'(?:^|[\s,;|])0*(\d{1,3})\s*(?:[:\-–=.)]|\s+)\s*([A-Ea-e])\b', txt)
    if pares:
        for num_s, letra in pares:
            n = int(num_s)
            if 1 <= n <= 200 and n not in mapa:
                mapa[n] = letra.upper()
        if mapa:
            return mapa

    letras = re.findall(r'\b([A-Ea-e])\b', txt)
    for i, l in enumerate(letras, start=1):
        mapa[i] = l.upper()
    return mapa


def extractUdescAnswerKeyPdf(pdf_bytes):
    # especifico para o da udesc
    if fitz is None or not pdf_bytes:
        return None
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    words = []
    for page in doc:
        words.extend(page.get_text('words'))
    doc.close()

    texto_tudo = ' '.join(w[4] for w in words).lower()
    if 'matutino' not in texto_tudo or 'vespertino' not in texto_tudo:
        return None

    y_vesp = None
    for w in words:
        if 'vespertino' in w[4].lower():
            y_vesp = w[1]
            break
    if y_vesp is None:
        return None

    mapa_nomes_hdr = {
        'matemática': 'Matemática',
        'biologia': 'Biologia',
        'inglês': 'LINGUA_ESTRANGEIRA',
        'espanhol': 'LINGUA_ESTRANGEIRA',
        'portuguesa': 'Português',
        'física': 'Física',
        'química': 'Química',
        'história': 'História',
        'geografia': 'Geografia',
        'filosofia': 'Filosofia',
        'sociologia': 'Sociologia',
    }

    resultado = {'matutino': {}, 'vespertino': {}}

    for periodo, filtro_y in [('matutino', lambda y: y < y_vesp), ('vespertino', lambda y: y >= y_vesp)]:
        ws = [w for w in words if filtro_y(w[1])]
        headers = []
        for w in ws:
            chave = w[4].strip().lower()
            if chave in mapa_nomes_hdr:
                headers.append(((w[0] + w[2]) / 2.0, w[1], mapa_nomes_hdr[chave]))

        ws_ord = sorted(ws, key=lambda w: (round(w[1] / 3.0), w[0]))
        linhas = []
        for w in ws_ord:
            if not linhas or abs(linhas[-1][0][1] - w[1]) > 4.0:
                linhas.append([w])
            else:
                linhas[-1].append(w)

        for linha in linhas:
            linha.sort(key=lambda w: w[0])
            i = 0
            while i < len(linha) - 1:
                w_num = linha[i]
                w_val = linha[i + 1]
                t_num = w_num[4].strip()
                t_val = w_val[4].strip()
                dx = w_val[0] - w_num[2]
                if (
                    t_num.isdigit()
                    and 1 <= int(t_num) <= 50
                    and 8 <= dx <= 75
                    and (re.fullmatch(r'[A-Ea-e]', t_val) or t_val.lower().startswith('anulad'))
                ):
                    num_q = int(t_num)
                    anulada = t_val.lower().startswith('anulad')
                    letra = None if anulada else t_val.upper()
                    x_mid = (w_num[0] + w_val[2]) / 2.0
                    y_row = w_num[1]

                    # Encontra o cabecalho de disciplina
                    cand_hdrs = [h for h in headers if h[1] < y_row and abs(h[0] - x_mid) <= 60]
                    disc = None
                    if cand_hdrs:
                        
                        cand_hdrs.sort(key=lambda h: (y_row - h[1]) + abs(h[0] - x_mid) * 1.5)
                        disc = cand_hdrs[0][2]

                    if num_q not in resultado[periodo] or disc != 'LINGUA_ESTRANGEIRA':
                        resultado[periodo][num_q] = {
                            'letra': letra,
                            'disciplina': disc,
                            'anulada': anulada
                        }
                    i += 2
                    continue
                i += 1

    return resultado if (resultado['matutino'] or resultado['vespertino']) else None


def detectUdescPeriod(texto_prova):
    # ve se eh matutino ou vespertino
    inicio = (texto_prova or '')[:4500].lower()
    if 'vespertino' in inicio:
        return 'vespertino'
    if 'matutino' in inicio:
        return 'matutino'
    t = (texto_prova or '').lower()
    pts_mat = sum(len(re.findall(p, t)) for p in [r'\bmatemática\b', r'\bbiologia\b', r'\blíngua\s+portuguesa\b'])
    pts_vesp = sum(len(re.findall(p, t)) for p in [r'\bfísica\b', r'\bquímica\b', r'\bhistória\b', r'\bgeografia\b', r'\bfilosofia\b', r'\bsociologia\b'])
    return 'vespertino' if pts_vesp > pts_mat else 'matutino'


def extractLetterAnswerKeyPdf(pdf_bytes):
    # gabarito de multipla escolha
    if fitz is None or not pdf_bytes:
        return {}
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    texto = '\n'.join(page.get_text('text') for page in doc)
    doc.close()

    mapa = {}
    tokens = [t.strip() for t in re.split(r'[\s|;:\-–]+', texto) if t.strip()]
    i = 0
    while i < len(tokens) - 1:
        tok = tokens[i]
        prox = tokens[i + 1]
        if tok.isdigit() and 1 <= int(tok) <= 200 and re.fullmatch(r'[A-Ea-e]', prox):
            n = int(tok)
            if n not in mapa:
                mapa[n] = prox.upper()
            i += 2
            continue
        i += 1

    if len(mapa) < 3:
        mapa.update(parseLetterAnswerKey(texto))
    return mapa


def splitMultipleChoicePdfQuestions(texto_completo, instituicao='', ignorar_lingua_estrangeira=True):
    # separa questao de multipla escolha
    eh_enem = (instituicao or '').strip().upper() == 'ENEM'
    eh_udesc = (instituicao or '').strip().upper() == 'UDESC'

    texto = texto_completo or ''
    texto = re.sub(r'[ \t]+', ' ', texto)
    texto = re.sub(r'\n{3,}', '\n\n', texto)

    # Normaliza formatos de alternativas
    texto = re.sub(r'(?:^|\n)\s*(?:\(\s*\)\s*)?([A-Ea-e])\s*[\)\.\-–]\s*(?:\(\s*\)\s*)?', lambda m: f'\n{m.group(1).upper()}) ', texto)
    texto = re.sub(r'(?:^|\n)\s*\(([A-Ea-e])\)\s*', lambda m: f'\n{m.group(1).upper()}) ', texto)

    # Marcadores de inicio de questao
    marc_questao = list(re.finditer(r'(?:^|\n)\s*(?:QUEST[AÃ]O|Quest[aã]o)\s*[:.\-–]?\s*0*(\d{1,3})\b[^\n]*', texto))
    marc_num_traco = list(re.finditer(r'(?:^|\n)\s*0*([1-9]\d{0,2})\s*[\-–]\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ(“"\d])', texto))
    marc_paren = list(re.finditer(r'(?:^|\n)\s*0*([1-9]\d{0,2})\)\s+', texto))
    marc_ponto = list(re.finditer(r'(?:^|\n)\s*0*([1-9]\d{0,2})\.\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ(“"])', texto))

    candidatos_marc = [marc_questao, marc_num_traco, marc_paren, marc_ponto]
    if len(marc_questao) >= 2:
        marcadores = marc_questao
    else:
        marcadores = max(candidatos_marc, key=len)

    if not marcadores:
        return []

    # Padrao principal de alternativas
    padrao_alt_norm = re.compile(
        r'(?:^|\n)\s*([A-E])\)\s*(.+?)(?=(?:\n\s*[A-E]\)\s*)|$)',
        re.DOTALL
    )
    padrao_alt_solta = re.compile(
        r'(?:^|\n)\s*([A-E])\s*\n\s*(.+?)(?=(?:\n\s*[A-E]\s*\n)|$)',
        re.DOTALL
    )

    disciplina_atual = None
    cab_inicial = detectSubjectFromText(texto[:marcadores[0].start()])
    if cab_inicial:
        disciplina_atual = cab_inicial

    questoes_parseadas = []
    vistos_num = set()

    for i, m in enumerate(marcadores):
        num_q = int(m.group(1))
        if num_q in vistos_num or num_q > 200:
            continue

        ini = m.end()
        fim = marcadores[i + 1].start() if i + 1 < len(marcadores) else len(texto)
        bloco = texto[ini:fim].strip()

        trecho_antes = texto[max(0, m.start() - 280):m.start()]
        disc_nova = detectSubjectFromText(trecho_antes)
        if disc_nova:
            disciplina_atual = disc_nova

        # Pula lingua estrangeira
        if ignorar_lingua_estrangeira:
            if eh_enem and 1 <= num_q <= 5:
                continue
            if disciplina_atual == 'LINGUA_ESTRANGEIRA':
                continue
            if re.search(r'\b(?:L[IÍ]NGUA\s+ESTRANGEIRA|INGL[EÊ]S\s*\n|ESPANHOL\s*\n)\b', trecho_antes, flags=re.I):
                continue

        matches = padrao_alt_norm.findall(bloco)
        usou_solta = False
        if len(matches) < 4:
            matches_s = padrao_alt_solta.findall(bloco)
            if len(matches_s) >= 4:
                matches = matches_s
                usou_solta = True

        if len(matches) < 4:
            continue

        alternativas = []
        letras_vistas = set()
        for letra_raw, txt_a in matches:
            letra = letra_raw.upper()
            if letra in letras_vistas:
                continue
            if not alternativas and letra != 'A':
                continue
            letras_vistas.add(letra)
            txt_limpo = re.sub(r'\s+', ' ', txt_a).strip()
            txt_limpo = re.sub(r'\b(?:RASCUNHO|PROVA\s+DE\s+REDA[ÇC][AÃ]O|VESTIBULAR\s+UDESC[^\n]*).*$', '', txt_limpo, flags=re.I).strip()
            alternativas.append((letra, txt_limpo))
            if len(alternativas) == 5:
                break

        if len(alternativas) < 4:
            continue

        if usou_solta:
            m_first = re.search(r'(?:^|\n)\s*A\s*\n', bloco)
        else:
            m_first = re.search(r'(?:^|\n)\s*A\)\s*', bloco)
        enunciado = bloco[:m_first.start()].strip() if m_first else bloco.strip()
        enunciado = re.sub(r'\n{3,}', '\n\n', enunciado).strip()
        if len(enunciado) < 8:
            continue

        vistos_num.add(num_q)
        questoes_parseadas.append({
            'numero': num_q,
            'disciplina_cabecalho': None if eh_enem else disciplina_atual,
            'enunciado': enunciado,
            'alternativas': alternativas
        })

    return questoes_parseadas


def importUnifiedExamPdf(
    pdf_bytes,
    id_vestibular,
    id_assunto='auto',
    upload_dir='static/uploads',
    id_professor=None,
    id_gestao=None,
    dificuldade='Media',
    gabarito_pdf_bytes=None,
    gabarito_str='',
    microdados_csv_bytes=None
):
    # importador geral
    con = connectDatabase()
    cur = con.cursor()
    cur.execute('select instituicao, ano from vestibular where id_vestibular = %s;', (int(id_vestibular),))
    row_v = cur.fetchone()
    cur.close()
    con.close()

    instituicao = (row_v[0] if row_v and row_v[0] else 'Vestibular').strip()
    ano_vest = row_v[1] if row_v else ''
    inst_up = instituicao.upper()

    # usa o extrair ufsc
    if inst_up == 'UFSC':
        return extractUfscPdfOffline(
            pdf_bytes=pdf_bytes,
            gabarito_str=gabarito_str,
            id_vestibular=id_vestibular,
            id_assunto=id_assunto,
            upload_dir=upload_dir,
            id_professor=id_professor,
            id_gestao=id_gestao,
            dificuldade=dificuldade,
            gabarito_pdf_bytes=gabarito_pdf_bytes
        )

    # extrai texto do pdf
    texto_completo, imagens_extraidas = readOrderedPdfText(pdf_bytes, upload_dir)
    modo_auto = str(id_assunto) == 'auto'

    # detecta se eh somatoria ou alternativa
    qtd_somas = len(re.findall(r'(?:^|\n)\s*(?:01|02|04|08|16)\.\s+', texto_completo))
    qtd_letras = len(re.findall(r'(?:^|\n)\s*(?:\([A-Ea-e]\)|[A-Ea-e]\s*[\)\.\-–])\s+', texto_completo))
    if inst_up != 'ENEM' and qtd_somas >= 6 and qtd_somas > qtd_letras:
        return extractUfscPdfOffline(
            pdf_bytes=pdf_bytes,
            gabarito_str=gabarito_str,
            id_vestibular=id_vestibular,
            id_assunto=id_assunto,
            upload_dir=upload_dir,
            id_professor=id_professor,
            id_gestao=id_gestao,
            dificuldade=dificuldade,
            gabarito_pdf_bytes=gabarito_pdf_bytes
        )

    # 3) Multipla escolha
    mapa_gab = {}
    mapa_gab_udesc = {}
    periodo_udesc = None

    if gabarito_pdf_bytes:
        udesc_parsed = extractUdescAnswerKeyPdf(gabarito_pdf_bytes) if inst_up == 'UDESC' else None
        if udesc_parsed:
            periodo_udesc = detectUdescPeriod(texto_completo)
            mapa_gab_udesc = udesc_parsed.get(periodo_udesc, {})
            for num_k, info_u in mapa_gab_udesc.items():
                if info_u.get('letra'):
                    mapa_gab[num_k] = info_u['letra']
        else:
            mapa_gab.update(extractLetterAnswerKeyPdf(gabarito_pdf_bytes))

    if gabarito_str:
        mapa_gab.update(parseLetterAnswerKey(gabarito_str))

    mapa_inep = classificador_enem.parseInepMicrodataCsv(microdados_csv_bytes) if microdados_csv_bytes else {}
    questoes = splitMultipleChoicePdfQuestions(
        texto_completo,
        instituicao=instituicao,
        ignorar_lingua_estrangeira=modo_auto
    )

    if not questoes:
        return [], (
            f'Não foram encontradas questões de múltipla escolha neste PDF de {instituicao}. '
            'Se o PDF for escaneado (imagem), utilize a opção "Extração inteligente (IA)".'
        )

    letras_ordem = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5}
    con = connectDatabase()
    cur = con.cursor()
    ids_criados = []
    com_gab = 0
    qtd_revisar = 0
    try:
        id_tag_rev = getOrCreateReviewTag(cur)
        id_tag_fmt = getOrCreateTagByName(cur, TAG_ERRO_FORMATACAO)
        cur.execute('select coalesce(max(id_questao), 0) from questao;')
        max_q = cur.fetchone()[0]
        cur.execute('select coalesce(max(id_alternativa), 0) from alternativa;')
        max_alt = cur.fetchone()[0]

        for idx, q in enumerate(questoes, start=1):
            num_q = q['numero']
            info_u = mapa_gab_udesc.get(num_q) if mapa_gab_udesc else None
            if info_u:
                if info_u.get('anulada'):
                    continue
                if modo_auto and info_u.get('disciplina') == 'LINGUA_ESTRANGEIRA':
                    continue

            letra_gab = mapa_gab.get(num_q) or mapa_gab.get(idx)
            if letra_gab:
                com_gab += 1

            rotulo_periodo = f' {periodo_udesc.capitalize()}' if periodo_udesc else ''
            prefixo = f"({instituicao} {ano_vest}{rotulo_periodo} — Q{num_q:02d}) " if ano_vest else f"({instituicao}{rotulo_periodo} — Q{num_q:02d}) "
            enunciado_final = prefixo + q['enunciado']

            cur.execute(
                'select id_questao from questao where id_vestibular = %s and enunciado like %s limit 1;',
                (int(id_vestibular), prefixo + '%')
            )
            if cur.fetchone():
                continue

            precisa_revisao = False
            texto_classif = q['enunciado'] + ' ' + ' '.join(a[1] for a in q['alternativas'])
            erro_fmt = looksLikeBrokenEquation(texto_classif)

            if modo_auto:
                disc_cab = (info_u.get('disciplina') if info_u and info_u.get('disciplina') else q.get('disciplina_cabecalho'))
                # separa port de literatura
                if disc_cab == 'Português' and re.search(
                    r'\b(?:poema|verso|estrofe|eu\s+lírico|romance|obra\s+literária|literatura|modernismo|romantismo|realismo|barroco|machado\s+de\s+assis|clarice\s+lispector|drummond|guimarães\s+rosa)\b',
                    texto_classif,
                    flags=re.IGNORECASE
                ):
                    disc_cab = 'Literatura'

                if disc_cab and disc_cab != 'LINGUA_ESTRANGEIRA':
                    frente_c, assunto_c, conf_c = classificador_enem.classifyTopicBySubject(disc_cab, texto_classif)
                    assunto_destino = getOrCreateClassifiedTopic(cur, disc_cab, frente_c, assunto_c)
                    precisa_revisao = not conf_c
                else:
                    slug = classificador_enem.inferEnemAreaByNumber(num_q) if inst_up == 'ENEM' else None
                    info_inep = mapa_inep.get(num_q) if mapa_inep else None
                    assunto_destino, precisa_revisao, _ = getOrCreateEnemAreaTopic(
                        cur, slug, texto_classif, info_inep=info_inep
                    )
            else:
                assunto_destino = int(id_assunto)

            max_q += 1
            cur.execute(
                'insert into questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) values (%s, %s, %s, %s, %s, %s, %s);',
                (max_q, int(id_vestibular), id_professor, id_gestao, 'Multipla Escolha', dificuldade, enunciado_final)
            )
            cur.execute('insert into assunto_questao (id_questao, id_assunto) values (%s, %s);', (max_q, assunto_destino))

            if precisa_revisao:
                cur.execute('insert into questao_tag (id_tag, id_questao) values (%s, %s) on conflict do nothing;', (id_tag_rev, max_q))
                qtd_revisar += 1
            if erro_fmt:
                cur.execute('insert into questao_tag (id_tag, id_questao) values (%s, %s) on conflict do nothing;', (id_tag_fmt, max_q))
                if not precisa_revisao:
                    qtd_revisar += 1

            for letra_alt, txt_alt in q['alternativas']:
                max_alt += 1
                val_p = letras_ordem.get(letra_alt, 1)
                correta = (letra_alt == letra_gab) if letra_gab else False
                cur.execute(
                    'insert into alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) values (%s, %s, %s, %s, %s);',
                    (max_alt, max_q, val_p, txt_alt, correta)
                )

            ids_criados.append(max_q)

        con.commit()
        if not ids_criados:
            return [], f'As questões desta prova de {instituicao} já estavam cadastradas para este vestibular.'
        extra_rev = f' • {qtd_revisar} marcada(s) com "Revisar Matéria" para conferência rápida.' if qtd_revisar else ' Todas classificadas com confiança!'
        return ids_criados, f'{len(ids_criados)} questões de {instituicao} importadas ({com_gab} com gabarito aplicado){extra_rev}'
    except Exception as e:
        con.rollback()
        return [], f'Erro ao importar PDF de {instituicao}: {e}'
    finally:
        cur.close()
        con.close()

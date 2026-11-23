import os
import re
import math
import json
import pandas as pd
from google import genai
from google.genai import types
from database.conexao import connectDatabase, loadEnvFile

try:
    import pymupdf as fitz
except ImportError:
    fitz = None

loadEnvFile()
API_KEY = os.environ.get('GEMINI_API_KEY', '')

# Modelos
MODELOS_LLM = ['gemini-3.5-flash', 'gemini-3.1-flash-lite']
TIMEOUT_TEXTO_MS = 45000
TIMEOUT_ARQUIVO_MS = 90000


def createGeminiClient(timeout_ms):
    return genai.Client(api_key=API_KEY, http_options=types.HttpOptions(timeout=timeout_ms))


def generateWithFallback(conteudo, timeout_ms, config=None):
    # tenta cada modelo
    ultimo_erro = None
    for modelo in MODELOS_LLM:
        try:
            cliente = createGeminiClient(timeout_ms)
            resposta = cliente.models.generate_content(
                model=modelo, contents=conteudo, config=config
            )
            if resposta and resposta.text:
                return resposta.text.strip(), None
        except Exception as e:
            ultimo_erro = f'{modelo}: {str(e)[:200]}'
            print(f'Falha no modelo {modelo}:', str(e)[:200])
    return None, ultimo_erro or 'Nenhum modelo respondeu.'


def callGeminiLlm(prompt):
    texto, _ = generateWithFallback(prompt, TIMEOUT_TEXTO_MS)
    return texto


def repairCorruptedLatex(texto):
    # corrige o latex
    if not isinstance(texto, str):
        return ''
    t = texto
    t = re.sub(r'\x0crac\b', r'\\frac', t)
    t = re.sub(r'\x08eta\b', r'\\beta', t)
    t = re.sub(r'\x08ar\b', r'\\bar', t)
    t = re.sub(r'\t(ext|imes|heta|au|an|o)\b', r'\\t\1', t)
    t = re.sub(r'\r(ho|ightarrow|angle)\b', r'\\r\1', t)
    return t.strip()


def parseResilientJson(texto):
   # divide o json
    if not texto:
        return None
    limpo = texto.strip()
    limpo = re.sub(r'^```(?:json)?\s*', '', limpo, flags=re.IGNORECASE)
    limpo = re.sub(r'\s*```$', '', limpo)

    try:
        return json.loads(limpo)
    except json.JSONDecodeError:
        pass

    # corrige barras
    corrigido = re.sub(r'(?<!\\)\\(?![\\"/bfnrtu])', r'\\\\', limpo)
    try:
        return json.loads(corrigido)
    except json.JSONDecodeError:
        pass

    # extrai bloco
    m_arr = re.search(r'\[.*\]', corrigido, flags=re.DOTALL)
    if m_arr:
        try:
            return json.loads(m_arr.group(0))
        except json.JSONDecodeError:
            pass
    objetos = []
    for m_obj in re.finditer(r'\{[^{}]*"enunciado"[^{}]*"alternativas"\s*:\s*\[.*?\][^{}]*\}', corrigido, flags=re.DOTALL):
        try:
            objetos.append(json.loads(m_obj.group(0)))
        except json.JSONDecodeError:
            continue
    return objetos if objetos else None


def splitPdfIntoBatches(pdf_bytes, paginas_por_lote=2):
    # divide o pdf
    if fitz is None:
        return [(1, 1, pdf_bytes)]
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    total_pags = len(doc)
    if total_pags <= paginas_por_lote:
        doc.close()
        return [(1, total_pags, pdf_bytes)]

    lotes = []
    for ini in range(0, total_pags, paginas_por_lote):
        fim = min(total_pags - 1, ini + paginas_por_lote - 1)
        sub = fitz.open()
        sub.insert_pdf(doc, from_page=ini, to_page=fim)
        lotes.append((ini + 1, fim + 1, sub.tobytes()))
        sub.close()
    doc.close()
    return lotes


def buildExtractionPrompt(gabarito_hint=''):
    extra_gab = ''
    if gabarito_hint and gabarito_hint.strip():
        extra_gab = (
            f"\nGABARITO OFICIAL INFORMADO PELO USUÁRIO (OBRIGATÓRIO SEGUIR): {gabarito_hint.strip()}\n"
            "- Use exatamente este gabarito para definir indicador_correta (em Somatoria, decomponha a soma em potencias de 2: 01, 02, 04, 08, 16, 32, 64).\n"
        )
    return f"""Você é um especialista em digitalização de provas de vestibulares brasileiros (UFSC, ENEM, UDESC e outros).
Analise o arquivo enviado (imagem ou páginas de PDF) e extraia TODAS as questões OBJETIVAS completas presentes (Somatória ou Múltipla Escolha).

IGNORE completamente:
- Capas, instruções gerais, folha de rascunho, redação, questões discursivas/abertas e questões de Língua Estrangeira (Inglês/Espanhol/Francês/Alemão/Italiano).
- Se a página não tiver nenhuma questão objetiva válida, retorne [].
{extra_gab}
Retorne EXCLUSIVAMENTE um JSON válido no formato de lista:
[
  {{
    "enunciado": "Texto completo e fiel do enunciado (incluindo contexto/texto de apoio resumido apenas se enorme, mas preservando todos os dados numéricos e equações)",
    "tipo": "Somatoria",
    "dificuldade": "Media",
    "alternativas": [
      {{"valor_proposicao": 1, "texto": "Texto da proposição sem o número/letra na frente", "indicador_correta": false}},
      {{"valor_proposicao": 2, "texto": "Texto da proposição sem o número/letra na frente", "indicador_correta": true}}
    ],
    "dica": "Dica conceitual objetiva em 1-2 frases sem revelar a resposta final",
    "resolucao": "Resolução passo a passo clara explicando por que cada item/alternativa está certo ou errado"
  }}
]

REGRAS ESTRITAS:
1. Somatória (01, 02, 04, 08, 16, 32, 64): "tipo" = "Somatoria" e "valor_proposicao" = 1, 2, 4, 8, 16, 32 ou 64.
2. Múltipla escolha (A, B, C, D, E): "tipo" = "Multipla Escolha", "valor_proposicao" = 1 a 5 (exatamente UMA alternativa com "indicador_correta": true).
3. Remova o prefixo ("01.", "A)", "(a)") do início do campo "texto" das alternativas.
4. Equações matemáticas: escreva em LaTeX limpo entre cifrões SEM espaço interno (ex: "$h(t) = -2t^2 + 8t + 0,6$", "$\\sqrt{{2}}$", "$\\frac{{a}}{{b}}$"). SEMPRE duplique a barra invertida em JSON ("\\\\frac", "\\\\sqrt", "\\\\Omega").
5. NUNCA coloque valores em dinheiro ("R$ 5,00") dentro de cifrões LaTeX — escreva literalmente "R$ 5,00".
6. "dificuldade" deve ser exatamente "Facil", "Media" ou "Dificil".
"""


def sanitizeExtractedQuestions(dados):
    # limpa o json retornado pela IA
    if not dados:
        return []
    if isinstance(dados, dict):
        dados = [dados]
    if not isinstance(dados, list):
        return []

    limpas = []
    for q in dados:
        if not isinstance(q, dict):
            continue
        enunciado = repairCorruptedLatex(q.get('enunciado') or '')
        alts_raw = q.get('alternativas') or []
        if not enunciado or len(alts_raw) < 2:
            continue

        tipo = (q.get('tipo') or 'Multipla Escolha').strip()
        if 'soma' in tipo.lower():
            tipo = 'Somatoria'
        else:
            tipo = 'Multipla Escolha'

        dif = (q.get('dificuldade') or 'Media').strip()
        if dif.lower().startswith('fac') or dif.lower().startswith('fác'):
            dif = 'Facil'
        elif dif.lower().startswith('dif'):
            dif = 'Dificil'
        else:
            dif = 'Media'

        alts_limpas = []
        for idx, a in enumerate(alts_raw, start=1):
            if not isinstance(a, dict):
                continue
            txt_a = repairCorruptedLatex(a.get('texto') or '')
            txt_a = re.sub(r'^(?:01|02|04|08|16|32|64)\s*[\.\-\)]\s*', '', txt_a)
            txt_a = re.sub(r'^[A-Ea-e]\s*[\)\.\-]\s*', '', txt_a).strip()
            if not txt_a:
                continue
            try:
                val_p = int(a.get('valor_proposicao', idx))
            except (TypeError, ValueError):
                val_p = (2 ** (idx - 1)) if tipo == 'Somatoria' else idx
            if tipo == 'Somatoria' and val_p not in (1, 2, 4, 8, 16, 32, 64):
                val_p = 2 ** (idx - 1)
            elif tipo == 'Multipla Escolha':
                val_p = idx
            alts_limpas.append({
                'valor_proposicao': val_p,
                'texto': txt_a,
                'indicador_correta': bool(a.get('indicador_correta', False))
            })

        if len(alts_limpas) < 2:
            continue

        # garante uma correta
        if tipo == 'Multipla Escolha':
            ja_teve = False
            for a in alts_limpas:
                if a['indicador_correta']:
                    if ja_teve:
                        a['indicador_correta'] = False
                    else:
                        ja_teve = True

        limpas.append({
            'enunciado': enunciado,
            'tipo': tipo,
            'dificuldade': dif,
            'alternativas': alts_limpas,
            'dica': repairCorruptedLatex(q.get('dica') or ''),
            'resolucao': repairCorruptedLatex(q.get('resolucao') or '')
        })
    return limpas


def extractQuestionsFromFile(arquivo_bytes, mime_type, gabarito_hint='', callback_progresso=None):
    # recebe pdf/imagem e retorna a questao
    prompt = buildExtractionPrompt(gabarito_hint=gabarito_hint)
    config = types.GenerateContentConfig(
        response_mime_type='application/json',
        temperature=0.1
    )

    if mime_type == 'application/pdf':
        lotes = splitPdfIntoBatches(arquivo_bytes, paginas_por_lote=2)
    else:
        lotes = [(1, 1, arquivo_bytes)]

    todas_questoes = []
    ultimo_erro = None
    total_lotes = len(lotes)

    for idx_lote, (p_ini, p_fim, lote_bytes) in enumerate(lotes, start=1):
        if callback_progresso:
            if total_lotes > 1:
                callback_progresso(
                    f'IA analisando páginas {p_ini}–{p_fim} (lote {idx_lote}/{total_lotes}) • {len(todas_questoes)} questão(ões) extraída(s)...'
                )
            else:
                callback_progresso('IA analisando o arquivo e transcrevendo equações e alternativas...')

        parte = types.Part.from_bytes(data=lote_bytes, mime_type=mime_type)
        texto, err = generateWithFallback([parte, prompt], TIMEOUT_ARQUIVO_MS, config=config)
        if err and not texto:
            ultimo_erro = err
            continue

        parsed = parseResilientJson(texto)
        if parsed:
            todas_questoes.extend(sanitizeExtractedQuestions(parsed))

    if not todas_questoes and ultimo_erro:
        raise RuntimeError(ultimo_erro)

    return todas_questoes


def saveExtractedQuestions(questoes_json, id_vestibular, id_assunto, id_professor=None, id_gestao=None, arquivo_midia=None, legenda_midia=None):
    # salva no db
    from services import importadores, classificador_enem

    modo_auto = str(id_assunto) == 'auto'
    ids_criados = []
    con = connectDatabase()
    cur = con.cursor()
    try:
        id_tag_rev = importadores.getOrCreateReviewTag(cur) if modo_auto else None
        cur.execute('select coalesce(max(id_questao), 0) from questao;')
        max_q = cur.fetchone()[0]
        cur.execute('select coalesce(max(id_alternativa), 0) from alternativa;')
        max_alt = cur.fetchone()[0]
        cur.execute('select coalesce(max(id_dica), 0) from dica;')
        max_dica = cur.fetchone()[0]
        cur.execute('select coalesce(max(id_midia), 0) from midia;')
        max_midia = cur.fetchone()[0]

        for q in questoes_json:
            enunciado = (q.get('enunciado') or '').strip()
            if not enunciado:
                continue

            max_q += 1
            tipo = q.get('tipo', 'Somatoria')
            if tipo not in ('Somatoria', 'Multipla Escolha'):
                tipo = 'Somatoria'
            dificuldade = q.get('dificuldade', 'Media')
            if dificuldade not in ('Facil', 'Media', 'Dificil'):
                dificuldade = 'Media'

            precisa_revisao = False
            if modo_auto:
                texto_cls = enunciado + ' ' + ' '.join((a.get('texto') or '') for a in q.get('alternativas', []))
                res_c = classificador_enem.classifyEnemQuestion(None, texto_cls)
                assunto_destino = importadores.getOrCreateClassifiedTopic(
                    cur, res_c['disciplina'], res_c['frente'], res_c['assunto']
                )
                precisa_revisao = res_c['precisa_revisao']
            else:
                assunto_destino = int(id_assunto)

            cur.execute(
                'insert into questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) values (%s, %s, %s, %s, %s, %s, %s);',
                (max_q, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado)
            )
            cur.execute('insert into assunto_questao (id_questao, id_assunto) values (%s, %s);', (max_q, assunto_destino))

            if precisa_revisao and id_tag_rev:
                cur.execute('insert into questao_tag (id_tag, id_questao) values (%s, %s) on conflict do nothing;', (id_tag_rev, max_q))

            for idx, alt in enumerate(q.get('alternativas', []), start=1):
                max_alt += 1
                val_p = int(alt.get('valor_proposicao', idx))
                txt_a = (alt.get('texto') or '').strip()
                corr = bool(alt.get('indicador_correta', False))
                cur.execute(
                    'insert into alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) values (%s, %s, %s, %s, %s);',
                    (max_alt, max_q, val_p, txt_a, corr)
                )

            dica_txt = (q.get('dica') or '').strip()
            if dica_txt:
                max_dica += 1
                cur.execute(
                    'insert into dica (id_dica, id_questao, tipo, conteudo_texto) values (%s, %s, %s, %s);',
                    (max_dica, max_q, 'Dica Inicial', dica_txt)
                )

            res_txt = (q.get('resolucao') or '').strip()
            if res_txt:
                max_dica += 1
                cur.execute(
                    'insert into dica (id_dica, id_questao, tipo, conteudo_texto) values (%s, %s, %s, %s);',
                    (max_dica, max_q, 'Resolucao Passo a Passo', res_txt)
                )

            if arquivo_midia:
                max_midia += 1
                cur.execute(
                    'insert into midia (id_midia, id_questao, legenda, arquivo) values (%s, %s, %s, %s);',
                    (max_midia, max_q, legenda_midia or 'Imagem original da questao', arquivo_midia)
                )

            ids_criados.append(max_q)

        con.commit()
        return ids_criados
    except Exception as e:
        con.rollback()
        print('Erro ao salvar questoes extraidas:', e)
        return []
    finally:
        cur.close()
        con.close()


def generateOwlHintAndSolution(id_questao):
    # gera dica inicial
    con = connectDatabase()
    cur = con.cursor()
    cur.execute('select tipo, dificuldade, enunciado from questao where id_questao = %s;', (id_questao,))
    q = cur.fetchone()
    if not q:
        cur.close()
        con.close()
        return False

    cur.execute(
        'select valor_proposicao, texto, indicador_correta from alternativa where id_questao = %s order by valor_proposicao;',
        (id_questao,)
    )
    alts = cur.fetchall()

    tipo_q, dif_q, enunc_q = q
    letras = ['A', 'B', 'C', 'D', 'E']
    linhas_alts = []
    corretas_rot = []
    soma = 0
    for i, (vp, txt, corr) in enumerate(alts):
        rot = f'{vp:02d}' if tipo_q == 'Somatoria' else letras[i % 5]
        marca = ' [CORRETA]' if corr else ' [INCORRETA]'
        linhas_alts.append(f'{rot}) {txt}{marca}')
        if corr:
            corretas_rot.append(rot)
            soma += vp

    gabarito_oficial = f'Somatória = {soma:02d} (itens {", ".join(corretas_rot)})' if tipo_q == 'Somatoria' else f'Alternativa {", ".join(corretas_rot)}'

    prompt = (
        f"Você é um professor do Cursinho Pré-Vestibular PES (UFSC).\n"
        f"Questão ({tipo_q} — {dif_q}):\n{enunc_q}\n\n"
        f"Itens:\n" + "\n".join(linhas_alts) + "\n\n"
        f"GABARITO OFICIAL: {gabarito_oficial}\n\n"
        "Retorne EXCLUSIVAMENTE um JSON válido com duas chaves:\n"
        '{"dica": "Dica conceitual curta (1 a 2 frases) que orienta o raciocínio sem revelar a resposta.", '
        '"resolucao": "Resolução passo a passo didática e fiel ao gabarito oficial, usando quebras de linha (\\\\n) entre cada item/etapa. Use LaTeX $...$ apenas para fórmulas matemáticas e nunca coloque R$ dentro de $...$."}'
    )

    config = types.GenerateContentConfig(response_mime_type='application/json', temperature=0.2)
    texto_llm, _ = generateWithFallback(prompt, TIMEOUT_TEXTO_MS, config=config)
    parsed = parseResilientJson(texto_llm) if texto_llm else None

    if isinstance(parsed, dict) and parsed.get('dica') and parsed.get('resolucao'):
        dica_texto = repairCorruptedLatex(parsed['dica'])
        resolucao_texto = repairCorruptedLatex(parsed['resolucao'])
    else:
        dica_texto = f'Analise os conceitos centrais do enunciado ({tipo_q}) e avalie cada item com atenção.'
        resolucao_texto = f'Gabarito oficial cadastrado: {gabarito_oficial}.'

    try:
        cur.execute('select coalesce(max(id_dica), 0) from dica;')
        max_id = cur.fetchone()[0]

        cur.execute(
            'insert into dica (id_dica, id_questao, tipo, conteudo_texto) values (%s, %s, %s, %s);',
            (max_id + 1, id_questao, 'Dica Inicial', dica_texto)
        )
        cur.execute(
            'insert into dica (id_dica, id_questao, tipo, conteudo_texto) values (%s, %s, %s, %s);',
            (max_id + 2, id_questao, 'Resolucao Passo a Passo', resolucao_texto)
        )
        con.commit()
        return True
    except Exception as e:
        con.rollback()
        print('Erro ao salvar dica:', e)
        return False
    finally:
        cur.close()
        con.close()


_TRANS_SEM_ACENTO = str.maketrans(
    'áàâãäéèêëíìîïóòôõöúùûüçñýÿ',
    'aaaaaeeeeiiiiooooouuuucnyy'
)


def normalizeSearchTokens(texto):
    if not texto:
        return []
    return re.findall(r'\w+', str(texto).lower().translate(_TRANS_SEM_ACENTO))


def buildEmbeddingVector(texto, vocabulario=None):
    from collections import Counter
    tokens = normalizeSearchTokens(texto)
    contagem = Counter(tokens)
    if vocabulario is not None:
        return [contagem.get(termo, 0) for termo in vocabulario]
    return contagem


def cosineSimilarity(v1, v2):
    if isinstance(v1, dict) and isinstance(v2, dict):
        if not v1 or not v2:
            return 0.0
        menor, maior = (v1, v2) if len(v1) <= len(v2) else (v2, v1)
        prod_escalar = sum(c * maior[k] for k, c in menor.items() if k in maior)
        if prod_escalar == 0:
            return 0.0
        norma1 = math.sqrt(sum(c * c for c in v1.values()))
        norma2 = math.sqrt(sum(c * c for c in v2.values()))
        return round(prod_escalar / (norma1 * norma2), 4)

    prod_escalar = sum(a * b for a, b in zip(v1, v2))
    norma1 = math.sqrt(sum(a * a for a in v1))
    norma2 = math.sqrt(sum(b * b for b in v2))
    if norma1 == 0 or norma2 == 0:
        return 0.0
    return round(prod_escalar / (norma1 * norma2), 4)


def semanticSearchQuestions(texto_busca):
    con = connectDatabase()
    cur = con.cursor()
    cur.execute('select id_questao, tipo, dificuldade, enunciado from questao;')
    questoes = cur.fetchall()
    cur.close()
    con.close()

    vetor_busca = buildEmbeddingVector(texto_busca)
    resultados = []
    for q in questoes:
        vetor_q = buildEmbeddingVector(q[3])
        sim = cosineSimilarity(vetor_busca, vetor_q)
        resultados.append((q[0], q[1], q[2], sim, q[3]))

    resultados.sort(key=lambda x: x[3], reverse=True)
    return pd.DataFrame(resultados, columns=['id_questao', 'tipo', 'dificuldade', 'cosineSimilarity', 'enunciado'])

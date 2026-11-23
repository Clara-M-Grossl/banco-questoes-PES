import csv
import io
import re


# Matiz de dados do enem -> CSV
MAPA_HABILIDADE_INEP = {
    # Ciencias da Natureza (CN)
    ('CN', 1):  ('Física', 'B', 'Ondulatória e Acústica'),
    ('CN', 2):  ('Física', 'B', 'Ondulatória e Acústica'),
    ('CN', 3):  ('Física', 'B', 'Óptica Geométrica'),
    ('CN', 4):  ('Física', 'C', 'Eletrodinâmica e Circuitos'),
    ('CN', 5):  ('Física', 'C', 'Eletrodinâmica e Circuitos'),
    ('CN', 6):  ('Física', 'C', 'Eletrodinâmica e Circuitos'),
    ('CN', 7):  ('Química', 'A', 'Química Geral e Separação de Misturas'),
    ('CN', 8):  (None, None, None),  # Interdisciplinar (Bio/Qui/Fis)
    ('CN', 9):  ('Biologia', 'A', 'Ecologia e Ciclos Biogeoquímicos'),
    ('CN', 10): ('Biologia', 'A', 'Impactos Ambientais e Sustentabilidade'),
    ('CN', 11): ('Biologia', 'A', 'Impactos Ambientais e Sustentabilidade'),
    ('CN', 12): ('Biologia', 'A', 'Impactos Ambientais e Sustentabilidade'),
    ('CN', 13): ('Biologia', 'C', 'Genética e Evolução'),
    ('CN', 14): ('Biologia', 'B', 'Citologia e Metabolismo Celular'),
    ('CN', 15): ('Biologia', 'B', 'Citologia e Metabolismo Celular'),
    ('CN', 16): ('Biologia', 'C', 'Genética e Evolução'),
    ('CN', 17): (None, None, None),  # Interdisciplinar (Fis/Qui/Bio)
    ('CN', 18): (None, None, None),
    ('CN', 19): ('Química', 'A', 'Atomística e Ligações Químicas'),
    ('CN', 20): ('Física', 'A', 'Leis de Newton e Dinâmica'),
    ('CN', 21): ('Física', 'B', 'Termologia e Calorimetria'),
    ('CN', 22): ('Física', 'A', 'Trabalho, Energia e Hidrostática'),
    ('CN', 23): ('Física', 'A', 'Trabalho, Energia e Hidrostática'),
    ('CN', 24): ('Química', 'A', 'Estequiometria e Soluções'),
    ('CN', 25): ('Química', 'B', 'Termoquímica e Cinética'),
    ('CN', 26): ('Química', 'C', 'Química Orgânica e Funções'),
    ('CN', 27): ('Química', 'B', 'Equilíbrio Químico e pH'),
    ('CN', 28): ('Biologia', 'A', 'Ecologia e Ciclos Biogeoquímicos'),
    ('CN', 29): ('Biologia', 'B', 'Microbiologia, Saúde e Imunologia'),
    ('CN', 30): ('Biologia', 'B', 'Microbiologia, Saúde e Imunologia'),

    # Matematica (MT)
    ('MT', 1):  ('Matemática', 'A', 'Razão, Proporção e Porcentagem'),
    ('MT', 2):  ('Matemática', 'C', 'Análise Combinatória e Probabilidade'),
    ('MT', 3):  ('Matemática', 'A', 'Razão, Proporção e Porcentagem'),
    ('MT', 4):  ('Matemática', 'A', 'Razão, Proporção e Porcentagem'),
    ('MT', 5):  ('Matemática', 'A', 'Razão, Proporção e Porcentagem'),
    ('MT', 6):  ('Matemática', 'B', 'Geometria Espacial e Plana'),
    ('MT', 7):  ('Matemática', 'B', 'Geometria Espacial e Plana'),
    ('MT', 8):  ('Matemática', 'B', 'Geometria Espacial e Plana'),
    ('MT', 9):  ('Matemática', 'B', 'Geometria Espacial e Plana'),
    ('MT', 10): ('Matemática', 'B', 'Geometria Espacial e Plana'),
    ('MT', 11): ('Matemática', 'A', 'Razão, Proporção e Porcentagem'),
    ('MT', 12): ('Matemática', 'B', 'Geometria Espacial e Plana'),
    ('MT', 13): ('Matemática', 'B', 'Geometria Espacial e Plana'),
    ('MT', 14): ('Matemática', 'B', 'Geometria Espacial e Plana'),
    ('MT', 15): ('Matemática', 'A', 'Razão, Proporção e Porcentagem'),
    ('MT', 16): ('Matemática', 'A', 'Razão, Proporção e Porcentagem'),
    ('MT', 17): ('Matemática', 'A', 'Razão, Proporção e Porcentagem'),
    ('MT', 18): ('Matemática', 'A', 'Funções de 1º e 2º Grau'),
    ('MT', 19): ('Matemática', 'A', 'Funções de 1º e 2º Grau'),
    ('MT', 20): ('Matemática', 'A', 'Funções de 1º e 2º Grau'),
    ('MT', 21): ('Matemática', 'A', 'Funções de 1º e 2º Grau'),
    ('MT', 22): ('Matemática', 'A', 'Funções de 1º e 2º Grau'),
    ('MT', 23): ('Matemática', 'A', 'Logaritmos, Exponenciais e Progressões'),
    ('MT', 24): ('Matemática', 'C', 'Estatística, Médias e Gráficos'),
    ('MT', 25): ('Matemática', 'C', 'Estatística, Médias e Gráficos'),
    ('MT', 26): ('Matemática', 'C', 'Estatística, Médias e Gráficos'),
    ('MT', 27): ('Matemática', 'C', 'Estatística, Médias e Gráficos'),
    ('MT', 28): ('Matemática', 'C', 'Análise Combinatória e Probabilidade'),
    ('MT', 29): ('Matemática', 'C', 'Análise Combinatória e Probabilidade'),
    ('MT', 30): ('Matemática', 'C', 'Análise Combinatória e Probabilidade'),

    # Ciencias Humanas (CH)
    ('CH', 1):  ('História', 'Geral', 'História Contemporânea e Guerras'),
    ('CH', 2):  ('História', 'Brasil', 'Brasil Colônia e Império'),
    ('CH', 3):  ('Sociologia', 'Única', 'Cultura, Identidade e Cidadania'),
    ('CH', 4):  ('Sociologia', 'Única', 'Trabalho, Desigualdade e Teoria Sociológica'),
    ('CH', 5):  ('História', 'Brasil', 'Brasil República e Era Vargas'),
    ('CH', 6):  ('Geografia', 'Física', 'Hidrografia, Biomas e Cartografia'),
    ('CH', 7):  ('Geografia', 'Política', 'Geopolítica Mundial e Urbanização'),
    ('CH', 8):  ('Geografia', 'Política', 'Geografia Agrária, Demografia e Economia'),
    ('CH', 9):  ('Geografia', 'Política', 'Geopolítica Mundial e Urbanização'),
    ('CH', 10): ('Geografia', 'Política', 'Geopolítica Mundial e Urbanização'),
    ('CH', 11): ('Sociologia', 'Única', 'Cultura, Identidade e Cidadania'),
    ('CH', 12): ('História', 'Brasil', 'Brasil República e Era Vargas'),
    ('CH', 13): ('Sociologia', 'Única', 'Cultura, Identidade e Cidadania'),
    ('CH', 14): ('Filosofia', 'Única', 'Filosofia Moderna, Ética e Política'),
    ('CH', 15): ('História', 'Brasil', 'Ditadura Militar e Redemocratização'),
    ('CH', 16): ('Geografia', 'Política', 'Geopolítica Mundial e Urbanização'),
    ('CH', 17): ('Sociologia', 'Única', 'Trabalho, Desigualdade e Teoria Sociológica'),
    ('CH', 18): ('Geografia', 'Política', 'Geografia Agrária, Demografia e Economia'),
    ('CH', 19): ('Geografia', 'Política', 'Geografia Agrária, Demografia e Economia'),
    ('CH', 20): ('Geografia', 'Política', 'Geopolítica Mundial e Urbanização'),
    ('CH', 21): ('Sociologia', 'Única', 'Cultura, Identidade e Cidadania'),
    ('CH', 22): ('Filosofia', 'Única', 'Filosofia Moderna, Ética e Política'),
    ('CH', 23): ('Filosofia', 'Única', 'Filosofia Moderna, Ética e Política'),
    ('CH', 24): ('Sociologia', 'Única', 'Cultura, Identidade e Cidadania'),
    ('CH', 25): ('Sociologia', 'Única', 'Cultura, Identidade e Cidadania'),
    ('CH', 26): ('Geografia', 'Física', 'Climatologia e Relevo Brasileiro'),
    ('CH', 27): ('Geografia', 'Física', 'Climatologia e Relevo Brasileiro'),
    ('CH', 28): ('Geografia', 'Física', 'Hidrografia, Biomas e Cartografia'),
    ('CH', 29): ('Geografia', 'Física', 'Hidrografia, Biomas e Cartografia'),
    ('CH', 30): ('Geografia', 'Física', 'Climatologia e Relevo Brasileiro'),

    # Linguagens e Codigos (LC)
    ('LC', 15): ('Literatura', 'Única', 'Escolas Literárias e Análise Poética'),
    ('LC', 16): ('Literatura', 'Única', 'Modernismo e Literatura Contemporânea'),
    ('LC', 17): ('Literatura', 'Única', 'Escolas Literárias e Análise Poética'),
    ('LC', 18): ('Português', 'Gramática', 'Interpretação de Texto e Gêneros Textuais'),
    ('LC', 19): ('Português', 'Gramática', 'Variação Linguística e Funções da Linguagem'),
    ('LC', 20): ('Português', 'Gramática', 'Interpretação de Texto e Gêneros Textuais'),
    ('LC', 21): ('Português', 'Gramática', 'Interpretação de Texto e Gêneros Textuais'),
    ('LC', 22): ('Português', 'Gramática', 'Interpretação de Texto e Gêneros Textuais'),
    ('LC', 23): ('Português', 'Gramática', 'Interpretação de Texto e Gêneros Textuais'),
    ('LC', 24): ('Português', 'Gramática', 'Interpretação de Texto e Gêneros Textuais'),
    ('LC', 25): ('Português', 'Gramática', 'Variação Linguística e Funções da Linguagem'),
    ('LC', 26): ('Português', 'Gramática', 'Variação Linguística e Funções da Linguagem'),
    ('LC', 27): ('Português', 'Gramática', 'Sintaxe e Concordância Verbal'),
}


def parseInepMicrodataCsv(csv_bytes, cor_preferida='AZUL'):
    # Le o arquivo oficial ITENS_PROVA_<ano>.csv dos Microdados do INEP e retorna um dicionario
    texto = None
    for enc in ('utf-8-sig', 'latin-1', 'cp1252'):
        try:
            texto = csv_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if not texto:
        return {}

    # Detecta ;/,
    primeira_linha = texto.splitlines()[0] if texto.splitlines() else ''
    delim = ';' if primeira_linha.count(';') >= primeira_linha.count(',') else ','
    leitor = csv.DictReader(io.StringIO(texto), delimiter=delim)

    mapa = {}
    mapa_fallback = {}
    for row in leitor:
        r = {(k or '').strip().upper(): (v or '').strip() for k, v in row.items()}
        pos_str = r.get('CO_POSICAO', '')
        hab_str = r.get('CO_HABILIDADE', '')
        area = r.get('SG_AREA', '').upper()
        cor = r.get('TX_COR', '').upper()
        lingua = r.get('TP_LINGUA', '')

        if not pos_str.isdigit() or not hab_str.isdigit() or not area:
            continue
        # Ignora lingua estrangeira
        pos = int(pos_str)
        if pos <= 5 and lingua in ('0', '1'):
            continue

        hab = int(hab_str)
        if cor == cor_preferida.upper():
            mapa[pos] = (area, hab)
        elif pos not in mapa_fallback:
            mapa_fallback[pos] = (area, hab)

    return mapa if mapa else mapa_fallback


# Regex
def scoreTextMatches(texto_orig, texto_low, regras_low, regras_case=()):
    score = 0
    for padrao, peso in regras_low:
        if re.search(padrao, texto_low):
            score += peso
    for padrao, peso in regras_case:
        if re.search(padrao, texto_orig):
            score += peso
    return score


# conteudos da disciplina
REGRAS_NATUREZA = {
    'Física': {
        'case': [
            (r'\b\d+(?:[.,]\d+)?\s*(?:m/s²?|km/h|Hz|kHz|MHz|kWh|kW|W|V|mV|kV|A|mA|Ω|ohm|N|Pa|kPa|J|kJ|cal|kcal|dB|°C|K)\b', 5),
            (r'\b(?:10\^[-+]?\d+|m\s*s[-−]1|m\s*s[-−]2)\b', 3),
        ],
        'low': [
            (r'\b(?:velocidade|aceleração|acelerar|trajetória|cinemática|movimento\s+uniforme|queda\s+livre)\b', 4),
            (r'\b(?:força\s+resultante|força\s+de\s+atrito|força\s+peso|força\s+normal|leis?\s+de\s+newton|inércia|torque|momento\s+linear|impulso)\b', 5),
            (r'\b(?:corrente\s+elétrica|resistor(?:es)?|resistência\s+elétrica|tensão\s+elétrica|diferença\s+de\s+potencial|ddp|voltagem|circuito\s+elétrico|disjuntor|fusível|gerador|capacitor|chuveiro\s+elétrico|lâmpada(?:s)?|potência\s+elétrica|lei\s+de\s+ohm)\b', 5),
            (r'\b(?:campo\s+magnético|eletromagnetismo|indução\s+eletromagnética|ímã|imã|bobina|transformador|campo\s+elétrico|carga\s+elétrica)\b', 5),
            (r'\b(?:lente(?:s)?|espelho(?:s)?|refração|reflexão|índice\s+de\s+refração|miopia|hipermetropia|foco|imagem\s+real|imagem\s+virtual|óptica|prisma|difração|interferência|polarização)\b', 5),
            (r'\b(?:onda(?:s)?\s+(?:sonora|eletromagnética|mecânica|transversal|longitudinal)|comprimento\s+de\s+onda|frequência|amplitude|ressonância|efeito\s+doppler|decibéis|acústic[ao]|ultrassom|eco|som\s+emitido|velocidade\s+do\s+som|velocidade\s+da\s+luz)\b', 5),
            (r'\b(?:calor\s+específico|calor\s+latente|capacidade\s+térmica|condução\s+térmica|convecção|irradiação|dilatação\s+térmica|termodinâmica|máquina\s+térmica|ciclo\s+de\s+carnot|rendimento\s+térmico|condutividade\s+térmica|isolante\s+térmico)\b', 5),
            (r'\b(?:empuxo|hidrostática|princípio\s+de\s+arquimedes|princípio\s+de\s+pascal|pressão\s+hidrostática|pressão\s+atmosférica|vasos\s+comunicantes|barômetro|manômetro)\b', 5),
            (r'\b(?:energia\s+cinética|energia\s+potencial|energia\s+mecânica|conservação\s+de\s+energia|trabalho\s+realizado|potência\s+média|gravidade|gravitacional|pêndulo|mola|elástica|polia|roldana|alavanca|plano\s+inclinado)\b', 4),
            (r'\b(?:massa|atrito|elétric[ao]|térmic[ao]|temperatura|calor|pressão|densidade|potência|energia|fóton|radiação)\b', 1),
        ]
    },
    'Química': {
        'case': [
            (r'\b(?:H2O|CO2|O2|N2|H2|CH4|NH3|NaCl|HCl|NaOH|H2SO4|CaCO3|NaHCO3|Fe2O3|SO2|NO2|C6H12O6|C2H5OH|CH3COOH|KMnO4|AgNO3|CuSO4)\b', 5),
            (r'\b(?:pH|pOH|Ka|Kb|Kps|ΔH|∆H|mol/L|g/mol|mol\s*L[-−]1|mg/L|ppm)\b', 5),
            (r'\b(?:[A-Z][a-z]?\d+(?:[A-Z][a-z]?\d*)+)\b', 3),
        ],
        'low': [
            (r'\b(?:estequiometria|massa\s+molar|número\s+de\s+mols?|mol(?:s|ar|aridade)?|reagente(?:s)?|reação\s+química|reações\s+químicas|equação\s+química|rendimento\s+da\s+reação|excesso|limitante)\b', 5),
            (r'\b(?:átomo(?:s)?|molécula(?:s)?|elétron(?:s)?|próton(?:s)?|nêutron(?:s)?|íon(?:s)?|cátion(?:s)?|ânion(?:s)?|isótopo(?:s)?|tabela\s+periódica|eletronegatividade|ligação\s+(?:iônica|covalente|metálica|de\s+hidrogênio)|interação\s+intermolecular|polaridade|apolar)\b', 5),
            (r'\b(?:ácido(?:s)?|alcalin[ao]|basicidade|acidez|neutralização|titulação|hidrólise|tampão|sal\s+mineral|sais\s+inorgânicos|óxido(?:s)?|hidróxido(?:s)?|bicarbonato|carbonato|sulfato|nitrato|cloreto)\b', 4),
            (r'\b(?:hidrocarboneto(?:s)?|cadeia\s+carbônica|função\s+orgânica|funções\s+orgânicas|álcool|álcoois|aldeído|cetona|ácido\s+carboxílico|éster(?:es)?|éter(?:es)?|amina(?:s)?|amida(?:s)?|fenol|benzeno|aromátic[ao]|isomeria|polímero(?:s)?|polimerização|esterificação|saponificação|transesterificação|biodiesel|petróleo|craqueamento)\b', 5),
            (r'\b(?:oxidação|redução|oxirredução|redox|nox|ânodo|cátodo|pilha(?:s)?|bateria\s+de\s+lítio|eletrólise|corrosão|metal\s+de\s+sacrifício|potencial\s+de\s+redução|galvanização)\b', 5),
            (r'\b(?:entalpia|exotérmic[ao]|endotérmic[ao]|energia\s+de\s+ativação|catalisador(?:es)?|cinética\s+química|velocidade\s+da\s+reação|equilíbrio\s+químico|le\s+chatelier|deslocamento\s+de\s+equilíbrio)\b', 5),
            (r'\b(?:destilação|filtração|decantação|centrifugação|cromatografia|floculação|coagulação|cloração|tratamento\s+de\s+água|solubilidade|solução\s+aquosa|soluto|solvente|diluição|concentração\s+comum|mistura\s+(?:homogênea|heterogênea)|precipitado|combustão|fermentação|radioatividade|meia-vida|decaimento)\b', 4),
            (r'\b(?:substância|composto|elemento\s+químico|químic[ao]|reage|reagir|solúvel|insolúvel|dissolvido|volátil|ebulição|fusão)\b', 2),
        ]
    },
    'Biologia': {
        'case': [
            (r'\b(?:DNA|RNA|RNAm|RNAt|ATP|NADH|CRISPR|PCR|HIV|AIDS|HPV|SARS-CoV)\b', 5),
        ],
        'low': [
            (r'\b(?:célula(?:s)?|celular(?:es)?|organela(?:s)?|mitocôndria(?:s)?|cloroplasto(?:s)?|ribossomo(?:s)?|lisossomo(?:s)?|retículo\s+endoplasmático|complexo\s+de\s+golgi|membrana\s+plasmática|parede\s+celular|citoplasma|núcleo\s+celular|osmose|transporte\s+ativo|fagocitose|mitose|meiose)\b', 5),
            (r'\b(?:fotossíntese|respiração\s+celular|clorofila|estômato(?:s)?|xilema|floema|seiva|transpiração\s+vegetal|angiosperma|gimnosperma|briófita|pteridófita|polinização|germinação|semente(?:s)?|fruto(?:s)?|raiz(?:es)?|folha(?:s)?|flor(?:es)?|fototropismo|fitormônio|auxina)\b', 5),
            (r'\b(?:gene(?:s)?|genétic[ao]|genoma|cromossomo(?:s)?|alelo(?:s)?|homozigoto|heterozigoto|dominante|recessivo|fenótipo|genótipo|hereditariedade|mutação|transcrição|tradução|códon|proteína(?:s)?|aminoácido(?:s)?|enzima(?:s)?|enzimátic[ao]|transgênic[ao]|clonagem|engenharia\s+genética|biotecnologia|terapia\s+gênica)\b', 5),
            (r'\b(?:ecossistema(?:s)?|cadeia\s+alimentar|teia\s+alimentar|nível\s+trófico|produtor(?:es)?|consumidor(?:es)?|decompositor(?:es)?|ecologia|ecológic[ao]|nicho\s+ecológico|habitat|sucessão\s+ecológica|relação\s+ecológica|mutualismo|parasitismo|predação|comensalismo|competição|eutrofização|magnificação\s+trófica|bioacumulação|ciclo\s+do\s+(?:nitrogênio|carbono)|fixação\s+biológica|biodiversidade|extinção|espécie(?:s)?|endemismo|bioma)\b', 5),
            (r'\b(?:evolução|evolutiv[ao]|seleção\s+natural|darwin|lamarck|especiação|adaptação\s+evolutiva|ancestral\s+comum|fóssil|fósseis|filogenia|cladograma|homologia|analogia)\b', 5),
            (r'\b(?:bactéria(?:s)?|bacterian[ao]|vírus|viral|fungo(?:s)?|protozoário(?:s)?|verme(?:s)?|parasita(?:s)?|patógeno|doença(?:s)?|infecção|epidemia|dengue|malária|chagas|esquistossomose|febre\s+amarela|vacina(?:s|ção)?|soro|anticorpo(?:s)?|antígeno(?:s)?|linfócito(?:s)?|sistema\s+imunológico|imunidade|antibiótico(?:s)?)\b', 5),
            (r'\b(?:fisiologia|sistema\s+(?:nervoso|digestório|respiratório|circulatório|excretor|endócrino|reprodutor)|neurônio(?:s)?|sinapse|hormônio(?:s)?|insulina|glucagon|adrenalina|sangue|hemoglobina|hemácia(?:s)?|coração|pulmão|pulmões|rim|rins|fígado|intestino|estômago|músculo(?:s)?|tecido\s+(?:epitelial|conjuntivo|muscular|nervoso)|vertebrado|invertebrado|inseto(?:s)?|anfíbio|réptil|mamífero(?:s)?|peixe(?:s)?|ave(?:s)?)\b', 4),
            (r'\b(?:organismo(?:s)?|seres?\s+vivos?|biológic[ao]|planta(?:s)?|vegetal|vegetais|animal|animais|reprodução|metabolismo)\b', 2),
        ]
    }
}

REGRAS_HUMANAS = {
    'Geografia': {
        'case': [],
        'low': [
            (r'\b(?:clima|climátic[ao]|precipitação|pluviométric[ao]|massas?\s+de\s+ar|frente\s+fria|el\s+niño|la\s+niña|ilha\s+de\s+calor|inversão\s+térmica|chuva\s+orográfica|zona\s+intertropical|monções|semiárido|equatorial|tropical)\b', 5),
            (r'\b(?:relevo|planalto|planície|depressão|cordilheira|intemperismo|erosão|assoreamento|voçoroca|solo(?:s)?|pedologia|laterização|lixiviação|placa(?:s)?\s+tectônica(?:s)?|vulcanismo|terremoto|bacia\s+sedimentar|escudo\s+cristalino|rocha(?:s)?)\b', 5),
            (r'\b(?:bacia\s+hidrográfica|hidrografia|aquífero|lençol\s+freático|nascente|foz|afluente|transposição|hidrelétrica|recursos\s+hídricos|amazônia|cerrado|caatinga|mata\s+atlântica|pantanal|pampa|manguezal)\b', 5),
            (r'\b(?:cartografia|mapa(?:s)?|escala\s+cartográfica|projeção\s+cartográfica|latitude|longitude|meridiano|paralelo|fuso\s+horário|coordenadas\s+geográficas|curvas?\s+de\s+nível|sensoriamento\s+remoto|geoprocessamento)\b', 5),
            (r'\b(?:urbanização|metrópole|megacidade|conurbação|gentrificação|segregação\s+socioespacial|favelização|periferia\s+urbana|mobilidade\s+urbana|êxodo\s+rural|migração|imigração|emigração|refugiado(?:s)?|demografia|transição\s+demográfica|pirâmide\s+etária|taxa\s+de\s+fecundidade|envelhecimento\s+populacional)\b', 5),
            (r'\b(?:agronegócio|latifúndio|minifúndio|reforma\s+agrária|fronteira\s+agrícola|matopiba|monocultura|agricultura\s+familiar|soja|pecuária|desmatamento|mineração|extrativismo|commodities|industrialização|desindustrialização|toyotismo|fordismo|blocos?\s+econômicos?|mercosul|união\s+europeia|geopolítica|globalização|território|fronteira(?:s)?|espaço\s+geográfico)\b', 4),
        ]
    },
    'Filosofia': {
        'case': [],
        'low': [
            (r'\b(?:sócrates|platão|aristóteles|pré-socrátic[ao]|heráclito|parmênides|epicuro|estoicismo|santo\s+agostinho|tomás\s+de\s+aquino|maquiavel|descartes|francis\s+bacon|spinoza|espinosa|john\s+locke|thomas\s+hobbes|david\s+hume|rousseau|montesquieu|immanuel\s+kant|hegel|schopenhauer|nietzsche|kierkegaard|sartre|simone\s+de\s+beauvoir|hannah\s+arendt|michel\s+foucault|habermas|john\s+rawls|karl\s+popper|adorno|horkheimer|walter\s+benjamin|merleau-ponty|wittgenstein|deleuze)\b', 6),
            (r'\b(?:filosofia|filósofo(?:s)?|filosófic[ao]|epistemologia|metafísica|ontologia|fenomenologia|existencialismo|racionalismo|empirismo|ceticismo|dogmatismo|imperativo\s+categórico|ética\s+a\s+nicômaco|eudaimonia|alegoria\s+da\s+caverna|mundo\s+das\s+ideias|maiêutica|dialética|contrato\s+social|estado\s+de\s+natureza|vontade\s+geral|cogito|dúvida\s+metódica|razão\s+pura|razão\s+prática|estética|virtude|prudência|justiça\s+distributiva|banalidade\s+do\s+mal|biopoder)\b', 5),
            (r'\b(?:ética|moral|razão|verdade|conhecimento\s+humano|liberdade\s+individual|autonomia\s+moral|pensamento\s+crítico|lógica)\b', 2),
        ]
    },
    'Sociologia': {
        'case': [],
        'low': [
            (r'\b(?:durkheim|max\s+weber|karl\s+marx|pierre\s+bourdieu|zygmunt\s+bauman|auguste\s+comte|gilberto\s+freyre|sérgio\s+buarque\s+de\s+holanda|caio\s+prado|florestan\s+fernandes|darcy\s+ribeiro|anthony\s+giddens|manuel\s+castells|norbert\s+elias|boaventura|djamila|milton\s+santos)\b', 6),
            (r'\b(?:sociologia|sociólog[ao]|sociológic[ao]|fato\s+social|ação\s+social|coerção\s+social|solidariedade\s+(?:mecânica|orgânica)|anomia|mais-valia|luta\s+de\s+classes|alienação|fetichismo|habitus|capital\s+cultural|violência\s+simbólica|modernidade\s+líquida|indústria\s+cultural|sociedade\s+de\s+consumo|esfera\s+pública)\b', 5),
            (r'\b(?:desigualdade\s+social|estratificação\s+social|mobilidade\s+social|classe\s+social|cidadania|direitos\s+humanos|direitos\s+civis|direitos\s+sociais|movimento(?:s)?\s+socia(?:l|is)|identidade\s+cultural|diversidade\s+cultural|multiculturalismo|etnocentrismo|relativismo\s+cultural|preconceito|racismo|discriminação|patriarcado|questões\s+de\s+gênero|feminismo|patrimônio\s+cultural|patrimônio\s+imaterial|instituição\s+social|socialização|meritocracia|uberização|precarização\s+do\s+trabalho)\b', 4),
        ]
    },
    'História': {
        'case': [],
        'low': [
            (r'\b(?:antiguidade|grécia\s+antiga|atenas|esparta|pólis|roma\s+antiga|império\s+romano|egito\s+antigo|mesopotâmia|idade\s+média|feudalismo|feudal|servidão|cruzadas|renascimento|reforma\s+protestante|contrarreforma|absolutismo|mercantilismo|grandes\s+navegações|iluminismo|revolução\s+(?:francesa|industrial|russa|inglesa|cubana|mexicana|haitiana))\b', 5),
            (r'\b(?:brasil\s+colônia|período\s+colonial|capitanias\s+hereditárias|engenho(?:s)?|açúcar|escravidão|escravizad[ao]s?|tráfico\s+negreiro|quilombo(?:s)?|palmares|bandeirantes|ciclo\s+do\s+ouro|inconfidência\s+mineira|conjuração\s+baiana|independência\s+do\s+brasil|primeiro\s+reinado|período\s+regencial|segundo\s+reinado|dom\s+pedro|abolição|lei\s+áurea)\b', 5),
            (r'\b(?:república\s+velha|primeira\s+república|coronelismo|voto\s+de\s+cabresto|canudos|contestado|revolta\s+da\s+vacina|revolta\s+da\s+chibata|era\s+vargas|estado\s+novo|getúlio\s+vargas|trabalhismo|clt|juscelino|jk|ditadura\s+militar|regime\s+militar|golpe\s+de\s+1964|ai-5|censura|redemocratização|diretas\s+já|constituição\s+de\s+1988)\b', 5),
            (r'\b(?:primeira\s+guerra|segunda\s+guerra|guerra\s+fria|nazismo|fascismo|holocausto|imperialismo|neocolonialismo|descolonização|apartheid|muro\s+de\s+berlim|união\s+soviética|urss|crise\s+de\s+1929)\b', 5),
            (r'\b(?:século\s+[xvi]+|império|monarquia|colônia|colonial|históric[ao]|historiografia|documento\s+histórico|memória\s+histórica|guerra|revolução|independência|república|constituição|indígenas?\s+no\s+período)\b', 2),
        ]
    }
}

REGRAS_LINGUAGENS = {
    'Literatura': {
        'case': [],
        'low': [
            (r'\b(?:poema|poesia|poétic[ao]|verso(?:s)?|estrofe(?:s)?|eu\s+lírico|lirismo|rima(?:s)?|métrica|soneto|haicai|ode|elegia)\b', 5),
            (r'\b(?:romance|narrador|personagem|personagens|enredo|conto|crônica|novela|ficção|ficcional|literatura|literári[ao]|obra\s+literária|texto\s+literário|intertextualidade\s+literária)\b', 4),
            (r'\b(?:quinhentismo|barroco|arcadismo|romantismo|realismo|naturalismo|parnasianismo|simbolismo|pré-modernismo|modernismo|semana\s+de\s+arte\s+moderna|geração\s+de\s+(?:22|30|45)|concretismo|trovadorismo|classicismo|humanismo)\b', 5),
            (r'\b(?:machado\s+de\s+assis|clarice\s+lispector|carlos\s+drummond|drummond|guimarães\s+rosa|graciliano\s+ramos|manuel\s+bandeira|cecília\s+meireles|mário\s+de\s+andrade|oswald\s+de\s+andrade|josé\s+de\s+alencar|castro\s+alves|gonçalves\s+dias|aluísio\s+azevedo|lima\s+barreto|euclides\s+da\s+cunha|rachel\s+de\s+queiroz|jorge\s+amado|joão\s+cabral|ferreira\s+gullar|cora\s+coralina|conceição\s+evaristo|carolina\s+maria\s+de\s+jesus|fernando\s+pessoa|camões|eça\s+de\s+queirós|gregório\s+de\s+matos|ariano\s+suassuna|vinicius\s+de\s+moraes|manoel\s+de\s+barros|paulo\s+leminski|adélia\s+prado|lygia\s+fagundes)\b', 6),
        ]
    },
    'Português': {
        'case': [],
        'low': [
            (r'\b(?:variação\s+linguística|variedade\s+linguística|norma\s+padrão|norma\s+culta|preconceito\s+linguístico|coloquial|formalidade|oralidade|gíria|regionalismo|neologismo|estrangeirismo)\b', 5),
            (r'\b(?:função\s+(?:referencial|emotiva|apelativa|conativa|fática|metalinguística|poética)|coesão|coerência|conectivo|conjunção|pronome|anafóric[ao]|sintaxe|concordância|regência|crase|pontuação|ambiguidade|ironia|metáfora|metonímia|eufemismo|hipérbole)\b', 4),
            (r'\b(?:campanha\s+publicitária|anúncio|propaganda|cartaz|infográfico|charge|tirinha|notícia|reportagem|editorial|artigo\s+de\s+opinião|resenha|verbete|manual|gênero\s+textual|interlocutor|leitor|estratégia\s+argumentativa|argumentação|persuasão|redes?\s+socia(?:l|is)|internet|tecnologia\s+digital|educação\s+física|esporte|dança|arte\s+contemporânea|pintura|escultura|museu|música|patrimônio)\b', 3),
        ]
    }
}


# Estrutura: disciplina -> lista de (frente, nome_assunto, regras_low, regras_case) -> especifica para cada frente
REGRAS_CONTEUDO = {
    'Física': [
        ('A', 'Cinemática e MUV', [
            (r'\b(?:velocidade\s+média|aceleração|cinemática|mru|muv|deslocamento|espaço\s+percorrido|tempo\s+de\s+percurso|frenagem|ultrapassagem|queda\s+livre|lançamento|movimento\s+circular|frequência\s+de\s+rotação|rpm)\b', 4),
        ], [(r'\b\d+(?:[.,]\d+)?\s*(?:m/s²?|km/h)\b', 3)]),
        ('A', 'Leis de Newton e Dinâmica', [
            (r'\b(?:newton|atrito|força\s+peso|força\s+normal|força\s+resultante|tração|polia|roldana|plano\s+inclinado|inércia|centrípeta|gravitação|órbita|satélite|impulso|quantidade\s+de\s+movimento|colisão|alavanca|torque)\b', 4),
        ], [(r'\b\d+(?:[.,]\d+)?\s*N\b', 2)]),
        ('A', 'Trabalho, Energia e Hidrostática', [
            (r'\b(?:energia\s+cinética|energia\s+potencial|energia\s+mecânica|trabalho\s+realizado|conservação\s+de\s+energia|potência\s+mecânica|empuxo|hidrostática|arquimedes|pascal|pressão\s+hidrostática|pressão\s+atmosférica|densidade|flutuar|submerso|vasos\s+comunicantes)\b', 4),
        ], [(r'\b\d+(?:[.,]\d+)?\s*(?:Pa|kPa|J|kJ)\b', 2)]),
        ('B', 'Termologia e Calorimetria', [
            (r'\b(?:calor|temperatura|térmic[ao]|calorimetria|calor\s+específico|calor\s+latente|dilatação|condução|convecção|irradiação|termodinâmica|máquina\s+térmica|geladeira|refrigerador|gás\s+ideal|isotérmic[ao]|adiabátic[ao]|ebulição|fusão|vaporização|isolante\s+térmico)\b', 5),
        ], [(r'\b\d+(?:[.,]\d+)?\s*(?:°C|cal|kcal)\b', 3)]),
        ('B', 'Óptica Geométrica', [
            (r'\b(?:óptica|lente(?:s)?|espelho(?:s)?|refração|reflexão|miopia|hipermetropia|astigmatismo|foco|imagem\s+(?:real|virtual)|prisma|dispersão\s+da\s+luz|arco-íris|sombra|penumbra|câmara\s+escura|fibra\s+óptica|luz\s+visível|cores)\b', 5),
        ], []),
        ('B', 'Ondulatória e Acústica', [
            (r'\b(?:onda(?:s)?|ondulatória|frequência|comprimento\s+de\s+onda|amplitude|acústic[ao]|som|sonor[ao]|decibéis|eco|reverberação|ressonância|doppler|ultrassom|difração|interferência|polarização|radiação\s+eletromagnética|micro-ondas|infravermelho|ultravioleta|raios?\s+x)\b', 5),
        ], [(r'\b\d+(?:[.,]\d+)?\s*(?:Hz|kHz|MHz|dB)\b', 4)]),
        ('C', 'Eletrodinâmica e Circuitos', [
            (r'\b(?:corrente\s+elétrica|resistor(?:es)?|resistência\s+elétrica|tensão|ddp|voltagem|circuito|lâmpada(?:s)?|chuveiro|disjuntor|fusível|potência\s+elétrica|consumo\s+de\s+energia|conta\s+de\s+luz|lei\s+de\s+ohm|em\s+série|em\s+paralelo|curto-circuito|gerador|bateria)\b', 5),
        ], [(r'\b\d+(?:[.,]\d+)?\s*(?:kWh|kW|W|V|A|mA|Ω)\b', 4)]),
        ('C', 'Eletrostática e Eletromagnetismo', [
            (r'\b(?:campo\s+magnético|campo\s+elétrico|carga\s+elétrica|eletrização|para-raios|relâmpago|ímã|imã|bússola|bobina|indução\s+eletromagnética|transformador|faraday|lorentz|eletrostática|capacitor)\b', 5),
        ], []),
    ],
    'Química': [
        ('A', 'Química Geral e Separação de Misturas', [
            (r'\b(?:destilação|filtração|decantação|centrifugação|cromatografia|floculação|coagulação|cloração|tratamento\s+de\s+água|mistura\s+(?:homogênea|heterogênea)|separação\s+de\s+misturas|mudança\s+de\s+estado|densidade|ponto\s+de\s+(?:fusão|ebulição))\b', 5),
        ], []),
        ('A', 'Atomística e Ligações Químicas', [
            (r'\b(?:átomo|elétron|próton|nêutron|isótopo|radioatividade|meia-vida|decaimento|tabela\s+periódica|eletronegatividade|ligação\s+(?:iônica|covalente|metálica|de\s+hidrogênio)|intermolecular|dipolo|polaridade|apolar|geometria\s+molecular|ácido|base|sal|óxido|neutralização|chuva\s+ácida)\b', 5),
        ], []),
        ('A', 'Estequiometria e Soluções', [
            (r'\b(?:estequiometria|massa\s+molar|mol(?:s|ar|aridade)?|concentração|diluição|solubilidade|soluto|solvente|solução\s+aquosa|rendimento|pureza|titulação|excesso|limitante|proporção\s+estequiométrica)\b', 5),
        ], [(r'\b(?:mol/L|g/mol|g/L|mg/L|ppm)\b', 4)]),
        ('B', 'Termoquímica e Cinética', [
            (r'\b(?:entalpia|exotérmic[ao]|endotérmic[ao]|calor\s+de\s+combustão|lei\s+de\s+hess|poder\s+calorífico|energia\s+de\s+ativação|catalisador|cinética\s+química|velocidade\s+da\s+reação|superfície\s+de\s+contato)\b', 5),
        ], [(r'\b(?:ΔH|∆H|kJ/mol)\b', 5)]),
        ('B', 'Equilíbrio Químico e pH', [
            (r'\b(?:equilíbrio\s+químico|le\s+chatelier|deslocamento\s+de\s+equilíbrio|solução\s+tampão|hidrólise\s+salina|constante\s+de\s+equilíbrio|indicador\s+ácido-base|acidez|alcalinidade|basicidade)\b', 5),
        ], [(r'\b(?:pH|pOH|Ka|Kb|Kps)\b', 5)]),
        ('B', 'Eletroquímica (Pilhas e Eletrólise)', [
            (r'\b(?:oxidação|redução|oxirredução|redox|pilha|bateria|eletrólise|ânodo|cátodo|corrosão|ferrugem|metal\s+de\s+sacrifício|galvanização|potencial\s+de\s+redução|nox|eletrodo)\b', 5),
        ], []),
        ('C', 'Química Orgânica e Funções', [
            (r'\b(?:orgânic[ao]|carbono|hidrocarboneto|álcool|fenol|aldeído|cetona|ácido\s+carboxílico|éster|éter|amina|amida|benzeno|aromátic[ao]|isomeria|quiral|enantiômero|cadeia\s+carbônica|petróleo|biodiesel|etanol)\b', 5),
        ], []),
        ('C', 'Reações Orgânicas e Polímeros', [
            (r'\b(?:polímero|polimerização|plástico|borracha|esterificação|saponificação|sabão|detergente|transesterificação|hidrogenação|fermentação|craqueamento|biodegradável)\b', 5),
        ], []),
    ],
    'Biologia': [
        ('A', 'Ecologia e Ciclos Biogeoquímicos', [
            (r'\b(?:ecossistema|cadeia\s+alimentar|teia\s+alimentar|nível\s+trófico|produtor|consumidor|decompositor|nicho\s+ecológico|sucessão\s+ecológica|mutualismo|parasitismo|predação|comensalismo|ciclo\s+do\s+(?:nitrogênio|carbono|água)|fixação\s+biológica|bioma|biodiversidade)\b', 5),
        ], []),
        ('A', 'Impactos Ambientais e Sustentabilidade', [
            (r'\b(?:desmatamento|queimada|efeito\s+estufa|aquecimento\s+global|eutrofização|magnificação\s+trófica|bioacumulação|poluição|esgoto|agrotóxico|pesticida|controle\s+biológico|extinção|espécie\s+invasora|sustentabilidade|reciclagem|biorremediação|compostagem)\b', 5),
        ], []),
        ('B', 'Citologia e Metabolismo Celular', [
            (r'\b(?:célula|celular|organela|mitocôndria|cloroplasto|ribossomo|lisossomo|golgi|membrana\s+plasmática|osmose|transporte\s+ativo|mitose|meiose|fotossíntese|respiração\s+celular|fermentação|enzima|proteína)\b', 5),
        ], [(r'\b(?:ATP|NADH)\b', 4)]),
        ('B', 'Microbiologia, Saúde e Imunologia', [
            (r'\b(?:bactéria|vírus|viral|fungo|protozoário|verme|parasita|dengue|malária|chagas|esquistossomose|febre\s+amarela|vacina|soro|anticorpo|antígeno|imunidade|imunológico|antibiótico|infecção|epidemia|saneamento|saúde\s+pública)\b', 5),
        ], [(r'\b(?:HIV|AIDS|HPV|SARS-CoV)\b', 5)]),
        ('B', 'Botânica e Fisiologia Vegetal', [
            (r'\b(?:planta|vegetal|angiosperma|gimnosperma|briófita|pteridófita|xilema|floema|seiva|estômato|transpiração\s+vegetal|polinização|semente|fruto|raiz|folha|flor|fototropismo|auxina|clorofila)\b', 5),
        ], []),
        ('C', 'Genética e Evolução', [
            (r'\b(?:gene|genétic[ao]|genoma|cromossomo|alelo|dominante|recessivo|fenótipo|genótipo|hereditariedade|mutação|transcrição|tradução|transgênic[ao]|clonagem|biotecnologia|evolução|seleção\s+natural|darwin|lamarck|especiação|adaptação|fóssil|filogenia|cladograma)\b', 5),
        ], [(r'\b(?:DNA|RNA|CRISPR|PCR)\b', 5)]),
        ('C', 'Fisiologia Humana e Zoologia', [
            (r'\b(?:fisiologia|neurônio|sinapse|hormônio|insulina|adrenalina|sangue|hemoglobina|coração|pulmão|rim|rins|fígado|digestão|intestino|músculo|tecido|vertebrado|invertebrado|inseto|anfíbio|réptil|mamífero|peixe|ave)\b', 5),
        ], []),
    ],
    'Matemática': [
        ('A', 'Razão, Proporção e Porcentagem', [
            (r'\b(?:porcentagem|percentual|%|razão|proporção|proporcional|regra\s+de\s+três|escala|desconto|acréscimo|juros|taxa\s+de\s+câmbio|densidade\s+demográfica|velocidade\s+média|consumo\s+médio|custo|preço|lucro|receita)\b', 4),
        ], []),
        ('A', 'Funções de 1º e 2º Grau', [
            (r'\b(?:função|funções|f\(x\)|equação|inequação|parábola|vértice|valor\s+máximo|valor\s+mínimo|linear|quadrática|coeficiente\s+angular|reta|polinômio|sistema\s+de\s+equações)\b', 5),
        ], []),
        ('A', 'Logaritmos, Exponenciais e Progressões', [
            (r'\b(?:logaritmo|log\b|exponencial|progressão\s+aritmética|progressão\s+geométrica|sequência|juros\s+compostos|meia-vida|crescimento\s+exponencial|decaimento\s+exponencial|escala\s+richter|decibel)\b', 5),
        ], []),
        ('B', 'Geometria Espacial e Plana', [
            (r'\b(?:triângulo|quadrado|retângulo|círculo|circunferência|raio|diâmetro|perímetro|área|volume|capacidade|cilindro|cone|esfera|prisma|pirâmide|cubo|paralelepípedo|polígono|ângulo|pitágoras|semelhança|projeção\s+ortogonal|planificação|simetria|poliedro)\b', 5),
        ], [(r'\b(?:cm²|m²|km²|cm³|m³|π)\b', 4)]),
        ('B', 'Trigonometria e Geometria Analítica', [
            (r'\b(?:seno|cosseno|tangente|sen\b|cos\b|tg\b|radiano|trigonométric[ao]|plano\s+cartesiano|coordenadas|distância\s+entre\s+dois\s+pontos|equação\s+da\s+reta|equação\s+da\s+circunferência|matriz|matrizes)\b', 5),
        ], []),
        ('C', 'Análise Combinatória e Probabilidade', [
            (r'\b(?:probabilidade|chance|sorteio|sortear|dado|moeda|baralho|urna|combinação|permutação|arranjo|análise\s+combinatória|fatorial|maneiras\s+distintas|senhas|placas|códigos|possibilidades)\b', 5),
        ], []),
        ('C', 'Estatística, Médias e Gráficos', [
            (r'\b(?:média\s+aritmética|média\s+ponderada|mediana|moda|desvio\s+padrão|variância|tabela|gráfico|histograma|pesquisa|levantamento|amostra|frequência|índice)\b', 4),
        ], []),
    ],
    'História': [
        ('Brasil', 'Brasil Colônia e Império', [
            (r'\b(?:colônia|colonial|capitanias|engenho|açúcar|escravidão|escravizad[ao]|tráfico\s+negreiro|quilombo|palmares|bandeirantes|ouro|inconfidência|conjuração|independência\s+do\s+brasil|império\s+do\s+brasil|primeiro\s+reinado|regencial|segundo\s+reinado|dom\s+pedro|abolição|lei\s+áurea|café|imigrantes\s+no\s+brasil)\b', 5),
        ], []),
        ('Brasil', 'Brasil República e Era Vargas', [
            (r'\b(?:república\s+velha|primeira\s+república|coronelismo|voto\s+de\s+cabresto|canudos|contestado|vacina|chibata|era\s+vargas|vargas|estado\s+novo|clt|trabalhismo|juscelino|jk|brasília|populismo|joão\s+goulart|brasil\s+república)\b', 5),
        ], []),
        ('Brasil', 'Ditadura Militar e Redemocratização', [
            (r'\b(?:ditadura\s+militar|regime\s+militar|golpe\s+de\s+1964|ai-5|censura|repressão|milagre\s+econômico|anistia|diretas\s+já|redemocratização|constituição\s+de\s+1988|nova\s+república|plano\s+real)\b', 5),
        ], []),
        ('Geral', 'Antiguidade e Idade Média', [
            (r'\b(?:antiguidade|grécia|atenas|esparta|pólis|roma\s+antiga|império\s+romano|egito|mesopotâmia|idade\s+média|medieval|feudalismo|feudal|servidão|cruzadas|bizantino|islã|árabes)\b', 5),
        ], []),
        ('Geral', 'Idade Moderna e Revolução Industrial', [
            (r'\b(?:idade\s+moderna|renascimento|reforma\s+protestante|contrarreforma|absolutismo|mercantilismo|navegações|iluminismo|revolução\s+(?:francesa|industrial|inglesa)|napoleão|independência\s+dos\s+estados\s+unidos|américa\s+espanhola)\b', 5),
        ], []),
        ('Geral', 'História Contemporânea e Guerras', [
            (r'\b(?:primeira\s+guerra|segunda\s+guerra|guerra\s+fria|nazismo|fascismo|holocausto|revolução\s+russa|crise\s+de\s+1929|imperialismo|neocolonialismo|descolonização|apartheid|urss|união\s+soviética|muro\s+de\s+berlim|século\s+xx)\b', 5),
        ], []),
    ],
    'Geografia': [
        ('Física', 'Climatologia e Relevo Brasileiro', [
            (r'\b(?:clima|climátic[ao]|precipitação|chuva|massas?\s+de\s+ar|el\s+niño|ilha\s+de\s+calor|inversão\s+térmica|relevo|planalto|planície|depressão|intemperismo|erosão|solo|tectônica|terremoto|vulcão|rocha)\b', 5),
        ], []),
        ('Física', 'Hidrografia, Biomas e Cartografia', [
            (r'\b(?:bacia\s+hidrográfica|hidrografia|aquífero|rio|hidrelétrica|recursos\s+hídricos|amazônia|cerrado|caatinga|mata\s+atlântica|pantanal|pampa|bioma|cartografia|mapa|escala|projeção|latitude|longitude|fuso\s+horário)\b', 5),
        ], []),
        ('Política', 'Geopolítica Mundial e Urbanização', [
            (r'\b(?:geopolítica|globalização|blocos?\s+econômicos?|mercosul|união\s+europeia|fronteira|território|urbanização|metrópole|megacidade|conurbação|gentrificação|segregação|mobilidade\s+urbana|favela|industrialização|fordismo|toyotismo)\b', 5),
        ], []),
        ('Política', 'Geografia Agrária, Demografia e Economia', [
            (r'\b(?:agronegócio|latifúndio|minifúndio|reforma\s+agrária|fronteira\s+agrícola|monocultura|agricultura\s+familiar|pecuária|mineração|extrativismo|migração|êxodo\s+rural|refugiado|demografia|pirâmide\s+etária|fecundidade|envelhecimento\s+populacional|população)\b', 5),
        ], []),
    ],
    'Português': [
        ('Gramática', 'Variação Linguística e Funções da Linguagem', [
            (r'\b(?:variação\s+linguística|variedade\s+linguística|norma\s+padrão|norma\s+culta|preconceito\s+linguístico|coloquial|oralidade|gíria|regionalismo|neologismo|função\s+(?:referencial|emotiva|apelativa|conativa|fática|metalinguística|poética)|linguagem\s+verbal|não\s+verbal)\b', 5),
        ], []),
        ('Gramática', 'Sintaxe e Concordância Verbal', [
            (r'\b(?:sintaxe|concordância|regência|crase|pontuação|coesão|conectivo|conjunção|pronome|anafóric[ao]|oração|sujeito|predicado|verbo|tempo\s+verbal|modo\s+verbal|voz\s+passiva)\b', 5),
        ], []),
        ('Gramática', 'Interpretação de Texto e Gêneros Textuais', [
            (r'\b(?:texto|leitor|argumento|argumentação|estratégia|campanha|anúncio|cartaz|notícia|reportagem|charge|tirinha|infográfico|gênero\s+textual|ironia|humor|interlocutor|intenção|finalidade|comunicação)\b', 3),
        ], []),
    ],
    'Literatura': [
        ('Única', 'Modernismo e Literatura Contemporânea', [
            (r'\b(?:modernismo|modernista|semana\s+de\s+arte\s+moderna|geração\s+de\s+(?:22|30|45)|drummond|clarice|guimarães\s+rosa|graciliano|manuel\s+bandeira|mário\s+de\s+andrade|oswald\s+de\s+andrade|rachel\s+de\s+queiroz|jorge\s+amado|joão\s+cabral|conceição\s+evaristo|carolina\s+maria|contemporâne[ao]|concretismo)\b', 5),
        ], []),
        ('Única', 'Escolas Literárias e Análise Poética', [
            (r'\b(?:barroco|arcadismo|romantismo|realismo|naturalismo|parnasianismo|simbolismo|pré-modernismo|machado\s+de\s+assis|josé\s+de\s+alencar|castro\s+alves|aluísio\s+azevedo|lima\s+barreto|poema|soneto|eu\s+lírico|verso|estrofe|metáfora|narrador|romance)\b', 4),
        ], []),
    ],
    'Filosofia': [
        ('Única', 'Filosofia Antiga e Medieval', [
            (r'\b(?:sócrates|platão|aristóteles|pré-socrátic[ao]|heráclito|parmênides|epicuro|estoicismo|agostinho|tomás\s+de\s+aquino|pólis|caverna|maiêutica|eudaimonia|escolástica|patrística|antiguidade|medieval)\b', 5),
        ], []),
        ('Única', 'Filosofia Moderna, Ética e Política', [
            (r'\b(?:maquiavel|descartes|bacon|spinoza|espinosa|locke|hobbes|hume|rousseau|montesquieu|kant|hegel|nietzsche|sartre|arendt|foucault|habermas|rawls|ética|moral|contrato\s+social|imperativo|iluminismo|racionalismo|empirismo|existencialismo|política|democracia|justiça|liberdade)\b', 4),
        ], []),
    ],
    'Sociologia': [
        ('Única', 'Cultura, Identidade e Cidadania', [
            (r'\b(?:cultura|cultural|identidade|diversidade|multiculturalismo|etnocentrismo|relativismo|patrimônio|cidadania|direitos\s+humanos|movimento\s+social|racismo|preconceito|discriminação|gênero|patriarcado|feminismo|indígena|quilombola|indústria\s+cultural)\b', 5),
        ], []),
        ('Única', 'Trabalho, Desigualdade e Teoria Sociológica', [
            (r'\b(?:durkheim|weber|marx|bourdieu|bauman|comte|fato\s+social|ação\s+social|mais-valia|alienação|habitus|trabalho|trabalhador|desigualdade|estratificação|classe\s+social|mobilidade\s+social|capitalismo|consumo|uberização|precarização|meritocracia|estado)\b', 5),
        ], []),
    ],
}

# padrao quando regex nao funciona
FALLBACK_CONTEUDO = {
    'Física':     ('A', 'Cinemática e MUV'),
    'Química':    ('A', 'Química Geral e Separação de Misturas'),
    'Biologia':   ('A', 'Ecologia e Ciclos Biogeoquímicos'),
    'Matemática': ('A', 'Razão, Proporção e Porcentagem'),
    'História':   ('Brasil', 'Brasil República e Era Vargas'),
    'Geografia':  ('Política', 'Geopolítica Mundial e Urbanização'),
    'Português':  ('Gramática', 'Interpretação de Texto e Gêneros Textuais'),
    'Literatura': ('Única', 'Escolas Literárias e Análise Poética'),
    'Filosofia':  ('Única', 'Filosofia Moderna, Ética e Política'),
    'Sociologia': ('Única', 'Cultura, Identidade e Cidadania'),
}


def classifyEnemQuestion(discipline_slug, texto_questao, info_inep=None):
    # Classifica uma questao em:{
    #     'disciplina': str,
    #      'frente': str,
    #      'assunto': str,
    #      'precisa_revisao': bool,
    #      'fonte': 'inep' | 'lexico'
    #  }
    texto_orig = texto_questao or ''
    texto_low = texto_orig.lower()

    # Se tiver o csv
    disc_inep = frente_inep = assunto_inep = None
    if info_inep:
        sg_area, co_hab = info_inep
        mapped = MAPA_HABILIDADE_INEP.get((sg_area, co_hab))
        if mapped and mapped[0]:
            disc_inep, frente_inep, assunto_inep = mapped

    # 2) regex
    fonte = 'lexico'
    precisa_revisao = False

    if disc_inep:
        disciplina = disc_inep
        fonte = 'inep'
    elif discipline_slug == 'matematica':
        disciplina = 'Matemática'
    elif discipline_slug == 'ciencias-natureza':
        scores = {
            d: scoreTextMatches(texto_orig, texto_low, cfg['low'], cfg['case'])
            for d, cfg in REGRAS_NATUREZA.items()
        }
        ordenado = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        disciplina = ordenado[0][0]
        s1, s2 = ordenado[0][1], ordenado[1][1]
        if s1 == 0 or (s1 < 6 and (s1 - s2) <= 1):
            precisa_revisao = True
    elif discipline_slug == 'ciencias-humanas':
        scores = {
            d: scoreTextMatches(texto_orig, texto_low, cfg['low'], cfg['case'])
            for d, cfg in REGRAS_HUMANAS.items()
        }
        ordenado = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        disciplina = ordenado[0][0] if ordenado[0][1] > 0 else 'História'
        s1, s2 = ordenado[0][1], ordenado[1][1]
        if s1 == 0 or (s1 < 6 and (s1 - s2) <= 1):
            precisa_revisao = True
    elif discipline_slug == 'linguagens':
        s_lit = scoreTextMatches(texto_orig, texto_low, REGRAS_LINGUAGENS['Literatura']['low'])
        s_por = scoreTextMatches(texto_orig, texto_low, REGRAS_LINGUAGENS['Português']['low'])
        if s_lit >= 5 and s_lit > s_por:
            disciplina = 'Literatura'
        elif s_lit >= 4 and s_por == 0:
            disciplina = 'Literatura'
        else:
            disciplina = 'Português'
            if s_lit > 0 and abs(s_lit - s_por) <= 1:
                precisa_revisao = True
    else:
        # quando n consegue regex
        todos_grupos = {**REGRAS_NATUREZA, **REGRAS_HUMANAS, **REGRAS_LINGUAGENS}
        scores = {
            d: scoreTextMatches(texto_orig, texto_low, cfg['low'], cfg.get('case', ()))
            for d, cfg in todos_grupos.items()
        }
        ordenado = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        disciplina = ordenado[0][0] if ordenado[0][1] > 0 else 'Português'
        if ordenado[0][1] == 0 or (ordenado[0][1] < 6 and (ordenado[0][1] - ordenado[1][1]) <= 1):
            precisa_revisao = True

    # determina a frente
    melhor_frente, melhor_assunto = FALLBACK_CONTEUDO.get(disciplina, ('A', f'Conteúdo Geral — {disciplina}'))
    melhor_score_c = 0
    for frente_c, assunto_c, reg_low, reg_case in REGRAS_CONTEUDO.get(disciplina, []):
        sc = scoreTextMatches(texto_orig, texto_low, reg_low, reg_case)
        if sc > melhor_score_c:
            melhor_score_c = sc
            melhor_frente = frente_c
            melhor_assunto = assunto_c

    # prioriza a classificacao do inep
    if fonte == 'inep' and melhor_score_c == 0 and frente_inep and assunto_inep:
        melhor_frente = frente_inep
        melhor_assunto = assunto_inep
    elif melhor_score_c == 0 and fonte != 'inep' and discipline_slug != 'linguagens':
        # revisao
        precisa_revisao = True

    return {
        'disciplina': disciplina,
        'frente': melhor_frente,
        'assunto': melhor_assunto,
        'precisa_revisao': precisa_revisao,
        'fonte': fonte
    }


def classifyTopicBySubject(disciplina, texto_questao):

    # utilzia as areas do proprio vestibular -> ufsc separa por materia
    texto_orig = texto_questao or ''
    texto_low = texto_orig.lower()

    melhor_frente, melhor_assunto = FALLBACK_CONTEUDO.get(disciplina, ('A', f'Conteúdo Geral — {disciplina}'))
    melhor_score = 0
    for frente_c, assunto_c, reg_low, reg_case in REGRAS_CONTEUDO.get(disciplina, []):
        sc = scoreTextMatches(texto_orig, texto_low, reg_low, reg_case)
        if sc > melhor_score:
            melhor_score = sc
            melhor_frente = frente_c
            melhor_assunto = assunto_c

    return melhor_frente, melhor_assunto, (melhor_score > 0)


def inferEnemAreaByNumber(num_questao):
    # mapeia o num_questao de acordo com a prova do enem
    if not num_questao:
        return None
    n = int(num_questao)
    if 1 <= n <= 45:
        return 'linguagens'
    if 46 <= n <= 90:
        return 'ciencias-humanas'
    if 91 <= n <= 135:
        return 'ciencias-natureza'
    if 136 <= n <= 180:
        return 'matematica'
    return None

DROP TABLE IF EXISTS resolucao_questao;
DROP TABLE IF EXISTS questao_tag;
DROP TABLE IF EXISTS questao_lista;
DROP TABLE IF EXISTS assunto_questao;
DROP TABLE IF EXISTS lista_exercicio;
DROP TABLE IF EXISTS midia;
DROP TABLE IF EXISTS tag;
DROP TABLE IF EXISTS dica;
DROP TABLE IF EXISTS alternativa;
DROP TABLE IF EXISTS questao;
DROP TABLE IF EXISTS vestibular;
DROP TABLE IF EXISTS aluno;
DROP TABLE IF EXISTS escola;
DROP TABLE IF EXISTS professor;
DROP TABLE IF EXISTS curso;
DROP TABLE IF EXISTS gestao;
DROP TABLE IF EXISTS usuario;
DROP TABLE IF EXISTS assunto;
DROP TABLE IF EXISTS disciplina;

CREATE TABLE disciplina
	(id_disciplina integer,
	nome varchar(80),
	frente varchar(30),
	area varchar(80));

ALTER TABLE disciplina add constraint pk_disciplina primary key (id_disciplina);

CREATE TABLE assunto
	(id_assunto integer,
	id_disciplina integer,
	nome varchar(100));

ALTER TABLE assunto add constraint pk_assunto primary key (id_assunto);

ALTER TABLE assunto add constraint fk_assunto_disciplina foreign key (id_disciplina) references disciplina (id_disciplina);

CREATE TABLE usuario
	(id_usuario integer,
	nome varchar(100),
	cpf varchar(11),
	senha varchar(255),
	email varchar(100),
	data_ingresso date);

ALTER TABLE usuario add constraint pk_usuario primary key (id_usuario);

CREATE TABLE gestao
	(id_usuario integer,
	cargo varchar(80),
	setor_atuacao varchar(80));

ALTER TABLE gestao add constraint pk_gestao primary key (id_usuario);

ALTER TABLE gestao add constraint fk_gestao_usuario foreign key (id_usuario) references usuario (id_usuario);

CREATE TABLE curso
	(id_curso integer,
	nome varchar(100));

ALTER TABLE curso add constraint pk_curso primary key (id_curso);

CREATE TABLE professor
	(id_usuario integer,
	id_disciplina integer,
	id_curso integer,
	matricula_ufsc varchar(20),
	fase_curso integer);

ALTER TABLE professor add constraint pk_professor primary key (id_usuario);

ALTER TABLE professor add constraint fk_professor_usuario foreign key (id_usuario) references usuario (id_usuario);

ALTER TABLE professor add constraint fk_professor_disciplina foreign key (id_disciplina) references disciplina (id_disciplina);

ALTER TABLE professor add constraint uq_professor_disciplina unique (id_disciplina);

ALTER TABLE professor add constraint fk_professor_curso foreign key (id_curso) references curso (id_curso);

CREATE TABLE escola
	(id_escola integer,
	nome varchar(100),
	cidade varchar(100));

ALTER TABLE escola add constraint pk_escola primary key (id_escola);

CREATE TABLE aluno
	(id_usuario integer,
	id_escola integer,
	turma varchar(50),
	situacao_em varchar(40),
	curso_desejado varchar(100));

ALTER TABLE aluno add constraint pk_aluno primary key (id_usuario);

ALTER TABLE aluno add constraint fk_aluno_usuario foreign key (id_usuario) references usuario (id_usuario);

ALTER TABLE aluno add constraint fk_aluno_escola foreign key (id_escola) references escola (id_escola);

CREATE TABLE vestibular
	(id_vestibular integer,
	ano integer,
	edicao varchar(50),
	instituicao varchar(80));

ALTER TABLE vestibular add constraint pk_vestibular primary key (id_vestibular);

CREATE TABLE questao
	(id_questao integer,
	id_vestibular integer,
	id_professor integer,
	id_gestao integer,
	tipo varchar(30),
	dificuldade varchar(30),
	enunciado text);

ALTER TABLE questao add constraint pk_questao primary key (id_questao);

ALTER TABLE questao add constraint fk_questao_vestibular foreign key (id_vestibular) references vestibular (id_vestibular);

ALTER TABLE questao add constraint fk_questao_professor foreign key (id_professor) references professor (id_usuario);

ALTER TABLE questao add constraint fk_questao_gestao foreign key (id_gestao) references gestao (id_usuario);

CREATE TABLE alternativa
	(id_alternativa integer,
	id_questao integer,
	valor_proposicao integer,
	texto text,
	indicador_correta boolean);

ALTER TABLE alternativa add constraint pk_alternativa primary key (id_alternativa);

ALTER TABLE alternativa add constraint fk_alternativa_questao foreign key (id_questao) references questao (id_questao);

CREATE TABLE dica
	(id_dica integer,
	id_questao integer,
	tipo varchar(50),
	conteudo_texto text);

ALTER TABLE dica add constraint pk_dica primary key (id_dica);

ALTER TABLE dica add constraint fk_dica_questao foreign key (id_questao) references questao (id_questao);

CREATE TABLE tag
	(id_tag integer,
	nome varchar(50));

ALTER TABLE tag add constraint pk_tag primary key (id_tag);

CREATE TABLE midia
	(id_midia integer,
	id_questao integer,
	legenda varchar(200),
	arquivo varchar(255));

ALTER TABLE midia add constraint pk_midia primary key (id_midia);

ALTER TABLE midia add constraint fk_midia_questao foreign key (id_questao) references questao (id_questao);

CREATE TABLE lista_exercicio
	(id_lista integer,
	id_usuario integer,
	publica boolean,
	titulo varchar(150),
	data_criacao timestamp);

ALTER TABLE lista_exercicio add constraint pk_lista_exercicio primary key (id_lista);

ALTER TABLE lista_exercicio add constraint fk_lista_usuario foreign key (id_usuario) references usuario (id_usuario);

CREATE TABLE assunto_questao
	(id_questao integer,
	id_assunto integer);

ALTER TABLE assunto_questao add constraint pk_assunto_questao primary key (id_questao, id_assunto);

ALTER TABLE assunto_questao add constraint fk_assunto_questao_questao foreign key (id_questao) references questao (id_questao);

ALTER TABLE assunto_questao add constraint fk_assunto_questao_assunto foreign key (id_assunto) references assunto (id_assunto);

CREATE TABLE questao_lista
	(id_questao integer,
	id_lista integer);

ALTER TABLE questao_lista add constraint pk_questao_lista primary key (id_questao, id_lista);

ALTER TABLE questao_lista add constraint fk_questao_lista_questao foreign key (id_questao) references questao (id_questao);

ALTER TABLE questao_lista add constraint fk_questao_lista_lista foreign key (id_lista) references lista_exercicio (id_lista);

CREATE TABLE questao_tag
	(id_tag integer,
	id_questao integer);

ALTER TABLE questao_tag add constraint pk_questao_tag primary key (id_tag, id_questao);

ALTER TABLE questao_tag add constraint fk_questao_tag_tag foreign key (id_tag) references tag (id_tag);

ALTER TABLE questao_tag add constraint fk_questao_tag_questao foreign key (id_questao) references questao (id_questao);

CREATE TABLE resolucao_questao
	(id_resolucao integer,
	id_questao integer,
	id_aluno integer,
	data timestamp,
	acerto boolean,
	tempo_gasto integer,
	resposta_aluno integer);

ALTER TABLE resolucao_questao add constraint pk_resolucao_questao primary key (id_resolucao);

ALTER TABLE resolucao_questao add constraint fk_resolucao_questao_questao foreign key (id_questao) references questao (id_questao);

ALTER TABLE resolucao_questao add constraint fk_resolucao_questao_aluno foreign key (id_aluno) references aluno (id_usuario);

-- Disciplinas 
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (1, 'Física', 'A', 'Ciências da Natureza');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (2, 'Física', 'B', 'Ciências da Natureza');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (3, 'Física', 'C', 'Ciências da Natureza');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (4, 'Química', 'A', 'Ciências da Natureza');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (5, 'Química', 'B', 'Ciências da Natureza');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (6, 'Química', 'C', 'Ciências da Natureza');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (7, 'Matemática', 'A', 'Matemática');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (8, 'Matemática', 'B', 'Matemática');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (9, 'Matemática', 'C', 'Matemática');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (10, 'Biologia', 'A', 'Ciências da Natureza');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (11, 'Biologia', 'B', 'Ciências da Natureza');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (12, 'Biologia', 'C', 'Ciências da Natureza');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (13, 'História', 'Brasil', 'Ciências Humanas');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (14, 'História', 'Geral', 'Ciências Humanas');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (15, 'Geografia', 'Física', 'Ciências Humanas');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (16, 'Geografia', 'Política', 'Ciências Humanas');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (17, 'Português', 'Gramática', 'Linguagens e Códigos');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (18, 'Literatura', 'Única', 'Linguagens e Códigos');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (19, 'Redação', 'UFSC', 'Linguagens e Códigos');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (20, 'Redação', 'ENEM', 'Linguagens e Códigos');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (21, 'Filosofia', 'Única', 'Ciências Humanas');
INSERT INTO disciplina (id_disciplina, nome, frente, area) VALUES (22, 'Sociologia', 'Única', 'Ciências Humanas');

-- Assuntos
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (1, 1, 'Cinemática e MUV');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (2, 1, 'Leis de Newton e Dinâmica');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (3, 2, 'Termologia e Calorimetria');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (4, 3, 'Eletrodinâmica e Circuitos');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (5, 4, 'Estequiometria e Soluções');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (6, 5, 'Termoquímica e Cinética');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (7, 6, 'Química Orgânica e Funções');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (8, 7, 'Funções de 1º e 2º Grau');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (9, 8, 'Geometria Espacial e Plana');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (10, 9, 'Análise Combinatória e Probabilidade');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (11, 10, 'Ecologia e Ciclos Biogeoquímicos');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (12, 11, 'Citologia e Metabolismo Celular');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (13, 12, 'Genética e Evolução');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (14, 13, 'Brasil República e Era Vargas');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (15, 14, 'Idade Moderna e Revolução Industrial');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (16, 15, 'Climatologia e Relevo Brasileiro');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (17, 16, 'Geopolítica Mundial e Urbanização');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (18, 17, 'Sintaxe e Concordância Verbal');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (19, 18, 'Obras Obrigatórias UFSC');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (20, 19, 'Gêneros Textuais UFSC');
INSERT INTO assunto (id_assunto, id_disciplina, nome) VALUES (21, 20, 'Dissertação-Argumentativa ENEM');

-- Usuários
INSERT INTO usuario (id_usuario, nome, cpf, senha, email, data_ingresso) VALUES (1, 'Clara Grossl', '11122233301', 'senha123', 'clara.grossl@pes.ufsc.br', '2025-03-10');
INSERT INTO usuario (id_usuario, nome, cpf, senha, email, data_ingresso) VALUES (2, 'Lucas Ferreira', '11122233302', 'senha123', 'lucas.ferreira@pes.ufsc.br', '2025-03-10');
INSERT INTO usuario (id_usuario, nome, cpf, senha, email, data_ingresso) VALUES (3, 'Gabriel Rocha', '22233344401', 'senha123', 'gabriel.rocha@pes.ufsc.br', '2025-08-04');
INSERT INTO usuario (id_usuario, nome, cpf, senha, email, data_ingresso) VALUES (4, 'Mariana Alves', '22233344402', 'senha123', 'mariana.alves@pes.ufsc.br', '2025-08-04');
INSERT INTO usuario (id_usuario, nome, cpf, senha, email, data_ingresso) VALUES (5, 'Rafael Mendes', '22233344403', 'senha123', 'rafael.mendes@pes.ufsc.br', '2026-03-02');
INSERT INTO usuario (id_usuario, nome, cpf, senha, email, data_ingresso) VALUES (6, 'Beatriz Lima', '22233344404', 'senha123', 'beatriz.lima@pes.ufsc.br', '2026-03-02');
INSERT INTO usuario (id_usuario, nome, cpf, senha, email, data_ingresso) VALUES (7, 'João Silva', '33344455501', 'senha123', 'joao.silva@gmail.com', '2026-03-09');
INSERT INTO usuario (id_usuario, nome, cpf, senha, email, data_ingresso) VALUES (8, 'Ana Souza', '33344455502', 'senha123', 'ana.souza@gmail.com', '2026-03-09');
INSERT INTO usuario (id_usuario, nome, cpf, senha, email, data_ingresso) VALUES (9, 'Pedro Santos', '33344455503', 'senha123', 'pedro.santos@gmail.com', '2026-03-09');
INSERT INTO usuario (id_usuario, nome, cpf, senha, email, data_ingresso) VALUES (10, 'Júlia Oliveira', '33344455504', 'senha123', 'julia.oliveira@gmail.com', '2026-03-10');
INSERT INTO usuario (id_usuario, nome, cpf, senha, email, data_ingresso) VALUES (11, 'Mateus Costa', '33344455505', 'senha123', 'mateus.costa@gmail.com', '2026-03-10');

-- Gestão
INSERT INTO gestao (id_usuario, cargo, setor_atuacao) VALUES (1, 'Diretor', 'T.I');
INSERT INTO gestao (id_usuario, cargo, setor_atuacao) VALUES (2, 'Presidente', 'Ensino');

-- Cursos de Graduação 
INSERT INTO curso (id_curso, nome) VALUES (1, 'Engenharia de Energia - UFSC');
INSERT INTO curso (id_curso, nome) VALUES (2, 'Engenharia de Computação - UFSC');
INSERT INTO curso (id_curso, nome) VALUES (3, 'Medicina - UFSC');
INSERT INTO curso (id_curso, nome) VALUES (4, 'Fisioterapia - UFSC');
INSERT INTO curso (id_curso, nome) VALUES (5, 'Tecnologias da Informação e Comunicação - UFSC');

-- Professores
INSERT INTO professor (id_usuario, id_disciplina, id_curso, matricula_ufsc, fase_curso) VALUES (3, 1, 1, '23104512', 6);
INSERT INTO professor (id_usuario, id_disciplina, id_curso, matricula_ufsc, fase_curso) VALUES (4, 7, 2, '24102388', 5);
INSERT INTO professor (id_usuario, id_disciplina, id_curso, matricula_ufsc, fase_curso) VALUES (5, 4, 3, '22201944', 7);
INSERT INTO professor (id_usuario, id_disciplina, id_curso, matricula_ufsc, fase_curso) VALUES (6, 10, 4, '24201105', 4);

-- Escolas
INSERT INTO escola (id_escola, nome, cidade) VALUES (1, 'EEB Castro Alves', 'Araranguá');
INSERT INTO escola (id_escola, nome, cidade) VALUES (2, 'EEB Prof. Maria Garcia Pessi', 'Araranguá');
INSERT INTO escola (id_escola, nome, cidade) VALUES (3, 'EEB Apolônio Ireno Cardoso', 'Balneário Arroio do Silva');
INSERT INTO escola (id_escola, nome, cidade) VALUES (4, 'EEB Dolvina Leite de Medeiros', 'Araranguá');
INSERT INTO escola (id_escola, nome, cidade) VALUES (5, 'EEB Timbé do Sul', 'Timbé do Sul');

-- Alunos 
INSERT INTO aluno (id_usuario, id_escola, turma, situacao_em, curso_desejado) VALUES (7, 1, 'A', '3º Ano EM', 'Engenharia de Computação');
INSERT INTO aluno (id_usuario, id_escola, turma, situacao_em, curso_desejado) VALUES (8, 2, 'A', 'Concluído', 'Medicina');
INSERT INTO aluno (id_usuario, id_escola, turma, situacao_em, curso_desejado) VALUES (9, 3, 'B', '3º Ano EM', 'Direito');
INSERT INTO aluno (id_usuario, id_escola, turma, situacao_em, curso_desejado) VALUES (10, 4, 'A', 'Concluído', 'Psicologia');
INSERT INTO aluno (id_usuario, id_escola, turma, situacao_em, curso_desejado) VALUES (11, 5, 'B', '3º Ano EM', 'Arquitetura e Urbanismo');

-- Vestibulares
INSERT INTO vestibular (id_vestibular, ano, edicao, instituicao) VALUES (1, 2025, 'Vestibular Unificado UFSC/UFFS 2025', 'UFSC');
INSERT INTO vestibular (id_vestibular, ano, edicao, instituicao) VALUES (2, 2024, 'Vestibular Unificado UFSC/UFFS 2024', 'UFSC');
INSERT INTO vestibular (id_vestibular, ano, edicao, instituicao) VALUES (3, 2024, 'Exame Nacional do Ensino Médio 2024', 'ENEM');
INSERT INTO vestibular (id_vestibular, ano, edicao, instituicao) VALUES (4, 2025, 'Vestibular de Verão UDESC 2025', 'UDESC');
INSERT INTO vestibular (id_vestibular, ano, edicao, instituicao) VALUES (5, 2023, 'Exame Nacional do Ensino Médio 2023', 'ENEM');

-- Questões reais de Vestibulares
INSERT INTO questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) VALUES (1, 1, 3, 1, 'Somatoria', 'Media', '(UFSC 2025) Um trem elétrico experimental parte do repouso em uma trajetória retilínea com aceleração escalar constante de $a = 2,0\ \text{m/s}^2$. Com base nas equações da cinemática do Movimento Uniformemente Variado (MUV), assinale a(s) proposição(ões) correta(s).');
INSERT INTO questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) VALUES (2, 2, 3, 1, 'Somatoria', 'Dificil', '(UFSC 2024) Em um laboratório de mecânica, dois blocos $A$ e $B$ de massas $m_A = 2\ \text{kg}$ e $m_B = 3\ \text{kg}$ estão apoiados sobre uma superfície horizontal sem atrito, ligados por um fio ideal. Aplica-se sobre o bloco $B$ uma força horizontal constante de $F = 20\ \text{N}$. Assinale a(s) proposição(ões) correta(s).');
INSERT INTO questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) VALUES (3, 3, 3, 2, 'Multipla Escolha', 'Facil', '(ENEM 2024) Um sistema de aquecimento solar residencial transfere $Q = 4\,200\ \text{J}$ de energia térmica para uma amostra de $100\ \text{g}$ de água líquida, sem mudança de estado físico. Considere o calor específico da água igual a $c = 4,2\ \text{J/(g}\cdot^\circ\text{C)}$. A variação de temperatura $\Delta T$ sofrida pela água é de:');
INSERT INTO questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) VALUES (4, 1, 3, 1, 'Somatoria', 'Media', '(UFSC 2025) Em um circuito residencial simplificado, um resistor ôhmico de resistência $R = 10\ \Omega$ é ligado a uma fonte contínua que mantém uma diferença de potencial $U = 20\ \text{V}$ entre seus terminais. Sobre grandezas elétricas e a Lei de Ohm, assinale a(s) proposição(ões) correta(s).');
INSERT INTO questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) VALUES (5, 1, 4, 1, 'Somatoria', 'Media', '(UFSC 2025) Considere a função quadrática $f: \mathbb{R} \to \mathbb{R}$ definida por $f(x) = x^2 - 5x + 6$. Analisando o gráfico dessa parábola e suas propriedades algébricas, assinale a(s) proposição(ões) correta(s).');
INSERT INTO questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) VALUES (6, 3, 4, 2, 'Multipla Escolha', 'Media', '(ENEM 2024) Uma cooperativa agrícola construiu um reservatório de água da chuva com formato de cilindro circular reto de raio da base $r = 2\ \text{m}$ e altura $h = 5\ \text{m}$. Utilizando a expressão do volume do cilindro $V = \pi r^2 h$, qual é a capacidade máxima desse reservatório em metros cúbicos?');
INSERT INTO questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) VALUES (7, 4, 4, 2, 'Multipla Escolha', 'Dificil', '(UDESC 2025) Uma comissão organizadora de um congresso estudantil na UFSC precisa escolher $3$ representantes dentre $6$ estudantes voluntários, sem distinção de cargo. De quantas maneiras distintas essa comissão pode ser formada?');
INSERT INTO questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) VALUES (8, 2, 5, 1, 'Somatoria', 'Dificil', '(UFSC 2024) O gás natural tem como principal componente o metano ($\text{CH}_4$), cuja reação de combustão completa balanceada é dada por $\text{CH}_4(g) + 2\text{O}_2(g) \rightarrow \text{CO}_2(g) + 2\text{H}_2\text{O}(g)$. Considerando massas molares $\text{C} = 12\ \text{g/mol}$, $\text{H} = 1\ \text{g/mol}$ e $\text{O} = 16\ \text{g/mol}$, assinale a(s) proposição(ões) correta(s).');
INSERT INTO questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) VALUES (9, 5, 5, 2, 'Multipla Escolha', 'Media', '(ENEM 2023) O ácido acético ($\text{CH}_3\text{COOH}$), principal componente responsável pelo sabor azedo do vinagre, pertence a qual função orgânica oxigenada?');
INSERT INTO questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) VALUES (10, 4, 6, 2, 'Multipla Escolha', 'Facil', '(UDESC 2025) No ciclo biogeoquímico do nitrogênio, bactérias do gênero Rhizobium vivem em associação mutualística nas raízes de plantas leguminosas. O papel biológico primordial dessas bactérias consiste em converter o gás nitrogênio atmosférico ($\text{N}_2$) em:');
INSERT INTO questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) VALUES (11, 1, 6, 1, 'Somatoria', 'Media', '(UFSC 2025) Na genética mendeliana clássica, considere o cruzamento entre dois indivíduos heterozigotos ($Aa \times Aa$) para uma característica com dominância completa, em que o alelo $A$ condiciona o fenótipo dominante e o alelo $a$ o fenótipo recessivo. Assinale a(s) proposição(ões) correta(s).');
INSERT INTO questao (id_questao, id_vestibular, id_professor, id_gestao, tipo, dificuldade, enunciado) VALUES (12, 3, 6, 2, 'Multipla Escolha', 'Facil', '(ENEM 2024) Durante a Era Vargas (1930-1945), especificamente no período do Estado Novo, a consolidação das leis trabalhistas (CLT) em 1943 representou um marco na política brasileira por:');

-- Alternativas
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (1, 1, 1, 'Após $t = 5\ \text{s}$ de movimento, a velocidade escalar do trem atinge $v = 10\ \text{m/s}$.', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (2, 1, 2, 'A distância percorrida nos primeiros $5\ \text{s}$ é igual a $50\ \text{m}$.', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (3, 1, 4, 'O deslocamento nos primeiros $5\ \text{s}$ é de $\Delta S = 25\ \text{m}$.', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (4, 1, 8, 'A velocidade média do trem no intervalo de $0$ a $5\ \text{s}$ é igual a $10\ \text{m/s}$.', false);

INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (5, 2, 1, 'A aceleração comum do conjunto de blocos é $a = 4\ \text{m/s}^2$.', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (6, 2, 2, 'A força de tração exercida pelo fio sobre o bloco $A$ vale $T = 8\ \text{N}$.', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (7, 2, 4, 'A força normal e a força peso que atuam no bloco $A$ formam um par ação-reação.', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (8, 2, 8, 'A força resultante sobre o bloco $B$ tem intensidade igual a $20\ \text{N}$.', false);

INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (9, 3, 1, '$5\ ^\circ\text{C}$', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (10, 3, 2, '$10\ ^\circ\text{C}$', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (11, 3, 3, '$20\ ^\circ\text{C}$', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (12, 3, 4, '$42\ ^\circ\text{C}$', false);

INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (13, 4, 1, 'A corrente elétrica que percorre o resistor tem intensidade $i = 2\ \text{A}$.', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (14, 4, 2, 'No Sistema Internacional (SI), a unidade de resistência elétrica é o Ampere ($\text{A}$).', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (15, 4, 4, 'A potência elétrica dissipada pelo resistor por efeito Joule é $P = 40\ \text{W}$.', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (16, 4, 8, 'Se a tensão for duplicada para $40\ \text{V}$, a resistência do resistor ôhmico também duplica.', false);

INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (17, 5, 1, 'As raízes reais da equação $f(x) = 0$ são $x_1 = 2$ e $x_2 = 3$.', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (18, 5, 2, 'Como o coeficiente líder é positivo ($a = 1 > 0$), a parábola tem concavidade voltada para cima.', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (19, 5, 4, 'O vértice da parábola possui abscissa $x_v = 5$.', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (20, 5, 8, 'A parábola intersecta o eixo vertical das ordenadas no ponto $(0, 6)$.', true);

INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (21, 6, 1, '$10\pi\ \text{m}^3$', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (22, 6, 2, '$15\pi\ \text{m}^3$', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (23, 6, 3, '$20\pi\ \text{m}^3$', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (24, 6, 4, '$40\pi\ \text{m}^3$', false);

INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (25, 7, 1, '$15$ comissões distintas.', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (26, 7, 2, '$18$ comissões distintas.', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (27, 7, 3, '$20$ comissões distintas.', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (28, 7, 4, '$120$ comissões distintas.', false);

INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (29, 8, 1, 'A queima completa de $1\ \text{mol}$ de $\text{CH}_4$ consome $64\ \text{g}$ de gás oxigênio ($\text{O}_2$).', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (30, 8, 2, 'Na combustão de $1\ \text{mol}$ de metano forma-se apenas $1\ \text{mol}$ de água ($\text{H}_2\text{O}$).', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (31, 8, 4, 'A massa de $\text{CO}_2$ produzida por mol de metano queimado é de $44\ \text{g}$.', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (32, 8, 8, 'A massa molar do metano ($\text{CH}_4$) é igual a $28\ \text{g/mol}$.', false);

INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (33, 9, 1, 'Álcool', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (34, 9, 2, 'Ácido carboxílico', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (35, 9, 3, 'Cetona', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (36, 9, 4, 'Éster', false);

INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (37, 10, 1, 'Amônia ($\text{NH}_3$) e íons amônio ($\text{NH}_4^+$), assimiláveis pelos vegetais.', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (38, 10, 2, 'Gás ozônio ($\text{O}_3$), responsável pela filtragem de radiação UV.', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (39, 10, 3, 'Dióxido de enxofre ($\text{SO}_2$), formando chuvas ácidas.', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (40, 10, 4, 'Gás metano ($\text{CH}_4$), liberado diretamente na atmosfera.', false);

INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (41, 11, 1, 'A proporção genotípica esperada na descendência é de $1\ AA : 2\ Aa : 1\ aa$.', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (42, 11, 2, 'A probabilidade de nascer um descendente com fenótipo recessivo ($aa$) é de $25\%$.', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (43, 11, 4, 'A proporção fenotípica esperada é de $1$ dominante para $3$ recessivos.', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (44, 11, 8, 'A probabilidade de um indivíduo apresentar o fenótipo dominante é de $75\%$.', true);

INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (45, 12, 1, 'Sistematizar direitos como jornada de 8 horas, férias remuneradas e salário mínimo, integrando o trabalhismo ao projeto estatal.', true);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (46, 12, 2, 'Instituir o regime de livre sindicalização totalmente desvinculado do Ministério do Trabalho.', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (47, 12, 3, 'Abolir o trabalho urbano assalariado em favor de cooperativas agrárias autônomas.', false);
INSERT INTO alternativa (id_alternativa, id_questao, valor_proposicao, texto, indicador_correta) VALUES (48, 12, 4, 'Substituir a constituição federal pela monarquia parlamentarista.', false);

-- Dicas e Resoluções Passo a Passo
INSERT INTO dica (id_dica, id_questao, tipo, conteudo_texto) VALUES (1, 1, 'Dica Inicial', 'Utilize as equações horárias do MUV partindo do repouso ($v_0 = 0$): $v = v_0 + a \cdot t$ e $\Delta S = v_0 t + \frac{a t^2}{2}$.');
INSERT INTO dica (id_dica, id_questao, tipo, conteudo_texto) VALUES (2, 1, 'Resolução Passo a Passo', 'Item 01 (Verdadeiro): $v = 0 + 2 \cdot 5 = 10\ \text{m/s}$. Item 02 (Falso) e Item 04 (Verdadeiro): $\Delta S = \frac{2 \cdot 5^2}{2} = 25\ \text{m}$. Item 08 (Falso): a velocidade média é $v_m = \frac{25}{5} = 5\ \text{m/s}$. Soma correta: $01 + 04 = 05$.');
INSERT INTO dica (id_dica, id_questao, tipo, conteudo_texto) VALUES (3, 2, 'Dica Inicial', 'Calcule primeiro a aceleração do conjunto pela Segunda Lei de Newton ($F = (m_A + m_B) \cdot a$) e depois isole o bloco $A$ para achar a tração.');
INSERT INTO dica (id_dica, id_questao, tipo, conteudo_texto) VALUES (4, 2, 'Resolução Passo a Passo', 'Item 01 (Verdadeiro): $a = \frac{20}{2 + 3} = 4\ \text{m/s}^2$. Item 02 (Verdadeiro): no bloco $A$, $T = m_A \cdot a = 2 \cdot 4 = 8\ \text{N}$. Item 04 (Falso): Normal e Peso atuam no mesmo corpo, nunca formando par ação-reação. Item 08 (Falso): $F_{res, B} = m_B \cdot a = 12\ \text{N}$. Soma correta: $01 + 02 = 03$.');
INSERT INTO dica (id_dica, id_questao, tipo, conteudo_texto) VALUES (5, 3, 'Dica Inicial', 'Aplique a equação fundamental da calorimetria para calor sensível: $Q = m \cdot c \cdot \Delta T$.');
INSERT INTO dica (id_dica, id_questao, tipo, conteudo_texto) VALUES (6, 3, 'Resolução Passo a Passo', 'Substituindo os valores: $4200 = 100 \cdot 4,2 \cdot \Delta T \Rightarrow 4200 = 420 \cdot \Delta T \Rightarrow \Delta T = \frac{4200}{420} = 10\ ^\circ\text{C}$. Alternativa correta: B.');
INSERT INTO dica (id_dica, id_questao, tipo, conteudo_texto) VALUES (7, 4, 'Dica Inicial', 'Relembre a Primeira Lei de Ohm ($U = R \cdot i$) e a expressão da potência dissipada ($P = U \cdot i$).');
INSERT INTO dica (id_dica, id_questao, tipo, conteudo_texto) VALUES (8, 4, 'Resolução Passo a Passo', 'Item 01 (Verdadeiro): $i = \frac{U}{R} = \frac{20}{10} = 2\ \text{A}$. Item 02 (Falso): a unidade de resistência no SI é o Ohm ($\Omega$). Item 04 (Verdadeiro): $P = U \cdot i = 20 \cdot 2 = 40\ \text{W}$. Item 08 (Falso): em um resistor ôhmico a resistência é constante. Soma correta: $01 + 04 = 05$.');
INSERT INTO dica (id_dica, id_questao, tipo, conteudo_texto) VALUES (9, 5, 'Dica Inicial', 'Encontre as raízes por Soma e Produto ($S = 5$ e $P = 6$), verifique o sinal do coeficiente $a$ e calcule $x_v = -\frac{b}{2a}$.');
INSERT INTO dica (id_dica, id_questao, tipo, conteudo_texto) VALUES (10, 5, 'Resolução Passo a Passo', 'Item 01 (Verdadeiro): $(x - 2)(x - 3) = 0 \Rightarrow x = 2$ ou $x = 3$. Item 02 (Verdadeiro): $a = 1 > 0$ implica concavidade para cima. Item 04 (Falso): $x_v = \frac{5}{2} = 2,5$. Item 08 (Verdadeiro): $f(0) = 6$, ponto $(0, 6)$. Soma correta: $01 + 02 + 08 = 11$.');
INSERT INTO dica (id_dica, id_questao, tipo, conteudo_texto) VALUES (11, 7, 'Dica Inicial', 'Como a ordem de escolha dos representantes na comissão não altera o grupo formado, utilize Combinação Simples: $C_{n,p} = \frac{n!}{p!(n-p)!}$.');
INSERT INTO dica (id_dica, id_questao, tipo, conteudo_texto) VALUES (12, 7, 'Resolução Passo a Passo', 'Calculando $C_{6,3} = \frac{6!}{3! \cdot 3!} = \frac{6 \cdot 5 \cdot 4}{3 \cdot 2 \cdot 1} = 20$ comissões distintas. Alternativa correta: C.');

-- Tags
INSERT INTO tag (id_tag, nome) VALUES (1, 'Somatória UFSC');
INSERT INTO tag (id_tag, nome) VALUES (2, 'Cálculo Direto');
INSERT INTO tag (id_tag, nome) VALUES (3, 'Pegadinha Conceitual');
INSERT INTO tag (id_tag, nome) VALUES (4, 'Alta Recorrência');
INSERT INTO tag (id_tag, nome) VALUES (5, 'Interpretação');

-- Listas de Exercícios
INSERT INTO lista_exercicio (id_lista, id_usuario, publica, titulo, data_criacao) VALUES (1, 3, true, 'Lista 01 — Revisão de Física UFSC e ENEM', '2026-04-10 14:00:00');
INSERT INTO lista_exercicio (id_lista, id_usuario, publica, titulo, data_criacao) VALUES (2, 4, true, 'Lista 02 — Matemática Essencial (Funções, Geometria e Combinatória)', '2026-04-12 16:30:00');
INSERT INTO lista_exercicio (id_lista, id_usuario, publica, titulo, data_criacao) VALUES (3, 1, true, 'Simulado Geral PES — Ciências da Natureza', '2026-05-01 08:00:00');
INSERT INTO lista_exercicio (id_lista, id_usuario, publica, titulo, data_criacao) VALUES (4, 7, false, 'Caderno Pessoal — Revisão de Somatórias', '2026-05-10 20:15:00');

-- Relacionamento Assunto_Questao
INSERT INTO assunto_questao (id_questao, id_assunto) VALUES (1, 1);
INSERT INTO assunto_questao (id_questao, id_assunto) VALUES (2, 2);
INSERT INTO assunto_questao (id_questao, id_assunto) VALUES (3, 3);
INSERT INTO assunto_questao (id_questao, id_assunto) VALUES (4, 4);
INSERT INTO assunto_questao (id_questao, id_assunto) VALUES (5, 8);
INSERT INTO assunto_questao (id_questao, id_assunto) VALUES (6, 9);
INSERT INTO assunto_questao (id_questao, id_assunto) VALUES (7, 10);
INSERT INTO assunto_questao (id_questao, id_assunto) VALUES (8, 5);
INSERT INTO assunto_questao (id_questao, id_assunto) VALUES (9, 7);
INSERT INTO assunto_questao (id_questao, id_assunto) VALUES (10, 11);
INSERT INTO assunto_questao (id_questao, id_assunto) VALUES (11, 13);
INSERT INTO assunto_questao (id_questao, id_assunto) VALUES (12, 14);

-- Relacionamento Questao_Lista
INSERT INTO questao_lista (id_questao, id_lista) VALUES (1, 1);
INSERT INTO questao_lista (id_questao, id_lista) VALUES (2, 1);
INSERT INTO questao_lista (id_questao, id_lista) VALUES (3, 1);
INSERT INTO questao_lista (id_questao, id_lista) VALUES (4, 1);
INSERT INTO questao_lista (id_questao, id_lista) VALUES (5, 2);
INSERT INTO questao_lista (id_questao, id_lista) VALUES (6, 2);
INSERT INTO questao_lista (id_questao, id_lista) VALUES (7, 2);
INSERT INTO questao_lista (id_questao, id_lista) VALUES (1, 3);
INSERT INTO questao_lista (id_questao, id_lista) VALUES (4, 3);
INSERT INTO questao_lista (id_questao, id_lista) VALUES (8, 3);
INSERT INTO questao_lista (id_questao, id_lista) VALUES (10, 3);
INSERT INTO questao_lista (id_questao, id_lista) VALUES (11, 3);
INSERT INTO questao_lista (id_questao, id_lista) VALUES (2, 4);
INSERT INTO questao_lista (id_questao, id_lista) VALUES (5, 4);
INSERT INTO questao_lista (id_questao, id_lista) VALUES (8, 4);

-- Relacionamento Questao_Tag
INSERT INTO questao_tag (id_tag, id_questao) VALUES (1, 1);
INSERT INTO questao_tag (id_tag, id_questao) VALUES (4, 1);
INSERT INTO questao_tag (id_tag, id_questao) VALUES (1, 2);
INSERT INTO questao_tag (id_tag, id_questao) VALUES (3, 2);
INSERT INTO questao_tag (id_tag, id_questao) VALUES (2, 3);
INSERT INTO questao_tag (id_tag, id_questao) VALUES (1, 4);
INSERT INTO questao_tag (id_tag, id_questao) VALUES (1, 5);
INSERT INTO questao_tag (id_tag, id_questao) VALUES (4, 5);
INSERT INTO questao_tag (id_tag, id_questao) VALUES (2, 6);
INSERT INTO questao_tag (id_tag, id_questao) VALUES (4, 7);
INSERT INTO questao_tag (id_tag, id_questao) VALUES (1, 8);
INSERT INTO questao_tag (id_tag, id_questao) VALUES (4, 9);
INSERT INTO questao_tag (id_tag, id_questao) VALUES (4, 10);
INSERT INTO questao_tag (id_tag, id_questao) VALUES (1, 11);
INSERT INTO questao_tag (id_tag, id_questao) VALUES (5, 12);

-- Histórico de Resoluções
INSERT INTO resolucao_questao (id_resolucao, id_questao, id_aluno, data, acerto, tempo_gasto, resposta_aluno) VALUES (1, 1, 7, '2026-05-02 19:10:00', true, 120, 5);
INSERT INTO resolucao_questao (id_resolucao, id_questao, id_aluno, data, acerto, tempo_gasto, resposta_aluno) VALUES (2, 2, 7, '2026-05-02 19:15:00', false, 210, 7);
INSERT INTO resolucao_questao (id_resolucao, id_questao, id_aluno, data, acerto, tempo_gasto, resposta_aluno) VALUES (3, 3, 7, '2026-05-02 19:18:00', true, 90, 2);
INSERT INTO resolucao_questao (id_resolucao, id_questao, id_aluno, data, acerto, tempo_gasto, resposta_aluno) VALUES (4, 5, 8, '2026-05-03 14:20:00', true, 150, 11);
INSERT INTO resolucao_questao (id_resolucao, id_questao, id_aluno, data, acerto, tempo_gasto, resposta_aluno) VALUES (5, 6, 8, '2026-05-03 14:25:00', false, 200, 1);
INSERT INTO resolucao_questao (id_resolucao, id_questao, id_aluno, data, acerto, tempo_gasto, resposta_aluno) VALUES (6, 8, 8, '2026-05-03 14:30:00', false, 195, 7);
INSERT INTO resolucao_questao (id_resolucao, id_questao, id_aluno, data, acerto, tempo_gasto, resposta_aluno) VALUES (7, 1, 9, '2026-05-04 10:00:00', true, 110, 5);
INSERT INTO resolucao_questao (id_resolucao, id_questao, id_aluno, data, acerto, tempo_gasto, resposta_aluno) VALUES (8, 4, 9, '2026-05-04 10:05:00', true, 140, 5);
INSERT INTO resolucao_questao (id_resolucao, id_questao, id_aluno, data, acerto, tempo_gasto, resposta_aluno) VALUES (9, 10, 9, '2026-05-04 10:08:00', true, 75, 1);
INSERT INTO resolucao_questao (id_resolucao, id_questao, id_aluno, data, acerto, tempo_gasto, resposta_aluno) VALUES (10, 7, 10, '2026-05-05 20:00:00', true, 160, 3);
INSERT INTO resolucao_questao (id_resolucao, id_questao, id_aluno, data, acerto, tempo_gasto, resposta_aluno) VALUES (11, 8, 10, '2026-05-05 20:06:00', true, 175, 5);
INSERT INTO resolucao_questao (id_resolucao, id_questao, id_aluno, data, acerto, tempo_gasto, resposta_aluno) VALUES (12, 11, 11, '2026-05-06 15:30:00', true, 130, 11);
INSERT INTO resolucao_questao (id_resolucao, id_questao, id_aluno, data, acerto, tempo_gasto, resposta_aluno) VALUES (13, 12, 11, '2026-05-06 15:34:00', true, 65, 1);

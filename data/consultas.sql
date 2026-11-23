-- Total de resolucoes e tempo medio gasto por Disciplina e Frente
SELECT d.nome,
       d.frente,
       COUNT(r.id_resolucao) AS total_resolucoes,
       AVG(r.tempo_gasto) AS tempo_medio_seg
FROM resolucao_questao r
INNER JOIN questao q ON r.id_questao = q.id_questao
INNER JOIN assunto_questao aq ON q.id_questao = aq.id_questao
INNER JOIN assunto a ON aq.id_assunto = a.id_assunto
INNER JOIN disciplina d ON a.id_disciplina = d.id_disciplina
GROUP BY d.nome, d.frente
ORDER BY total_resolucoes DESC;

-- Engajamento e tempo medio de resolucao por Aluno e Turma (A e B)
SELECT u.nome,
       al.turma,
       COUNT(r.id_resolucao) AS questoes_resolvidas,
       AVG(r.tempo_gasto) AS tempo_medio_seg
FROM usuario u
INNER JOIN aluno al ON u.id_usuario = al.id_usuario
INNER JOIN resolucao_questao r ON al.id_usuario = r.id_aluno
INNER JOIN questao q ON r.id_questao = q.id_questao
GROUP BY u.nome, al.turma
ORDER BY questoes_resolvidas DESC;

-- Quantidade de questoes cadastradas por Vestibular e Professor
SELECT v.instituicao,
       u.nome AS professor,
       COUNT(q.id_questao) AS total_questoes
FROM questao q
INNER JOIN vestibular v ON q.id_vestibular = v.id_vestibular
INNER JOIN professor p ON q.id_professor = p.id_usuario
INNER JOIN usuario u ON p.id_usuario = u.id_usuario
GROUP BY v.instituicao, u.nome
ORDER BY total_questoes DESC;

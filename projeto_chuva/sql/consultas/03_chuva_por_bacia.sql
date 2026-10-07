-- Média, por bacia e ano, dos totais anuais das estações.
-- Duas etapas com WITH (CTE): primeiro o total de cada estação no ano, depois a média por bacia.
-- Somar chuva de estações diferentes não tem sentido físico; tirar a média dos totais, sim.
-- Só entram estação-anos com pelo menos 300 dias válidos (regra de decisão, ajuste se precisar).
WITH por_estacao_ano AS (
    SELECT estacao_id,
           strftime('%Y', data) AS ano,
           SUM(chuva_mm)        AS total_mm,
           COUNT(chuva_mm)      AS n_validos
    FROM chuva_diaria
    GROUP BY estacao_id, ano
)
SELECT e.bacia                        AS bacia,
       p.ano                          AS ano,
       COUNT(*)                       AS estacoes,
       ROUND(AVG(p.total_mm), 1)      AS media_dos_totais_mm
FROM por_estacao_ano AS p
JOIN estacao AS e ON e.id = p.estacao_id
WHERE p.n_validos >= 300
GROUP BY e.bacia, p.ano
ORDER BY e.bacia, p.ano;

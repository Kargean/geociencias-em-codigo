-- Quantas linhas, quantas medidas válidas e quantas ausentes por estação.
-- COUNT(*) conta linhas; COUNT(coluna) conta só as linhas em que a coluna NÃO é NULL.
SELECT e.id            AS estacao,
       e.nome          AS nome,
       e.bacia         AS bacia,
       COUNT(*)        AS linhas,
       COUNT(c.chuva_mm)            AS validos,
       COUNT(*) - COUNT(c.chuva_mm) AS ausentes,
       MIN(c.data)     AS primeira,
       MAX(c.data)     AS ultima
FROM estacao AS e
JOIN chuva_diaria AS c ON c.estacao_id = e.id
GROUP BY e.id, e.nome, e.bacia
ORDER BY e.id;

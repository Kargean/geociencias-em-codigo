-- Rx5day: maior chuva acumulada em 5 dias consecutivos, por estação (a janela só vale se completa).
-- A janela é por DATA, não por número de linhas: RANGE sobre o número juliano da data.
-- "4 PRECEDING" + o próprio dia = 5 dias. (SQLite exige um valor constante ali; precisa de versão >= 3.28.)
-- Erro clássico: usar ROWS em vez de RANGE. Se faltar uma data, ROWS pega dias NÃO consecutivos.
WITH janelas AS (
    SELECT estacao_id,
           data AS fim,
           SUM(chuva_mm)   OVER w AS acumulado_mm,
           COUNT(chuva_mm) OVER w AS n_validos
    FROM chuva_diaria
    WINDOW w AS (PARTITION BY estacao_id ORDER BY julianday(data) RANGE BETWEEN 4 PRECEDING AND CURRENT ROW)
),
completas AS (
    SELECT * FROM janelas WHERE n_validos = 5
),
ordenadas AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY estacao_id ORDER BY acumulado_mm DESC, fim ASC) AS posicao
    FROM completas
)
SELECT estacao_id AS estacao, ROUND(acumulado_mm, 1) AS acumulado_mm, fim
FROM ordenadas
WHERE posicao = 1
ORDER BY estacao_id;

-- CDD: maior sequência de dias consecutivos com chuva < :limiar, por estação.
-- Técnica "lacunas e ilhas" (gaps and islands):
--   1) só entram dias secos; NULL < x é NULL, então dia sem medida fica de fora e QUEBRA a sequência;
--   2) data (como número juliano) menos o número da linha é CONSTANTE dentro de uma sequência de dias
--      seguidos, e muda quando há um buraco. Esse valor identifica a "ilha".
WITH secos AS (
    SELECT estacao_id,
           data,
           julianday(data) - ROW_NUMBER() OVER (PARTITION BY estacao_id ORDER BY data) AS ilha
    FROM chuva_diaria
    WHERE chuva_mm < :limiar
),
periodos AS (
    SELECT estacao_id, MIN(data) AS inicio, MAX(data) AS fim, COUNT(*) AS dias
    FROM secos
    GROUP BY estacao_id, ilha
),
ordenados AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY estacao_id ORDER BY dias DESC, inicio ASC) AS posicao
    FROM periodos
)
SELECT estacao_id AS estacao, dias, inicio, fim
FROM ordenados
WHERE posicao = 1
ORDER BY estacao_id;

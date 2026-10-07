-- Dias com chuva >= :limiar, por estação e ano (ETCCDI: Rnnmm com nn = limiar).
-- Comparação com NULL dá NULL (nem verdadeiro nem falso); SUM ignora NULL. Por isso dias sem medida não contam.
-- COALESCE troca o NULL de uma estação-ano sem nenhuma medida por 0.
SELECT estacao_id                                   AS estacao,
       strftime('%Y', data)                         AS ano,
       COALESCE(SUM(chuva_mm >= :limiar), 0)        AS dias_de_chuva
FROM chuva_diaria
GROUP BY estacao_id, ano
ORDER BY estacao_id, ano;

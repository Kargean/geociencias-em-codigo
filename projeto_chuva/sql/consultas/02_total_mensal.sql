-- Total de chuva por estação e mês, com o número de dias válidos e se o mês está completo.
-- Equivale a chuva.resumo.total_mensal. SUM ignora NULL; se TODOS forem NULL, o resultado é NULL.
SELECT estacao_id                      AS estacao,
       strftime('%Y-%m', data)         AS mes,
       ROUND(SUM(chuva_mm), 1)         AS total_mm,
       COUNT(chuva_mm)                 AS n_validos,
       COUNT(*)                        AS n_registrados,
       CAST(strftime('%d', date(MIN(data), 'start of month', '+1 month', '-1 day')) AS INTEGER) AS dias_no_mes,
       COUNT(chuva_mm) = CAST(strftime('%d', date(MIN(data), 'start of month', '+1 month', '-1 day')) AS INTEGER) AS completo
FROM chuva_diaria
GROUP BY estacao_id, mes
ORDER BY estacao_id, mes;

-- Registro do PostgreSQL do capítulo P1-07 (SQL essencial II, Geociências em Código).
-- Como usar:  psql -d <um banco de teste> -X -f tools/registro_postgresql_p1-07.sql
-- Só cria tabelas TEMPORÁRIAS (somem quando a sessão termina) e não mexe em nenhuma tabela existente.
-- Registrado em 08/10/2026 com PostgreSQL 16.15 (Ubuntu), cliente psql 16.15, Linux.
-- As tabelas equivalem às do capítulo, com data do tipo date, valor do tipo double precision e ids automáticos (IDENTITY).
-- As sondas de dialeto (ao final) são o registro citado na seção "Dialetos" do capítulo.
\pset null 'NULL'
CREATE TEMP TABLE ponto (codigo text PRIMARY KEY, descricao text NOT NULL);
CREATE TEMP TABLE parametro (codigo text PRIMARY KEY, unidade text NOT NULL, minimo double precision, maximo double precision);
CREATE TEMP TABLE resultado (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, ponto text NOT NULL REFERENCES ponto (codigo), data date NOT NULL, parametro text NOT NULL REFERENCES parametro (codigo), valor double precision);
CREATE TEMP TABLE fonte (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, ponto text NOT NULL REFERENCES ponto (codigo), tipo text NOT NULL);
INSERT INTO ponto VALUES ('P01','montante do lançamento'),('P02','jusante do lançamento'),('P03','afluente'),('P04','cadastrado, ainda sem coleta');
INSERT INTO parametro VALUES ('OD','mg/L',5.0,NULL),('pH','adim.',6.0,9.0),('turbidez','UNT',NULL,100.0);
INSERT INTO resultado (ponto, data, parametro, valor) VALUES
('P01','2024-02-20','OD',7.8),('P01','2024-02-20','pH',7.2),('P01','2024-02-20','turbidez',18.0),
('P02','2024-02-20','OD',6.1),('P02','2024-02-20','pH',6.8),('P02','2024-02-20','turbidez',135.0),
('P01','2024-05-14','OD',7.5),('P01','2024-05-14','pH',7.0),('P01','2024-05-14','turbidez',12.0),
('P02','2024-05-14','OD',4.8),('P02','2024-05-14','pH',6.3),('P02','2024-05-14','turbidez',60.0),
('P01','2024-08-13','OD',7.1),('P01','2024-08-13','pH',6.9),('P01','2024-08-13','turbidez',9.0),
('P02','2024-08-13','OD',3.9),('P02','2024-08-13','pH',5.8),('P02','2024-08-13','turbidez',NULL),
('P03','2024-08-13','OD',6.5),('P03','2024-08-13','pH',7.4);
INSERT INTO fonte (ponto, tipo) VALUES ('P02','lançamento de esgoto tratado'),('P02','drenagem urbana'),('P03','drenagem rural'),('P03','pecuária');
\pset tuples_only on
\pset format unaligned
\pset fieldsep ' | '
\pset null 'NULL'
\echo '=== Consultas do capítulo (resultados que devem coincidir com os do SQLite) ==='
\echo '@@ agregados_turbidez'
SELECT COUNT(*), COUNT(valor), SUM(valor), AVG(valor), MIN(valor), MAX(valor) FROM resultado WHERE parametro = 'turbidez';
\echo '@@ media_ingenua'
SELECT AVG(valor), AVG(COALESCE(valor, 0)), SUM(valor) / COUNT(*) FROM resultado WHERE parametro = 'turbidez';
\echo '@@ media_de_tudo'
SELECT AVG(valor) FROM resultado;
\echo '@@ campanhas'
SELECT COUNT(DISTINCT data) FROM resultado;
\echo '@@ por_parametro'
SELECT parametro, COUNT(*), COUNT(valor), ROUND(CAST(AVG(valor) AS numeric), 2), MIN(valor), MAX(valor) FROM resultado GROUP BY parametro ORDER BY parametro;
\echo '@@ od_por_ponto'
SELECT ponto, COUNT(*), ROUND(CAST(AVG(valor) AS numeric), 2) FROM resultado WHERE parametro = 'OD' GROUP BY ponto ORDER BY ponto;
\echo '@@ grupo_null'
SELECT valor, COUNT(*) FROM resultado WHERE parametro = 'turbidez' GROUP BY valor;
\echo '@@ having_media'
SELECT ponto, COUNT(*), ROUND(CAST(AVG(valor) AS numeric), 2) FROM resultado WHERE parametro = 'OD' GROUP BY ponto HAVING AVG(valor) < 5.0;
\echo '@@ having_contagem'
SELECT ponto, COUNT(valor), ROUND(CAST(AVG(valor) AS numeric), 2) FROM resultado WHERE parametro = 'OD' GROUP BY ponto HAVING COUNT(valor) >= 2 ORDER BY ponto;
\echo '@@ min_ou_media'
SELECT ponto, COUNT(*), MIN(valor) FROM resultado WHERE parametro = 'OD' GROUP BY ponto HAVING MIN(valor) < 5.0 ORDER BY ponto;
\echo '@@ join_parametro'
SELECT r.id, r.ponto, r.parametro, r.valor, p.unidade, p.minimo, p.maximo FROM resultado r JOIN parametro p ON p.codigo = r.parametro ORDER BY r.id LIMIT 5;
\echo '@@ conformidade'
SELECT r.ponto, r.parametro, COUNT(r.valor), SUM(CASE WHEN r.valor < p.minimo OR r.valor > p.maximo THEN 1 ELSE 0 END) FROM resultado r JOIN parametro p ON p.codigo = r.parametro GROUP BY r.ponto, r.parametro ORDER BY r.ponto, r.parametro;
\echo '@@ inner_ponto_fonte'
SELECT po.codigo, f.tipo FROM ponto po JOIN fonte f ON f.ponto = po.codigo;
\echo '@@ left_ponto_fonte'
SELECT po.codigo, f.tipo FROM ponto po LEFT JOIN fonte f ON f.ponto = po.codigo;
\echo '@@ left_contagem'
SELECT po.codigo, COUNT(*), COUNT(r.id) FROM ponto po LEFT JOIN resultado r ON r.ponto = po.codigo GROUP BY po.codigo ORDER BY po.codigo;
\echo '@@ filtro_no_where'
SELECT po.codigo, COUNT(r.id) FROM ponto po LEFT JOIN resultado r ON r.ponto = po.codigo WHERE r.parametro = 'OD' GROUP BY po.codigo ORDER BY po.codigo;
\echo '@@ filtro_no_on'
SELECT po.codigo, COUNT(r.id) FROM ponto po LEFT JOIN resultado r ON r.ponto = po.codigo AND r.parametro = 'OD' GROUP BY po.codigo ORDER BY po.codigo;
\echo '@@ anti_join'
SELECT po.codigo FROM ponto po LEFT JOIN resultado r ON r.ponto = po.codigo WHERE r.id IS NULL ORDER BY po.codigo;
\echo '@@ right_join'
SELECT COUNT(*) FROM resultado r RIGHT JOIN ponto po ON r.ponto = po.codigo;
\echo '@@ fanout_linhas'
SELECT (SELECT COUNT(*) FROM resultado), (SELECT COUNT(*) FROM resultado r JOIN fonte f ON f.ponto = r.ponto), (SELECT COUNT(*) FROM resultado r LEFT JOIN fonte f ON f.ponto = r.ponto);
\echo '@@ fanout_media'
SELECT (SELECT AVG(r.valor) FROM resultado r WHERE r.parametro = 'OD'), (SELECT AVG(r.valor) FROM resultado r JOIN fonte f ON f.ponto = r.ponto WHERE r.parametro = 'OD'), (SELECT AVG(r.valor) FROM resultado r LEFT JOIN fonte f ON f.ponto = r.ponto WHERE r.parametro = 'OD');
\echo '@@ fanout_por_ponto'
SELECT r.ponto, COUNT(*), COUNT(DISTINCT r.id), ROUND(CAST(SUM(r.valor) AS numeric), 1), ROUND(CAST(AVG(r.valor) AS numeric), 2) FROM resultado r LEFT JOIN fonte f ON f.ponto = r.ponto WHERE r.parametro = 'OD' GROUP BY r.ponto ORDER BY r.ponto;
\echo '@@ fanout_distinct'
SELECT COUNT(DISTINCT r.id) FROM resultado r LEFT JOIN fonte f ON f.ponto = r.ponto;
\echo '@@ corrigido'
SELECT r.ponto, COUNT(*), ROUND(CAST(AVG(r.valor) AS numeric), 2), COALESCE(fo.n_fontes, 0) FROM resultado r LEFT JOIN (SELECT ponto, COUNT(*) AS n_fontes FROM fonte GROUP BY ponto) AS fo ON fo.ponto = r.ponto WHERE r.parametro = 'OD' GROUP BY r.ponto, fo.n_fontes ORDER BY r.ponto;
\echo '@@ corrigido_global'
SELECT AVG(r.valor), (SELECT COUNT(*) FROM resultado r2 LEFT JOIN (SELECT ponto, COUNT(*) AS n_fontes FROM fonte GROUP BY ponto) AS fo2 ON fo2.ponto = r2.ponto) FROM resultado r LEFT JOIN (SELECT ponto, COUNT(*) AS n_fontes FROM fonte GROUP BY ponto) AS fo ON fo.ponto = r.ponto WHERE r.parametro = 'OD';
\echo '@@ relatorio'
SELECT ponto, campanhas, medidos, fora, ROUND(100.0 * (medidos - fora) / NULLIF(medidos, 0), 1) AS pct_conforme FROM (SELECT po.codigo AS ponto, COUNT(DISTINCT r.data) AS campanhas, COUNT(r.valor) AS medidos, SUM(CASE WHEN r.valor < p.minimo OR r.valor > p.maximo THEN 1 ELSE 0 END) AS fora FROM ponto po LEFT JOIN resultado r ON r.ponto = po.codigo LEFT JOIN parametro p ON p.codigo = r.parametro GROUP BY po.codigo) AS por_ponto ORDER BY ponto;
\echo '@@ largo'
SELECT po.codigo, ROUND(CAST(AVG(CASE WHEN r.parametro = 'OD' THEN r.valor END) AS numeric), 2), ROUND(CAST(AVG(CASE WHEN r.parametro = 'pH' THEN r.valor END) AS numeric), 2), ROUND(CAST(AVG(CASE WHEN r.parametro = 'turbidez' THEN r.valor END) AS numeric), 2) FROM ponto po LEFT JOIN resultado r ON r.ponto = po.codigo GROUP BY po.codigo ORDER BY po.codigo;
\echo '=== Sondas de dialeto ==='
\echo '@@ coluna_solta'
SELECT COUNT(*) FROM (SELECT ponto, valor FROM resultado GROUP BY ponto) AS t;
\echo '@@ apelido_having'
SELECT ponto, AVG(valor) AS media FROM resultado GROUP BY ponto HAVING media < 10 ORDER BY ponto;
\echo '@@ round_media'
SELECT ROUND(AVG(valor), 1) FROM resultado WHERE parametro = 'OD';
\echo '@@ avg_inteiros'
SELECT AVG(v) FROM (SELECT 1 AS v UNION ALL SELECT 2) AS t;
\echo '@@ agregado_where'
SELECT ponto FROM resultado WHERE AVG(valor) < 5 GROUP BY ponto;
\echo '@@ conjunto_vazio'
SELECT COUNT(valor), SUM(valor), AVG(valor) FROM resultado WHERE parametro = 'nada';
\echo '@@ group_concat'
SELECT group_concat(codigo, ', ') FROM ponto;
\echo '@@ string_agg'
SELECT string_agg(codigo, ', ' ORDER BY codigo) FROM ponto;
\echo '@@ fk_padrao'
INSERT INTO resultado (ponto, data, parametro, valor) VALUES ('PX', '2024-09-01', 'OD', 6.0);
\echo '@@ pk_texto_nulo'
CREATE TEMP TABLE tpk (c text PRIMARY KEY);
INSERT INTO tpk VALUES (NULL);
\echo '@@ ordem_null'
SELECT valor FROM resultado WHERE parametro = 'turbidez' GROUP BY valor ORDER BY valor LIMIT 1;
\echo '@@ div_zero_pct'
SELECT 100.0 * 4 / 0;
\echo '@@ nullif_pct'
SELECT 100.0 * 4 / NULLIF(0, 0);
\echo '@@ avg_distinct'
SELECT AVG(DISTINCT v) FROM (SELECT 7.0 AS v UNION ALL SELECT 7.0 UNION ALL SELECT 5.0) AS t;
\echo '@@ right_join'
SELECT COUNT(*) FROM resultado r RIGHT JOIN ponto po ON r.ponto = po.codigo;


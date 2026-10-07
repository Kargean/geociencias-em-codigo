-- Esquema do banco de chuva diária (SQLite).
--
-- Ideias que este arquivo ensina:
--   * cada tabela tem uma CHAVE PRIMÁRIA (identifica a linha);
--   * a CHAVE ESTRANGEIRA liga a medida à estação, e o banco recusa estação que não existe;
--   * CHECK impede dado impossível (chuva negativa, data em formato errado) antes de entrar;
--     armadilha: CHECK só reprova quando a expressão dá FALSO. Se der NULL, o dado PASSA.
--     Por isso a data usa IS (que nunca devolve NULL) em vez de = ;
--   * ausente é NULL, nunca -999. O NULL "não é zero e não é igual a nada";
--   * os TIPOS do SQLite são só sugestões (afinidade): sem proteção, REAL aceita o texto 'abc'. E 'abc' >= 0 é
--     VERDADEIRO (texto compara maior que número), então um CHECK de faixa não pega. Por isso cada coluna numérica
--     exige typeof(...) IN ('real', 'integer'). (Tabelas STRICT, do SQLite 3.37 em diante, fazem isso por você,
--     mas exigiriam uma versão mais nova do que as janelas deste projeto precisam.)
--
-- Cuidado clássico do SQLite: a verificação de chave estrangeira é DESLIGADA por padrão em cada conexão.
-- Por isso chuva/banco.py executa PRAGMA foreign_keys = ON ao conectar.

CREATE TABLE IF NOT EXISTS estacao (
    id          TEXT PRIMARY KEY,
    nome        TEXT NOT NULL,
    lat         REAL NOT NULL CHECK (typeof(lat) IN ('real', 'integer') AND lat BETWEEN -90 AND 90),
    lon         REAL NOT NULL CHECK (typeof(lon) IN ('real', 'integer') AND lon BETWEEN -180 AND 180),
    altitude_m  REAL CHECK (altitude_m IS NULL OR typeof(altitude_m) IN ('real', 'integer')),
    bacia       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chuva_diaria (
    estacao_id  TEXT NOT NULL REFERENCES estacao (id),
    data        TEXT NOT NULL CHECK (date(data) IS data),         -- ISO 8601: AAAA-MM-DD
    chuva_mm    REAL CHECK (chuva_mm IS NULL OR (typeof(chuva_mm) IN ('real', 'integer') AND chuva_mm >= 0)),  -- NULL = sem medida válida
    PRIMARY KEY (estacao_id, data)
);

-- Índice por data: acelera consultas que filtram só pelo período, sem olhar a estação.
CREATE INDEX IF NOT EXISTS idx_chuva_data ON chuva_diaria (data);

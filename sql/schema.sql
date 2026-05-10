DROP TABLE IF EXISTS patent_company_relationships;
DROP TABLE IF EXISTS patent_inventor_relationships;
DROP TABLE IF EXISTS locations;
DROP TABLE IF EXISTS companies;
DROP TABLE IF EXISTS inventors;
DROP TABLE IF EXISTS patents;

CREATE TABLE patents (
    patent_id TEXT PRIMARY KEY,
    title TEXT,
    abstract TEXT,
    filing_date TEXT,
    year INTEGER
);

CREATE TABLE inventors (
    inventor_id TEXT PRIMARY KEY,
    name TEXT,
    gender TEXT,
    location_id TEXT
);

CREATE TABLE companies (
    company_id TEXT PRIMARY KEY,
    name TEXT
);

CREATE TABLE locations (
    location_id TEXT PRIMARY KEY,
    country TEXT,
    state TEXT,
    city TEXT
);

CREATE TABLE patent_company_relationships (
    patent_id TEXT,
    company_id TEXT,
    location_id TEXT,
    PRIMARY KEY (patent_id, company_id, location_id)
);

CREATE TABLE patent_inventor_relationships (
    patent_id TEXT,
    inventor_id TEXT,
    inventor_sequence INTEGER,
    location_id TEXT,
    PRIMARY KEY (patent_id, inventor_id, inventor_sequence)
);

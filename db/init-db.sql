-- PostgreSQL schema for PT Companies

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Companies table (unified data from all sources)
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nif VARCHAR(9) UNIQUE NOT NULL,
    name VARCHAR(500) NOT NULL,
    
    -- Source tracking
    source VARCHAR(50) NOT NULL,  -- 'einforma', 'nif_api', 'nif_search'
    source_url TEXT,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Basic info
    registration_date DATE,
    status VARCHAR(100),
    
    -- Contact info
    phone VARCHAR(50),
    email VARCHAR(255),
    website TEXT,
    fax VARCHAR(50),
    
    -- Address
    address TEXT,
    city VARCHAR(200),
    postal_code VARCHAR(20),
    region VARCHAR(200),
    county VARCHAR(200),
    parish VARCHAR(200),
    
    -- Business classification
    cae VARCHAR(20),
    activity_description TEXT,
    sector VARCHAR(100),  -- Derived sector
    company_nature VARCHAR(200),
    capital DECIMAL(15, 2),
    
    -- Metadata
    enriched_at TIMESTAMP WITH TIME ZONE,
    last_verified_at TIMESTAMP WITH TIME ZONE,
    
    -- Full-text search
    search_vector tsvector
);

-- Indexes for common queries
CREATE INDEX idx_companies_nif ON companies(nif);
CREATE INDEX idx_companies_source ON companies(source);
CREATE INDEX idx_companies_sector ON companies(sector);
CREATE INDEX idx_companies_region ON companies(region);
CREATE INDEX idx_companies_city ON companies(city);
CREATE INDEX idx_companies_registration_date ON companies(registration_date);
CREATE INDEX idx_companies_search ON companies USING gin(search_vector);

-- Trigger to update search vector
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('portuguese', COALESCE(NEW.name, '')), 'A') ||
        setweight(to_tsvector('portuguese', COALESCE(NEW.city, '')), 'B') ||
        setweight(to_tsvector('portuguese', COALESCE(NEW.region, '')), 'C') ||
        setweight(to_tsvector('portuguese', COALESCE(NEW.activity_description, '')), 'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER companies_search_update
    BEFORE INSERT OR UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_search_vector();

-- Enrichment log (track API usage)
CREATE TABLE IF NOT EXISTS enrichment_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nif VARCHAR(9) NOT NULL,
    source VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,  -- 'success', 'not_found', 'rate_limited', 'error'
    error_message TEXT,
    enriched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_enrichment_log_nif ON enrichment_log(nif);
CREATE INDEX idx_enrichment_log_date ON enrichment_log(enriched_at);

-- Rate limiting tracking
CREATE TABLE IF NOT EXISTS rate_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service VARCHAR(50) NOT NULL UNIQUE,
    requests_count INTEGER DEFAULT 0,
    window_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    daily_count INTEGER DEFAULT 0,
    daily_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    monthly_count INTEGER DEFAULT 0,
    monthly_start TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert initial rate limit records
INSERT INTO rate_limits (service) VALUES ('nif_api') ON CONFLICT (service) DO NOTHING;

-- Leads without contact info (companies enriched but no phone/email/website)
CREATE TABLE IF NOT EXISTS leads_without_personal_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nif VARCHAR(9) UNIQUE NOT NULL,
    name VARCHAR(500) NOT NULL,
    source VARCHAR(50) NOT NULL,
    source_url TEXT,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    registration_date DATE,
    status VARCHAR(100),
    phone VARCHAR(50),
    email VARCHAR(255),
    website TEXT,
    fax VARCHAR(50),
    address TEXT,
    city VARCHAR(200),
    postal_code VARCHAR(20),
    region VARCHAR(200),
    county VARCHAR(200),
    parish VARCHAR(200),
    cae VARCHAR(20),
    activity_description TEXT,
    sector VARCHAR(100),
    company_nature VARCHAR(200),
    capital DECIMAL(15, 2),
    enriched_at TIMESTAMP WITH TIME ZONE,
    last_verified_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_leads_nip ON leads_without_personal_data(nif);
CREATE INDEX idx_leads_sector ON leads_without_personal_data(sector);

-- Lead status tracking for outreach pipeline
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'companies' AND column_name = 'lead_status'
    ) THEN
        ALTER TABLE companies ADD COLUMN lead_status VARCHAR(50) DEFAULT 'new';
        ALTER TABLE companies ADD COLUMN lead_notes TEXT;
        ALTER TABLE companies ADD COLUMN last_contacted_at TIMESTAMP WITH TIME ZONE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_companies_lead_status ON companies(lead_status);
CREATE INDEX IF NOT EXISTS idx_companies_phone ON companies(phone) WHERE phone IS NOT NULL;

-- Views for dashboard
CREATE OR REPLACE VIEW vw_companies_enriched AS
SELECT 
    id, nif, name, phone, email, website,
    address, city, postal_code, region, county,
    cae, activity_description, sector, status,
    registration_date, enriched_at
FROM companies
WHERE source IN ('nif_api', 'einforma')
  AND phone IS NOT NULL OR email IS NOT NULL OR website IS NOT NULL;

CREATE OR REPLACE VIEW vw_companies_by_sector AS
SELECT 
    sector,
    COUNT(*) as total,
    COUNT(phone) as with_phone,
    COUNT(email) as with_email,
    COUNT(website) as with_website
FROM companies
GROUP BY sector
ORDER BY total DESC;

CREATE OR REPLACE VIEW vw_companies_by_region AS
SELECT 
    region,
    COUNT(*) as total
FROM companies
WHERE region IS NOT NULL
GROUP BY region
ORDER BY total DESC;

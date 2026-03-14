# Portugal Company Data Enrichment Sources

## Overview of Available Data Sources for Company Information (2022-2025)

---

## 🆓 FREE / FREEMIUM SOURCES

### 1. NIF.pt API ⭐ (Recommended for Basic Data)

**Website:** https://www.nif.pt/api/

**Data Available:**
- ✅ NIF (Tax ID)
- ✅ Company Name
- ✅ Address (full address)
- ✅ Postal Code (PC4 + PC3)
- ✅ City
- ✅ Region, County, Parish
- ✅ Phone Number
- ✅ Email
- ✅ Website
- ✅ Fax
- ✅ Activity Description
- ✅ CAE (Economic Activity Code)
- ✅ Legal Form (Nature)
- ✅ Capital Social
- ✅ Status (Active/Inactive)

**Free Tier:**
- 1,000 queries/month
- 100 queries/day
- 10 queries/hour
- 1 query/minute

**Pricing:**
- €10 per 1,000 additional queries
- Payment via Multibanco or Homebanking

**How to Get API Key:**
1. Visit: https://www.nif.pt/contactos/api/
2. Request API access
3. Receive key via email

**API Example:**
```bash
curl "http://www.nif.pt/?json=1&q=519280458&key=YOUR_KEY"
```

**Pros:**
- ✅ Free tier available
- ✅ No rate limit (within free tier)
- ✅ Real-time data
- ✅ Easy to use

**Cons:**
- ❌ No historical data (only current status)
- ❌ Limited free queries
- ❌ No directors/owners names (only basic structure)

---

## 💰 COMMERCIAL APIs (PAID)

### 2. HitHorizons API

**Website:** https://www.hithorizons.com/services/api

**Data Available:**
- ✅ Company Name & Registration Number
- ✅ Full Address
- ✅ Phone & Email (limited)
- ✅ Website
- ✅ Industry Classification (NACE/SIC)
- ✅ **Year of Establishment** (can filter by 2022-2025)
- ✅ Company Type
- ✅ Sales/Revenue (3 years)
- ✅ Employee Count
- ✅ Directors/Managers
- ✅ Shareholders
- ✅ Group Structure
- ✅ Social Media Links

**Coverage:** 823,000+ Portuguese companies

**Pricing:** Contact for quote (typically €€€)

**API Features:**
- Screener API (filter by incorporation date)
- Sales & Marketing Data API
- Invoicing Data API

**Pros:**
- ✅ Filter by incorporation year (2022-2025)
- ✅ Comprehensive financial data
- ✅ Director/Shareholder information
- ✅ European coverage

**Cons:**
- ❌ Expensive
- ❌ Requires contract

---

### 3. GlobalDatabase API

**Website:** https://www.globaldatabase.com/api

**Data Available:**
- ✅ Company Name & NIF
- ✅ Full Address
- ✅ **Phone Numbers (Direct)**
- ✅ **Email Addresses (Verified)**
- ✅ Website
- ✅ **Directors & Key Decision Makers**
- ✅ **Manager Names & Functions**
- ✅ Financial Data (5 years)
- ✅ Employee Count
- ✅ Revenue
- ✅ Industry Classification
- ✅ Technology Stack

**Coverage:** 729,435 Portuguese companies

**Pricing:** 
- Contact for quote
- Typically €200-500/month for API access

**Pros:**
- ✅ Direct contact information
- ✅ Key decision makers with titles
- ✅ Verified emails
- ✅ 5 years financial history
- ✅ Technology insights

**Cons:**
- ❌ Expensive
- ❌ No free trial

---

### 4. BoldData (CompanyData.com)

**Website:** https://datarade.ai/data-products/business-data-portugal

**Data Available:**
- ✅ Company Names & Legal Forms
- ✅ Registration Numbers
- ✅ **Contact Information (Verified Emails, Phones, Mobiles)**
- ✅ **Executive & Decision-Maker Details**
- ✅ Industry Codes (NACE)
- ✅ Revenue
- ✅ Employee Count
- ✅ **Founding Year** (filter by 2022-2025)
- ✅ Company Status
- ✅ Group Structures

**Coverage:** 831,000+ Portuguese companies

**Pricing:** 
- Per-record pricing or subscription
- Contact for quote

**Pros:**
- ✅ Verified contact data
- ✅ Mobile phone numbers
- ✅ Decision-maker details
- ✅ Can filter by founding year

**Cons:**
- ❌ No free tier
- ❌ Requires commitment

---

### 5. Iberinform (Atradius Group)

**Website:** https://datarade.ai/data-products/database-from-portugal-and-or-spain-iberinform

**Data Available:**
- ✅ TaxID / VAT No.
- ✅ Name
- ✅ Address, Locality, Zip Code
- ✅ District, Municipality
- ✅ Phone, Fax, Email, Website
- ✅ Economic Activities Classification
- ✅ Legal Form
- ✅ **Date of Incorporation** (2022-2025)
- ✅ **Key Manager**
- ✅ **Name of Managers + Functions**
- ✅ **Name of Directors 1st Line + Functions**
- ✅ Import/Export Countries
- ✅ Stock Capital
- ✅ Number of Employees
- ✅ Turnover

**Coverage:** Portugal + Spain

**Pricing:** Contact for quote

**Pros:**
- ✅ Very comprehensive management data
- ✅ Director names with functions
- ✅ Import/Export information
- ✅ Part of Atradius (credit insurance)

**Cons:**
- ❌ Expensive
- ❌ Focus on Iberia only

---

### 6. Info-Clipper

**Website:** https://www.info-clipper.com/en/company/search/portugal.pt.html

**Data Available:**
- ✅ Company Registration Data
- ✅ Financial Performance
- ✅ Credit Rating
- ✅ **Directors Information**
- ✅ **Shareholders**
- ✅ Corporate Trees

**Pricing:** Per-report or subscription

**Pros:**
- ✅ Credit ratings included
- ✅ Corporate structure
- ✅ Shareholder information

**Cons:**
- ❌ Limited API access
- ❌ Mostly manual lookup

---

## 🏛️ GOVERNMENT SOURCES

### 7. RNPC - Registo Nacional de Pessoas Coletivas

**Website:** https://www.rnpc.mjustica.gov.pt/

**Data Available:**
- ✅ Company Name
- ✅ NIF
- ✅ Legal Form
- ✅ Registration Date
- ✅ Address
- ❌ No phone/email directly
- ❌ No director names directly

**Access:** 
- Free public access (limited)
- Paid certificates with full data

**Pros:**
- ✅ Official source
- ✅ Most accurate
- ✅ Free basic access

**Cons:**
- ❌ Limited programmatic access
- ❌ No contact details
- ❌ Manual process for detailed info

---

### 8. Portal das Finanças

**Website:** https://www.portaldasfinancas.gov.pt/

**Data Available:**
- ✅ NIF Validation
- ✅ Basic company info
- ✅ Tax status

**Access:** Requires authentication

**Pros:**
- ✅ Official tax authority data
- ✅ Free

**Cons:**
- ❌ Very limited API
- ❌ Requires authentication
- ❌ No bulk access

---

## 📊 COMPARISON TABLE

| Source | Free Tier | Directors | Phone | Email | Historical | API | Cost |
|--------|-----------|-----------|-------|-------|------------|-----|------|
| **NIF.pt** | ✅ 1K/mo | ❌ | ✅ | ✅ | ❌ | ✅ | €10/1K |
| **HitHorizons** | ❌ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | €€€ |
| **GlobalDatabase** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | €€€ |
| **BoldData** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | €€ |
| **Iberinform** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | €€€ |
| **RNPC** | ✅ | ❌ | ❌ | ❌ | ✅ | ⚠️ | Free |

---

## 🎯 RECOMMENDATIONS

### For FREE / Low Budget:
1. **NIF.pt API** - Best free option
   - Get API key: https://www.nif.pt/contactos/api/
   - 1,000 free queries/month
   - Provides: address, phone, email, activity, capital
   - No directors/owners

### For HISTORICAL DATA (2022-2025):
1. **HitHorizons** - Filter by incorporation year
2. **BoldData** - Founding year filter
3. **GlobalDatabase** - 5 years financial history

### For DIRECT CONTACT INFO:
1. **GlobalDatabase** - Verified emails & phones
2. **BoldData** - Mobile numbers
3. **Iberinform** - Key managers with functions

### For DIRECTORS/OWNERS:
1. **GlobalDatabase** - Best coverage
2. **Iberinform** - Detailed functions
3. **HitHorizons** - Shareholders included

---

## 💡 RECOMMENDED APPROACH

### Phase 1: Free Enrichment
1. Get NIF.pt API key
2. Enrich your 400+ companies with:
   - Full address
   - Phone
   - Email
   - Website
   - Activity details

### Phase 2: Paid Enrichment (if needed)
1. Identify high-value leads (70+ score)
2. Use GlobalDatabase or BoldData for:
   - Director names
   - Direct contact info
   - Financial data

### Phase 3: Historical Data
1. Use HitHorizons Screener API
2. Filter by incorporation date: 2022-01-01 to 2025-12-31
3. Export full dataset

---

## 📝 NEXT STEPS

1. **Request NIF.pt API Key**
   - Visit: https://www.nif.pt/contactos/api/
   - Fill form
   - Receive key within 24-48h

2. **Test Free API**
   - I can integrate NIF.pt into your scraper
   - Enrich all 400 companies with contact info

3. **Evaluate Paid Options**
   - Contact GlobalDatabase for trial
   - Compare pricing with HitHorizons

4. **Decision Time**
   - Free tier: NIF.pt only
   - Paid tier: Choose based on budget and needs

---

## 📞 CONTACT INFO FOR APIS

- **NIF.pt:** https://www.nif.pt/contactos/api/
- **HitHorizons:** https://www.hithorizons.com/contact
- **GlobalDatabase:** https://www.globaldatabase.com/contact
- **BoldData:** https://www.bolddata.nl/contact/
- **Iberinform:** Contact via Datarade

---

**Generated:** 2026-03-05
**For:** Portugal New Companies Tracker Project

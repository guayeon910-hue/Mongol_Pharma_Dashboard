-- =============================================================================
-- MN (몽골) 전용 테이블 (Supabase SQL Editor에서 한 번 실행)
-- =============================================================================

-- 1. 몽골 약가 수집 결과 (3계층 크롤링 통합)
create table if not exists mn_pricing (
  id                      uuid primary key default gen_random_uuid(),
  created_at              timestamptz not null default now(),

  -- 성분·제품
  inn_name                text not null,
  drug_name               text,
  brand_name              text,
  strength                text,
  dosage_form             text,
  pack_size               int,

  -- 가격 (MNT 및 USD)
  price_mnt               decimal(14,2),
  price_usd               decimal(12,6),
  hif_reimbursement_mnt   decimal(14,2),
  copayment_mnt           decimal(14,2),

  -- 공급망
  manufacturer            text,
  importer                text,

  -- 인허가
  registration_no         text,
  expiry_date             date,
  is_essential            boolean default false,

  -- 소스
  source_site             text check (source_site in (
    'licemed', 'emd_pricing', 'emd_pharmacy',
    'tender_gov_mn', 'tender_gov_mn_html',
    'mmra', 'monos', 'meic', 'gobigate', 'lenusmed', 'manual'
  )),
  source_url              text,
  file_url                text,
  raw_text                text,
  confidence              decimal(3,2) check (confidence between 0.0 and 1.0),
  fob_estimated_usd       decimal(12,6)
);

-- 2. Licemed 경쟁 의약품 등록 현황
create table if not exists mn_licemed_registry (
  id                uuid primary key default gen_random_uuid(),
  crawled_at        timestamptz not null default now(),
  inn_name          text not null,
  brand_name        text,
  dosage_form       text,
  strength          text,
  registration_no   text unique,
  expiry_date       date,
  manufacturer      text,
  importer          text,
  is_essential      boolean default false,
  spc_text          text,
  source_url        text
);

-- 3. 입찰 낙찰 결과
create table if not exists mn_tender_awards (
  id                    uuid primary key default gen_random_uuid(),
  crawled_at            timestamptz not null default now(),
  tender_id             text,
  title                 text,
  purchaser             text,
  inn_name              text,
  keyword               text,
  deadline              text,
  bid_security_mnt      decimal(16,2),
  vendor_name           text,
  contract_amount_mnt   decimal(16,2),
  contract_amount_usd   decimal(14,2),
  award_date            text,
  status                text,
  source_url            text
);

-- 4. 유통사 파트너 점수
create table if not exists mn_partner_scores (
  id                  uuid primary key default gen_random_uuid(),
  scored_at           timestamptz not null default now(),
  distributor_id      text not null,
  distributor_name    text,
  url                 text,
  covered_inns        jsonb default '[]'::jsonb,
  missing_inns        jsonb default '[]'::jsonb,
  whitespace_count    int default 0,
  tender_wins         int default 0,
  partner_score       int default 0
);

-- 5. MMRA 규제 공시
create table if not exists mn_mmra_notices (
  id            uuid primary key default gen_random_uuid(),
  crawled_at    timestamptz not null default now(),
  title         text,
  link          text,
  date          text,
  category      text check (category in ('legislation', 'safety', 'advertising', 'approval', 'general')),
  matched_inn   text,
  attachments   jsonb default '[]'::jsonb,
  raw_text      text,
  source_url    text
);

-- =============================================================================
-- 인덱스
-- =============================================================================
create index if not exists idx_mn_pricing_inn        on mn_pricing(inn_name);
create index if not exists idx_mn_pricing_source     on mn_pricing(source_site);
create index if not exists idx_mn_pricing_created    on mn_pricing(created_at desc);
create index if not exists idx_mn_pricing_expiry     on mn_pricing(expiry_date);
create index if not exists idx_mn_licemed_inn        on mn_licemed_registry(inn_name);
create index if not exists idx_mn_licemed_expiry     on mn_licemed_registry(expiry_date);
create index if not exists idx_mn_tender_inn         on mn_tender_awards(inn_name);
create index if not exists idx_mn_tender_vendor      on mn_tender_awards(vendor_name);
create index if not exists idx_mn_notices_inn        on mn_mmra_notices(matched_inn);
create index if not exists idx_mn_notices_category   on mn_mmra_notices(category);

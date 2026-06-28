select
    provider,
    campaign_id,
    campaign_name,
    channel,
    country,
    date,
    impressions,
    clicks,
    spend,
    date_trunc('month', date) as month
from {{ ref('stg_ads') }}

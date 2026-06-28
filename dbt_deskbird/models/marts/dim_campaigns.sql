select distinct
    provider,
    campaign_id,
    campaign_name,
    channel,
    country
from {{ ref('stg_ads') }}

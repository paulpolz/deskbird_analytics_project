select
    provider,
    campaign_id,
    campaign_name,
    channel,
    country,
    cast(date as date) as date,
    impressions,
    clicks,
    spend
from {{ source('raw', 'ads_campaign_daily') }}

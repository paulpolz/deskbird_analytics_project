select
    lead_id,
    utm_source as provider,
    utm_campaign as campaign_id,
    channel,
    country,
    segment,
    cast(created_at as timestamp) as created_at
from {{ source('raw', 'crm_leads') }}

select
    l.lead_id,
    l.provider,
    l.campaign_id,
    l.channel,
    l.country,
    l.created_at,
    date_trunc('month', l.created_at) as lead_month
from {{ ref('stg_crm_leads') }} l

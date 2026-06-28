select
    funnel_event_id,
    lead_id,
    stage,
    cast(entered_at as timestamp) as entered_at
from {{ source('raw', 'crm_opportunity_funnel') }}

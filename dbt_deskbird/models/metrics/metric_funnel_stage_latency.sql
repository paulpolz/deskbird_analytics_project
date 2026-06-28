select
    lead_id,
    channel,
    country,
    segment,
    date_trunc('month', created_at) as lead_month,
    outcome,
    lead_to_call_days,
    lead_to_demo_days,
    lead_to_proposal_days
from {{ ref('fct_lead_journey') }}

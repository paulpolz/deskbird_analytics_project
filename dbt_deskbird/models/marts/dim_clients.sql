select
    w.client_id,
    w.lead_id,
    w.contract_start_date,
    w.contract_end_date,
    w.contract_length_months,
    w.seats,
    w.additional_services,
    w.market,
    l.segment,
    w.has_analytics_addon,
    l.channel,
    l.provider,
    l.campaign_id,
    l.country
from {{ ref('stg_crm_wins') }} w
left join {{ ref('stg_crm_leads') }} l on w.lead_id = l.lead_id

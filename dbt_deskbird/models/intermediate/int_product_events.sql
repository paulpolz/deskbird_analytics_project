select
    p.*,
    w.seats,
    l.segment,
    w.has_analytics_addon,
    w.contract_start_date,
    w.contract_end_date
from {{ ref('stg_product_events') }} p
inner join {{ ref('stg_crm_wins') }} w on p.client_id = w.client_id
inner join {{ ref('stg_crm_leads') }} l on w.lead_id = l.lead_id

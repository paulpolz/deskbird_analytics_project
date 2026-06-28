select
    l.lead_id,
    l.provider,
    l.campaign_id,
    l.channel,
    l.country,
    l.created_at,
    f.call_at,
    f.demo_at,
    f.proposal_at,
    f.won_at,
    f.lost_at,
    f.terminal_stage,
    f.call_to_demo_days,
    f.demo_sla_breached,
    case
        when f.terminal_stage = 'won' then 'win'
        when f.terminal_stage = 'lost' then 'loss'
        else 'open'
    end as outcome,
    case
        when f.call_at is not null
        then date_diff('day', l.created_at, f.call_at)
    end as lead_to_call_days,
    case
        when f.demo_at is not null
        then date_diff('day', l.created_at, f.demo_at)
    end as lead_to_demo_days,
    case
        when f.proposal_at is not null
        then date_diff('day', l.created_at, f.proposal_at)
    end as lead_to_proposal_days,
    w.client_id,
    w.contract_start_date,
    w.seats,
    l.segment,
    w.market,
    w.has_analytics_addon,
    case when f.call_at is not null then true else false end as entered_funnel
from {{ ref('stg_crm_leads') }} l
left join {{ ref('int_funnel_events') }} f on l.lead_id = f.lead_id
left join {{ ref('stg_crm_wins') }} w on l.lead_id = w.lead_id

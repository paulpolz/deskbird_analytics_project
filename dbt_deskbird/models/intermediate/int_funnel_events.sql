with events as (
    select * from {{ ref('stg_crm_funnel') }}
),
pivoted as (
    select
        lead_id,
        min(case when stage = 'call' then entered_at end) as call_at,
        min(case when stage = 'demo' then entered_at end) as demo_at,
        min(case when stage = 'proposal' then entered_at end) as proposal_at,
        min(case when stage = 'won' then entered_at end) as won_at,
        min(case when stage = 'lost' then entered_at end) as lost_at,
        max(case when stage in ('won', 'lost') then stage end) as terminal_stage,
        max(entered_at) as last_event_at
    from events
    group by lead_id
)
select
    *,
    case
        when call_at is not null and demo_at is not null
        then date_diff('day', call_at, demo_at)
    end as call_to_demo_days,
    case
        when call_at is not null and demo_at is null
             and date_diff('day', call_at, current_timestamp) > {{ var('demo_sla_days') }}
        then true
        when call_at is not null and demo_at is not null
             and date_diff('day', call_at, demo_at) > {{ var('demo_sla_days') }}
        then true
        else false
    end as demo_sla_breached
from pivoted

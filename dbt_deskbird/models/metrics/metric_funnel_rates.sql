with ad_clicks as (
    select
        month,
        channel,
        country,
        sum(clicks) as clicks
    from {{ ref('int_campaign_spend') }}
    group by 1, 2, 3
),
lead_stages as (
    select
        date_trunc('month', created_at) as month,
        channel,
        country,
        segment,
        count(distinct lead_id) as leads,
        count(distinct case when call_at is not null then lead_id end) as calls,
        count(distinct case when demo_at is not null then lead_id end) as demos,
        count(distinct case when proposal_at is not null then lead_id end) as proposals,
        count(distinct case when terminal_stage = 'won' then lead_id end) as wins,
        count(distinct case when terminal_stage = 'lost' and proposal_at is not null then lead_id end) as losses
    from {{ ref('fct_lead_journey') }}
    group by 1, 2, 3, 4
)
select
    l.month,
    l.channel,
    l.country,
    l.segment,
    coalesce(a.clicks, 0) as clicks,
    l.leads,
    l.calls,
    l.demos,
    l.proposals,
    l.wins,
    l.losses,
    l.leads::double / nullif(a.clicks, 0) as lead_to_funnel_rate,
    l.calls::double / nullif(l.leads, 0) as call_rate,
    l.demos::double / nullif(l.calls, 0) as demo_rate,
    l.proposals::double / nullif(l.demos, 0) as proposal_rate,
    l.wins::double / nullif(l.proposals, 0) as win_rate,
    l.losses::double / nullif(l.proposals, 0) as loss_rate
from lead_stages l
left join ad_clicks a
    on l.month = a.month
    and l.channel = a.channel
    and l.country = a.country

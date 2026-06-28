with spend as (
    select
        provider,
        campaign_id,
        channel,
        country,
        month,
        sum(spend) as total_spend
    from {{ ref('int_campaign_spend') }}
    group by 1, 2, 3, 4, 5
),
wins as (
    select
        provider,
        campaign_id,
        channel,
        country,
        date_trunc('month', won_at) as month,
        count(distinct client_id) as won_clients
    from {{ ref('fct_lead_journey') }}
    where terminal_stage = 'won'
    group by 1, 2, 3, 4, 5
)
select
    s.provider,
    s.campaign_id,
    s.channel,
    s.country,
    s.month,
    s.total_spend,
    coalesce(w.won_clients, 0) as won_clients,
    case
        when coalesce(w.won_clients, 0) > 0
        then s.total_spend / w.won_clients
    end as cac
from spend s
left join wins w
    on s.provider = w.provider
    and s.campaign_id = w.campaign_id
    and s.country = w.country
    and s.month = w.month

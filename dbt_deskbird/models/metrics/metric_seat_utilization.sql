with snapshots as (
    select
        p.client_id,
        date_trunc('day', p.event_at)::date as day,
        p.seats_active,
        c.seats as contracted_seats,
        c.contract_length_months,
        c.segment,
        c.market,
        c.has_analytics_addon,
        p.seats_active::double / nullif(c.seats, 0) as seat_utilization,
        case
            when c.contract_length_months <= 18 then '12-18 mo'
            when c.contract_length_months <= 24 then '19-24 mo'
            else '25-36 mo'
        end as contract_length_bucket,
        case
            when c.seats < 100 then '<100'
            when c.seats < 200 then '100-199'
            when c.seats < 400 then '200-399'
            else '400+'
        end as seats_bucket
    from {{ ref('int_product_events') }} p
    inner join {{ ref('dim_clients') }} c on p.client_id = c.client_id
    where p.event_type = 'seat_snapshot'
)
select
    client_id,
    day,
    segment,
    market,
    has_analytics_addon,
    contract_length_months,
    contracted_seats,
    contract_length_bucket,
    seats_bucket,
    avg(seat_utilization) as avg_seat_utilization
from snapshots
group by 1, 2, 3, 4, 5, 6, 7, 8, 9

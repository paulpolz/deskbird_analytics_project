with events as (
    select
        date_trunc('month', p.event_at)::date as month,
        p.user_id,
        p.event_type,
        p.feature_name,
        c.segment,
        c.has_analytics_addon,
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
    where p.event_type in ('login', 'feature_adopted')
),
login_counts as (
    select
        month,
        segment,
        has_analytics_addon,
        contract_length_bucket,
        seats_bucket,
        count(distinct user_id) as login_users
    from events
    where event_type = 'login'
    group by 1, 2, 3, 4, 5
),
feature_adoptions as (
    select
        month,
        segment,
        has_analytics_addon,
        contract_length_bucket,
        seats_bucket,
        feature_name,
        count(distinct user_id) as adopt_users
    from events
    where event_type = 'feature_adopted'
    group by 1, 2, 3, 4, 5, 6
)
select
    f.month,
    f.segment,
    f.has_analytics_addon,
    f.contract_length_bucket,
    f.seats_bucket,
    f.feature_name,
    l.login_users,
    f.adopt_users,
    f.adopt_users::double / nullif(l.login_users, 0) as feature_adoption_rate
from feature_adoptions f
inner join login_counts l
    on f.month = l.month
    and f.segment = l.segment
    and f.has_analytics_addon = l.has_analytics_addon
    and f.contract_length_bucket = l.contract_length_bucket
    and f.seats_bucket = l.seats_bucket

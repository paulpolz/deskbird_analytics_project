with date_spine as (
    select unnest(generate_series(
        (select min(date) from {{ ref('stg_ads') }}),
        (select max(date) from {{ ref('stg_ads') }}),
        interval '1 day'
    ))::date as date
)
select
    date,
    date_trunc('week', date) as week,
    date_trunc('month', date) as month,
    extract(year from date) as year,
    extract(month from date) as month_num
from date_spine

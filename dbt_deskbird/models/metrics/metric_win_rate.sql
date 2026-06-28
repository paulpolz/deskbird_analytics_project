select
    month,
    channel,
    country,
    segment,
    wins,
    losses,
    proposals,
    wins::double / nullif(proposals, 0) as win_rate,
    losses::double / nullif(proposals, 0) as loss_rate
from {{ ref('metric_funnel_rates') }}
where proposals > 0

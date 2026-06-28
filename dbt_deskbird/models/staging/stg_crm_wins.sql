select
    client_id,
    lead_id,
    cast(contract_start_date as date) as contract_start_date,
    cast(contract_end_date as date) as contract_end_date,
    contract_length_months,
    seats,
    additional_services,
    market,
    case when position('analytics' in additional_services) > 0 then true else false end as has_analytics_addon
from {{ source('raw', 'crm_wins') }}

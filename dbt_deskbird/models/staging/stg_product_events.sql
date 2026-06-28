select
    event_id,
    client_id,
    user_id,
    event_type,
    cast(event_at as timestamp) as event_at,
    seats_active,
    feature_name
from {{ source('raw', 'product_events') }}

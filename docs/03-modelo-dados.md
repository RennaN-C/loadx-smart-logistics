# Modelo de dados inicial

## Entidades do MVP

### users

- id
- name
- email
- password_hash
- role
- active
- created_at

### customers

- id
- name
- document
- phone
- address
- city
- state
- created_at

### drivers

- id
- name
- phone
- license_number
- active
- created_at

### trucks

- id
- plate
- model
- internal_width_cm
- internal_height_cm
- internal_length_cm
- max_weight_kg
- active
- created_at

### products

- id
- code
- name
- width_cm
- height_cm
- length_cm
- weight_kg
- fragile
- stackable
- rotation_allowed
- created_at

### orders

- id
- customer_id
- status
- priority
- delivery_address
- expected_delivery_at
- created_at

### order_items

- id
- order_id
- product_id
- quantity
- delivery_sequence

### load_plans

- id
- truck_id
- status
- occupancy_percent
- total_weight_kg
- loaded_count
- unloaded_count
- algorithm_version
- created_at
- approved_at

### load_plan_orders

- load_plan_id
- order_id

### load_plan_items

- id
- load_plan_id
- order_item_id
- volume_index
- position_x_cm
- position_y_cm
- position_z_cm
- used_width_cm
- used_height_cm
- used_length_cm
- rotation_code
- loading_sequence
- placed
- rejection_reason

### loading_sessions

- id
- load_plan_id
- status
- started_at
- finished_at

### trips

- id
- load_plan_id
- driver_id
- status
- started_at
- finished_at

### deliveries

- id
- trip_id
- order_id
- status
- sequence
- delivered_at

### occurrences

- id
- trip_id
- delivery_id
- type
- description
- photo_url
- created_at

### status_history

- id
- entity_type
- entity_id
- old_status
- new_status
- changed_by
- created_at

## Relacionamentos principais

- customer 1:N orders
- order 1:N order_items
- product 1:N order_items
- truck 1:N load_plans
- load_plan N:N orders
- load_plan 1:N load_plan_items
- load_plan 1:1 loading_session
- load_plan 1:1 trip
- trip 1:N deliveries
- trip 1:N occurrences

## Observação

O modelo é inicial. Qualquer mudança estrutural deve ser registrada por migration e documentada em uma ADR quando alterar uma decisão relevante.

# Data dictionary and assumptions

The public demo contains entirely synthetic 2025 property-portfolio data. It is safe to share and does not represent any client or real property.

| Table | Field | Meaning |
|---|---|---|
| `properties` | `property_id` | Stable numeric entity identifier |
| `properties` | `property_name`, `market`, `property_type`, `bedrooms` | Synthetic property descriptors |
| `monthly_performance` | `month` | First day of the monthly reporting period (`YYYY-MM-01`) |
| `monthly_performance` | `available_nights`, `booked_nights` | Inventory available and occupied in that month |
| `monthly_performance` | `revenue`, `operating_cost` | USD revenue and direct operating cost |
| `monthly_performance` | `bookings`, `cancellations` | Count of completed booking records and cancellations |

## KPI definitions

- Occupancy = booked nights / available nights
- ADR = revenue / booked nights
- RevPAR = revenue / available nights
- Contribution margin = revenue - operating cost
- Cancellation rate = cancellations / bookings

The data contains intentionally varied patterns: Property 7 has low occupancy with comparatively stable pricing, Property 4 improves later in the year, and Property 8 has elevated cancellations. It does not contain channel, guest-satisfaction, traffic, conversion, or causal operational data.

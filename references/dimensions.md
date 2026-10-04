# Comparable dimensions

Use the same field names, units and evidence rules for the focal company and competitors. Package v1.1 defines 12 standard dimensions. Every competitor gets one explicit state per dimension. Keep values and their finding references in frontmatter; prose is context, not an analytics source.

| Dimension | Research targets |
| --- | --- |
| identity | brand/company name, canonical domain, company type, stated target customer |
| description | factual 1-3 sentence description, business model, primary offering and sales model |
| geography | city/region, stated market scope, languages, online/physical/omnichannel scope, branch evidence |
| offering | product/service categories, major lines, options, capabilities and breadth |
| pricing | item/service prices, sampled category ranges, currency, unit, price type, discounts, installments, free-shipping threshold |
| positioning | observed claims and evidence-backed normalized themes |
| customer_experience | shipping, delivery, returns, exchange, warranty, support, consultation, fitting, tracking, after-sales, appointment |
| sales_channels | ecommerce, physical_store, instagram_social, marketplace, phone, messaging, b2b, online_appointment, in_person |
| digital_presence | ecommerce, mobile_app, virtual_try_on, prescription_upload, online_consultation, online_booking, blog_content, guides, product_filters, online_support, social_presence |
| trust | warranty, return_policy, guarantee, professional_credentials, certifications, physical_presence, review_mechanism, expert_claim, optometry_presence |
| promotions | percentage_discount, fixed_discount, coupon, bundle, loyalty, referral, free_shipping, installments, seasonal_campaign |
| physical_presence | observed locations, branches and cities; state `observed` or `unknown`, never infer national coverage from one store |

## Dimension states

- `SUPPORTED`: credible finding(s) support the dimension.
- `PARTIAL`: useful evidence exists, with a stated limitation.
- `SEARCHED_UNKNOWN`: targeted searches were logged, but no reliable finding was established.
- `NOT_RESEARCHED`: no meaningful attempt was made; document why.
- `RESTRICTED`: source/access restrictions prevented meaningful research; cite the restriction record and reason.

Do not treat a blank as an outcome. A source restriction does not invalidate the competitor; seek other permitted sources. An attempt can end `SEARCHED_UNKNOWN`. Never mark a capability absent unless an explicit, scoped observation supports absence.

## Eyewear taxonomy

Products may use: `prescription_frames`, `sunglasses`, `optical_frames`, `blue_light_glasses`, `contact_lenses`, `optical_lenses`, `children_eyewear`, `sports_eyewear`, `reading_glasses`, `accessories`.

Services may use: `eye_exam`, `optometry`, `prescription_service`, `prescription_upload`, `frame_fitting`, `lens_fitting`, `repair`, `customization`, `consultation`, `virtual_try_on`.

Record only supported items. Each product, service, theme, channel, digital capability, trust signal and experience capability is a structured entry with finding IDs. Do not encode unobserved items as `false`.

Positioning themes: `affordability`, `premium`, `fashion_design`, `medical_expertise`, `quality`, `variety`, `convenience`, `speed`, `customization`, `digital_convenience`, `physical_expertise`, `family`, `children`, `professional_optics`. Treat these as labels for observed company claims, not analyst-assigned personalities.

## Prices and derived measures

Each price observation preserves the displayed denomination and includes category, item/service, amount or amount_min/amount_max, currency, unit, price type, promotion state, observation time, source IDs and linked finding IDs. Ranges require separate scalar money findings for each endpoint. Do not convert currencies silently: for Iranian prices displayed in toman, preserve the numeric toman value with `currency: IRR` and `unit: toman`; never multiply by ten. A price summary is grouped by category, currency and unit. With ranges, minimum is the lowest lower bound, maximum the highest upper bound, median is the median of each item's midpoint, and count is the number of distinct item/service observations. Include every input finding ID, exact formula and sampling limitations. No price observation means unknown, not zero. Relative price indexes require a matched basket, currency, unit, period and an explicit missing-item rule.

Coverage percentage is `(SUPPORTED + PARTIAL) / applicable_dimensions * 100`. Research-attempt percentage is `(all states except NOT_RESEARCHED) / applicable_dimensions * 100`. Publish exact state counts too. These measures describe evidence coverage, not competitor quality or market completeness.

Derived breadth counts and similarity inputs must name their formula, inputs and limitations. Similarity may use only transparently defined category, channel, service or price-position overlap. Never produce an opaque overall competitor score, winner, site-derived market share, traffic estimate or revenue estimate.

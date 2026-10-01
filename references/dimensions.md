# Comparable dimensions

Use identical field keys and units across company and competitors. Null is unknown, never false or zero. Unobserved features are not absent; explicit support is needed for absence. Define extensions in `RUN.md.extension_dimensions`, preferably industry_<name>.

| Dimension | Fields to consider |
| --- | --- |
| identity | brand_name, canonical_domain, geographies, company_type, stated_target_customer |
| offering | category, product_line, variant, capability, offering_breadth |
| pricing | visible_price, tier_price, price_range_min/max, billing_period, free_trial, free_tier, installment_terms |
| positioning | headline_claim, value_proposition, claimed_differentiator, audience_language, claimed_price_position |
| experience | shipping_terms, delivery_time, return_terms, warranty_terms, support_channel, consultation, booking, customization |
| channels | ecommerce, physical_store, marketplace, b2b, app, other_channel |
| digital | website_section, resource_type, public_social_url, public_app_url, conversion_mechanism |
| trust | guarantee, stated_certification, company_published_testimonial, company_published_review |
| promotions | discount_mechanism, bundle, loyalty, referral, seasonal_campaign |

Company-published testimonials are not independent satisfaction evidence. Certifications remain stated claims until verified. Observe conversion availability without forms, uploads, bookings or support contact.

Relevant eyewear extensions: prescription, sunglasses, blue-light, children, lenses/options, frame materials, virtual try-on, face-shape guidance, prescription-upload availability, gender positioning, physical fitting and optical services. Never submit medical/customer information. Other industries choose publicly observable extensions.

Money retains original text, currency, tax/shipping context, variant, availability and period. Explicit toman prices normalize to IRR by multiplying by 10 with a recorded rule; ambiguous currency remains unknown. Currency conversion needs a dated public rate source and formula. Compare separate currencies otherwise. Ranges describe observed samples, not entire catalogs.

Derived metrics document field_key, entity_id, value, unit, formula, inputs (finding IDs), limitations. Examples: distinct observed category/channel/service/promotion counts; supported dimensions / planned applicable dimensions. Explain denominators and sampled pages. Relative price indexes require matched basket, currency/unit/period and missing-item rule. No overall score/winner or site-derived market share.

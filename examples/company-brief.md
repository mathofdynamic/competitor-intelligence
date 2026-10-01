# Illustrative company input

This is a fictional brief, not permission to research DIDAR or assert facts about example.com.

```text
Use $competitor-intelligence.
Company name: Example Optics
Website: https://example.com
Description: online retail prescription frames and sunglasses
Industry: eyewear retail
Products/services: frames, sunglasses; optical-service availability unknown
Target customers: adults buying online
Geography: Iran
Languages: Persian; English discovery where useful
Channels: ecommerce; physical stores unknown
Price position: unknown
Known competitors: none supplied
Goals: compare offerings, visible prices, returns and digital purchase mechanisms
Include: consumer eyewear retailers serving the target geography
Exclude: wholesale-only suppliers and unrelated reference brands
Budget: 20 credible subjects, 12 pages per subject, 90 minutes total
Output directory: ./research/example-optics/
Previous package: none
ZIP: yes
```

Normalize provenance, discover identities, research, compare and validate without additional stage prompts. Tool availability and safe public access constrain coverage. The receiving application/human approves evidence later.

To inspect a complete synthetic package without network activity, run from the skill directory:

```text
python -c "import sys; from pathlib import Path; sys.path.insert(0, 'tests'); from package_factory import make_package; make_package(Path('/your/new/output/competitor-intelligence-package'))"
```

Replace the output path with a new local directory outside the skill. The fixture factory is for testing only; it must never replace real research or be uploaded as real competitor evidence.

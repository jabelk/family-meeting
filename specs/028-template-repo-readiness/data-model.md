# Data Model: Template Repo Readiness

## Family Config Schema (`config/family.yaml`)

### Top-Level Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `bot` | object | Yes | Assistant identity and behavior |
| `family` | object | Yes | Family structure and identity |
| `preferences` | object | No | Family preferences (grocery, recipes, diet) |
| `calendar` | object | No | Calendar-specific configuration |
| `childcare` | object | No | Childcare detection configuration |

### `bot` Object

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | Assistant display name (e.g., "Mom Bot") |
| `welcome_message` | string | No | Auto-generated | Welcome message for new users |

### `family` Object

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | Family display name (e.g., "The Belk Family") |
| `timezone` | string | Yes | — | IANA timezone (e.g., "America/Los_Angeles") |
| `location` | string | No | "" | City/region for context (e.g., "Reno, NV") |
| `partners` | list[Partner] | Yes | — | Adult family members (1-4) |
| `children` | list[Child] | No | [] | Children in the family |
| `caregivers` | list[Caregiver] | No | [] | Non-partner caregivers (grandparents, nannies) |

### `Partner` Object

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | First name |
| `role` | string | No | "partner" | Role label |
| `work` | string | No | "" | Work description for context (e.g., "works from home at Cisco") |
| `has_work_calendar` | bool | No | false | Whether this partner has a separate work calendar |

### `Child` Object

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | First name |
| `age` | int | Yes | — | Current age |
| `details` | string | No | "" | School, activities, etc. (e.g., "kindergarten at Roy Gomm, M-F") |

### `Caregiver` Object

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | Display name |
| `role` | string | No | "caregiver" | Relationship (e.g., "grandma", "nanny") |
| `keywords` | list[string] | No | [lowercase name] | Keywords for childcare detection in calendar events |

### `preferences` Object

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `grocery_store` | string | No | "grocery store" | Preferred grocery store name |
| `recipe_source` | string | No | "" | External recipe source name (e.g., "Downshiftology") |
| `dietary_restrictions` | list[string] | No | [] | Family dietary restrictions |

### `calendar` Object

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `event_mappings` | dict[string, string] | No | {} | Event name → person association (e.g., "BSF": "Erin") |

### `childcare` Object

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `keywords` | list[string] | No | Auto-generated | Keywords for childcare detection (auto-includes child names + caregiver keywords) |
| `caregiver_mappings` | dict[string, string] | No | Auto-generated | Keyword → display label (e.g., "sandy": "Sandy") |

## Validation Rules

1. `bot.name` must be non-empty string
2. `family.name` must be non-empty string
3. `family.timezone` must be valid IANA timezone (validated via `zoneinfo.ZoneInfo`)
4. `family.partners` must contain at least 1 partner
5. Each partner must have a non-empty `name`
6. Each child must have a non-empty `name` and `age` >= 0
7. `childcare.keywords` auto-generated from children names (lowercase) + caregiver keywords if not explicitly provided
8. `childcare.caregiver_mappings` auto-generated from caregiver names if not explicitly provided

## Derived Values (computed at load time)

These values are computed from the config and made available as template placeholders:

| Placeholder | Source | Example |
|-------------|--------|---------|
| `{bot_name}` | `bot.name` | "Mom Bot" |
| `{family_name}` | `family.name` | "The Belk Family" |
| `{partner1_name}` | `family.partners[0].name` | "Jason" |
| `{partner2_name}` | `family.partners[1].name` | "Erin" |
| `{partner1_work}` | `family.partners[0].work` | "works from home at Cisco" |
| `{partner2_work}` | `family.partners[1].work` | "stays at home with the kids" |
| `{children_summary}` | Generated from children list | "Vienna (daughter, age 5), Zoey (daughter, age 3)" |
| `{child1_name}` | First child name or "" | "Vienna" |
| `{child2_name}` | Second child name or "" | "Zoey" |
| `{grocery_store}` | `preferences.grocery_store` | "Whole Foods" |
| `{recipe_source}` | `preferences.recipe_source` | "Downshiftology" |
| `{location}` | `family.location` | "Reno, NV" |
| `{timezone}` | `family.timezone` | "America/Los_Angeles" |
| `{welcome_message}` | `bot.welcome_message` or auto | "Welcome to Mom Bot! ..." |

## Integration Status Entity (runtime, not persisted)

Returned by the enhanced health check endpoint:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Integration identifier (e.g., "whatsapp", "notion") |
| `required` | bool | Whether this integration is required for operation |
| `configured` | bool | Whether credentials/config exist |
| `connected` | bool | Whether a live connectivity test passed |
| `error` | string | null | Error message if connectivity test failed |

## Example Config: Jason & Erin (Current Family)

```yaml
bot:
  name: "Mom Bot"

family:
  name: "The Belk Family"
  timezone: "America/Los_Angeles"
  location: "Reno, NV"

  partners:
    - name: "Jason"
      role: "partner"
      work: "works from home at Cisco"
      has_work_calendar: true
    - name: "Erin"
      role: "partner"
      work: "stays at home with the kids"

  children:
    - name: "Vienna"
      age: 5
      details: "kindergarten at Roy Gomm, M-F"
    - name: "Zoey"
      age: 3

  caregivers:
    - name: "Sandy"
      role: "grandma"
      keywords: ["sandy", "grandma"]

preferences:
  grocery_store: "Whole Foods"
  recipe_source: "Downshiftology"

calendar:
  event_mappings:
    "BSF": "Erin"
    "Gymnastics": "Vienna"
    "Church": "Family"
    "Nature class": "Vienna"

childcare:
  keywords: ["zoey", "sandy", "preschool", "milestones", "grandma"]
  caregiver_mappings:
    "sandy": "Sandy"
    "milestones": "preschool"
```

## Example Config: Different Family (No Kids)

```yaml
bot:
  name: "Home Helper"

family:
  name: "The Martinez Family"
  timezone: "America/New_York"
  location: "Austin, TX"

  partners:
    - name: "Carlos"
      role: "partner"
      work: "software engineer at Google"
      has_work_calendar: true
    - name: "Maria"
      role: "partner"
      work: "freelance designer"
      has_work_calendar: false

preferences:
  grocery_store: "H-E-B"
```

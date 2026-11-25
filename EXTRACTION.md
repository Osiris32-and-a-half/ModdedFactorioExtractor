# Extraction JSON structure

This document describes the JSON files written by
[`archipelago-extractor/control.lua`](./archipelago-extractor/control.lua) when
`/ap-get-info-dump` runs. Except for `fluids.json`, the files contain JSON
objects keyed by prototype name or mod name.

| File | Top-level structure | Contents |
| --- | --- | --- |
| `autoplace.json` | Object keyed by autoplace-control name | Each value has `richness` (boolean), `can_be_disabled` (boolean), and `category` (string). Only visible controls are included. |
| `entityToItem.json` | Object keyed by entity name | Each value is the item name that places the entity, when the two names differ. |
| `extractorInfo.json` | Object | `factorio_version` is a string; `extraction_version` is a number. |
| `fluids.json` | Array of strings | Fluid prototype names. Parameterized fluids are omitted. |
| `generators.json` | Object keyed by offshore-pump entity name | Each value is the name of the fluid filtered by that pump. |
| `items.json` | Object keyed by item name | Each value is its stack size (number). Hidden, parameterized, spawnable, and cursor-only items are omitted. |
| `machines.json` | Object keyed by entity name | Each value is an object mapping supported crafting or resource categories to `true`. Unfiltered offshore pumps use the `offshore-pump` category. |
| `modSettings.json` | Object keyed by mod name | Each value maps startup setting names to objects containing `type` (string) and `value` (the setting's value). Mods without startup settings have an empty object. |
| `modVersions.json` | Object keyed by mod name | Each value is the active mod's version string. |
| `recipes.json` | Object keyed by recipe name | Each value has `energy` (number), `categories` (array of strings), `ingredients` (object mapping ingredient names to amounts), and `products` (object mapping product names to expected amounts). |
| `resources.json` | Object keyed by resource entity name | Each value has `minable` and `infinite` (booleans), `category` (string), `mining_time` (number), and `products` (object mapping product names to expected amounts). `infinite_depletion`, `required_fluid`, and `fluid_amount` are included when applicable. |
| `specialTiles.json` | Object keyed by tile name | Each value has `fluid` (string), identifying the fluid associated with that visible tile. Data is not split by planet. |
| `techs.json` | Object keyed by technology name | Each value has `unlocks` and `requires` (arrays of names), `infinite` (boolean), and optionally `modifiers` (array of effect type strings). |

## Collection details

- Technologies and recipes are included only when enabled; parameterized
  recipes are excluded. Technology `unlocks` lists recipe names, while
  `requires` lists prerequisite technology names. Other technology effects
  are represented by their effect type in `modifiers`.
- Recipe and resource product amounts represent expected quantities. A
  probability is multiplied by the product amount; a ranged amount uses the
  midpoint of its range. Products with the same name are combined.
- Machines include visible entities with crafting categories and mining
  drills with resource categories. Filtered offshore pumps are recorded in
  `generators.json` instead, mapped to their filtered fluid.
- `entityToItem.json` is derived from retained items whose placed entity has a
  different name.
- Mod settings and versions omit `archipelago-extractor`,
  `modded-archipelago-extractor`, `base`, `helmod`, `creative-mod`,
  `EditorExtensions`, and `RecipeBook`. Only startup settings are exported.
  The extractor reports an error if an Archipelago session mod is loaded.

The command writes these files to Factorio's `script-output/Extractor/`
directory, replacing existing files with the same names. The helper runner
documented in [`README.md`](./README.md) can launch Factorio and invoke the
command over RCON.
